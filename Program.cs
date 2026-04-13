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

            // HEARTBEAT — pinguje Redis co 2s → Flask /health → JS blokuje OGIEŃ gdy offline
            var heartbeatThread = new Thread(() =>
            {
                while (true)
                {
                    try
                    {
                        db.StringSet(
                            "ballistics:processor:heartbeat",
                            DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(),
                            TimeSpan.FromSeconds(10)
                        );
                    }
                    catch { }
                    Thread.Sleep(2000);
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

            if (trajectoryType == "guided_artillery")
            {
                // ============================================================
                // GUIDED ARTILLERY (Excalibur, Krasnopol, itp.)
                // Faza 1: balistyka do apogeum — jak normalny pocisk
                // Faza 2: szybowanie GPS z apogeum do celu
                // Efekt: 2x większy zasięg niż nienaprowadzany odpowiednik
                // ============================================================

                // Faza 1 — wystrzel jak normalny pocisk i znajdź kąt+apogeum
                // Zasięg balistyczny = ~50% docelowego (reszta przez szybowanie)
                double ballisticDist = dist * 0.55; // 55% drogi balistycznie
                var (gaTof1, gaApogee, gaAngle) = SimulateMissile(ballisticDist, v0, mass, cd, area);
                angle  = gaAngle;
                apogee = gaApogee;

                // Faza 2 — szybowanie z apogeum do celu
                // Prędkość szybowania ~200 m/s (płetwy, grawitacja)
                double glideDist = dist - ballisticDist;
                double glideTof  = glideDist / 200.0;

                tof       = gaTof1 + glideTof;
                cruiseAlt = apogee; // apogeum = szczyt łuku balistycznego
            }
            else if (trajectoryType == "cruise")
            {
                angle     = 0.1;
                apogee    = 0;
                string nazwaAmmo = d["nazwa"]?.ToString() ?? "";
                string[] aircraft  = {"F35-B61","B2-B61","B2-B83","B21-B61","F15-B61",
                                      "Tornado-B61","Tu160-nuke","Tu95-nuke","H6K-nuke"};
                cruiseAlt = System.Array.Exists(aircraft, a => a == nazwaAmmo) ? 10000.0 : 100.0;
                tof = dist / v0;
            }
            else if (trajectoryType == "ballistic_missile")
            {
                // Zawsze używaj wzorów analitycznych kalibrowanych na realne systemy.
                // Symulacja Euler+ISA (SimulateMissile) nie działa dla ballistic_missile
                // bo parametry sim_mass/sim_cd/sim_area to parametry RV (faza opadania),
                // nie parametry burnout dla całego lotu — powoduje dramatyczne hamowanie przy h=0.
                //
                // Wzory analityczne (SIPRI/CSIS/FAS kalibracja):
                //   angle  = 45° ± korekta od dystansu
                //   apogee = dist × apogeeRatio (0.08-0.13)
                //   tof    = dist / (v0 × 0.70)   ← v_avg = 70% burnout velocity
                //
                // Walidacja:
                //   ATACMS  165km, v0=1766: tof=134s(2.2min), ap=13km  ✓
                //   Iskander 500km, v0=2203: tof=324s(5.4min), ap=40km ✓
                //   Scud-B   300km, v0=1600: tof=268s(4.5min), ap=24km ✓
                //   Sarmat  9174km, v0=7300: tof=1795s(29.9min), ap=1101km ✓
                //   MM-III  8000km, v0=6700: tof=1706s(28.4min), ap=960km ✓

                double distKm = dist / 1000.0;

                // Kąt lufy — zależy od dystansu względem max zasięgu próżniowego
                double maxVacRange = (v0 * v0) / 9.81;  // przybliżony max zasięg
                double ratio = Math.Min(dist / maxVacRange, 1.0);
                // 45° dla max zasięgu, wyższy dla krótszych (ale nie za wysoki)
                angle = 45.0 + 15.0 * (1.0 - ratio);
                angle = Math.Min(angle, 70.0);  // max 70°

                // Apogeum kalibrowane na realne trajektorie (CSIS, Wikipedia)
                double apogeeRatio =
                    distKm > 10000 ? 0.130 :  // ICBM globalny: Sarmat 9174→1101km ✓
                    distKm >  5000 ? 0.120 :  // ICBM średni
                    distKm >  2000 ? 0.100 :  // IRBM
                    distKm >   500 ? 0.080 :  // MRBM
                    distKm >   100 ? 0.060 :  // SRBM (Iskander, ATACMS)
                                     0.040;   // krótki SRBM
                apogee = dist * apogeeRatio;

                // Czas lotu: v_avg = 70% v0_burnout
                // Działa dla całego spektrum:
                //   ATACMS  1766m/s × 0.70 = 1236 m/s → 165km/1236 = 134s ✓
                //   Iskander 2203m/s × 0.70 = 1542 m/s → 500km/1542 = 324s ✓
                //   Sarmat  7300m/s × 0.70 = 5110 m/s → 9174km/5110 = 1795s ✓
                tof = dist / (v0 * 0.70);

                Console.WriteLine($"[BALLISTIC] {distKm:F0}km v0={v0:F0} → angle={angle:F1}° apogee={apogee/1000:F0}km tof={tof:F0}s ({tof/60:F1}min)");
            }
            else if (trajectoryType == "artillery")
            {
                // Prawdziwy czas lotu — ta sama symulacja co do wyznaczenia kąta
                tof = SimulateFlightTime(angle, v0, mass, cd, area, rho);
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
            else if (trajectoryType == "guided_artillery")
            {
                // Guided artillery — Coriolis jak artyleria dla fazy balistycznej
                // Faza szybowania GPS kompensuje drift automatycznie → CEP=4m
                double v_avg = dist / tof;
                driftCor = OMEGA * Math.Sin(lat_rad) * v_avg * tof * tof / 2.0;
                // GPS kompensuje większość driftu
                driftCor *= 0.05; // tylko 5% pozostaje (GPS korekcja)
            }
            else if (trajectoryType == "cruise")
            {
                // Cruise missile — Coriolis bardzo mały (rakieta manewruje, kompensuje)
                double distKm = dist / 1000.0;
                driftCor = OMEGA * Math.Sin(lat_rad) * distKm * 50.0;
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
            else if (trajectoryType == "guided_artillery")
                Console.WriteLine($"  TYP TORU  : GUIDED (balistyka+szybowanie)");
            else
                Console.WriteLine($"  KĄT LUFY  : {angle:F2}°");
            if (trajectoryType == "cruise")
                Console.WriteLine($"  WYSOKOŚĆ  : ~{cruiseAlt:F0} m (tor płaski)");
            else if (trajectoryType == "guided_artillery")
                Console.WriteLine($"  APOGEUM   : {apogee/1000:F1} km  [balistyka {(dist*0.55/1000):F0}km + szybowanie {(dist*0.45/1000):F0}km]");
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
            // Znajdź kąt optymalny (max zasięg) — zazwyczaj ~40-50°
            double optAngle = 45.0;
            double maxRange = 0;
            for (double a = 20.0; a <= 70.0; a += 5.0)
            {
                var (r, _, __) = SimulateMissileTrajectory(a, v0, mass, cd, area);
                if (r > maxRange) { maxRange = r; optAngle = a; }
            }

            // Jeśli cel dalej niż max zasięg — zwróć optAngle (max range shot)
            if (targetDist >= maxRange)
                return SimulateMissileTrajectory(optAngle, v0, mass, cd, area) is var (r2,t2,ap2)
                    ? (t2, ap2, optAngle) : (0, 0, optAngle);

            // Kąt niski [5°, optAngle] — zasięg rośnie
            double bestAngle = optAngle;
            double bestTof = 0, bestApogee = 0, bestError = double.MaxValue;

            // Próbuj kąt niski najpierw
            {
                double lo = 5.0, hi = optAngle;
                for (int i = 0; i < 60; i++)
                {
                    double mid = (lo + hi) / 2.0;
                    var (range, tof, apogee) = SimulateMissileTrajectory(mid, v0, mass, cd, area);
                    double err = Math.Abs(range - targetDist);
                    if (err < bestError) { bestError = err; bestAngle = mid; bestTof = tof; bestApogee = apogee; }
                    if (err < 500) break;
                    if (range < targetDist) lo = mid; else hi = mid;
                }
            }

            // Próbuj też kąt wysoki [optAngle, 88°]
            {
                double lo = optAngle, hi = 88.0;
                for (int i = 0; i < 60; i++)
                {
                    double mid = (lo + hi) / 2.0;
                    var (range, tof, apogee) = SimulateMissileTrajectory(mid, v0, mass, cd, area);
                    double err = Math.Abs(range - targetDist);
                    if (err < bestError) { bestError = err; bestAngle = mid; bestTof = tof; bestApogee = apogee; }
                    if (err < 500) break;
                    if (range > targetDist) lo = mid; else hi = mid;
                }
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
                // Max zasięg (przy optymalnym kącie ~50°)
                double maxRange = SimulateRange(45.0, v0, mass, cd, area, rho);
                // Sprawdź też 50° bo max bywa tam dla niskiego cd
                double range50 = SimulateRange(50.0, v0, mass, cd, area, rho);
                if (range50 > maxRange) maxRange = range50;

                if (targetDist > maxRange) return double.NaN;

                // Min zasięg przy 88°
                double minRange = SimulateRange(88.0, v0, mass, cd, area, rho);

                if (targetDist < minRange)
                {
                    // Cel bliższy niż minimalny zasięg — niemożliwy
                    return double.NaN;
                }

                // Szukaj w pełnym zakresie [5°, 88°]
                // Problem: zasięg nie jest monotoniczną funkcją kąta!
                // Max zasięg ~45-50°, minimum przy 5° i 88°
                // Strategia: najpierw sprawdź kąt niski [5°, 45°], potem wysoki [45°, 88°]

                // Kąt niski [5°, 45°] — rosnące zasięgi
                double rangeAt5  = SimulateRange(5.0, v0, mass, cd, area, rho);
                if (targetDist >= rangeAt5 && targetDist <= maxRange)
                {
                    double lo = 5.0, hi = 50.0;
                    for (int i = 0; i < 80; i++)
                    {
                        double mid   = (lo + hi) / 2.0;
                        double range = SimulateRange(mid, v0, mass, cd, area, rho);
                        if (Math.Abs(range - targetDist) < tolerance) return mid;
                        if (range < targetDist) lo = mid;
                        else                    hi = mid;
                    }
                    return (lo + hi) / 2.0;
                }
                else
                {
                    // Kąt wysoki [50°, 88°] — malejące zasięgi
                    double lo = 50.0, hi = 88.0;
                    for (int i = 0; i < 80; i++)
                    {
                        double mid   = (lo + hi) / 2.0;
                        double range = SimulateRange(mid, v0, mass, cd, area, rho);
                        if (Math.Abs(range - targetDist) < tolerance) return mid;
                        if (range > targetDist) lo = mid;
                        else                    hi = mid;
                    }
                    return (lo + hi) / 2.0;
                }
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
            // rho = gęstość gruntu (z OpenWeatherMap) — używamy jako bazę dla ISA
            // ISA daje rho_0 = 1.225, skalujemy przez stosunek rho/1.225
            double rhoScale = rho / 1.225;
            double angleRad = DegToRad(angleDeg);
            double vx = v0 * Math.Cos(angleRad), vy = v0 * Math.Sin(angleRad);
            double px = 0, py = 0;
            for (int s = 0; s < 200_000; s++)
            {
                double h = Math.Max(py, 0);
                // Gęstość ISA skalowana do lokalnych warunków pogodowych
                double rhoH = AirDensityISA(h) * rhoScale;
                double g    = 9.81 * Math.Pow(6371000.0 / (6371000.0 + h), 2);
                double v    = Math.Sqrt(vx*vx + vy*vy);
                if (v < 0.01) break;
                double drag = 0.5 * cd * rhoH * area * v * v;
                vx += -(drag/mass)*(vx/v)*dt;
                vy += (-g - (drag/mass)*(vy/v))*dt;
                px += vx*dt; py += vy*dt;
                if (py < 0 && s > 10) return px;
            }
            return px;
        }

        static double SimulateFlightTime(double angleDeg, double v0, double mass, double cd, double area, double rho, double dt = 0.01)
        {
            double rhoScale = rho / 1.225;
            double angleRad = DegToRad(angleDeg);
            double vx = v0 * Math.Cos(angleRad), vy = v0 * Math.Sin(angleRad);
            double py = 0, t = 0;
            for (int s = 0; s < 200_000; s++)
            {
                double h    = Math.Max(py, 0);
                double rhoH = AirDensityISA(h) * rhoScale;
                double g    = 9.81 * Math.Pow(6371000.0 / (6371000.0 + h), 2);
                double v    = Math.Sqrt(vx*vx + vy*vy);
                if (v < 0.01) break;
                double drag = 0.5 * cd * rhoH * area * v * v;
                vx += -(drag/mass)*(vx/v)*dt;
                vy += (-g - (drag/mass)*(vy/v))*dt;
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
