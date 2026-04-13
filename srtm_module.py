"""
SRTM Terrain Masking Module dla BALISTIC V5
Pobiera dane z srtm.kurviger.de (działa, darmowe, globalne)
Format: SRTM3, 90m rozdzielczość, pliki .hgt w ZIP
"""
import os, math, random as _rand, zipfile, io
import numpy as np
import requests

SRTM_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "srtm_cache")
os.makedirs(SRTM_CACHE_DIR, exist_ok=True)

# Cache tile'ów w pamięci (klucz = "N36W116")
_tile_cache = {}

def _tile_name(lat, lon):
    la = int(math.floor(lat))
    lo = int(math.floor(lon))
    ns = 'N' if la >= 0 else 'S'
    ew = 'E' if lo >= 0 else 'W'
    return f"{ns}{abs(la):02d}{ew}{abs(lo):03d}"

def _continent(lat, lon):
    if lat >= 0:
        if lon < -30:  return "North_America"
        if lon < 60:   return "Africa"
        return "Eurasia"
    else:
        if lon < -30:  return "South_America"
        if lon < 60:   return "Africa"
        return "Australia"

def _load_tile(lat, lon):
    """Załaduj tile SRTM z cache lub pobierz z kurviger.de"""
    name = _tile_name(lat, lon)
    if name in _tile_cache:
        return _tile_cache[name]

    # Sprawdź cache dyskowy
    npy_path = os.path.join(SRTM_CACHE_DIR, f"{name}.npy")
    if os.path.exists(npy_path):
        arr = np.load(npy_path)
        _tile_cache[name] = arr
        return arr

    # Pobierz z kurviger.de
    la_i = int(math.floor(lat))
    lo_i = int(math.floor(lon))
    cont = _continent(la_i, lo_i)

    # Próbuj kilka URL (kontynenty)
    urls = [
        f"https://srtm.kurviger.de/SRTM3/{cont}/{name}.hgt.zip",
        f"https://srtm.kurviger.de/SRTM3/Eurasia/{name}.hgt.zip",
        f"https://srtm.kurviger.de/SRTM3/North_America/{name}.hgt.zip",
        f"https://srtm.kurviger.de/SRTM3/South_America/{name}.hgt.zip",
        f"https://srtm.kurviger.de/SRTM3/Africa/{name}.hgt.zip",
        f"https://srtm.kurviger.de/SRTM3/Australia/{name}.hgt.zip",
        f"https://srtm.kurviger.de/SRTM3/Islands/{name}.hgt.zip",
    ]

    hgt_data = None
    for url in urls:
        try:
            print(f"[SRTM] Pobieranie {name} ({url.split('/')[4]})...")
            r = requests.get(url, timeout=20,
                             headers={'User-Agent': 'BalisticSim/6.0'})
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                for fname in z.namelist():
                    if fname.upper().endswith('.HGT'):
                        hgt_data = z.read(fname)
                        break
                if hgt_data:
                    print(f"[SRTM] OK — {name} ({len(hgt_data)//1024}KB)")
                    break
        except Exception as e:
            continue

    if not hgt_data:
        print(f"[SRTM] Brak danych dla {name} — fallback: 0m")
        _tile_cache[name] = None
        return None

    # Parsuj HGT (big-endian int16, 1201x1201)
    n = 1201
    arr = np.frombuffer(hgt_data, dtype='>i2').reshape((n, n)).astype(np.float32)
    arr[arr == -32768] = 0

    np.save(npy_path, arr)
    _tile_cache[name] = arr
    return arr


def get_elevation(lat, lon):
    """Zwraca wysokość [m n.p.m.]. Interpolacja bilinearna."""
    arr = _load_tile(lat, lon)
    if arr is None:
        return 0.0

    n = arr.shape[0]  # 1201
    la_i = int(math.floor(lat))
    lo_i = int(math.floor(lon))

    row_f = (1.0 - (lat - la_i)) * (n - 1)  # HGT: row 0 = north
    col_f = (lon - lo_i) * (n - 1)

    r0 = int(row_f); r1 = min(r0+1, n-1)
    c0 = int(col_f); c1 = min(c0+1, n-1)
    dr = row_f - r0;  dc = col_f - c0

    h = (arr[r0,c0]*(1-dr)*(1-dc) + arr[r0,c1]*(1-dr)*dc +
         arr[r1,c0]*dr*(1-dc)     + arr[r1,c1]*dr*dc)
    return float(h)


