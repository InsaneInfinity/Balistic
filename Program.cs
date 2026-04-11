using System;
using System.IO;
using System.Threading;
using StackExchange.Redis;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Balistic
{
    class Program
    {
        const string LOG_FILE      = "balistic_log.txt";
        const string STREAM_KEY    = "ballistics:stream";
        const string CONSUMER_GROUP = "processors";
        const string CONSUMER_NAME = "proc-1";

        static IDatabase db;

        static void Main()
        {
            try
            {
                var mux = ConnectionMultiplexer.Connect("localhost:6379");
                db = mux.GetDatabase();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[BŁĄD] Redis: {ex.Message}");
                Console.ReadLine();
                return;
            }

            try { db.StreamCreateConsumerGroup(STREAM_KEY, CONSUMER_GROUP, "0", createStream: true); }
            catch (RedisServerException ex) when (ex.Message.Contains("BUSYGROUP")) { }
            catch (Exception ex) { Log($"[WARN] Grupa: {ex.Message}"); }

            Console.Clear();
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("#############################################");
            Console.WriteLine("#      PROCESOR BALISTYCZNY: BALISTIC V5    #");
            Console.WriteLine("#############################################");
            Console.WriteLine("Oczekiwanie na dane strzeleckie...\n");
            Console.ResetColor();

            // ============================================================
            // HEARTBEAT — pinguje Redis co 2s
            // Flask /health sprawdza czy ostatni ping był < 5s temu
            // ============================================================
            var heartbeatThread = new Thread(() =>
            {
                while (true)
                {
                    try
                    {
                        db.StringSet(
                            "ballistics:processor:heartbeat",
                            DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(),
                            TimeSpan.FromSeconds(10) // auto-expire po 10s
                        );
                    }
                    catch { /* Redis chwilowo niedostepny */ }
                    Thread.Sleep(2000); // ping co 2s
                }
            });
            heartbeatThread.IsBackground = true;
            heartbeatThread.Name = "HeartbeatThread";
            heartbeatThread.Start();
            Console.WriteLine("[OK] Heartbeat aktywny (co 2s → Redis)\n");

            while (true)
            {
                try
                {
                    var entries = db.StreamReadGroup(STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME, count: 1, noAck: false);
                    if (entries != null && entries.Length > 0)
                    {
                        foreach (var entry in entries)
                        {
                            string entryId = entry.Id;
                            string rawJson = entry["data"];
                            try
                            {
                                ProcessShot(rawJson);
                                db.StreamAcknowledge(STREAM_KEY, CONSUMER_GROUP, entryId);
                            }
                            catch (JsonException ex)
                            {
                                Log($"[BŁĄD JSON] {entryId}: {ex.Message}");
                                db.StreamAcknowledge(STREAM_KEY, CONSUMER_GROUP, entryId);
                            }
                            catch (Exception ex)
                            {
                                Log($"[BŁĄD] {entryId}: {ex.Message}");
                                // brak ACK = retry
                            }
                        }
                    }
                }
                catch (RedisConnectionException ex)
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine($"[REDIS] {ex.Message} — retry za 2s...");
                    Console.ResetColor();
                    Thread.Sleep(2000);
                }
                catch (Exception ex) { Log($"[KRYTYCZNY] {ex.GetType().Name}: {ex.Message}"); }

                Thread.Sleep(500);
            }
        }

        static void ProcessShot(string rawJson)
        {
            JObject d = JObject.Parse(rawJson);

            string shotId   = d["shot_id"]?.ToString() ?? "";
            double dist     = (double)d["dist"];
            double v0       = (double)d["v0"];
            double mass     = (double)d["waga"];
            double cd       = d["cd"]  != null ? (double)d["cd"]  : 0.40;
            double area     = d["area"]!= null ? (double)d["area"]: 0.015;
            int    cep      = d["cep"] != null ? (int)d["cep"]    : 100;
            double rho      = d["dens"]!= null ? (double)d["dens"]: 1.225;
            double windV    = d["wiatr_v"]  != null ? (double)d["wiatr_v"]  : 0.0;
            double windDir  = d["wiatr_dir"]!= null ? (double)d["wiatr_dir"]: 0.0;
            double ts       = d["ts"]  != null ? (double)d["ts"]  : 0.0;

            // Azymut geodezyjny
            double lat1 = DegToRad((double)d["m_lat"]);
            double lat2 = DegToRad((double)d["t_lat"]);
            double dLon = DegToRad((double)d["t_lon"] - (double)d["m_lon"]);
            double y    = Math.Sin(dLon) * Math.Cos(lat2);
            double x    = Math.Cos(lat1) * Math.Sin(lat2) - Math.Sin(lat1) * Math.Cos(lat2) * Math.Cos(dLon);
            double az   = (RadToDeg(Math.Atan2(y, x)) + 360) % 360;

            string trajectoryType = d["trajectory"]?.ToString() ?? "artillery";

            // Kąt podniesienia
            double angle = 0;
            if (trajectoryType != "ballistic_missile" && trajectoryType != "cruise")
            {
                angle = FindElevationAngle(dist, v0, mass, cd, area, rho, trajectoryType);
                if (double.IsNaN(angle))
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine($"[!] POZA ZASIĘGIEM: {dist/1000:F2} km dla {d["nazwa"]}");
                    Console.ResetColor();
                    Log($"[ZASIĘG] {d["pojazd"]} | {d["nazwa"]} | D:{dist:F0}m");
                    return;
                }
            }

            double tof;
            double apogee = 0;
            double cruiseAlt = 0; // wysokość przelotowa [m] dla cruise missiles

            if (trajectoryType == "cruise")
            {
                angle     = 0.1;
                apogee    = 0;
                // Samoloty lecą na 10000m, rakiety manewrujące na 100m
                string[] aircraft = {"F35-B61","B2-B61","B2-B83","B21-B61","F15-B61",
                                     "Tornado-B61","Tu160-nuke","Tu95-nuke","H6K-nuke"};
                string nazwaAmmo = d["nazwa"]?.ToString() ?? "";
                cruiseAlt = System.Array.Exists(aircraft, a => a == nazwaAmmo) ? 10000.0 : 100.0;
                tof       = dist / v0;
            }
            else if (trajectoryType == "ballistic_missile")
            {
                // Wzory empiryczne dla rakiet balistycznych
                // Kąt: 45° dla max zasięgu, rośnie dla krótszych dystansów
                double maxRangeMissile = v0 * v0 / 9.81; // uproszczony max zasięg w próżni
                double ratio = Math.Min(dist / maxRangeMissile, 1.0);
                angle = 45.0 + 20.0 * (1.0 - ratio); // 45°-65°

                // Apogeum: ~1/4 zasięgu dla ICBM, ~1/6 dla MRBM
                double apogeeRatio = dist > 5_000_000 ? 0.20 :   // ICBM >5000km
                                     dist > 2_000_000 ? 0.15 :   // IRBM >2000km
                                     dist > 500_000   ? 0.10 :   // MRBM >500km
                                                        0.06;     // SRBM
                apogee = dist * apogeeRatio;

                // Czas lotu: realny dla ICBM ~25-35 min na 9000km
                // v_avg pozioma ≈ dist / tof → tof = dist / v_avg
                // Dla Sarmat (v0=1500 m/s): tof ≈ dist / 5000 m/s (śr. prędkość)
                double avgSpeedH = dist > 5_000_000 ? 5000.0 :   // ICBM
                                   dist > 2_000_000 ? 3500.0 :   // IRBM
                                   dist > 500_000   ? 2500.0 :   // MRBM
                                                      1500.0;     // SRBM
                tof = dist / avgSpeedH;
            }
            else if (trajectoryType == "artillery")
            {
                // Realny czas lotu artylerii 155mm:
                // ~5km → ~20s, ~10km → ~35s, ~20km → ~55s
                // Wzór empiryczny: t ≈ dist / (v0 * cos(angle)) * korekcja
                double angleRad = DegToRad(angle);
                double tof_base = dist / (v0 * Math.Cos(angleRad));
                // Korekcja na tor balistyczny (pocisk leci po łuku, nie prosto)
                tof = tof_base * (1.0 + 0.4 * Math.Sin(angleRad));
            }
            else
            {
                tof = SimulateFlightTime(angle, v0, mass, cd, area, rho);
            }
            double windPerpComp = windV * Math.Sin(DegToRad(windDir - az));
            double driftWind    = windPerpComp * tof;

            // === EFEKT CORIOLISA ===
            const double OMEGA = 7.2921e-5;
            double lat_rad  = DegToRad((double)d["m_lat"]);
            double driftCor;
            if (trajectoryType == "ballistic_missile")
            {
                // Coriolis dla rakiet balistycznych
                // Wzór: d = Ω × sin(φ) × v_avg × tof² / 2
                // v_avg = dist / tof (średnia prędkość pozioma)
                // Dla MRBM 1500km ~30°N: ~1500-3000m odchylenia
                double v_avg = dist / tof;
                driftCor = OMEGA * Math.Sin(lat_rad) * v_avg * tof * tof / 2.0;
                // Ogranicz do realistycznych wartości
                // ICBM max ~3km, MRBM max ~2km, SRBM max ~500m
                double maxCor = dist > 5_000_000 ? 3000.0 :
                                dist > 2_000_000 ? 2000.0 :
                                dist > 500_000   ? 1000.0 :
                                                    300.0;
                driftCor = Math.Sign(driftCor) * Math.Min(Math.Abs(driftCor), maxCor);
            }
            else if (trajectoryType == "cruise")
            {
                // Cruise missile — Coriolis bardzo mały (rakieta manewruje, kompensuje)
                // Realnie ~100-500m na 2500km
                double distKm = dist / 1000.0;
                driftCor = OMEGA * Math.Sin(lat_rad) * distKm * 50.0;
                // Max 500m dla cruise missiles
                driftCor = Math.Sign(driftCor) * Math.Min(Math.Abs(driftCor), 500.0);
            }
            else
            {
                double v_avg = dist / tof;
                driftCor = OMEGA * Math.Sin(lat_rad) * v_avg * tof * tof / 2.0;
            }

            double drift = driftWind + driftCor;
            double ek    = 0.5 * mass * v0 * v0 / 1_000_000;

            // Wyświetl w konsoli
            Console.Clear();
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("=============================================");
            Console.WriteLine($"  JEDNOSTKA : {d["pojazd"]}");
            Console.WriteLine($"  POCISK    : {d["nazwa"]}");
            Console.WriteLine("=============================================");
            Console.ForegroundColor = ConsoleColor.White;
            Console.WriteLine($"  DYSTANS   : {dist:F0} m  ({dist/1000:F2} km)");
            Console.WriteLine($"  AZYMUT    : {az:F1}°");
            if (trajectoryType == "cruise")
                Console.WriteLine($"  TYP TORU  : MANEWRUJĄCA (płaski, ~{cruiseAlt:F0}m)");
            else
                Console.WriteLine($"  KĄT LUFY  : {angle:F2}°");
            if (trajectoryType == "cruise")
                Console.WriteLine($"  WYSOKOŚĆ  : ~{cruiseAlt:F0} m (tor płaski)");
            else if (apogee > 0)
                Console.WriteLine($"  APOGEUM   : {apogee/1000:F1} km");
            Console.WriteLine($"  CZAS LOTU : {tof:F1} s  ({tof/60:F1} min)");
            Console.WriteLine($"  DRYFT     : {drift:F1} m  ({(drift >= 0 ? "prawo" : "lewo")})");
            Console.WriteLine($"  WIATR:     : {driftWind:F1} m  |  CORIOLIS: {driftCor:F2} m");
            Console.WriteLine($"  ENERGIA   : {ek:F2} MJ  |  CEP: {cep} m");
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine($"  WIATR     : {windV:F1} m/s @ {windDir:F0}°");
            Console.WriteLine($"  GĘSTOŚĆ   : {rho:F4} kg/m³");
            Console.WriteLine("=============================================");
            Console.ResetColor();

            // Zapisz wynik z powrotem do Redis
            if (!string.IsNullOrEmpty(shotId))
            {
                var blastObj = d["blast"] as JObject ?? new JObject {
                    ["total"] = 0, ["heavy"] = 0, ["light"] = 0, ["hazard"] = 0, ["type"] = "HE"
                };
                var result = new JObject
                {
                    ["shot_id"]      = shotId,
                    ["pojazd"]       = d["pojazd"]?.ToString(),
                    ["nazwa"]        = d["nazwa"]?.ToString(),
                    ["dist"]         = dist,
                    ["az"]           = az,
                    ["angle"]        = angle,
                    ["tof"]          = tof,
                    ["apogee"]       = apogee,
                    ["cruise_alt"]   = cruiseAlt,
                    ["trajectory"]   = trajectoryType,
                    ["drift"]        = drift,
                    ["drift_wind"]   = driftWind,
                    ["drift_cor"]    = driftCor,
                    ["ek"]           = ek,
                    ["cep"]          = cep,
                    ["blast"]        = blastObj,
                    ["wiatr_v"]      = windV,
                    ["wiatr_dir"]    = windDir,
                    ["dens"]         = rho,
                    ["ts"]           = ts
                };
                db.StringSet($"ballistics:result:{shotId}", result.ToString(), TimeSpan.FromSeconds(120));
            }

            string logLine = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {d["pojazd"]} | {d["nazwa"]} | " +
                             $"D:{dist:F0}m | Az:{az:F1}° | Tor:{trajectoryType} | Lot:{tof:F1}s | Dryft:{drift:F1}m";
            Log(logLine);
        }

        // ===================================================
        // SYMULACJA RAKIETY BALISTYCZNEJ
        // - Atmosfera warstwowa ISA (International Standard Atmosphere)
        // - Grawitacja zmienna z wysokością
        // - Zakrzywienie Ziemi
        // Zwraca: (czas_lotu, apogeum, kąt_startowy)
        // ===================================================
        static (double tof, double apogee, double angle) SimulateMissile(
            double targetDist, double v0, double mass, double cd, double area)
        {
            const double R_EARTH = 6371000.0;
            const double G0      = 9.81;
            double bestAngle = 45.0;
            double bestTof   = 0;
            double bestApogee = 0;
            double bestError = double.MaxValue;

            // Szukamy kąta startowego przez bisekcję
            double lo = 20.0, hi = 75.0;
            for (int iter = 0; iter < 60; iter++)
            {
                double mid = (lo + hi) / 2.0;
                var (range, tof, apogee) = SimulateMissileTrajectory(mid, v0, mass, cd, area);
                double error = Math.Abs(range - targetDist);
                if (error < bestError)
                {
                    bestError  = error;
                    bestAngle  = mid;
                    bestTof    = tof;
                    bestApogee = apogee;
                }
                if (error < 500) break; // tolerancja 500m dla rakiet
                if (range < targetDist) lo = mid;
                else                    hi = mid;
            }
            return (bestTof, bestApogee, bestAngle);
        }

        static (double range, double tof, double apogee) SimulateMissileTrajectory(
            double angleDeg, double v0, double mass, double cd, double area, double dt = 1.0)
        {
            const double R_EARTH = 6371000.0;
            double angleRad = DegToRad(angleDeg);
            double vx = v0 * Math.Cos(angleRad);
            double vy = v0 * Math.Sin(angleRad);
            double px = 0, py = 0;
            double t = 0, apogee = 0;

            for (int s = 0; s < 100_000; s++)
            {
                double h = py; // wysokość nad ziemią
                if (h < 0 && s > 10) break;

                // Grawitacja zmienna z wysokością
                double g = 9.81 * Math.Pow(R_EARTH / (R_EARTH + Math.Max(h, 0)), 2);

                // Gęstość powietrza ISA (atmosfera warstwowa)
                double rho = AirDensityISA(Math.Max(h, 0));

                double v    = Math.Sqrt(vx * vx + vy * vy);
                double drag = (v > 0) ? 0.5 * cd * rho * area * v * v : 0;

                double ax = -(drag / mass) * (vx / v);
                double ay = -g - (drag / mass) * (vy / v);

                vx += ax * dt;
                vy += ay * dt;
                px += vx * dt;
                py += vy * dt;
                t  += dt;

                if (py > apogee) apogee = py;
            }
            return (px, t, apogee);
        }

        // Gęstość powietrza wg ISA [kg/m³] w funkcji wysokości [m]
        static double AirDensityISA(double h)
        {
            if (h < 11000)      // Troposfera
                return 1.225 * Math.Pow(1 - 2.2558e-5 * h, 4.2561);
            else if (h < 25000) // Dolna stratosfera (izotermiczna)
                return 0.3639 * Math.Exp(-1.5788e-4 * (h - 11000));
            else if (h < 50000) // Górna stratosfera
                return 0.0880 * Math.Pow(1 + 1.6e-3 * (h - 25000) / 216.65, -35.16);
            else                // Mezosfera i wyżej — praktycznie próżnia
                return 0.001;
        }

        static double FindElevationAngle(double targetDist, double v0, double mass, double cd, double area, double rho, string trajectoryType, double tolerance = 1.0)
        {
            if (trajectoryType == "artillery")
            {
                double maxRange45 = SimulateRange(45.0, v0, mass, cd, area, rho);
                if (targetDist > maxRange45) return double.NaN;

                // Wzór empiryczny: kąt artyleryjski rośnie liniowo od 45° (max zasięg)
                // do 70° (min zasięg ~30% max zasięgu)
                // Dla dystansu d: angle = 45 + 25 * (1 - d/maxRange45)
                // Daje: przy d=maxRange → 45°, przy d=0 → 70°
                double ratio = targetDist / maxRange45;  // 0..1
                double empiricalAngle = 45.0 + 25.0 * (1.0 - ratio);
                return empiricalAngle;
            }
            else
            {
                // Tor płaski: KE / HEAT — zakres 0.1°-45°
                double maxRange = SimulateRange(45.0, v0, mass, cd, area, rho);
                if (targetDist > maxRange) return double.NaN;

                double minRange = SimulateRange(0.1, v0, mass, cd, area, rho);
                if (targetDist < minRange) return 0.1;

                double lo = 0.1, hi = 45.0;
                for (int i = 0; i < 100; i++)
                {
                    double mid   = (lo + hi) / 2.0;
                    double range = SimulateRange(mid, v0, mass, cd, area, rho);
                    if (Math.Abs(range - targetDist) < tolerance) return mid;
                    if (range < targetDist) lo = mid;
                    else                    hi = mid;
                }
                return (lo + hi) / 2.0;
            }
        }

        static double SimulateRange(double angleDeg, double v0, double mass, double cd, double area, double rho, double dt = 0.01)
        {
            double g = 9.81, angleRad = DegToRad(angleDeg);
            double vx = v0 * Math.Cos(angleRad), vy = v0 * Math.Sin(angleRad);
            double px = 0, py = 0;
            for (int s = 0; s < 200_000; s++)
            {
                double v = Math.Sqrt(vx*vx + vy*vy);
                double drag = 0.5 * cd * rho * area * v * v;
                vx += -(drag/mass)*(vx/v)*dt;
                vy += (-9.81 - (drag/mass)*(vy/v))*dt;
                px += vx*dt; py += vy*dt;
                if (py < 0 && s > 10) return px;
            }
            return px;
        }

        static double SimulateFlightTime(double angleDeg, double v0, double mass, double cd, double area, double rho, double dt = 0.01)
        {
            double angleRad = DegToRad(angleDeg);
            double vx = v0 * Math.Cos(angleRad), vy = v0 * Math.Sin(angleRad);
            double py = 0, t = 0;
            for (int s = 0; s < 200_000; s++)
            {
                double v = Math.Sqrt(vx*vx + vy*vy);
                double drag = 0.5 * cd * rho * area * v * v;
                vx += -(drag/mass)*(vx/v)*dt;
                vy += (-9.81 - (drag/mass)*(vy/v))*dt;
                py += vy*dt; t += dt;
                if (py < 0 && s > 10) return t;
            }
            return t;
        }

        static double DegToRad(double d) => d * Math.PI / 180.0;
        static double RadToDeg(double r) => r * 180.0 / Math.PI;

        static void Log(string msg)
        {
            try { File.AppendAllText(LOG_FILE, msg + Environment.NewLine); }
            catch (IOException ex) { Console.WriteLine($"[WARN LOG] {ex.Message}"); }
        }
    }
}