def terrain_shadowing_factor(lat0, lon0, elev0, azimuth_deg,
                              max_dist_m, n_samples=35):
    """Horizon scan — zwraca współczynnik 0..1 (1=brak przeszkód)."""
    az        = math.radians(azimuth_deg)
    m_per_lat = 111320.0
    m_per_lon = 111320.0 * math.cos(math.radians(lat0))
    max_hz    = -999.0
    shadow    = max_dist_m

    # Próg cienia zależy od odległości — dalsze góry muszą być wyższe żeby blokować
    # min 0.5° dla bliskich przeszkód, 0.2° dla dalekich (tarcza kulista Ziemi)
    for i in range(1, n_samples + 1):
        d     = max_dist_m * i / n_samples
        p_lat = lat0 + (d * math.cos(az)) / m_per_lat
        p_lon = lon0 + (d * math.sin(az)) / m_per_lon
        elev  = get_elevation(p_lat, p_lon)
        angle = math.degrees(math.atan2(elev - elev0, d))

        if angle > max_hz:
            max_hz = angle
        elif max_hz > 3.0 and angle < max_hz - 3.0:
            # Shadow zone — tylko przy wyraźnej przeszkodzie (>3° horyzont)
            # i znaczącym spadku za nią (>3°)
            # Zapobiega fałszywym cieniom na pagórkowatym terenie
            shadow = d
            break

    return shadow / max_dist_m


def compute_blast_radii_with_terrain(lat, lon, blast_zones,
                                      n_rays=72, n_samples=35):
    """Nieregularne polygony stref rażenia z terrain masking."""
    elev0     = get_elevation(lat, lon)
    m_per_lat = 111320.0
    m_per_lon = 111320.0 * math.cos(math.radians(lat))
    rng       = _rand.Random(int(abs(lat)*1e4 + abs(lon)*1e4))
    max_r     = max(blast_zones.get(k, 0)
                    for k in ['hazard','light','heavy','total'])
    if max_r <= 0:
        return dict(polygons={}, terrain_type='?', osm_density=0,
                    canyon=False, rays=n_rays, samples=n_samples,
                    elevation_impact=elev0)

    # Oblicz terrain factor dla każdego promienia
    factors = [
        terrain_shadowing_factor(lat, lon, elev0,
                                  360.0*i/n_rays, max_r, n_samples)
        for i in range(n_rays)
    ]

    # Generuj polygony
    polygons = {}
    for key in ['hazard','light','heavy','total']:
        radius = blast_zones.get(key, 0)
        if radius <= 0:
            continue
        pts = []
        for i in range(n_rays):
            az    = math.radians(360.0 * i / n_rays)
            r     = radius * factors[i] * (1 + (rng.random()-0.5)*0.04)
            dlat  = r * math.cos(az) / m_per_lat
            dlon  = r * math.sin(az) / m_per_lon
            pts.append([round(lat+dlat, 6), round(lon+dlon, 6)])
        pts.append(pts[0])
        polygons[key] = pts

    srtm_ok = _tile_cache.get(_tile_name(lat, lon)) is not None
    label   = (f"⛰️ SRTM ({elev0:.0f}m n.p.m.)" if srtm_ok
               else "🏘️ Fallback (brak SRTM)")

    return dict(polygons=polygons, terrain_type=label,
                osm_density=0.0, canyon=False,
                rays=n_rays, samples=n_samples,
                elevation_impact=elev0)


if __name__ == "__main__":
    print("=== Test SRTM (kurviger.de) ===\n")
    tests = [
        ("Warszawa",   52.23,  21.01,  90),
        ("Las Vegas",  36.17,-115.14, 610),
        ("Red Rock",   36.15,-115.45,1200),
        ("Alpy",       46.50,   8.00,2000),
    ]
    print(f"{'Miejsce':<12} {'Wys.':>7}  {'Oczekiwane':>12}")
    print("-"*38)
    for name, lat, lon, expected in tests:
        h = get_elevation(lat, lon)
        ok = "✅" if abs(h - expected) < expected*0.4 else "⚠️"
        print(f"{name:<12} {h:>6.0f}m  (~{expected}m) {ok}")
    print("\nGotowe!")
