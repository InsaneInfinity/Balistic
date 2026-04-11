import requests, redis, json, math, time, threading, webbrowser, os, secrets
from flask import Flask, request, jsonify, abort, send_file
from dotenv import load_dotenv
from datetime import datetime
import io

load_dotenv()

app = Flask(__name__)

# === KONFIGURACJA ===
USER_DB = {"admin": "admin"}
API_KEY_WEATHER = os.getenv("WEATHER_API_KEY", "")
CESIUM_TOKEN = os.getenv("CESIUM_TOKEN", "")
SESSION_TOKEN = secrets.token_hex(16)

CEP = {
    "M107 HE":    150,
    "EXCALIBUR":   10,
    "HE STD":      80,
    "SMOKE":      120,
    "APFSDS":      20,
    "HEAT":        40,
    # Rakiety NATO
    "ATACMS-A":    10,
    "ATACMS-B":   200,
    "9M723":        5,
    "GMLRS":        5,
    "GMLRS-ER":     5,
    "PAC-3 MSE":    1,
    "PrSM":         5,
    "SM-3":         1,
    "Lance":      450,
    # Rosja
    "Kinzal":       3,
    "Sarmat":      10,
    "Kalibr":       3,
    "Tochka-U":   150,
    "Scud-B":     450,
    "Rubezh":      50,
    "Oniks":        5,
    # Chiny
    "DF-21D":      20,
    "DF-41":      100,
    "DF-17":        5,
    "DF-11A":     200,
    "DF-26":       50,
    # Korea Płn
    "Hwasong-12": 1000,
    "Hwasong-17":  500,
    "KN-23":       50,
    # Iran
    "Shahab-3":   500,
    "Khorramshahr": 30,
    "Fateh-110":   100,
    "Zolfaghar":    50,
    # USA
    "Minuteman-III": 120,
    "Trident-II":    90,
    # Izrael
    "Jericho-II":  500,
    "Jericho-III":  50,
    # Indie
    "Prithvi-II":  250,
    "Agni-V":      100,
    # Pakistan
    "Shaheen-III": 100,
    # Francja
    "M51":          50,
    # Rosja dodatkowe SLBM/ICBM
    "Bulava":       150,   # RSM-56 ~150m CEP
    "Sinewa":       250,   # RSM-54 ~250m CEP
    "Yars":          50,   # RS-24 ~50m CEP
    "Topol-M":      200,   # RS-12M2 ~200m CEP
    "Avangard":      10,   # HGV ~10m CEP (manewrujący)
    # == NOWE SYSTEMY ==
    # Chiny dodatkowe
    "DF-5B":         300,  "DF-15B":        30,   "DF-31AG":      100,
    "DF-4":          300,  "CJ-10":          10,  "YJ-12":         20,
    "DF-100":         10,
    # Rosja dodatkowe
    "9K720":           5,  "Kh-47M2":        1,   "RS-28-MIRVed": 10,
    "Tochka":        150,  "OTR-21":        150,
    # USA/NATO dodatkowe
    "BGM-109":        10,  "MGM-52C":       450,  "Pershing-II":   30,
    "LRASM":          10,  "JASSM-ER":       10,  "Tomahawk":      10,
    "HIMARS-ATACMS":  10,  "GLCM":           30,  "SM-6":           5,
    "TAURUS":         10,  "SCALP":          10,  "Storm-Shadow":  10,
    "Brimstone":       5,  "Meteor":          5,
    # UK
    "Trident-II-UK":  90,
    # Niemcy
    "KEPD-350":       10,
    # Włochy/Francja
    "ASTER-30":        5,  "APACHE":         10,
    # Turcja
    "SOM":            10,  "Bora":           50,  "Kasirga":       30,
    "J-600T":         50,  "TRG-300":        30,  "Roketsan-SOM":  10,
    # Korea Płd
    "Hyunmoo-2C":     30,  "Hyunmoo-3C":     10,  "Hyunmoo-4":     10,
    "Hyunmoo-5":      50,
    # Japonia
    "Type-12":        10,  "ASM-3":          10,
    # Arabia Saudyjska
    "CSS-5":         300,  "Otokar":         50,
    # Tajwan
    "Hsiung-Feng-III": 10, "Yun-Feng":       50,
    # ZEA
    "BADR-2000":     300,
    # Brazylia
    "SS-300":        100,  "Astros-II":      50,
    # Ukraina
    "OTR-21-UA":     150,  "Vilkha":          5,  "Neptune":       10,
    "Grom-2":         50,  "Hrim-2":          50,
    # Szwecja
    "RBS-15":         10,
    # Iran dodatkowe
    "Emad":           50,   # MRBM precyzyjny ~50m CEP
    "Ghadr":         300,   # wariant Shahab-3 ~300m CEP
    # Głowice kasetowe
    "Scud-B-Cluster":  450,  "9M723-Cluster":    5,
    "ATACMS-Cluster":  200,  "Tochka-Cluster":  150,
    "Shahab-Cluster":  500,  "Khorramshahr-Cluster": 30,
    # Grecja
    "SCALP-EG":       10,
    # Egipt
    "Scud-D":        450,  "Vector":         50,
    # Syria
    "M-600":         100,  "Tishreen":      200,
    # Tajlandia/Indonezja/Malezja
    "C-802":          10,  "C-705":          10,
    # Singapur
    "SPIKE-NLOS":      5,
    # Wielka Brytania
    "Harpoon":        10,
    # USA nowe głowice
    "B61-12":         30,   # bomba grawitacyjna, INS+GPS ~30m CEP
    "W80-4":          10,   # JASSM-ER wariant nuklearny ~10m CEP
    "W76-2":         100,
    # Hiroszima / Nagasaki 1945
    "LittleBoy":    2000, "FatMan":       2000,
    # Nowe v5.7
    "Zircon":          2,  "Burevestnik":   50,  "Tu22M-nuke":   200,
    "B52-ALCM":       30,  "B52-B61":       30,  "ALCM":          30,
    "THAAD":           1,  "DF-27":         50,  "DF-ZF":         10,
    "Hwasong-18":    500,  "Hwasong-15":   1000, "Fattah":        50,
    "Kheibar":       100,  "Agni-VI":      100,  "BrahMos":        3,
    "Ababeel":       200,  "Raad":          50,
    # v5.8
    "Kh-101":          5,  "Kh-102":         5,  "ARRW":           5,
    "B1B-conv":       30,  "JL-2":          150,  "JL-3":         100,
    "Pukguksong-3":  500,  "K-4":           200,  "K-15":         200,
    "ASMP-A":         30,  "Rafale-ASMP":   30,  "Vulcan-WE177": 500,
    # Artyleria v5.9
    "M109-HE":       150,  "M109-EXCAL":    10,
    "PzH-HE":        120,  "PzH-EXCAL":      8,
    "AS90-HE":       150,  "CAESAR-HE":     120,  "CAESAR-EXCAL":   8,
    "Archer-HE":     100,  "Archer-EXCAL":    8,
    "K9-HE":         120,  "K9-EXCAL":       10,
    "Msta-HE":       200,  "Msta-Krasnopol": 10,
    "Akacja-HE":     250,  "Pion-HE":       300,
    "Koalicja-HE":    80,  "Koalicja-Prec":   5,
    "PLZ05-HE":      150,  "PCL181-HE":     150,
    "ATHOS-HE":      150,  "Soltam-HE":     150,
    "Firtina-HE":    150,  "ATAGS-HE":      100,
    "Dhanush-HE":    150,  "Krab2-HE":      150,
    "Krab2-EXCAL":    10,  "Bohdana-HE":    150,
    "Type99-HE":     120,  "K55-HE":        150,
    "AS90AU-HE":     150,  "M109BR-HE":     150,
    "Koksan-HE":     300,  "Hoveyzeh-HE":   150,  "Raad122-HE":    200,
    "M109PK-HE":     150,  "M109SA-HE":     150,  "T69-HE":        150,
    "PzH2000GR-HE":  120,  "K9NO-HE":       120,  "K9FI-HE":       120,
    "M109CA-HE":     150,  "Gvozdika-HE":   200,  "Gvozdika2-HE":  200,
    "D30-HE":        250,  "M198-HE":       150,  "FH70-HE":       150,
    "K9AU-HE":       120,  "Zuzana-HE":     100,  "Dana-HE":       150,
    "KrabUA-HE":     150,
    # Samoloty nuklearne
    "F35-B61":        30,   "B2-B61":         30,   "B2-B83":         50,
    "B21-B61":        20,   "F15-B61":        30,   "Tornado-B61":    30,
    "Tu160-nuke":    200,   "Tu95-nuke":     300,   "H6K-nuke":      300,
}

# Strefy rażenia — patrz poniżej (nuclear_blast + BLAST_ZONES)

def nuclear_blast(kt):
    """
    Wzory Glasstone & Dolan 'The Effects of Nuclear Weapons' (1977) — jawna publikacja rządowa USA.
    Promienie stref w metrach dla wybuchu naziemnego.
    kt = moc głowicy w kilotonach
    """
    fireball  = int(100  * kt**0.41)   # Kula ognia — totalne zniszczenie, oparzenia 3°
    heavy     = int(290  * kt**0.33)   # 20 psi fala uderzeniowa — ciężkie zniszczenia
    light     = int(690  * kt**0.33)   # 5 psi fala uderzeniowa — lekkie zniszczenia
    hazard    = int(2200 * kt**0.41)   # Strefa oparzeń 1° — zagrożenie życia
    return {"total": fireball, "heavy": heavy, "light": light, "hazard": hazard, "type": "NUCLEAR"}

# Strefy rażenia [m] — dane na podstawie jawnych podręczników NATO / FM 6-40
BLAST_ZONES = {
    "M107 HE":   {"total": 30,   "heavy": 100,  "light": 300,  "hazard": 800,  "type": "HE"},
    "EXCALIBUR": {"total": 30,   "heavy": 100,  "light": 300,  "hazard": 800,  "type": "HE"},
    "HE STD":    {"total": 8,    "heavy": 30,   "light": 80,   "hazard": 200,  "type": "HE"},
    "SMOKE":     {"total": 0,    "heavy": 0,    "light": 0,    "hazard": 80,   "type": "SMOKE"},
    "APFSDS":    {"total": 0,    "heavy": 0,    "light": 0,    "hazard": 0,    "type": "KE"},
    "HEAT":      {"total": 0,    "heavy": 0,    "light": 0,    "hazard": 5,    "type": "HEAT"},
    # Rakiety NATO konwencjonalne
    "ATACMS-A":  {"total": 50,   "heavy": 200,  "light": 500,  "hazard": 1500, "type": "HE"},
    "ATACMS-B":  {"total": 150,  "heavy": 500,  "light": 1000, "hazard": 3000, "type": "HE"},
    "9M723":     {"total": 50,   "heavy": 250,  "light": 600,  "hazard": 2000, "type": "HE"},
    "GMLRS":     {"total": 20,   "heavy": 80,   "light": 200,  "hazard": 500,  "type": "HE"},
    "GMLRS-ER":  {"total": 20,   "heavy": 80,   "light": 200,  "hazard": 500,  "type": "HE"},
    "PAC-3 MSE": {"total": 0,    "heavy": 0,    "light": 0,    "hazard": 0,    "type": "KE"},
    # Rosja konwencjonalne
    "Kinzal":    {"total": 30,   "heavy": 150,  "light": 400,  "hazard": 1000, "type": "HE"},
    "Kalibr":    {"total": 30,   "heavy": 150,  "light": 400,  "hazard": 1000, "type": "HE"},
    "Tochka-U":  {"total": 30,   "heavy": 100,  "light": 250,  "hazard": 700,  "type": "HE"},
    "Scud-B":    {"total": 30,   "heavy": 100,  "light": 250,  "hazard": 700,  "type": "HE"},
    "Oniks":     {"total": 30,   "heavy": 150,  "light": 400,  "hazard": 1000, "type": "HE"},
    # Chiny konwencjonalne
    "DF-21D":    {"total": 50,   "heavy": 200,  "light": 500,  "hazard": 1500, "type": "HE"},
    "DF-17":     {"total": 30,   "heavy": 150,  "light": 400,  "hazard": 1200, "type": "HE"},
    "DF-11A":    {"total": 30,   "heavy": 100,  "light": 250,  "hazard": 700,  "type": "HE"},
    # Korea Płn konwencjonalne
    "Hwasong-12":{"total": 50,   "heavy": 200,  "light": 500,  "hazard": 1500, "type": "HE"},
    "KN-23":     {"total": 30,   "heavy": 100,  "light": 250,  "hazard": 700,  "type": "HE"},
    # Iran
    "Shahab-3":  {"total": 30,   "heavy": 120,  "light": 300,  "hazard": 800,  "type": "HE"},
    "Khorramshahr":{"total": 30, "heavy": 120,  "light": 300,  "hazard": 800,  "type": "HE"},
    "Fateh-110": {"total": 20,   "heavy": 80,   "light": 200,  "hazard": 500,  "type": "HE"},
    "Zolfaghar": {"total": 20,   "heavy": 80,   "light": 200,  "hazard": 500,  "type": "HE"},
    # NATO dodatkowe
    "PrSM":      {"total": 30,   "heavy": 100,  "light": 250,  "hazard": 700,  "type": "HE"},
    "SM-3":      {"total": 0,    "heavy": 0,    "light": 0,    "hazard": 0,    "type": "KE"},
    "Prithvi-II":{"total": 30,   "heavy": 100,  "light": 250,  "hazard": 700,  "type": "HE"},
    # ================================================================
    # GŁOWICE JĄDROWE — wzory Glasstone & Dolan (1977)
    # Promienie dla wybuchu naziemnego, moc w kt
    # ================================================================
    "Sarmat":        nuclear_blast(750),    # jedna głowica 750kt (RS-28)
    "Rubezh":        nuclear_blast(500),    # RS-26 ~500kt
    "DF-41":         nuclear_blast(250),    # jedna głowica 250kt
    "DF-26":         nuclear_blast(250),    # ~250kt
    "Hwasong-17":    nuclear_blast(1000),   # szacunek ~1000kt
    "Minuteman-III": nuclear_blast(300),    # W87 ~300kt
    "Trident-II":    nuclear_blast(475),    # W88 ~475kt
    "Jericho-II":    nuclear_blast(400),    # ~400kt
    "Jericho-III":   nuclear_blast(400),    # ~400kt
    "Agni-V":        nuclear_blast(200),    # ~200kt
    "Shaheen-III":   nuclear_blast(100),    # ~100kt
    "M51":           nuclear_blast(110),    # TN 75 ~110kt
    "Lance":         nuclear_blast(1),      # W70 taktyczna ~1kt
    # Rosja dodatkowe SLBM/ICBM
    "Bulava":        nuclear_blast(150),    # RSM-56 ~150kt jedna głowica
    "Sinewa":        nuclear_blast(100),    # RSM-54 ~100kt jedna głowica
    "Yars":          nuclear_blast(300),    # RS-24 ~300kt jedna głowica
    "Topol-M":       nuclear_blast(550),    # RS-12M2 ~550kt
    "Avangard":      {**nuclear_blast(2000), "burst": "air"},  # HGV ~2Mt — wybuch powietrzny, mniejszy opad
    # ================================================================
    # NOWE SYSTEMY — uzupełnienie globalne
    # ================================================================
    # Chiny dodatkowe
    "DF-5B":         nuclear_blast(5000),   # 5Mt ICBM
    "DF-31AG":       nuclear_blast(150),    # ~150kt ICBM mobilny
    "DF-4":          nuclear_blast(3300),   # 3.3Mt stara ICBM
    "DF-15B":        {"total": 50,  "heavy": 200, "light": 500,  "hazard": 1500, "type": "HE"},
    "CJ-10":         {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "YJ-12":         {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "DF-100":        {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    # Rosja dodatkowe
    "9K720":         {"total": 50,  "heavy": 250, "light": 600,  "hazard": 2000, "type": "HE"},
    "Kh-47M2":       nuclear_blast(300),    # Kinzhal nuklearny ~300kt
    "Tochka":        {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "OTR-21":        {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    # USA/NATO cruise
    "BGM-109":       {"total": 20,  "heavy": 100, "light": 300,  "hazard": 800,  "type": "HE"},
    "Tomahawk":      {"total": 20,  "heavy": 100, "light": 300,  "hazard": 800,  "type": "HE"},
    "LRASM":         {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "JASSM-ER":      {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "GLCM":          nuclear_blast(150),    # BGM-109G ~150kt
    "MGM-52C":       nuclear_blast(10),     # Lance nuklearny ~10kt
    "Pershing-II":   nuclear_blast(80),     # W85 ~80kt
    "SM-6":          {"total": 0,   "heavy": 0,   "light": 0,    "hazard": 0,    "type": "KE"},
    "TAURUS":        {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "SCALP":         {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "Storm-Shadow":  {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "KEPD-350":      {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "ASTER-30":      {"total": 0,   "heavy": 0,   "light": 0,    "hazard": 0,    "type": "KE"},
    "APACHE":        {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Brimstone":     {"total": 5,   "heavy": 20,  "light": 50,   "hazard": 150,  "type": "HE"},
    "Meteor":        {"total": 0,   "heavy": 0,   "light": 0,    "hazard": 0,    "type": "KE"},
    "Trident-II-UK": nuclear_blast(100),    # UK ~100kt
    # Turcja
    "SOM":           {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Bora":          {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "Kasirga":       {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "J-600T":        {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "TRG-300":       {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Roketsan-SOM":  {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    # Korea Płd
    "Hyunmoo-2C":    {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "Hyunmoo-3C":    {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Hyunmoo-4":     {"total": 50,  "heavy": 200, "light": 500,  "hazard": 1500, "type": "HE"},
    "Hyunmoo-5":     {"total": 50,  "heavy": 200, "light": 500,  "hazard": 1500, "type": "HE"},
    # Japonia
    "Type-12":       {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "ASM-3":         {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    # Tajwan
    "Hsiung-Feng-III":{"total":20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Yun-Feng":      {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    # Arabia Saudyjska
    "CSS-5":         nuclear_blast(300),    # DF-21 export
    # Brazylia
    "SS-300":        {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Astros-II":     {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    # Ukraina
    "OTR-21-UA":     {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "Vilkha":        {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Neptune":       {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "Grom-2":        {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "Hrim-2":        {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    # Szwecja/UK/inne NATO
    "RBS-15":        {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "Harpoon":       {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    # Egipt/Syria/Bliski Wschód
    "Scud-D":        {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "M-600":         {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    "Tishreen":      {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "BADR-2000":     {"total": 30,  "heavy": 100, "light": 250,  "hazard": 700,  "type": "HE"},
    # Azja Płd-Wsch
    "C-802":         {"total": 20,  "heavy": 80,  "light": 200,  "hazard": 500,  "type": "HE"},
    "C-705":         {"total": 10,  "heavy": 40,  "light": 100,  "hazard": 300,  "type": "HE"},
    "SPIKE-NLOS":    {"total": 5,   "heavy": 20,  "light": 50,   "hazard": 150,  "type": "HE"},
    "RS-28-MIRVed":  nuclear_blast(750),
    # USA nowe głowice
    "B61-12":        nuclear_blast(50),
    "W80-4":         nuclear_blast(150),
    "W76-2":         nuclear_blast(5),
    # Hiroszima / Nagasaki 1945
    "LittleBoy":     nuclear_blast(15),
    "FatMan":        nuclear_blast(21),
    # Nowe v5.7
    "Zircon":        {"total": 30,  "heavy": 150, "light": 400,  "hazard": 1000, "type": "HE"},
    "Burevestnik":   nuclear_blast(200),
    "Tu22M-nuke":    nuclear_blast(500),
    "B52-ALCM":      nuclear_blast(150),   # W80 ~150kt
    "B52-B61":       nuclear_blast(50),
    "ALCM":          nuclear_blast(150),
    "THAAD":         {"total": 0, "heavy": 0, "light": 0, "hazard": 0, "type": "KE"},
    "DF-27":         nuclear_blast(250),
    "DF-ZF":         {"total": 30, "heavy": 150, "light": 400, "hazard": 1200, "type": "HE"},
    "Hwasong-18":    nuclear_blast(1000),
    "Hwasong-15":    nuclear_blast(1000),
    "Fattah":        {"total": 30, "heavy": 150, "light": 400, "hazard": 1000, "type": "HE"},
    "Kheibar":       {"total": 30, "heavy": 120, "light": 300, "hazard": 800,  "type": "HE"},
    "Agni-VI":       nuclear_blast(300),
    "BrahMos":       {"total": 20, "heavy": 80,  "light": 200, "hazard": 500,  "type": "HE"},
    "Ababeel":       nuclear_blast(100),
    "Raad":          nuclear_blast(10),
    # v5.8
    "Kh-101":        {"total": 30, "heavy": 150, "light": 400, "hazard": 1000, "type": "HE"},
    "Kh-102":        nuclear_blast(250),
    "ARRW":          {"total": 30, "heavy": 150, "light": 400, "hazard": 1000, "type": "HE"},
    "B1B-conv":      {"total": 30, "heavy": 150, "light": 400, "hazard": 1000, "type": "HE"},
    "JL-2":          nuclear_blast(250),
    "JL-3":          nuclear_blast(250),
    "Pukguksong-3":  nuclear_blast(500),
    "K-4":           nuclear_blast(200),
    "K-15":          nuclear_blast(200),
    "ASMP-A":        nuclear_blast(300),
    "Rafale-ASMP":   nuclear_blast(300),
    "Vulcan-WE177":  nuclear_blast(400),
    # Artyleria v5.9 — wszystkie HE
    "M109-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "M109-EXCAL":    {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "PzH-HE":        {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "PzH-EXCAL":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "AS90-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "CAESAR-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "CAESAR-EXCAL":  {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Archer-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Archer-EXCAL":  {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "K9-HE":         {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "K9-EXCAL":      {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Msta-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Msta-Krasnopol":{"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Akacja-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Pion-HE":       {"total": 50, "heavy": 200, "light": 500, "hazard": 1500, "type": "HE"},
    "Koalicja-HE":   {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Koalicja-Prec": {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "PLZ05-HE":      {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "PCL181-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "ATHOS-HE":      {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Soltam-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Firtina-HE":    {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "ATAGS-HE":      {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Dhanush-HE":    {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Krab2-HE":      {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Krab2-EXCAL":   {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Bohdana-HE":    {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Type99-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "K55-HE":        {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "AS90AU-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "M109BR-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Koksan-HE":     {"total": 50, "heavy": 200, "light": 500, "hazard": 1500, "type": "HE"},
    "Hoveyzeh-HE":   {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Raad122-HE":    {"total": 8,  "heavy": 30,  "light": 80,  "hazard": 200,  "type": "HE"},
    "M109PK-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "M109SA-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "T69-HE":        {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "PzH2000GR-HE":  {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "K9NO-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "K9FI-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "M109CA-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Gvozdika-HE":   {"total": 8,  "heavy": 30,  "light": 80,  "hazard": 200,  "type": "HE"},
    "Gvozdika2-HE":  {"total": 8,  "heavy": 30,  "light": 80,  "hazard": 200,  "type": "HE"},
    "D30-HE":        {"total": 8,  "heavy": 30,  "light": 80,  "hazard": 200,  "type": "HE"},
    "M198-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "FH70-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "K9AU-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Zuzana-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "Dana-HE":       {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    "KrabUA-HE":     {"total": 30, "heavy": 100, "light": 300, "hazard": 800,  "type": "HE"},
    # Samoloty nuklearne
    "F35-B61":       nuclear_blast(50),    # B61-12 max 50kt
    "B2-B61":        nuclear_blast(50),    # B61-12
    "B2-B83":        nuclear_blast(1200),  # B83 ~1.2Mt
    "B21-B61":       nuclear_blast(50),    # B61-12
    "F15-B61":       nuclear_blast(50),    # B61-12
    "Tornado-B61":   nuclear_blast(50),    # B61-12
    "Tu160-nuke":    nuclear_blast(500),   # ~500kt
    "Tu95-nuke":     nuclear_blast(500),   # ~500kt
    "H6K-nuke":      nuclear_blast(300),   # ~300kt
    # Iran dodatkowe
    "Emad":          {"total": 30,  "heavy": 120, "light": 300, "hazard": 800,  "type": "HE"},
    "Ghadr":         {"total": 30,  "heavy": 120, "light": 300, "hazard": 800,  "type": "HE"},
    # ================================================================
    # GŁOWICE KASETOWE (CLUSTER)
    # submunitions = liczba submunitions
    # dispersion   = promień rozrzutu [m]
    # total/heavy/light/hazard = strefa rażenia JEDNEJ submunition [m]
    # ================================================================
    "Scud-B-Cluster":         {"total": 5,  "heavy": 15, "light": 40,  "hazard": 100, "type": "CLUSTER", "submunitions": 650,  "dispersion": 400},
    "9M723-Cluster":          {"total": 5,  "heavy": 15, "light": 40,  "hazard": 100, "type": "CLUSTER", "submunitions": 54,   "dispersion": 200},
    "ATACMS-Cluster":         {"total": 3,  "heavy": 10, "light": 25,  "hazard": 60,  "type": "CLUSTER", "submunitions": 950,  "dispersion": 500},
    "Tochka-Cluster":         {"total": 5,  "heavy": 15, "light": 40,  "hazard": 100, "type": "CLUSTER", "submunitions": 50,   "dispersion": 150},
    "Shahab-Cluster":         {"total": 5,  "heavy": 15, "light": 40,  "hazard": 100, "type": "CLUSTER", "submunitions": 200,  "dispersion": 300},
    "Khorramshahr-Cluster":   {"total": 5,  "heavy": 15, "light": 40,  "hazard": 100, "type": "CLUSTER", "submunitions": 300,  "dispersion": 350},
}

DRAG_COEFF = {
    "M107 HE":   0.47,
    "EXCALIBUR": 0.20,
    "HE STD":    0.45,
    "SMOKE":     0.50,
    "APFSDS":    0.05,
    "HEAT":      0.35,
    # Rakiety — niski Cd (smukłe ciała)
    "ATACMS-A":   0.15,
    "ATACMS-B":   0.15,
    "9M723":      0.12,
    "GMLRS":      0.18,
    "GMLRS-ER":   0.16,
    "PAC-3 MSE":  0.08,
    # Rosja
    "Kinzal":     0.08,   # hipersoniczna, bardzo niski Cd
    "Sarmat":     0.20,   # ICBM
    "Kalibr":     0.25,   # manewrująca — wyższy Cd
    # Chiny
    "DF-21D":     0.15,
    "DF-41":      0.18,
    "DF-17":      0.10,   # HGV — hipersoniczny szybowiec
    # Korea Płn
    "Hwasong-12": 0.18,
    "Hwasong-17": 0.20,
    # Iran
    "Shahab-3":   0.22,
    "Khorramshahr": 0.20,
    # USA dodatkowe
    "Minuteman-III": 0.18,
    "Trident-II":    0.16,
    "PrSM":          0.15,
    "SM-3":          0.08,
    "Lance":         0.25,
    # Rosja dodatkowe
    "Tochka-U":   0.22,
    "Scud-B":     0.25,
    "Rubezh":     0.18,
    "Oniks":      0.12,
    # Chiny dodatkowe
    "DF-11A":     0.22,
    "DF-26":      0.18,
    # Korea Płn dodatkowa
    "KN-23":      0.20,
    # Iran dodatkowe
    "Fateh-110":  0.22,
    "Zolfaghar":  0.20,
    # Izrael
    "Jericho-II":  0.20,
    "Jericho-III": 0.18,
    # Indie
    "Prithvi-II":  0.22,
    "Agni-V":      0.18,
    # Pakistan
    "Shaheen-III": 0.18,
    # Francja
    "M51":         0.16,
    # Rosja dodatkowe SLBM/ICBM
    "Bulava":      0.18,
    "Sinewa":      0.18,
    "Yars":        0.18,
    "Topol-M":     0.20,
    "Avangard":    0.06,   # HGV — bardzo niski Cd
    # Nowe systemy
    "DF-5B":0.20,"DF-31AG":0.18,"DF-4":0.22,"DF-15B":0.15,"CJ-10":0.25,"YJ-12":0.12,"DF-100":0.10,
    "9K720":0.12,"Kh-47M2":0.08,"Tochka":0.22,"OTR-21":0.22,
    "BGM-109":0.25,"Tomahawk":0.25,"LRASM":0.12,"JASSM-ER":0.15,"GLCM":0.25,"MGM-52C":0.25,
    "Pershing-II":0.18,"SM-6":0.08,"TAURUS":0.20,"SCALP":0.22,"Storm-Shadow":0.22,
    "KEPD-350":0.20,"ASTER-30":0.08,"APACHE":0.22,"Brimstone":0.08,"Meteor":0.06,
    "Trident-II-UK":0.16,
    "SOM":0.22,"Bora":0.18,"Kasirga":0.20,"J-600T":0.18,"TRG-300":0.20,"Roketsan-SOM":0.22,
    "Hyunmoo-2C":0.18,"Hyunmoo-3C":0.22,"Hyunmoo-4":0.16,"Hyunmoo-5":0.16,
    "Type-12":0.22,"ASM-3":0.10,
    "Hsiung-Feng-III":0.12,"Yun-Feng":0.18,
    "CSS-5":0.18,"SS-300":0.20,"Astros-II":0.22,
    "OTR-21-UA":0.22,"Vilkha":0.18,"Neptune":0.20,"Grom-2":0.18,"Hrim-2":0.18,
    "RBS-15":0.20,"Harpoon":0.22,
    "Scud-D":0.25,"M-600":0.22,"Tishreen":0.25,"BADR-2000":0.22,
    "C-802":0.20,"C-705":0.22,"SPIKE-NLOS":0.08,
    "RS-28-MIRVed":0.20,
    "B61-12":0.35, "W80-4":0.15, "W76-2":0.16,
    "LittleBoy":0.35, "FatMan":0.35,
    "Zircon":0.06, "Burevestnik":0.25, "Tu22M-nuke":0.02,
    "B52-ALCM":0.02, "B52-B61":0.02, "ALCM":0.25,
    "THAAD":0.06, "DF-27":0.12, "DF-ZF":0.08,
    "Hwasong-18":0.20, "Hwasong-15":0.20, "Fattah":0.08,
    "Kheibar":0.18, "Agni-VI":0.18, "BrahMos":0.08,
    "Ababeel":0.20, "Raad":0.22,
    "Kh-101":0.20, "Kh-102":0.20, "ARRW":0.06, "B1B-conv":0.02,
    "JL-2":0.18, "JL-3":0.18, "Pukguksong-3":0.20,
    "K-4":0.18, "K-15":0.22, "ASMP-A":0.08,
    "Rafale-ASMP":0.02, "Vulcan-WE177":0.02,
    # Artyleria v5.9
    "M109-HE":0.47,"M109-EXCAL":0.20,"PzH-HE":0.47,"PzH-EXCAL":0.20,
    "AS90-HE":0.47,"CAESAR-HE":0.47,"CAESAR-EXCAL":0.20,
    "Archer-HE":0.47,"Archer-EXCAL":0.20,"K9-HE":0.47,"K9-EXCAL":0.20,
    "Msta-HE":0.47,"Msta-Krasnopol":0.20,"Akacja-HE":0.47,
    "Pion-HE":0.45,"Koalicja-HE":0.47,"Koalicja-Prec":0.20,
    "PLZ05-HE":0.47,"PCL181-HE":0.47,"ATHOS-HE":0.47,"Soltam-HE":0.47,
    "Firtina-HE":0.47,"ATAGS-HE":0.47,"Dhanush-HE":0.47,
    "Krab2-HE":0.47,"Krab2-EXCAL":0.20,"Bohdana-HE":0.47,
    "Type99-HE":0.47,"K55-HE":0.47,"AS90AU-HE":0.47,"M109BR-HE":0.47,
    "Koksan-HE":0.45,"Hoveyzeh-HE":0.47,"Raad122-HE":0.47,
    "M109PK-HE":0.47,"M109SA-HE":0.47,"T69-HE":0.47,"PzH2000GR-HE":0.47,
    "K9NO-HE":0.47,"K9FI-HE":0.47,"M109CA-HE":0.47,
    "Gvozdika-HE":0.47,"Gvozdika2-HE":0.47,"D30-HE":0.47,
    "M198-HE":0.47,"FH70-HE":0.47,"K9AU-HE":0.47,
    "Zuzana-HE":0.47,"Dana-HE":0.47,"KrabUA-HE":0.47,
    "F35-B61":0.02,"B2-B61":0.02,"B2-B83":0.02,"B21-B61":0.02,
    "F15-B61":0.02,"Tornado-B61":0.02,"Tu160-nuke":0.02,"Tu95-nuke":0.02,"H6K-nuke":0.02,
    "Emad":0.20, "Ghadr":0.22,
    "Scud-B-Cluster":0.25, "9M723-Cluster":0.12, "ATACMS-Cluster":0.15,
    "Tochka-Cluster":0.22, "Shahab-Cluster":0.22, "Khorramshahr-Cluster":0.20,
}

AREA = {
    "M107 HE":   0.0189,
    "EXCALIBUR": 0.0189,
    "HE STD":    0.0113,
    "SMOKE":     0.0113,
    "APFSDS":    0.0113,
    "HEAT":      0.0113,
    # Rakiety NATO
    "ATACMS-A":   0.0380,
    "ATACMS-B":   0.0380,
    "9M723":      0.0415,
    "GMLRS":      0.0254,
    "GMLRS-ER":   0.0254,
    "PAC-3 MSE":  0.0113,
    # Rosja
    "Kinzal":     0.0314,   # ~200mm
    "Sarmat":     0.7854,   # ~1000mm (3m średnica!)
    "Kalibr":     0.0314,   # ~200mm
    # Chiny
    "DF-21D":     0.0707,   # ~300mm
    "DF-41":      0.7854,   # ~1000mm
    "DF-17":      0.1963,   # ~500mm HGV
    # Korea Płn
    "Hwasong-12": 0.1963,   # ~500mm
    "Hwasong-17": 0.7854,   # ~1000mm
    # Iran
    "Shahab-3":   0.0707,   # ~300mm
    "Khorramshahr": 0.1963,
    # USA dodatkowe
    "Minuteman-III": 0.7854,
    "Trident-II":    0.5027,
    "PrSM":          0.0314,
    "SM-3":          0.0113,
    "Lance":         0.0452,
    # Rosja dodatkowe
    "Tochka-U":   0.0452,
    "Scud-B":     0.0707,
    "Rubezh":     0.3848,
    "Oniks":      0.0452,
    # Chiny dodatkowe
    "DF-11A":     0.0452,
    "DF-26":      0.1963,
    # Korea Płn dodatkowa
    "KN-23":      0.0707,
    # Iran dodatkowe
    "Fateh-110":  0.0314,
    "Zolfaghar":  0.0452,
    # Izrael
    "Jericho-II":  0.0707,
    "Jericho-III": 0.1963,
    # Indie
    "Prithvi-II":  0.0452,
    "Agni-V":      0.1963,
    # Pakistan
    "Shaheen-III": 0.1963,
    # Francja
    "M51":         0.5027,
    # Rosja dodatkowe SLBM/ICBM
    "Bulava":      0.3848,   # ~700mm
    "Sinewa":      0.3848,   # ~700mm
    "Yars":        0.5027,   # ~800mm
    "Topol-M":     0.5027,   # ~800mm
    "Avangard":    0.1963,   # ~500mm HGV
    # Nowe systemy
    "DF-5B":0.7854,"DF-31AG":0.3848,"DF-4":0.7854,"DF-15B":0.0707,"CJ-10":0.0314,"YJ-12":0.0452,"DF-100":0.0314,
    "9K720":0.0415,"Kh-47M2":0.0314,"Tochka":0.0452,"OTR-21":0.0452,
    "BGM-109":0.0314,"Tomahawk":0.0314,"LRASM":0.0707,"JASSM-ER":0.0707,"GLCM":0.0314,"MGM-52C":0.0452,
    "Pershing-II":0.1963,"SM-6":0.0113,"TAURUS":0.0707,"SCALP":0.0707,"Storm-Shadow":0.0707,
    "KEPD-350":0.0707,"ASTER-30":0.0113,"APACHE":0.0452,"Brimstone":0.0078,"Meteor":0.0078,
    "Trident-II-UK":0.5027,
    "SOM":0.0314,"Bora":0.0707,"Kasirga":0.0452,"J-600T":0.1963,"TRG-300":0.0707,"Roketsan-SOM":0.0314,
    "Hyunmoo-2C":0.1963,"Hyunmoo-3C":0.0707,"Hyunmoo-4":0.1963,"Hyunmoo-5":0.1963,
    "Type-12":0.0452,"ASM-3":0.0707,
    "Hsiung-Feng-III":0.0452,"Yun-Feng":0.1963,
    "CSS-5":0.0707,"SS-300":0.0452,"Astros-II":0.0314,
    "OTR-21-UA":0.0452,"Vilkha":0.0452,"Neptune":0.0314,"Grom-2":0.1963,"Hrim-2":0.1963,
    "RBS-15":0.0452,"Harpoon":0.0314,
    "Scud-D":0.0707,"M-600":0.0452,"Tishreen":0.0707,"BADR-2000":0.1963,
    "C-802":0.0314,"C-705":0.0254,"SPIKE-NLOS":0.0078,
    "RS-28-MIRVed":0.7854,
    "B61-12":0.0452, "W80-4":0.0707, "W76-2":0.5027,
    "LittleBoy":0.0452, "FatMan":0.0707,
    "Zircon":0.0314, "Burevestnik":0.0314, "Tu22M-nuke":0.1963,
    "B52-ALCM":0.1963, "B52-B61":0.0452, "ALCM":0.0314,
    "THAAD":0.0113, "DF-27":0.1963, "DF-ZF":0.1963,
    "Hwasong-18":0.7854, "Hwasong-15":0.7854, "Fattah":0.0707,
    "Kheibar":0.0707, "Agni-VI":0.3848, "BrahMos":0.0452,
    "Ababeel":0.1963, "Raad":0.0314,
    "Kh-101":0.0314, "Kh-102":0.0314, "ARRW":0.0707, "B1B-conv":0.1963,
    "JL-2":0.3848, "JL-3":0.5027, "Pukguksong-3":0.1963,
    "K-4":0.1963, "K-15":0.0707, "ASMP-A":0.0314,
    "Rafale-ASMP":0.0314, "Vulcan-WE177":0.1963,
    # Artyleria v5.9 — 155mm/152mm = ~0.0189m², 203mm Pion = ~0.0324m²
    "M109-HE":0.0189,"M109-EXCAL":0.0189,"PzH-HE":0.0189,"PzH-EXCAL":0.0189,
    "AS90-HE":0.0189,"CAESAR-HE":0.0189,"CAESAR-EXCAL":0.0189,
    "Archer-HE":0.0189,"Archer-EXCAL":0.0189,"K9-HE":0.0189,"K9-EXCAL":0.0189,
    "Msta-HE":0.0182,"Msta-Krasnopol":0.0182,"Akacja-HE":0.0182,
    "Pion-HE":0.0324,"Koalicja-HE":0.0182,"Koalicja-Prec":0.0182,
    "PLZ05-HE":0.0189,"PCL181-HE":0.0189,"ATHOS-HE":0.0189,"Soltam-HE":0.0189,
    "Firtina-HE":0.0189,"ATAGS-HE":0.0189,"Dhanush-HE":0.0189,
    "Krab2-HE":0.0189,"Krab2-EXCAL":0.0189,"Bohdana-HE":0.0189,
    "Type99-HE":0.0189,"K55-HE":0.0189,"AS90AU-HE":0.0189,"M109BR-HE":0.0189,
    "Koksan-HE":0.0227,"Hoveyzeh-HE":0.0189,"Raad122-HE":0.0117,
    "M109PK-HE":0.0189,"M109SA-HE":0.0189,"T69-HE":0.0189,"PzH2000GR-HE":0.0189,
    "K9NO-HE":0.0189,"K9FI-HE":0.0189,"M109CA-HE":0.0189,
    "Gvozdika-HE":0.0117,"Gvozdika2-HE":0.0117,"D30-HE":0.0117,
    "M198-HE":0.0189,"FH70-HE":0.0189,"K9AU-HE":0.0189,
    "Zuzana-HE":0.0189,"Dana-HE":0.0189,"KrabUA-HE":0.0189,
    "F35-B61":0.0452,"B2-B61":0.0452,"B2-B83":0.1963,"B21-B61":0.0452,
    "F15-B61":0.0452,"Tornado-B61":0.0452,"Tu160-nuke":0.1963,"Tu95-nuke":0.1963,"H6K-nuke":0.1963,
    "Emad":0.1963, "Ghadr":0.0707,
    "Scud-B-Cluster":0.0707, "9M723-Cluster":0.0415, "ATACMS-Cluster":0.0380,
    "Tochka-Cluster":0.0452, "Shahab-Cluster":0.0707, "Khorramshahr-Cluster":0.1963,
}

SYSTEMY = {
    # ================================================================
    # ARTYLERIA
    # Format: [nazwa_amunicji, masa_pocisku_kg, predkosc_wylotowa_m/s]
    # ================================================================
    "1":  {"n": "AHS KRAB (155mm)",      "a": {"1": ["M107 HE",   43.2,  827],   # 155mm HE, v0=827 m/s
                                               "2": ["EXCALIBUR",  48.0,  827]}}, # GPS guided, same v0
    "2":  {"n": "M120 RAK (120mm)",      "a": {"1": ["HE STD",    13.5,  354],   # 120mm moździerz, v0=354 m/s
                                               "2": ["SMOKE",      13.0,  320]}}, # dymna
    "3":  {"n": "LEOPARD 2 (120mm)",     "a": {"1": ["APFSDS",     4.6, 1650],   # DM63, penetrator ~4.6kg, v0=1650 m/s
                                               "2": ["HEAT",       13.5, 1140]}}, # DM12
    # ================================================================
    # NATO RAKIETY
    # Format: [nazwa, masa_startowa_kg, predkosc_srednia_m/s]
    # Dla rakiet balistycznych: predkosc_srednia to v_avg (nie v0)
    # ================================================================
    "4":  {"n": "ATACMS (MGM-140)",      "a": {"1": ["ATACMS-A",   1674, 1100], "2": ["ATACMS-B",      1670,  900], "3": ["ATACMS-Cluster", 1674, 1100]}},
    "5":  {"n": "HIMARS (GMLRS)",        "a": {"1": ["GMLRS",       154,  930],  # M31, zasięg 70km
                                               "2": ["GMLRS-ER",   154,  930]}}, # zasięg 150km
    "6":  {"n": "PrSM (MGM-168)",        "a": {"1": ["PrSM",        400, 1400]}}, # zasięg 500km+
    "7":  {"n": "PATRIOT PAC-3",         "a": {"1": ["PAC-3 MSE",   312, 1700]}}, # przechwytywacz, v=1700 m/s
    "8":  {"n": "SM-3 (przechwytywacz)", "a": {"1": ["SM-3",        750, 3000]}}, # Mach 10 = ~3000 m/s
    "9":  {"n": "Lance (MGM-52)",        "a": {"1": ["Lance",       1285,  700]}}, # 1285kg, v_avg ~700 m/s
    # ================================================================
    # NATO ICBM/SLBM
    # ================================================================
    "30": {"n": "Minuteman III (ICBM) ☢","a": {"1": ["Minuteman-III", 35300, 6700]}}, # 35.3t, v_max ~7km/s
    "31": {"n": "Trident II D5 (SLBM) ☢","a": {"1": ["Trident-II",   59000, 7200]}}, # 59t, v_max ~7.2km/s
    # ================================================================
    # ROSJA
    # ================================================================
    "10": {"n": "ISKANDER-M",            "a": {"1": ["9M723",      3800, 2100], "2": ["9M723-Cluster",  3800, 2100]}},
    "11": {"n": "Tochka-U",              "a": {"1": ["Tochka-U",   2000,  900], "2": ["Tochka-Cluster", 2000,  900]}},
    "12": {"n": "Scud-B (R-17)",         "a": {"1": ["Scud-B",     5900, 1500], "2": ["Scud-B-Cluster", 5900, 1500]}},
    "13": {"n": "Kinżał (MiG-31K)",      "a": {"1": ["Kinzal",     4000, 3000]}}, # ~4t, Mach 10 = ~3000 m/s
    "14": {"n": "Kalibr (3M14)",         "a": {"1": ["Kalibr",     1780,  250]}}, # 1.78t, v_przelot=250 m/s (subsonic)
    "15": {"n": "Oniks (P-800)",         "a": {"1": ["Oniks",      3000,  750]}}, # 3t, Mach 2.5 = ~750 m/s
    "16": {"n": "RS-26 Rubezh",          "a": {"1": ["Rubezh",    36000, 6500]}}, # ~36t, v ~6.5km/s
    "17": {"n": "Sarmat (RS-28) ☢",      "a": {"1": ["Sarmat",   210000, 7300]}}, # 210t!, v ~7.3km/s
    "38": {"n": "Bulava (RSM-56) ☢",     "a": {"1": ["Bulava",    36800, 6800]}}, # 36.8t, v ~6.8km/s
    "39": {"n": "Sinewa (RSM-54) ☢",     "a": {"1": ["Sinewa",    40300, 6800]}}, # 40.3t, v ~6.8km/s
    "40": {"n": "Yars (RS-24) ☢",        "a": {"1": ["Yars",      49600, 6800]}}, # 49.6t, v ~6.8km/s
    "41": {"n": "Topol-M (RS-12M2) ☢",  "a": {"1": ["Topol-M",   47200, 6600]}}, # 47.2t, v ~6.6km/s
    "42": {"n": "Avangard (HGV) ☢",      "a": {"1": ["Avangard",  33000, 6700]}}, # ~33t, Mach 20+ = ~6700 m/s
    # ================================================================
    # CHINY
    # ================================================================
    "18": {"n": "DF-11A (SRBM)",         "a": {"1": ["DF-11A",     6000,  900]}}, # 6t, zasięg 600km
    "19": {"n": "DF-21D (ASBM)",         "a": {"1": ["DF-21D",    14700, 3500]}}, # 14.7t, Mach 10+
    "20": {"n": "DF-17 (HGV)",           "a": {"1": ["DF-17",     13000, 3000]}}, # 13t, Mach 10 HGV
    "21": {"n": "DF-26 (IRBM) ☢",        "a": {"1": ["DF-26",     20000, 4000]}}, # 20t, zasięg 4000km
    "22": {"n": "DF-41 (ICBM) ☢",        "a": {"1": ["DF-41",     80000, 7000]}}, # 80t, v ~7km/s
    # ================================================================
    # KOREA PÓŁNOCNA
    # ================================================================
    "23": {"n": "KN-23 (SRBM)",          "a": {"1": ["KN-23",      4000, 1800]}}, # ~4t, Mach 6
    "24": {"n": "Hwasong-12 (IRBM)",     "a": {"1": ["Hwasong-12", 18000, 3000]}}, # ~18t
    "25": {"n": "Hwasong-17 (ICBM) ☢",   "a": {"1": ["Hwasong-17", 80000, 6700]}}, # ~80t
    # ================================================================
    # IRAN
    # ================================================================
    "26": {"n": "Fateh-110 (SRBM)",      "a": {"1": ["Fateh-110",   3450,  900]}}, # 3.45t, zasięg 300km
    "27": {"n": "Zolfaghar (SRBM)",      "a": {"1": ["Zolfaghar",   3700,  900]}}, # 3.7t, zasięg 700km
    "28": {"n": "Shahab-3 (MRBM)",       "a": {"1": ["Shahab-3",   15850, 1700], "2": ["Shahab-Cluster",      15850, 1700]}},
    "29": {"n": "Khorramshahr (MRBM)",   "a": {"1": ["Khorramshahr",22000, 1800], "2": ["Khorramshahr-Cluster", 22000, 1800]}},
    # ================================================================
    # IZRAEL
    # ================================================================
    "32": {"n": "Jericho II (MRBM)",     "a": {"1": ["Jericho-II",  14000, 2500]}}, # 14t, zasięg 1500km
    "33": {"n": "Jericho III (ICBM) ☢",  "a": {"1": ["Jericho-III", 30000, 6000]}}, # 30t, zasięg 6500km
    # ================================================================
    # INDIE
    # ================================================================
    "34": {"n": "Prithvi-II (SRBM)",     "a": {"1": ["Prithvi-II",   4600,  1000]}}, # 4.6t, zasięg 350km
    "35": {"n": "Agni-V (ICBM) ☢",       "a": {"1": ["Agni-V",      50000,  6500]}}, # 50t, zasięg 5000km+
    # ================================================================
    # PAKISTAN
    # ================================================================
    "36": {"n": "Shaheen-III (MRBM) ☢",  "a": {"1": ["Shaheen-III", 24000, 2500]}}, # 24t, zasięg 2750km
    # ================================================================
    # FRANCJA
    # ================================================================
    "37": {"n": "M51 (SLBM) ☢",          "a": {"1": ["M51",         52000, 7000]}}, # 52t, zasięg 10000km
    # ================================================================
    # CHINY dodatkowe
    # ================================================================
    "43": {"n": "DF-5B (ICBM) ☢",         "a": {"1": ["DF-5B",       183000, 6500]}}, # 183t, 13000km
    "44": {"n": "DF-31AG (ICBM) ☢",        "a": {"1": ["DF-31AG",      42000, 6500]}}, # 42t mobilny, 11000km
    "45": {"n": "DF-4 (ICBM) ☢",           "a": {"1": ["DF-4",         82000, 5500]}}, # 82t, stara
    "46": {"n": "DF-15B (SRBM)",           "a": {"1": ["DF-15B",        6200, 1500]}}, # 6.2t, 900km
    "47": {"n": "CJ-10 (Cruise)",          "a": {"1": ["CJ-10",         2500,  250]}}, # cruise 2500km
    "48": {"n": "YJ-12 (ASM)",             "a": {"1": ["YJ-12",         2500, 1000]}}, # hipersoniczna
    "49": {"n": "DF-100 (Cruise)",         "a": {"1": ["DF-100",        2000,  300]}}, # cruise 3000km
    # ================================================================
    # ROSJA dodatkowe
    # ================================================================
    "50": {"n": "9K720 Iskander-K",        "a": {"1": ["9K720",         3800, 2100]}}, # cruise wariant
    "51": {"n": "Kh-47M2 Kinzhal ☢",       "a": {"1": ["Kh-47M2",       4000, 3000]}}, # nuklearny wariant
    "52": {"n": "OTR-21 Tochka",           "a": {"1": ["OTR-21",        2000,  900]}}, # starsza Tochka
    # ================================================================
    # USA/NATO dodatkowe
    # ================================================================
    "53": {"n": "BGM-109 Tomahawk",        "a": {"1": ["Tomahawk",      1300,  250]}}, # cruise 1600km
    "54": {"n": "JASSM-ER (USAF)",         "a": {"1": ["JASSM-ER",      1100,  250]}}, # cruise 1000km
    "55": {"n": "LRASM (Navy)",            "a": {"1": ["LRASM",          900,  250]}}, # cruise 930km
    "56": {"n": "Pershing II ☢",           "a": {"1": ["Pershing-II",   7400, 2000]}}, # 7.4t, 1800km
    "57": {"n": "SM-6 (interceptor)",      "a": {"1": ["SM-6",           900, 1700]}}, # interceptor
    "58": {"n": "GLCM BGM-109G ☢",         "a": {"1": ["GLCM",          1200,  250]}}, # cruise nuklearny
    # ================================================================
    # UK
    # ================================================================
    "59": {"n": "Storm Shadow (UK)",       "a": {"1": ["Storm-Shadow",  1300,  280]}}, # cruise 560km
    "60": {"n": "Trident II D5 (UK) ☢",   "a": {"1": ["Trident-II-UK", 59000, 7200]}}, # UK SLBM
    "61": {"n": "Harpoon (UK Navy)",       "a": {"1": ["Harpoon",        650,  280]}}, # cruise 280km
    # ================================================================
    # NIEMCY
    # ================================================================
    "62": {"n": "TAURUS KEPD 350",         "a": {"1": ["TAURUS",        1400,  280]}}, # cruise 500km
    # ================================================================
    # FRANCJA
    # ================================================================
    "63": {"n": "SCALP-EG",               "a": {"1": ["SCALP",          1300,  280]}}, # cruise 560km
    "64": {"n": "APACHE",                 "a": {"1": ["APACHE",          780,  280]}}, # 130km
    # ================================================================
    # TURCJA
    # ================================================================
    "65": {"n": "SOM (Roketsan)",          "a": {"1": ["SOM",             600,  260]}}, # cruise 250km
    "66": {"n": "Bora (MRBM)",            "a": {"1": ["Bora",            1900, 1000]}}, # 150km SRBM
    "67": {"n": "Kasirga (MRL)",           "a": {"1": ["Kasirga",         270,  800]}}, # 100km
    "68": {"n": "J-600T Yıldırım",        "a": {"1": ["J-600T",          1800, 1000]}}, # 150-900km
    "69": {"n": "TRG-300 Kasirga II",     "a": {"1": ["TRG-300",          600,  900]}}, # 120km
    # ================================================================
    # KOREA POŁUDNIOWA
    # ================================================================
    "70": {"n": "Hyunmoo-2C (MRBM)",      "a": {"1": ["Hyunmoo-2C",     3500, 1500]}}, # 800km
    "71": {"n": "Hyunmoo-3C (Cruise)",    "a": {"1": ["Hyunmoo-3C",     1500,  250]}}, # cruise 1500km
    "72": {"n": "Hyunmoo-4 (SRBM)",       "a": {"1": ["Hyunmoo-4",      3500, 1500]}}, # 800km
    "73": {"n": "Hyunmoo-5 (IRBM)",       "a": {"1": ["Hyunmoo-5",      8000, 2000]}}, # 3000km
    # ================================================================
    # JAPONIA
    # ================================================================
    "74": {"n": "Type-12 (Cruise)",        "a": {"1": ["Type-12",        700,  250]}}, # cruise 200km→1200km
    "75": {"n": "ASM-3 (hipersoniczna)",   "a": {"1": ["ASM-3",          900, 1000]}}, # Mach 3+
    # ================================================================
    # TAJWAN
    # ================================================================
    "76": {"n": "Hsiung-Feng III",         "a": {"1": ["Hsiung-Feng-III", 680, 1000]}}, # Mach 2, 300km
    "77": {"n": "Yun-Feng (LACM)",        "a": {"1": ["Yun-Feng",        900,  280]}}, # cruise 2000km
    # ================================================================
    # ARABIA SAUDYJSKA
    # ================================================================
    "78": {"n": "CSS-5 (DF-21) ☢",        "a": {"1": ["CSS-5",         14700, 3500]}}, # 1700km
    # ================================================================
    # BRAZYLIA
    # ================================================================
    "79": {"n": "SS-300 Astros",           "a": {"1": ["SS-300",          600,  800]}}, # 300km
    "80": {"n": "Astros II MRL",           "a": {"1": ["Astros-II",       150,  600]}}, # 90km
    # ================================================================
    # UKRAINA
    # ================================================================
    "81": {"n": "OTR-21 Tochka-U (UA)",   "a": {"1": ["OTR-21-UA",      2000,  900]}}, # dziedziczone
    "82": {"n": "Vilkha (Ukraina)",        "a": {"1": ["Vilkha",          800,  900]}}, # 70km
    "83": {"n": "Neptune (Ukraina)",       "a": {"1": ["Neptune",        870,  280]}}, # cruise 300km
    "84": {"n": "Grom-2 (SRBM)",          "a": {"1": ["Grom-2",         4500, 1000]}}, # 280km
    "85": {"n": "Hrim-2 (MRBM)",          "a": {"1": ["Hrim-2",         5000, 1500]}}, # 500km
    # ================================================================
    # SZWECJA
    # ================================================================
    "86": {"n": "RBS-15 Mk3",             "a": {"1": ["RBS-15",          800,  280]}}, # cruise 400km
    # ================================================================
    # EGIPT
    # ================================================================
    "87": {"n": "Scud-D (Egipt)",          "a": {"1": ["Scud-D",         5900, 1500]}}, # 700km
    # ================================================================
    # SYRIA
    # ================================================================
    "88": {"n": "M-600 (Syria)",           "a": {"1": ["M-600",          3450,  900]}}, # 300km
    "89": {"n": "Tishreen (Syria)",        "a": {"1": ["Tishreen",        985,  800]}}, # 300km
    # ================================================================
    # ARABIA SAUDYJSKA / ZEA
    # ================================================================
    "90": {"n": "BADR-2000 (SA)",          "a": {"1": ["BADR-2000",      4000, 1000]}}, # 900km
    # ================================================================
    # AZJA PŁD-WSCH (Chiny export)
    # ================================================================
    "91": {"n": "C-802 (eksport CN)",      "a": {"1": ["C-802",           715,  280]}},
    "92": {"n": "C-705 (eksport CN)",      "a": {"1": ["C-705",           315,  280]}},
    # Iran dodatkowe
    "93": {"n": "Emad (MRBM)",             "a": {"1": ["Emad",           16000, 1700]}},
    "94": {"n": "Ghadr (MRBM)",            "a": {"1": ["Ghadr",          17000, 1700]}},
    # USA nowe głowice
    "95": {"n": "B61-12 (bomba) ☢",        "a": {"1": ["B61-12",           320,  280]}}, # 320kg, v~280 m/s (prędkość F-35)
    "96": {"n": "JASSM-ER (W80-4) ☢",      "a": {"1": ["W80-4",           1100,  250]}}, # cruise nuklearny
    "97": {"n": "Trident II (W76-2) ☢",    "a": {"1": ["W76-2",          59000, 7200]}}, # 5kt low-yield SLBM
    # ================================================================
    # SAMOLOTY NUKLEARNE
    # Format: [nazwa_bomby, masa_kg, predkosc_m/s]
    # Strzelec = baza lotnicza, cel = cel bombardowania
    # Tor: cruise na wysokości ~10000m
    # ================================================================
    "98": {"n": "F-35A (NATO) ☢",          "a": {"1": ["F35-B61",          320,  500]}}, # F-35A ~500 m/s (Mach 1.6)
    "99": {"n": "B-2 Spirit (USA) ☢",       "a": {"1": ["B2-B61",           320,  250],  # B-2 ~250 m/s subsonic
                                                   "2": ["B2-B83",          1100,  250]}}, # B83 1.2Mt
    "100":{"n": "B-21 Raider (USA) ☢",      "a": {"1": ["B21-B61",          320,  280]}}, # subsonic stealth
    "101":{"n": "F-15E Strike Eagle ☢",     "a": {"1": ["F15-B61",          320,  600]}}, # F-15E ~600 m/s (Mach 2)
    "102":{"n": "Tornado IDS (NATO) ☢",     "a": {"1": ["Tornado-B61",      320,  400]}}, # ~400 m/s
    "103":{"n": "Tu-160 Blackjack ☢",       "a": {"1": ["Tu160-nuke",      1100,  600]}}, # ~600 m/s (Mach 2)
    "104":{"n": "Tu-95 Bear ☢",             "a": {"1": ["Tu95-nuke",       1100,  180]}}, # ~180 m/s turboprop
    "105":{"n": "H-6K (Chiny) ☢",           "a": {"1": ["H6K-nuke",         900,  220]}},
    # Hiroszima / Nagasaki 1945
    "106":{"n": "B-29 Superfortress ☢",      "a": {"1": ["LittleBoy",       4400,  140],
                                                   "2": ["FatMan",           4670,  140]}},
    # ================================================================
    # NOWE SYSTEMY v5.7
    # ================================================================
    # ROSJA nowe
    "107":{"n": "Zircon (3M22) 🇷🇺",         "a": {"1": ["Zircon",          3000, 2778]}}, # Mach 9, cruise hipersoniczny
    "108":{"n": "Burevestnik ☢ 🇷🇺",          "a": {"1": ["Burevestnik",     2000,  250]}}, # nuklearny cruise, nieogr. zasięg
    "109":{"n": "Tu-22M Backfire ☢ 🇷🇺",      "a": {"1": ["Tu22M-nuke",      1100,  550]}}, # bombowiec średniego zasięgu
    # USA nowe
    "110":{"n": "B-52 Stratofortress ☢ 🇺🇸",  "a": {"1": ["B52-ALCM",        1000,  250],  # AGM-86 ALCM cruise nuklearny
                                                   "2": ["B52-B61",           320,  250]}}, # B61-12
    "111":{"n": "AGM-86 ALCM ☢ 🇺🇸",          "a": {"1": ["ALCM",            1430,  250]}}, # cruise nuklearny 2500km
    "112":{"n": "THAAD 🇺🇸",                  "a": {"1": ["THAAD",           900, 2800]}}, # interceptor
    # CHINY nowe
    "113":{"n": "DF-27 (IRBM) 🇨🇳",           "a": {"1": ["DF-27",          20000, 4000]}}, # hipersoniczny HGV ~8000km
    "114":{"n": "DF-ZF (HGV) 🇨🇳",            "a": {"1": ["DF-ZF",          15000, 3000]}}, # hipersoniczny szybowiec
    # KOREA PÓŁNOCNA nowe
    "115":{"n": "Hwasong-18 (ICBM) ☢ 🇰🇵",    "a": {"1": ["Hwasong-18",     80000, 6800]}}, # nowy ICBM 2023, paliwo stałe
    "116":{"n": "Hwasong-15 (ICBM) ☢ 🇰🇵",    "a": {"1": ["Hwasong-15",     80000, 6500]}}, # 2017
    # IRAN nowe
    "117":{"n": "Fattah (hiperson.) 🇮🇷",      "a": {"1": ["Fattah",          1400, 4000]}}, # Mach 13+, 1400km
    "118":{"n": "Kheibar Shekan 🇮🇷",          "a": {"1": ["Kheibar",         3500, 1700]}}, # MRBM 2000km
    # INDIE nowe
    "119":{"n": "Agni-VI (ICBM) ☢ 🇮🇳",       "a": {"1": ["Agni-VI",        55000, 6800]}}, # ~8000km, MIRVed
    "120":{"n": "BrahMos 🇮🇳",                 "a": {"1": ["BrahMos",         3000,  880]}}, # cruise Mach 2.8, 450km
    # PAKISTAN nowe
    "121":{"n": "Ababeel ☢ 🇵🇰",               "a": {"1": ["Ababeel",        17000, 2500]}}, # MRBM MIRVed, 2200km
    "122":{"n": "Ra'ad ALCM ☢ 🇵🇰",            "a": {"1": ["Raad",             500,  250]}},
    # ================================================================
    # NOWE SYSTEMY v5.8
    # ================================================================
    "123":{"n": "Kh-101 (cruise) 🇷🇺",          "a": {"1": ["Kh-101",          2400,  250]}},
    "124":{"n": "Kh-102 ☢ (cruise) 🇷🇺",         "a": {"1": ["Kh-102",          2400,  250]}},
    "125":{"n": "AGM-183 ARRW 🇺🇸",              "a": {"1": ["ARRW",             900, 6000]}},
    "126":{"n": "B-1B Lancer ✈️ 🇺🇸",            "a": {"1": ["B1B-conv",       86000,  490]}},
    "127":{"n": "JL-2 (SLBM) ☢ 🇨🇳",             "a": {"1": ["JL-2",           42000, 6500]}},
    "128":{"n": "JL-3 (SLBM) ☢ 🇨🇳",             "a": {"1": ["JL-3",           50000, 7000]}},
    "129":{"n": "Pukguksong-3 ☢ 🇰🇵",             "a": {"1": ["Pukguksong-3",   23800, 6000]}},
    "130":{"n": "K-4 (SLBM) ☢ 🇮🇳",              "a": {"1": ["K-4",            17000, 3500]}},
    "131":{"n": "K-15 Sagarika ☢ 🇮🇳",            "a": {"1": ["K-15",            6000, 2800]}},
    "132":{"n": "ASMP-A ☢ 🇫🇷",                   "a": {"1": ["ASMP-A",           860,  900]}},
    "133":{"n": "Rafale F3 ☢ ✈️ 🇫🇷",             "a": {"1": ["Rafale-ASMP",      860,  550]}},
    "134":{"n": "Avro Vulcan B2 ☢ ✈️ 🇬🇧",        "a": {"1": ["Vulcan-WE177",    9750,  270]}},
    # ================================================================
    # ARTYLERIA — v5.9
    # ================================================================
    # USA
    "135":{"n": "M109A7 Paladin 🇺🇸",        "a": {"1": ["M109-HE",       43.2,  827],
                                                   "2": ["M109-EXCAL",     48.0,  827]}},
    # NIEMCY
    "136":{"n": "PzH 2000 🇩🇪",               "a": {"1": ["PzH-HE",        43.5,  945],   # v0=945 m/s
                                                   "2": ["PzH-EXCAL",     48.0,  945]}},
    # UK
    "137":{"n": "AS-90 🇬🇧",                  "a": {"1": ["AS90-HE",       43.2,  827]}},
    # FRANCJA
    "138":{"n": "CAESAR (155mm) 🇫🇷",          "a": {"1": ["CAESAR-HE",     43.2,  930],
                                                   "2": ["CAESAR-EXCAL",  48.0,  930]}},
    # SZWECJA
    "139":{"n": "Archer (FH77BW) 🇸🇪",         "a": {"1": ["Archer-HE",     43.2,  945],
                                                   "2": ["Archer-EXCAL",  48.0,  945]}},
    # KOREA PŁD
    "140":{"n": "K9 Thunder 🇰🇷",              "a": {"1": ["K9-HE",         43.2,  900],
                                                   "2": ["K9-EXCAL",      48.0,  900]}},
    # ROSJA
    "141":{"n": "2S19 Msta-S 🇷🇺",             "a": {"1": ["Msta-HE",       43.5,  828],   # 152mm
                                                   "2": ["Msta-Krasnopol", 50.0,  828]}}, # precyzyjny
    "142":{"n": "2S3 Akacja 🇷🇺",              "a": {"1": ["Akacja-HE",     43.5,  655]}}, # 152mm
    "143":{"n": "2S7 Pion 🇷🇺",                "a": {"1": ["Pion-HE",      110.0,  960]}}, # 203mm — największa!
    "144":{"n": "2S35 Koalicja 🇷🇺",           "a": {"1": ["Koalicja-HE",   43.5,  1100],  # 152mm, aktywna
                                                   "2": ["Koalicja-Prec", 50.0,  1100]}},
    # CHINY
    "145":{"n": "PLZ-05 (155mm) 🇨🇳",          "a": {"1": ["PLZ05-HE",      43.2,  930]}},
    "146":{"n": "PCL-181 (155mm) 🇨🇳",         "a": {"1": ["PCL181-HE",     43.2,  930]}},
    # IZRAEL
    "147":{"n": "ATHOS 2052 🇮🇱",              "a": {"1": ["ATHOS-HE",      43.2,  827]}},
    "148":{"n": "Soltam M-71 🇮🇱",             "a": {"1": ["Soltam-HE",     43.2,  827]}},
    # TURCJA
    "149":{"n": "T-155 Firtina 🇹🇷",           "a": {"1": ["Firtina-HE",    43.2,  827]}},
    # INDIE
    "150":{"n": "ATAGS (155mm) 🇮🇳",           "a": {"1": ["ATAGS-HE",      43.2,  900]}},
    "151":{"n": "Dhanush (155mm) 🇮🇳",         "a": {"1": ["Dhanush-HE",    43.2,  827]}},
    # POLSKA
    "152":{"n": "Krab (Kopia) 🇵🇱",            "a": {"1": ["Krab2-HE",      43.2,  827],
                                                   "2": ["Krab2-EXCAL",   48.0,  827]}},
    # UKRAINA
    "153":{"n": "2S22 Bohdana 🇺🇦",            "a": {"1": ["Bohdana-HE",    43.2,  827]}}, # 155mm ukraińska
    # JAPONIA
    "154":{"n": "Type 99 (155mm) 🇯🇵",         "a": {"1": ["Type99-HE",     43.2,  900]}},
    # KOREA PŁD dodatkowe
    "155":{"n": "K55A1 (155mm) 🇰🇷",           "a": {"1": ["K55-HE",        43.2,  827]}},
    # AUSTRALIA
    "156":{"n": "AS-90 Braveheart 🇦🇺",        "a": {"1": ["AS90AU-HE",     43.2,  827]}},
    # BRAZYLIA
    "157":{"n": "M109 BR (155mm) 🇧🇷",         "a": {"1": ["M109BR-HE",     43.2,  827]}},
    # ================================================================
    # ARTYLERIA — brakujące kraje v5.9b
    # ================================================================
    "158":{"n": "Koksan M-1978 🇰🇵",    "a": {"1": ["Koksan-HE",    100.0,  900]}}, # 170mm, zasięg 60km!
    "159":{"n": "Hoveyzeh (155mm) 🇮🇷", "a": {"1": ["Hoveyzeh-HE",   43.2,  827]}},
    "160":{"n": "Raad (122mm) 🇮🇷",     "a": {"1": ["Raad122-HE",    27.3,  690]}},
    "161":{"n": "M109 Pakistan 🇵🇰",    "a": {"1": ["M109PK-HE",     43.2,  827]}},
    "162":{"n": "M109 Saudi 🇸🇦",       "a": {"1": ["M109SA-HE",     43.2,  827]}},
    "163":{"n": "T-69 (155mm) 🇹🇼",     "a": {"1": ["T69-HE",        43.2,  827]}},
    "164":{"n": "PzH 2000 🇬🇷",         "a": {"1": ["PzH2000GR-HE",  43.5,  945]}},
    "165":{"n": "K9 Thunder 🇳🇴",       "a": {"1": ["K9NO-HE",       43.2,  900]}},
    "166":{"n": "K9 Thunder 🇫🇮",       "a": {"1": ["K9FI-HE",       43.2,  900]}},
    "167":{"n": "M109A4 Canada 🇨🇦",    "a": {"1": ["M109CA-HE",     43.2,  827]}},
    "168":{"n": "2S1 Gvozdika 🇮🇶",     "a": {"1": ["Gvozdika-HE",   15.5,  690]}},
    "169":{"n": "2S1 Gvozdika 🇷🇺",     "a": {"1": ["Gvozdika2-HE",  15.5,  690]}},
    "170":{"n": "D-30 (122mm) 🇸🇾",     "a": {"1": ["D30-HE",        21.8,  690]}},
    "171":{"n": "M198 (155mm) 🇺🇸",     "a": {"1": ["M198-HE",       43.2,  827]}},
    "172":{"n": "FH-70 (155mm) 🇮🇹",    "a": {"1": ["FH70-HE",       43.2,  827]}},
    "173":{"n": "K9 Thunder 🇦🇺",       "a": {"1": ["K9AU-HE",       43.2,  900]}},
    "174":{"n": "ZUZANA 2 🇸🇰",         "a": {"1": ["Zuzana-HE",     43.2,  945]}},
    "175":{"n": "Dana M2 🇨🇿",          "a": {"1": ["Dana-HE",       43.2,  827]}},
    "176":{"n": "Krab (UA) 🇺🇦",        "a": {"1": ["KrabUA-HE",     43.2,  827]}},
}

state = {
    "my_pos":      {"lat": 54.1944, "lon": 16.1722},
    "active_sys":  None,
    "active_ammo": None,
    "shot_history": [],
    "r_client": redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
}

MAP_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
    <title>BALISTIC SYSTEM V5</title>
    <!-- Leaflet (artyleria i rakiety <500km) -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- CesiumJS (rakiety >500km — kula ziemska 3D) -->
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Widgets/widgets.css" rel="stylesheet"/>
    <script src="https://cesium.com/downloads/cesiumjs/releases/1.114/Build/Cesium/Cesium.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { display: flex; height: 100vh; font-family: monospace; background: #0a0a0a; }
        #map-container { position: relative; flex: 1; }
        #map    { height: 100vh; width: 100%; }
        #cesium { height: 100vh; width: 100%; display: none; }
        /* Przycisk przełączania widoku */
        #view-toggle {
            position: absolute; top: 10px; right: 10px; z-index: 1000;
            background: rgba(13,17,23,0.90); color: #58a6ff;
            border: 1px solid #58a6ff; padding: 6px 12px;
            font-family: monospace; font-size: 11px; cursor: pointer;
        }
        #view-toggle:hover { background: #58a6ff; color: #0d1117; }
        #panel {
            width: 320px; min-width: 320px;
            background: #0d1117; color: #c9d1d9;
            display: flex; flex-direction: column;
            border-left: 1px solid #21262d; overflow: hidden;
        }
        #panel-header { background: #161b22; padding: 12px 16px; border-bottom: 1px solid #21262d; }
        #panel-header h2 { color: #58a6ff; font-size: 14px; letter-spacing: 2px; }
        #panel-header .sub { color: #8b949e; font-size: 11px; margin-top: 2px; }
        #result-box { padding: 12px 16px; border-bottom: 1px solid #21262d; min-height: 230px; }
        #result-box .label { color: #8b949e; font-size: 10px; letter-spacing: 1px; margin-top: 5px; }
        #result-box .val   { color: #e6edf3; font-size: 13px; }
        #result-box .highlight { color: #3fb950; font-size: 15px; font-weight: bold; }
        #result-box .waiting { color: #484f58; font-size: 12px; padding: 30px 0; text-align: center; }
        #history-header {
            padding: 8px 16px; background: #161b22; border-bottom: 1px solid #21262d;
            color: #8b949e; font-size: 11px; letter-spacing: 1px;
            display: flex; justify-content: space-between; align-items: center;
        }
        #history-header button {
            background: #21262d; color: #f85149; border: 1px solid #f85149;
            padding: 2px 8px; font-size: 10px; cursor: pointer; font-family: monospace;
        }
        #history-list { flex: 1; overflow-y: auto; padding: 4px 0; }
        .hist-item { padding: 6px 16px; border-bottom: 1px solid #161b22; cursor: pointer; transition: background 0.15s; }
        .hist-item:hover { background: #161b22; }
        .hist-item .hi-top { display: flex; justify-content: space-between; }
        .hist-item .hi-ammo { color: #d2a8ff; font-size: 11px; }
        .hist-item .hi-dist { color: #79c0ff; font-size: 11px; }
        .hist-item .hi-time { color: #484f58; font-size: 10px; margin-top: 2px; }
        #actions { padding: 10px 16px; border-top: 1px solid #21262d; display: flex; gap: 8px; }
        #actions button { flex: 1; padding: 7px 4px; font-family: monospace; font-size: 11px; cursor: pointer; border: 1px solid; letter-spacing: 1px; }
        .btn-fire   { background: #0d1117; color: #3fb950; border-color: #3fb950 !important; font-weight: bold; font-size: 12px !important; }
        .btn-fire:hover:not(:disabled) { background: #3fb950; color: #0d1117; }
        .btn-cancel { background: #0d1117; color: #f85149; border-color: #f85149 !important; }
        .btn-cancel:hover { background: #f85149; color: #0d1117; }
        .btn-pdf { background: #0d1117; color: #f0883e; border-color: #f0883e !important; }
        .btn-pdf:hover { background: #f0883e; color: #0d1117; }
        .map-hint {
            position: absolute; top: 10px; left: 10px; z-index: 1000;
            background: rgba(13,17,23,0.85); color: #58a6ff;
            padding: 8px 12px; border: 1px solid #21262d;
            font-family: monospace; font-size: 11px; pointer-events: none;
        }
        #spinner { display:none; color: #3fb950; font-size: 11px; padding: 4px 0; text-align: center; }
        /* Cesium toolbar ukrycie zbędnych elementów */
        .cesium-viewer-toolbar { display: none !important; }
        .cesium-viewer-animationContainer { display: none !important; }
        .cesium-viewer-timelineContainer { display: none !important; }
        .cesium-viewer-bottom { display: none !important; }
    </style>
</head>
<body>
<div id="map-container">
    <div class="map-hint" id="map-hint">PPM: Przesuń strzelca &nbsp;|&nbsp; LPM: Zaznacz cele &nbsp;|&nbsp; OGIEŃ: strzał do wszystkich</div>
    <button id="view-toggle" onclick="toggleView()">🌍 Widok 3D</button>
    <button id="layer-toggle" onclick="toggleLayer()" style="position:absolute;top:50px;right:10px;z-index:1000;background:rgba(13,17,23,0.90);color:#58a6ff;border:1px solid #58a6ff;padding:6px 12px;font-family:monospace;font-size:11px;cursor:pointer;">🛰️ Satelita</button>
    <button id="urban-toggle" onclick="toggleUrbanMode()" style="position:absolute;top:90px;right:10px;z-index:1000;background:rgba(13,17,23,0.90);color:#8b949e;border:1px solid #444;padding:6px 12px;font-family:monospace;font-size:11px;cursor:pointer;" title="Urban Canyon Effect — fala kanałuje się między budynkami">🏙️ Urban OFF</button>
    <div id="map" style="height:100vh;"></div>
    <div id="cesium"></div>
</div>
<div id="panel">
    <div id="panel-header">
        <h2>&#x2B21; BALISTIC SYSTEM V5</h2>
        <div style="margin-top:8px;">
            <div class="label">SYSTEM</div>
            <select id="sel-sys" onchange="onSysChange()" style="width:100%; background:#0d1117; color:#c9d1d9; border:1px solid #21262d; font-family:monospace; font-size:11px; padding:3px;">
                <optgroup label="━━ 🇵🇱 POLSKA — ARTYLERIA ━━">
                <option value="1">AHS KRAB (155mm)</option>
                <option value="2">M120 RAK (120mm)</option>
                <option value="3">LEOPARD 2 (120mm)</option>
                <option value="152">Krab (155mm) — nowszy</option>
                </optgroup>
                <optgroup label="━━ 🇺🇸 USA — ARTYLERIA ━━">
                <option value="135">M109A7 Paladin (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇺🇸 USA — RAKIETY ━━">
                <option value="4">ATACMS (MGM-140)</option>
                <option value="5">HIMARS (GMLRS)</option>
                <option value="6">PrSM (MGM-168)</option>
                <option value="7">PATRIOT PAC-3</option>
                <option value="8">SM-3</option>
                <option value="9">Lance (MGM-52) ☢</option>
                <option value="56">Pershing II ☢</option>
                <option value="58">GLCM ☢</option>
                <option value="30">Minuteman III ☢</option>
                <option value="31">Trident II D5 ☢</option>
                <option value="97">Trident II (W76-2 5kt) ☢</option>
                </optgroup>
                <optgroup label="━━ 🇺🇸 USA — CRUISE ━━">
                <option value="53">Tomahawk (BGM-109)</option>
                <option value="54">JASSM-ER</option>
                <option value="55">LRASM</option>
                <option value="57">SM-6</option>
                <option value="112">THAAD (interceptor)</option>
                <option value="111">AGM-86 ALCM ☢</option>
                <option value="125">AGM-183 ARRW (Mach 20)</option>
                <option value="95">B61-12 (bomba) ☢</option>
                <option value="96">JASSM-ER (W80-4) ☢</option>
                </optgroup>
                <optgroup label="━━ 🇺🇸 USA — SAMOLOTY ✈️ ━━">
                <option value="106">B-29 Superfortress ☢ (1945)</option>
                <option value="110">B-52 Stratofortress ☢</option>
                <option value="126">B-1B Lancer</option>
                <option value="98">F-35A ☢</option>
                <option value="99">B-2 Spirit ☢</option>
                <option value="100">B-21 Raider ☢</option>
                <option value="101">F-15E Strike Eagle ☢</option>
                </optgroup>
                <optgroup label="━━ 🇷🇺 ROSJA — ARTYLERIA ━━">
                <option value="141">2S19 Msta-S (152mm)</option>
                <option value="142">2S3 Akacja (152mm)</option>
                <option value="143">2S7 Pion (203mm)</option>
                <option value="144">2S35 Koalicja (152mm)</option>
                </optgroup>
                <optgroup label="━━ 🇷🇺 ROSJA — RAKIETY ━━">
                <option value="10">ISKANDER-M</option>
                <option value="11">Tochka-U</option>
                <option value="12">Scud-B (R-17)</option>
                <option value="52">OTR-21 Tochka</option>
                <option value="50">9K720 Iskander-K</option>
                <option value="13">Kinżał (MiG-31K)</option>
                <option value="51">Kh-47M2 Kinzhal ☢</option>
                <option value="16">RS-26 Rubezh ☢</option>
                <option value="17">Sarmat (RS-28) ☢</option>
                <option value="38">Bulava (RSM-56) ☢</option>
                <option value="39">Sinewa (RSM-54) ☢</option>
                <option value="40">Yars (RS-24) ☢</option>
                <option value="41">Topol-M (RS-12M2) ☢</option>
                <option value="42">Avangard (HGV) ☢</option>
                </optgroup>
                <optgroup label="━━ 🇷🇺 ROSJA — CRUISE ━━">
                <option value="14">Kalibr (3M14)</option>
                <option value="15">Oniks (P-800)</option>
                <option value="107">Zircon (3M22) — hiperson.</option>
                <option value="108">Burevestnik ☢</option>
                <option value="123">Kh-101 (strategiczny)</option>
                <option value="124">Kh-102 ☢ (strategiczny)</option>
                </optgroup>
                <optgroup label="━━ 🇷🇺 ROSJA — SAMOLOTY ✈️ ━━">
                <option value="103">Tu-160 Blackjack ☢</option>
                <option value="104">Tu-95 Bear ☢</option>
                <option value="109">Tu-22M Backfire ☢</option>
                </optgroup>
                <optgroup label="━━ 🇨🇳 CHINY — ARTYLERIA ━━">
                <option value="145">PLZ-05 (155mm)</option>
                <option value="146">PCL-181 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇨🇳 CHINY — RAKIETY ━━">
                <option value="18">DF-11A (SRBM)</option>
                <option value="46">DF-15B (SRBM)</option>
                <option value="19">DF-21D (ASBM)</option>
                <option value="20">DF-17 (HGV)</option>
                <option value="114">DF-ZF (HGV)</option>
                <option value="21">DF-26 (IRBM) ☢</option>
                <option value="113">DF-27 (IRBM) ☢</option>
                <option value="43">DF-5B (ICBM) ☢</option>
                <option value="44">DF-31AG (ICBM) ☢</option>
                <option value="45">DF-4 (ICBM) ☢</option>
                <option value="22">DF-41 (ICBM) ☢</option>
                <option value="127">JL-2 (SLBM) ☢</option>
                <option value="128">JL-3 (SLBM) ☢</option>
                </optgroup>
                <optgroup label="━━ 🇨🇳 CHINY — CRUISE ━━">
                <option value="47">CJ-10</option>
                <option value="48">YJ-12 (ASM)</option>
                <option value="49">DF-100</option>
                <option value="91">C-802 (eksport)</option>
                <option value="92">C-705 (eksport)</option>
                </optgroup>
                <optgroup label="━━ 🇨🇳 CHINY — SAMOLOTY ✈️ ━━">
                <option value="105">H-6K ☢</option>
                </optgroup>
                <optgroup label="━━ 🇰🇵 KOREA PŁN — ARTYLERIA ━━">
                <option value="158">Koksan M-1978 (170mm)</option>
                </optgroup>
                <optgroup label="━━ 🇰🇵 KOREA PŁN — RAKIETY ━━">
                <option value="23">KN-23 (SRBM)</option>
                <option value="24">Hwasong-12 (IRBM)</option>
                <option value="25">Hwasong-17 (ICBM) ☢</option>
                <option value="115">Hwasong-18 (ICBM) ☢</option>
                <option value="116">Hwasong-15 (ICBM) ☢</option>
                <option value="129">Pukguksong-3 (SLBM) ☢</option>
                </optgroup>
                <optgroup label="━━ 🇮🇷 IRAN — ARTYLERIA ━━">
                <option value="159">Hoveyzeh (155mm)</option>
                <option value="160">Raad (122mm)</option>
                </optgroup>
                <optgroup label="━━ 🇮🇷 IRAN — RAKIETY ━━">
                <option value="26">Fateh-110 (SRBM)</option>
                <option value="27">Zolfaghar (SRBM)</option>
                <option value="28">Shahab-3 (MRBM)</option>
                <option value="29">Khorramshahr (MRBM)</option>
                <option value="93">Emad (MRBM)</option>
                <option value="94">Ghadr (MRBM)</option>
                <option value="117">Fattah (hiperson.)</option>
                <option value="118">Kheibar Shekan</option>
                </optgroup>
                <optgroup label="━━ 🇮🇱 IZRAEL — ARTYLERIA ━━">
                <option value="147">ATHOS 2052 (155mm)</option>
                <option value="148">Soltam M-71 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇮🇱 IZRAEL — RAKIETY ━━">
                <option value="32">Jericho II (MRBM)</option>
                <option value="33">Jericho III (ICBM) ☢</option>
                </optgroup>
                <optgroup label="━━ 🇮🇳 INDIE — ARTYLERIA ━━">
                <option value="150">ATAGS (155mm)</option>
                <option value="151">Dhanush (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇮🇳 INDIE — RAKIETY ━━">
                <option value="34">Prithvi-II (SRBM)</option>
                <option value="35">Agni-V (ICBM) ☢</option>
                <option value="119">Agni-VI (ICBM) ☢</option>
                <option value="130">K-4 (SLBM) ☢</option>
                <option value="131">K-15 Sagarika (SLBM) ☢</option>
                <option value="120">BrahMos (Cruise)</option>
                </optgroup>
                <optgroup label="━━ 🇵🇰 PAKISTAN — ARTYLERIA ━━">
                <option value="161">M109 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇵🇰 PAKISTAN — RAKIETY ━━">
                <option value="36">Shaheen-III (MRBM) ☢</option>
                <option value="121">Ababeel (MRBM) ☢</option>
                <option value="122">Ra'ad ALCM ☢</option>
                </optgroup>
                <optgroup label="━━ 🇬🇧 UK — ARTYLERIA ━━">
                <option value="137">AS-90 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇬🇧 UK — RAKIETY ━━">
                <option value="59">Storm Shadow</option>
                <option value="60">Trident II D5 ☢</option>
                <option value="61">Harpoon</option>
                <option value="134">Avro Vulcan B2 ☢ ✈️ (hist.)</option>
                </optgroup>
                <optgroup label="━━ 🇫🇷 FRANCJA — ARTYLERIA ━━">
                <option value="138">CAESAR (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇫🇷 FRANCJA — RAKIETY ━━">
                <option value="37">M51 (SLBM) ☢</option>
                <option value="63">SCALP-EG</option>
                <option value="64">APACHE</option>
                <option value="132">ASMP-A ☢</option>
                <option value="133">Rafale F3 ☢ ✈️</option>
                </optgroup>
                <optgroup label="━━ 🇩🇪 NIEMCY — ARTYLERIA ━━">
                <option value="136">PzH 2000 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇩🇪 NIEMCY — RAKIETY ━━">
                <option value="62">TAURUS KEPD 350</option>
                </optgroup>
                <optgroup label="━━ 🇩🇪🇮🇹🇧🇪 NATO — SAMOLOTY ✈️ ━━">
                <option value="102">Tornado IDS ☢</option>
                </optgroup>
                <optgroup label="━━ 🇹🇷 TURCJA — ARTYLERIA ━━">
                <option value="149">T-155 Firtina (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇹🇷 TURCJA — RAKIETY ━━">
                <option value="65">SOM (Roketsan)</option>
                <option value="66">Bora (MRBM)</option>
                <option value="67">Kasirga (MRL)</option>
                <option value="68">J-600T Yıldırım</option>
                <option value="69">TRG-300</option>
                </optgroup>
                <optgroup label="━━ 🇰🇷 KOREA PŁD — ARTYLERIA ━━">
                <option value="140">K9 Thunder (155mm)</option>
                <option value="155">K55A1 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇰🇷 KOREA PŁD — RAKIETY ━━">
                <option value="70">Hyunmoo-2C</option>
                <option value="71">Hyunmoo-3C (Cruise)</option>
                <option value="72">Hyunmoo-4</option>
                <option value="73">Hyunmoo-5 (IRBM)</option>
                </optgroup>
                <optgroup label="━━ 🇯🇵 JAPONIA — ARTYLERIA ━━">
                <option value="154">Type 99 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇯🇵 JAPONIA — RAKIETY ━━">
                <option value="74">Type-12 (Cruise)</option>
                <option value="75">ASM-3</option>
                </optgroup>
                <optgroup label="━━ 🇹🇼 TAJWAN — ARTYLERIA ━━">
                <option value="163">T-69 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇹🇼 TAJWAN — RAKIETY ━━">
                <option value="76">Hsiung-Feng III</option>
                <option value="77">Yun-Feng (LACM)</option>
                </optgroup>
                <optgroup label="━━ 🇸🇦 ARABIA SAUDYJSKA — ARTYLERIA ━━">
                <option value="162">M109 (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇸🇦 ARABIA SAUDYJSKA — RAKIETY ━━">
                <option value="78">CSS-5 (DF-21) ☢</option>
                <option value="90">BADR-2000</option>
                </optgroup>
                <optgroup label="━━ 🇺🇦 UKRAINA — ARTYLERIA ━━">
                <option value="153">2S22 Bohdana (155mm)</option>
                <option value="176">Krab (155mm, PL→UA)</option>
                </optgroup>
                <optgroup label="━━ 🇺🇦 UKRAINA — RAKIETY ━━">
                <option value="81">OTR-21 Tochka-U</option>
                <option value="82">Vilkha</option>
                <option value="83">Neptune (Cruise)</option>
                <option value="84">Grom-2</option>
                <option value="85">Hrim-2</option>
                </optgroup>
                <optgroup label="━━ 🇸🇪 SZWECJA — ARTYLERIA ━━">
                <option value="139">Archer FH77BW (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇸🇪 SZWECJA — RAKIETY ━━">
                <option value="86">RBS-15 Mk3</option>
                </optgroup>
                <optgroup label="━━ 🇧🇷 BRAZYLIA — ARTYLERIA ━━">
                <option value="157">M109 BR (155mm)</option>
                </optgroup>
                <optgroup label="━━ 🇧🇷 BRAZYLIA — RAKIETY ━━">
                <option value="79">SS-300 Astros</option>
                <option value="80">Astros II MRL</option>
                </optgroup>
                <optgroup label="━━ 🇪🇬 EGIPT ━━">
                <option value="87">Scud-D</option>
                </optgroup>
                <optgroup label="━━ 🇸🇾 SYRIA ━━">
                <option value="88">M-600</option>
                <option value="89">Tishreen</option>
                </optgroup>
                <optgroup label="━━ 🇦🇺 AUSTRALIA — ARTYLERIA ━━">
                <option value="156">AS-90 Braveheart (155mm)</option>
                </optgroup>
            </select>
        </div>
        <div style="margin-top:6px;">
            <div class="label">AMUNICJA</div>
            <select id="sel-ammo" onchange="onAmmoChange()" style="width:100%; background:#0d1117; color:#c9d1d9; border:1px solid #21262d; font-family:monospace; font-size:11px; padding:3px;">
            </select>
        </div>
        <div id="sys-status" style="color:#3fb950; font-size:10px; margin-top:4px;">&#x25CF; Gotowy</div>
        <div id="processor-status" style="color:#484f58; font-size:10px; margin-top:2px;">&#x25CF; Sprawdzanie procesora...</div>
    </div>
    <div id="result-box">
        <div class="waiting" id="waiting-msg">&#x23F3; Oczekiwanie na strzał...</div>
        <div id="result-content" style="display:none;">
            <div class="label">JEDNOSTKA / POCISK</div><div class="val" id="r-unit">—</div>
            <div class="label">DYSTANS</div><div class="highlight" id="r-dist">—</div>
            <div class="label">AZYMUT</div><div class="val" id="r-az">—</div>
            <div class="label">KĄT LUFY</div><div class="val" id="r-angle">—</div>
            <div class="label">APOGEUM</div><div class="val" id="r-apogee" style="display:none;">—</div>
            <div class="label">CZAS LOTU</div><div class="val" id="r-tof">—</div>
            <div class="label">DRYFT WIATRU</div><div class="val" id="r-drift">—</div>
            <div class="label">ENERGIA / CEP</div><div class="val" id="r-ek">—</div>
            <div class="label">WARUNKI</div><div class="val" id="r-weather">—</div>
            <div id="r-blast"></div>
        </div>
        <div id="spinner">&#x231B; Obliczanie...</div>
    </div>
    <div id="history-header">
        <span>HISTORIA STRZAŁÓW</span>
        <button onclick="clearHistory()">&#x2715; WYCZYŚĆ</button>
    </div>
    <div id="history-list"></div>
    <div id="actions">
        <button id="btn-fire" class="btn-fire" onclick="fireAll()" disabled style="opacity:0.4">OGIEŃ</button>
        <button class="btn-cancel" onclick="cancelTargets()">&#x2715; ANULUJ CELE</button>
        <button class="btn-pdf" onclick="exportPDF()">&#x2B07; PDF</button>
    </div>
</div>
<script>
var TOKEN = "{{token}}";
var MISSILE_DIST_THRESHOLD = 500000; // 500km — próg przełączenia na Cesium

// ===================== LEAFLET =====================
var map;
// Usuń stary kontener Leaflet jeśli istnieje
if (window._balistic_map) {
    window._balistic_map.remove();
    window._balistic_map = null;
}
map = L.map('map', { preferCanvas: true }).setView([{{lat}}, {{lon}}], 14);
window._balistic_map = map;

var canvasRenderer = L.canvas({ padding: 1.0, tolerance: 10 });
var shotDataStore = {};

// Warstwy mapy
var layers = {
    hybrid:    L.tileLayer('https://mt1.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}', { maxZoom:20, attribution:'Google Hybrid' }),
    satellite: L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', { maxZoom:20, attribution:'Google Satellite' }),
    road:      L.tileLayer('https://mt1.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}', { maxZoom:20, attribution:'Google Maps EN' }),
};
var layerOrder = ['hybrid', 'satellite', 'road'];
var layerNames = { hybrid: '🛰️ Hybryda', satellite: '🌑 Czysta sat.', road: '🗺️ Mapa' };
var currentLayer = 'hybrid';
layers.hybrid.addTo(map);

function toggleLayer() {
    var idx = layerOrder.indexOf(currentLayer);
    var nextKey = layerOrder[(idx + 1) % layerOrder.length];
    map.removeLayer(layers[currentLayer]);
    layers[nextKey].addTo(map);
    currentLayer = nextKey;
    document.getElementById('layer-toggle').textContent = layerNames[nextKey];
}

// ===================== CESIUM =====================
var cesiumViewer = null;
var cesiumActive = false;

async function initCesium() {
    if (cesiumViewer) return;
    Cesium.Ion.defaultAccessToken = '{{cesium_token}}';
    cesiumViewer = new Cesium.Viewer('cesium', {
        terrainProvider: await Cesium.CesiumTerrainProvider.fromIonAssetId(1),
        baseLayerPicker: false,
        navigationHelpButton: false,
        sceneModePicker: false,
        geocoder: false,
        homeButton: false,
        fullscreenButton: false,
        animation: false,
        timeline: false,
    });
    cesiumViewer.scene.globe.enableLighting = true;
}

async function toggleView() {
    cesiumActive = !cesiumActive;
    var btn = document.getElementById('view-toggle');
    var hint = document.getElementById('map-hint');
    if (cesiumActive) {
        await initCesium();
        document.getElementById('map').style.display = 'none';
        document.getElementById('cesium').style.display = 'block';
        btn.textContent = '🗺️ Widok 2D';
        hint.textContent = 'Widok 3D — kula ziemska';
        // Przenieś kamerę nad pozycję strzelca
        var sll = shooter.getLatLng();
        cesiumViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(sll.lng, sll.lat, 2000000),
            duration: 2
        });
    } else {
        document.getElementById('map').style.display = 'block';
        document.getElementById('cesium').style.display = 'none';
        btn.textContent = '🌍 Widok 3D';
        hint.textContent = 'PPM: Przesuń strzelca | LPM: Zaznacz cele | OGIEŃ: strzał do wszystkich';
    }
}

// Automatyczne przełączenie na Cesium gdy dystans > 500km
function autoSwitchView(distM) {
    if (!cesiumActive) {
        toggleView();
    }
    // Jeśli już Cesium aktywne — nic nie rób, zostań w 3D
}

// ===================== CESIUM ANIMACJA =====================
var animTimer     = null;   // setInterval dla animacji
var animStep      = 0;      // aktualny krok animacji
var animPoints    = [];     // punkty trajektorii
var animTof       = 0;      // czas lotu [s]
var animSpeed     = 10;     // mnożnik prędkości
var animPlaying   = false;
var animData      = null;   // dane strzału
var missileEntity = null;   // animowana kropka
var trailPositions = [];    // ogon świetlny

function drawCesiumTrajectory(d, shooterLat, shooterLon, targetLat, targetLon) {
    if (!cesiumViewer) return;
    // Każdy strzał dodaje własną trajektorię — nie zatrzymujemy poprzednich
    // stopAnimation(); // <-- usunięte dla salwy

    animData   = d;
    animTof    = d.tof || 1200;
    var apogeeM = (d.apogee && d.apogee > 0) ? d.apogee : 800000;

    // Generuj punkty trajektorii
    animPoints = [];
    var N = 200;
    var geodesic = new Cesium.EllipsoidGeodesic(
        Cesium.Cartographic.fromDegrees(shooterLon, shooterLat),
        Cesium.Cartographic.fromDegrees(targetLon, targetLat)
    );
    var isCruise = (d.trajectory === 'cruise');
    var cruiseAltM = d.cruise_alt || 100;
    for (var i = 0; i <= N; i++) {
        var t = i / N;
        var midPoint = geodesic.interpolateUsingFraction(t);
        var lat = Cesium.Math.toDegrees(midPoint.latitude);
        var lon = Cesium.Math.toDegrees(midPoint.longitude);
        var alt = isCruise
            ? cruiseAltM                            // stała wysokość przelotowa
            : apogeeM * Math.sin(Math.PI * t);     // łuk balistyczny
        animPoints.push(Cesium.Cartesian3.fromDegrees(lon, lat, Math.max(alt, isCruise ? cruiseAltM : 0)));
    }

    // Rysuj statyczną trajektorię (blada linia)
    cesiumViewer.entities.add({
        polyline: {
            positions: animPoints,
            width: 1.5,
            material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.15,
                color: Cesium.Color.fromCssColorString('#ff4444').withAlpha(0.4)
            }),
            clampToGround: false
        }
    });

    // Marker strzelca
    cesiumViewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(shooterLon, shooterLat, 0),
        point: { pixelSize: 12, color: Cesium.Color.fromCssColorString('#ff4444') },
        label: {
            text: 'STRZELEC',
            font: '12px monospace',
            fillColor: Cesium.Color.fromCssColorString('#ff4444'),
            pixelOffset: new Cesium.Cartesian2(0, -20),
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2
        }
    });

    // Marker celu
    cesiumViewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(targetLon, targetLat, 0),
        point: { pixelSize: 12, color: Cesium.Color.fromCssColorString('#3fb950') },
        label: {
            text: d.nazwa + '\n' + (d.dist/1000).toFixed(0) + ' km',
            font: '11px monospace',
            fillColor: Cesium.Color.fromCssColorString('#3fb950'),
            pixelOffset: new Cesium.Cartesian2(0, -20),
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2
        }
    });

    // Marker apogeum — tylko dla rakiet balistycznych
    if (!isCruise && apogeeM > 0) {
        var geodesicAp = new Cesium.EllipsoidGeodesic(
            Cesium.Cartographic.fromDegrees(shooterLon, shooterLat),
            Cesium.Cartographic.fromDegrees(targetLon, targetLat)
        );
        var apMidPoint = geodesicAp.interpolateUsingFraction(0.5);
        var apLat = Cesium.Math.toDegrees(apMidPoint.latitude);
        var apLon = Cesium.Math.toDegrees(apMidPoint.longitude);
        cesiumViewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(apLon, apLat, apogeeM),
            point: { pixelSize: 8, color: Cesium.Color.fromCssColorString('#f0883e') },
            label: {
                text: '▲ APOGEUM ' + (apogeeM/1000).toFixed(0) + ' km',
                font: '10px monospace',
                fillColor: Cesium.Color.fromCssColorString('#f0883e'),
                pixelOffset: new Cesium.Cartesian2(10, 0)
            }
        });
    }

    // Animowana ikona — samolot lub rakieta
    var isNuclear = (d.blast && d.blast.type === 'NUCLEAR');
    var isAircraft = ['F35-B61','B2-B61','B2-B83','B21-B61','F15-B61',
                      'Tornado-B61','Tu160-nuke','Tu95-nuke','H6K-nuke',
                      'LittleBoy','FatMan','B61-12','W80-4'].indexOf(d.nazwa) >= 0;

    // Wybierz emoji w zależności od typu
    var planeEmoji = '✈️';
    if (d.nazwa === 'B2-B61' || d.nazwa === 'B2-B83' || d.nazwa === 'B21-B61') planeEmoji = '🛩️';
    if (d.nazwa === 'Tu160-nuke' || d.nazwa === 'Tu95-nuke') planeEmoji = '✈️';
    if (d.nazwa === 'LittleBoy' || d.nazwa === 'FatMan') planeEmoji = '✈️';

    var thisMissile = cesiumViewer.entities.add({
        position: animPoints[0],
        label: isAircraft ? {
            text: planeEmoji,
            font: '28px sans-serif',
            style: Cesium.LabelStyle.FILL,
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            pixelOffset: new Cesium.Cartesian2(0, 0),
            disableDepthTestDistance: Number.POSITIVE_INFINITY
        } : undefined,
        point: isAircraft ? undefined : {
            pixelSize: isNuclear ? 14 : 10,
            color: isNuclear
                ? Cesium.Color.fromCssColorString('#ffaa00')
                : Cesium.Color.fromCssColorString('#ffffff'),
            outlineColor: Cesium.Color.fromCssColorString('#ff4444'),
            outlineWidth: 2
        }
    });
    missileEntity = thisMissile;

    // Każda trajektoria startuje własną niezależną animację przez closure
    var closurePoints  = animPoints.slice();
    var closureTof     = d.tof || 1200;
    var closureData    = d;
    var closureMissile = thisMissile;

    function startThisAnimation() {
        var step  = 0;
        var trail = null;
        var trailPts = [];
        var timer = setInterval(function() {
            step += animSpeed;
            if (step >= closurePoints.length) {
                step = closurePoints.length - 1;
                clearInterval(timer);
                onImpact(closurePoints, closureData, closureMissile);
                return;
            }
            if (closureMissile) {
                closureMissile.position = new Cesium.ConstantPositionProperty(closurePoints[step]);
            }
            trailPts.push(closurePoints[step]);
            if (trailPts.length > 20) trailPts.shift();
            if (trail) cesiumViewer.entities.remove(trail);
            if (trailPts.length >= 2) {
                trail = cesiumViewer.entities.add({
                    polyline: {
                        positions: trailPts.slice(),
                        width: 4,
                        material: new Cesium.PolylineGlowMaterialProperty({
                            glowPower: 0.5,
                            color: Cesium.Color.fromCssColorString('#ffaa00').withAlpha(0.8)
                        })
                    }
                });
            }
            // Timer tylko dla ostatniej animacji
            var elapsed = Math.round((step / closurePoints.length) * closureTof);
            var timerEl = document.getElementById('anim-timer');
            if (timerEl) timerEl.textContent = 'T+ ' + elapsed + 's / ' + Math.round(closureTof) + 's';
            var pct = (step / (closurePoints.length - 1) * 100).toFixed(1);
            var bar = document.getElementById('anim-bar');
            if (bar) bar.style.width = pct + '%';
        }, 50);
    }

    // Zoom kamery — tylko przy pierwszym strzale (gdy Cesium właśnie się włączyło)
    var midLat = (shooterLat + targetLat) / 2;
    var midLon = (shooterLon + targetLon) / 2;
    var camAlt = apogeeM > 500000 ? 12000000 : Math.min(Math.max(apogeeM * 3, d.dist * 0.5, 2000000), 8000000);

    // Zoom do pozycji obejmującej strzelca i cel
    if (cesiumViewer.entities.values.length <= 5) {
        // Pierwszy strzał — zoom do trajektorii
        cesiumViewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(midLon, midLat, camAlt),
            duration: 2
        });
    }

    function waitAndStartThis() {
        if (cesiumViewer.scene.globe.tilesLoaded) {
            setTimeout(startThisAnimation, 500);
        } else {
            setTimeout(waitAndStartThis, 300);
        }
    }
    setTimeout(waitAndStartThis, 2000);

    // Pokaż kontrolki animacji
    showAnimControls(d, isNuclear);
}

function showAnimControls(d, isNuclear) {
    var existing = document.getElementById('anim-controls');
    if (existing) existing.remove();

    var ctrl = document.createElement('div');
    ctrl.id = 'anim-controls';
    ctrl.style.cssText = 'position:absolute;bottom:20px;left:50%;transform:translateX(-50%);'
        + 'background:rgba(13,17,23,0.92);border:1px solid #21262d;padding:12px 20px;'
        + 'font-family:monospace;font-size:11px;color:#c9d1d9;z-index:1000;'
        + 'display:flex;flex-direction:column;align-items:center;gap:8px;min-width:320px;';

    ctrl.innerHTML = '<div style="color:#58a6ff;font-size:13px;font-weight:bold;">'
        + (isNuclear ? '☢ ' : '🚀 ') + d.nazwa + ' — ' + (d.dist/1000).toFixed(0) + ' km'
        + '</div>'
        + '<div id="anim-timer" style="color:#3fb950;font-size:16px;">T+ 0s / ' + Math.round(animTof) + 's</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<button onclick="toggleAnimation()" id="btn-play" style="background:#0d1117;color:#3fb950;border:1px solid #3fb950;padding:5px 16px;font-family:monospace;cursor:pointer;font-size:13px;">⏸ PAUSE</button>'
        + '<button onclick="resetAnimation()" style="background:#0d1117;color:#f85149;border:1px solid #f85149;padding:5px 12px;font-family:monospace;cursor:pointer;">⟳ RESET</button>'
        + '</div>'
        + '<div style="display:flex;gap:6px;align-items:center;">'
        + '<span style="color:#8b949e;">Prędkość:</span>'
        + '<button onclick="setSpeed(1)"   id="spd-1"    style="background:#21262d;color:#c9d1d9;border:1px solid #444;padding:3px 8px;font-family:monospace;cursor:pointer;font-size:10px;">x1</button>'
        + '<button onclick="setSpeed(10)"  id="spd-10"   style="background:#58a6ff;color:#0d1117;border:1px solid #58a6ff;padding:3px 8px;font-family:monospace;cursor:pointer;font-size:10px;">x10</button>'
        + '<button onclick="setSpeed(50)"  id="spd-50"   style="background:#21262d;color:#c9d1d9;border:1px solid #444;padding:3px 8px;font-family:monospace;cursor:pointer;font-size:10px;">x50</button>'
        + '<button onclick="setSpeed(100)" id="spd-100"  style="background:#21262d;color:#c9d1d9;border:1px solid #444;padding:3px 8px;font-family:monospace;cursor:pointer;font-size:10px;">x100</button>'
        + '<button onclick="setSpeed(500)" id="spd-500"  style="background:#21262d;color:#c9d1d9;border:1px solid #444;padding:3px 8px;font-family:monospace;cursor:pointer;font-size:10px;">x500</button>'
        + '</div>'
        + '<div id="anim-progress" style="width:100%;height:4px;background:#21262d;border-radius:2px;margin-top:2px;">'
        + '<div id="anim-bar" style="height:4px;background:#3fb950;width:0%;border-radius:2px;transition:width 0.1s;"></div>'
        + '</div>';

    document.getElementById('map-container').appendChild(ctrl);
}

function startAnimation() {
    animStep    = 0;
    animPlaying = true;
    trailPositions = [];
    if (animTimer) clearInterval(animTimer);

    // Kopia lokalna danych dla tej animacji
    var localPoints  = animPoints.slice();
    var localTof     = animTof;
    var localData    = animData;
    var localMissile = missileEntity;
    var localTrail   = null;

    animTimer = setInterval(function() {
        if (!animPlaying) return;

        animStep += animSpeed;
        if (animStep >= localPoints.length) {
            animStep = localPoints.length - 1;
            clearInterval(animTimer);
            onImpact(localPoints, localData, localMissile);
            return;
        }

        if (localMissile) {
            localMissile.position = new Cesium.ConstantPositionProperty(localPoints[animStep]);
        }

        // Ogon
        trailPositions.push(localPoints[animStep]);
        if (trailPositions.length > 20) trailPositions.shift();
        if (localTrail) cesiumViewer.entities.remove(localTrail);
        if (trailPositions.length >= 2) {
            localTrail = cesiumViewer.entities.add({
                polyline: {
                    positions: trailPositions.slice(),
                    width: 4,
                    material: new Cesium.PolylineGlowMaterialProperty({
                        glowPower: 0.5,
                        color: Cesium.Color.fromCssColorString('#ffaa00').withAlpha(0.8)
                    })
                }
            });
        }

        var elapsed = Math.round((animStep / localPoints.length) * localTof);
        var timerEl = document.getElementById('anim-timer');
        if (timerEl) timerEl.textContent = 'T+ ' + elapsed + 's / ' + Math.round(localTof) + 's';
        var pct = (animStep / (localPoints.length - 1) * 100).toFixed(1);
        var bar = document.getElementById('anim-bar');
        if (bar) bar.style.width = pct + '%';

    }, 50);
}

var trailEntity = null;
function updateTrail() {
    if (trailPositions.length < 2) return;
    if (trailEntity) cesiumViewer.entities.remove(trailEntity);
    trailEntity = cesiumViewer.entities.add({
        polyline: {
            positions: trailPositions.slice(),
            width: 4,
            material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.5,
                color: Cesium.Color.fromCssColorString('#ffaa00').withAlpha(0.8)
            })
        }
    });
}

function onImpact(localPoints, localData, localMissile) {
    animPlaying = false;

    var isNuclear = (localData && localData.blast && localData.blast.type === 'NUCLEAR');
    var impactPos  = localPoints[localPoints.length - 1];
    var impactCart = Cesium.Cartographic.fromCartesian(impactPos);
    var impactLon  = Cesium.Math.toDegrees(impactCart.longitude);
    var impactLat  = Cesium.Math.toDegrees(impactCart.latitude);

    // Efekt eksplozji
    cesiumViewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(impactLon, impactLat, 0),
        point: {
            pixelSize: isNuclear ? 60 : 30,
            color: isNuclear
                ? Cesium.Color.fromCssColorString('#ff8800').withAlpha(0.9)
                : Cesium.Color.fromCssColorString('#ff4444').withAlpha(0.9),
            outlineColor: Cesium.Color.fromCssColorString('#ffffff'),
            outlineWidth: 3
        },
        label: {
            text: isNuclear ? '☢ UDERZENIE' : '💥 UDERZENIE',
            font: '14px monospace',
            fillColor: Cesium.Color.fromCssColorString('#ffffff'),
            pixelOffset: new Cesium.Cartesian2(0, -30),
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2
        }
    });

    // Strefy rażenia na powierzchni Ziemi
    var bz = animData.blast || {};
    if (isNuclear) {
        // Realne strefy z wzorów Glasstone & Dolan
        var nucZones = [
            { r: localData.blast.hazard, color: '#44ff88', label: 'Oparzenia 1° — ' + Math.round(localData.blast.hazard/1000) + ' km' },
            { r: localData.blast.light,  color: '#ffdd00', label: 'Lekkie (5 psi) — ' + Math.round(localData.blast.light/1000) + ' km'  },
            { r: localData.blast.heavy,  color: '#ff8800', label: 'Ciężkie (20 psi) — ' + Math.round(localData.blast.heavy/1000) + ' km' },
            { r: localData.blast.total,  color: '#ff0000', label: 'Kula ognia — ' + Math.round(localData.blast.total/1000) + ' km'      },
        ];
        nucZones.forEach(function(z) {
            if (!z.r || z.r <= 0) return;
            cesiumViewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(impactLon, impactLat, 0),
                ellipse: {
                    semiMajorAxis: z.r,
                    semiMinorAxis: z.r,
                    material: Cesium.Color.fromCssColorString(z.color).withAlpha(0.10),
                    outline: true,
                    outlineColor: Cesium.Color.fromCssColorString(z.color).withAlpha(0.8),
                    outlineWidth: 2,
                    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
                }
            });
        });
    } else if (bz.hazard > 0) {
        // Konwencjonalne strefy rażenia
        var convZones = [
            { r: bz.total,  color: '#ff4444', label: 'Totalne'    },
            { r: bz.heavy,  color: '#ff8800', label: 'Ciężkie'    },
            { r: bz.light,  color: '#ffdd00', label: 'Lekkie'     },
            { r: bz.hazard, color: '#44ff88', label: 'Zagrożenie' },
        ];
        convZones.forEach(function(z) {
            if (!z.r || z.r <= 0) return;
            cesiumViewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(impactLon, impactLat, 0),
                ellipse: {
                    semiMajorAxis: z.r,
                    semiMinorAxis: z.r,
                    material: Cesium.Color.fromCssColorString(z.color).withAlpha(0.10),
                    outline: true,
                    outlineColor: Cesium.Color.fromCssColorString(z.color).withAlpha(0.7),
                    outlineWidth: 2,
                    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
                }
            });
        });
    }

    // Zoom kamery na miejsce uderzenia
    var zoomAlt = isNuclear
        ? Math.max((localData.blast.hazard || 150000) * 3, 500000)
        : Math.max((localData.blast.hazard || 5000) * 5, 50000);
    cesiumViewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(impactLon, impactLat, zoomAlt),
        duration: 2
    });

    // Usuń kropkę pocisku
    if (localMissile) cesiumViewer.entities.remove(localMissile);

    // Aktualizuj timer
    var timerEl = document.getElementById('anim-timer');
    if (timerEl) {
        timerEl.textContent = 'UDERZENIE — T+ ' + Math.round(localData.tof || 0) + 's';
        timerEl.style.color = isNuclear ? '#ffaa00' : '#ff4444';
    }
    var bar = document.getElementById('anim-bar');
    if (bar) { bar.style.width = '100%'; bar.style.background = isNuclear ? '#ffaa00' : '#ff4444'; }
}

function toggleAnimation() {
    animPlaying = !animPlaying;
    var btn = document.getElementById('btn-play');
    if (btn) btn.textContent = animPlaying ? '⏸ PAUSE' : '▶ PLAY';
}

function resetAnimation() {
    stopAnimation();
    if (animData && animPoints.length > 0) startAnimation();
}

function stopAnimation() {
    if (animTimer) clearInterval(animTimer);
    animPlaying = false;
    animStep    = 0;
}

function setSpeed(s) {
    animSpeed = s;
    ['1','10','50','100','500'].forEach(function(v) {
        var b = document.getElementById('spd-' + v);
        if (b) {
            b.style.background = (parseInt(v) === s) ? '#58a6ff' : '#21262d';
            b.style.color      = (parseInt(v) === s) ? '#0d1117' : '#c9d1d9';
            b.style.borderColor= (parseInt(v) === s) ? '#58a6ff' : '#444';
        }
    });
}
// ================================================================
// TERRAIN MASKING + URBAN DAMAGE MODEL — PATCH v1.0
// Zastępuje: onImpact(), showResult() strefy HE/NUCLEAR na mapie
// Nowe funkcje: computeTerrainMaskedZones(), getUrbanDensity(),
//               drawMaskedZones2D(), drawMaskedZones3D()
// ================================================================

// ----------------------------------------------------------------
// HELPERS — geometria
// ----------------------------------------------------------------
function offsetPointMeters(lat, lon, bearingDeg, distM) {
    var R = 6371000;
    var brng = bearingDeg * Math.PI / 180;
    var lat1 = lat * Math.PI / 180;
    var lon1 = lon * Math.PI / 180;
    var lat2 = Math.asin(Math.sin(lat1)*Math.cos(distM/R) +
                Math.cos(lat1)*Math.sin(distM/R)*Math.cos(brng));
    var lon2 = lon1 + Math.atan2(Math.sin(brng)*Math.sin(distM/R)*Math.cos(lat1),
                Math.cos(distM/R)-Math.sin(lat1)*Math.sin(lat2));
    return { lat: lat2 * 180/Math.PI, lon: lon2 * 180/Math.PI };
}

// Wysokość fali uderzeniowej nad terenem w odległości dist od epicentrum
// Model uproszczony: paraboliczna kopuła, max na epicentrum = 15% promienia strefy
function blastWaveHeight(dist_m, zone_radius_m) {
    if (dist_m >= zone_radius_m) return 0;
    var t = dist_m / zone_radius_m;
    return zone_radius_m * 0.15 * (1 - t * t);
}

// ----------------------------------------------------------------
// URBAN DENSITY — OSM Overpass API + fallback heurystyka
// ----------------------------------------------------------------
var urbanDensityCache = {};
var urbanCanyonCache = {};
var urbanModeActive = false;  // Toggle urban canyon effect

// Toggle urban mode
function toggleUrbanMode() {
    urbanModeActive = !urbanModeActive;
    var btn = document.getElementById('urban-toggle');
    if (urbanModeActive) {
        btn.style.color = '#f0883e';
        btn.style.borderColor = '#f0883e';
        btn.style.background = 'rgba(240,136,62,0.15)';
        btn.textContent = '🏙️ Urban ON';
    } else {
        btn.style.color = '#8b949e';
        btn.style.borderColor = '#444';
        btn.style.background = 'rgba(13,17,23,0.90)';
        btn.textContent = '🏙️ Urban OFF';
    }
}

// ================================================================
// OSM QUERY — budynki + ulice jednocześnie (jeden request)
// Zwraca: { density, canyonAngle, canyonStrength }
// ================================================================
async function getUrbanData(lat, lon, radiusM) {
    var key = lat.toFixed(3) + ',' + lon.toFixed(3) + ',' + Math.round(radiusM);
    if (urbanDensityCache[key] !== undefined) {
        return { density: urbanDensityCache[key], canyonAngle: urbanCanyonCache[key] || null };
    }

    var r = Math.min(radiusM, 3000);
    // Jeden query — budynki (count) + główne ulice (geometry dla kierunku)
    var query = '[out:json][timeout:12];'
        + '(way["building"](around:' + r + ',' + lat + ',' + lon + ');)->.buildings;'
        + '(way["highway"~"^(primary|secondary|tertiary|trunk|motorway)$"](around:' + r + ',' + lat + ',' + lon + ');)->.roads;'
        + '(.buildings;.roads;);'
        + 'out geom qt;';

    try {
        var resp = await fetch('https://overpass-api.de/api/interpreter', {
            method: 'POST',
            body: 'data=' + encodeURIComponent(query),
            signal: AbortSignal.timeout(12000)
        });
        var data = await resp.json();

        // Zlicz budynki
        var buildingCount = 0;
        var roadAngles = [];

        data.elements.forEach(function(el) {
            if (el.tags && el.tags.building) {
                buildingCount++;
            } else if (el.tags && el.tags.highway && el.geometry && el.geometry.length >= 2) {
                // Oblicz kierunek każdej drogi (dominujący azymut sieci ulic)
                for (var i = 0; i < el.geometry.length - 1; i++) {
                    var dx = el.geometry[i+1].lon - el.geometry[i].lon;
                    var dy = el.geometry[i+1].lat - el.geometry[i].lat;
                    var angle = Math.atan2(dx, dy) * 180 / Math.PI;
                    // Normalizuj do [0, 180] — kierunek ulicy (nie ma znaczenia w którą stronę)
                    if (angle < 0) angle += 180;
                    roadAngles.push(angle);
                }
            }
        });

        // Gęstość zabudowy
        var density = Math.min(buildingCount / 300, 1.0);
        urbanDensityCache[key] = density;

        // Dominujący kierunek ulic — histogram kątów
        var canyonAngle = null;
        var canyonStrength = 0;
        if (roadAngles.length > 3) {
            // Podziel na 18 kubełków po 10°
            var bins = new Array(18).fill(0);
            roadAngles.forEach(function(a) { bins[Math.floor(a / 10) % 18]++; });
            var maxBin = 0, maxIdx = 0;
            bins.forEach(function(v, i) { if (v > maxBin) { maxBin = v; maxIdx = i; } });
            canyonAngle = (maxIdx * 10 + 5); // środek kubełka w stopniach
            canyonStrength = Math.min(maxBin / roadAngles.length * 3, 1.0); // siła kanałowania
        }
        urbanCanyonCache[key] = { angle: canyonAngle, strength: canyonStrength };

        console.log('[OSM] density=' + density.toFixed(2) + ' canyonAngle=' + canyonAngle + '° strength=' + (canyonStrength||0).toFixed(2) + ' buildings=' + buildingCount + ' roadSegs=' + roadAngles.length);
        return { density: density, canyonAngle: canyonAngle, canyonStrength: canyonStrength };

    } catch (e) {
        console.warn('[OSM] Fallback dla ' + lat + ',' + lon + ' : ' + e.message);
        urbanDensityCache[key] = 0.5;
        urbanCanyonCache[key] = { angle: null, strength: 0 };
        return { density: 0.5, canyonAngle: null, canyonStrength: 0 };
    }
}

// Backward compat — stara funkcja
async function getUrbanDensity(lat, lon, radiusM) {
    var d = await getUrbanData(lat, lon, radiusM);
    return d.density;
}

// ================================================================
// URBAN CANYON — modyfikuje raycast per-kąt
// Fala wzmacnia się wzdłuż ulic, słabnie prostopadle
// ================================================================
function canyonRayModifier(rayAngleDeg, canyonAngle, canyonStrength, density) {
    if (!urbanModeActive || !canyonAngle || density < 0.3) return 1.0;

    // Różnica kąta promienia względem osi kanału
    var diff = Math.abs(rayAngleDeg - canyonAngle) % 180;
    if (diff > 90) diff = 180 - diff;
    // diff = 0 → wzdłuż ulicy, diff = 90 → prostopadle

    var alignment = 1.0 - (diff / 90); // 1=wzdłuż, 0=prostopadle

    // Wzdłuż ulicy: fala idzie dalej (+30% max)
    // Prostopadle: fala tłumiona (-20% max)
    var boost    =  0.30 * canyonStrength * density;
    var dampen   = -0.20 * canyonStrength * density;
    var modifier = 1.0 + alignment * boost + (1 - alignment) * dampen;

    return Math.max(0.5, Math.min(1.5, modifier));
}

// Urban modifier — jak gęstość zabudowy wpływa na zasięg stref
// Ciasna zabudowa tłumi falę ale wzmacnia pożary → różny efekt per strefa
function urbanModifier(density, zoneType) {
    // density: 0=open, 0.5=suburban, 1=dense urban
    if (zoneType === 'total' || zoneType === 'heavy') {
        // Fala uderzeniowa — budynki trochę tłumią ale efekt minimalny
        return 1.0 - density * 0.1;
    } else if (zoneType === 'light') {
        // Lekkie zniszczenia — zabudowa drewniana zwiększa zasięg pożarów
        return 1.0 + density * 0.2;
    } else { // hazard / thermal
        // Oparzenia / promieniowanie — zabudowa trochę chroni
        return 1.0 - density * 0.15;
    }
}

// ----------------------------------------------------------------
// TERRAIN MASKING — główna funkcja
// Returns: { total: [...pts], heavy: [...pts], light: [...pts], hazard: [...pts] }
// ----------------------------------------------------------------
async function computeTerrainMaskedZones(impactLat, impactLon, blast, isNuclear, onProgress) {
    if (!cesiumViewer) return null;

    var zones = isNuclear
        ? { total: blast.total, heavy: blast.heavy, light: blast.light, hazard: blast.hazard }
        : { total: blast.total, heavy: blast.heavy, light: blast.light, hazard: blast.hazard };

    var maxZoneR = Math.max(zones.hazard||0, zones.light||0, zones.heavy||0, zones.total||0);
    var skipTerrain = false;
    var RAYS, STEPS;
    if (maxZoneR > 50000) {
        skipTerrain = true; RAYS = 36; STEPS = 1;
        console.log('[Terrain] SKIP strefa=' + (maxZoneR/1000).toFixed(0) + 'km');
    } else if (maxZoneR > 10000) {
        RAYS = 36; STEPS = 15;
    } else if (maxZoneR > 2000) {
        RAYS = 54; STEPS = 20;
    } else {
        RAYS = 72; STEPS = 25;
    }
    var urbanR = Math.min(zones.heavy || zones.total || 500, 3000);
    var urbanData = await getUrbanData(impactLat, impactLon, urbanR);
    var density = urbanData.density;
    var canyonAngle = urbanData.canyonAngle;
    var canyonStrength = urbanData.canyonStrength || 0;

    var result = { total: [], heavy: [], light: [], hazard: [], urbanDensity: density };
    var zoneKeys = ['total', 'heavy', 'light', 'hazard'];
    var zoneTypes = ['total', 'heavy', 'light', 'hazard'];

    // Dla każdej strefy rażenia
    for (var zi = 0; zi < zoneKeys.length; zi++) {
        var key = zoneKeys[zi];
        var baseRadius = zones[key] || 0;
        if (baseRadius <= 0) { result[key] = []; continue; }

        var umod = urbanModifier(density, zoneTypes[zi]);
        var effectiveRadius = baseRadius * umod;

        var polygonPts = [];

        if (skipTerrain) {
            for (var ri = 0; ri < RAYS; ri++) {
                var angle = (ri / RAYS) * 360;
                var canyonMod = canyonRayModifier(angle, canyonAngle, canyonStrength, density);
                var pt = offsetPointMeters(impactLat, impactLon, angle, Math.max(effectiveRadius * canyonMod, 10));
                polygonPts.push([pt.lat, pt.lon]);
            }
        } else {
            var allCartographics = [];
            var rayData = [];
            for (var ri = 0; ri < RAYS; ri++) {
                var angle = (ri / RAYS) * 360;
                var stepPts = [];
                for (var si = 1; si <= STEPS; si++) {
                    var dist = (si / STEPS) * effectiveRadius;
                    var pt = offsetPointMeters(impactLat, impactLon, angle, dist);
                    stepPts.push({ dist: dist, lat: pt.lat, lon: pt.lon, cartoIdx: allCartographics.length });
                    allCartographics.push(Cesium.Cartographic.fromDegrees(pt.lon, pt.lat));
                }
                rayData.push({ angle: angle, stepPts: stepPts });
            }
            var sampled;
            try {
                sampled = await Cesium.sampleTerrainMostDetailed(cesiumViewer.terrainProvider, allCartographics);
            } catch (e) {
                sampled = allCartographics.map(function() { return { height: 0 }; });
            }
            var epicCarto = [Cesium.Cartographic.fromDegrees(impactLon, impactLat)];
            var epicSampled = await Cesium.sampleTerrainMostDetailed(cesiumViewer.terrainProvider, epicCarto).catch(function() { return [{height:0}]; });
            var epicHeight = epicSampled[0].height || 0;
            for (var ri = 0; ri < RAYS; ri++) {
                var ray = rayData[ri];
                var blockedDist = effectiveRadius;
                for (var si = 0; si < ray.stepPts.length; si++) {
                    var sp = ray.stepPts[si];
                    if ((sampled[sp.cartoIdx].height||0) > blastWaveHeight(sp.dist, effectiveRadius) + epicHeight) {
                        blockedDist = sp.dist * 0.85; break;
                    }
                }
                var canyonMod = canyonRayModifier(ray.angle, canyonAngle, canyonStrength, density);
                var finalPt = offsetPointMeters(impactLat, impactLon, ray.angle, Math.max(blockedDist * canyonMod, 10));
                polygonPts.push([finalPt.lat, finalPt.lon]);
            }
        }

        // Wygładź polygon (moving average 3-punktowy)
        var smoothed = [];
        for (var i = 0; i < polygonPts.length; i++) {
            var prev = polygonPts[(i - 1 + polygonPts.length) % polygonPts.length];
            var curr = polygonPts[i];
            var next = polygonPts[(i + 1) % polygonPts.length];
            smoothed.push([(prev[0]+curr[0]+next[0])/3, (prev[1]+curr[1]+next[1])/3]);
        }
        result[key] = smoothed;

        if (onProgress) onProgress(zi + 1, zoneKeys.length, density);
    }

    result.canyonAngle    = canyonAngle;
    result.canyonStrength = canyonStrength;
    result.skipTerrain    = skipTerrain;
    result.raysUsed       = RAYS;
    result.stepsUsed      = STEPS;
    return result;
}

// ----------------------------------------------------------------
// RYSOWANIE 2D — Leaflet polygony zamiast okręgów
// ----------------------------------------------------------------
function drawMaskedZones2D(latlng, maskedZones, isNuclear, shotLayers, shotData) {
    var zoneStyles = isNuclear ? [
        { key: 'hazard', color: '#44ff88', opacity: 0.04, weight: 1, dash: '6 3', tooltip: 'Oparzenia 1°' },
        { key: 'light',  color: '#ffdd00', opacity: 0.07, weight: 1.5, dash: null, tooltip: 'Lekkie (5 psi)' },
        { key: 'heavy',  color: '#ff8800', opacity: 0.12, weight: 2,   dash: null, tooltip: 'Ciężkie (20 psi)' },
        { key: 'total',  color: '#ff4444', opacity: 0.30, weight: 2,   dash: null, tooltip: 'Kula ognia' },
    ] : [
        { key: 'hazard', color: '#44ff88', opacity: 0.04, weight: 1, dash: '6 3', tooltip: 'Strefa zagrożenia' },
        { key: 'light',  color: '#ffdd00', opacity: 0.07, weight: 1.5, dash: null, tooltip: 'Lekkie uszkodzenia' },
        { key: 'heavy',  color: '#ff8800', opacity: 0.12, weight: 2,   dash: null, tooltip: 'Ciężkie uszkodzenia' },
        { key: 'total',  color: '#ff4444', opacity: 0.25, weight: 2,   dash: null, tooltip: 'Zniszczenie totalne' },
    ];

    var features = [];
    zoneStyles.forEach(function(style) {
        var pts = maskedZones[style.key];
        if (!pts || pts.length < 3) return;
        var dx = pts[0][0] - latlng.lat, dy = pts[0][1] - latlng.lng;
        var approxR = Math.round(Math.sqrt(dx*dx+dy*dy) * 111000);
        var radiusStr = approxR >= 1000 ? (approxR/1000).toFixed(1)+'km' : approxR+'m';
        var urbanTag = maskedZones.urbanDensity > 0.6 ? ' [URBAN]' : maskedZones.urbanDensity < 0.2 ? ' [OPEN]' : '';
        var coords = pts.map(function(p) { return [p[1], p[0]]; });
        coords.push(coords[0]);
        features.push({
            type: 'Feature',
            geometry: { type: 'Polygon', coordinates: [coords] },
            properties: {
                shot_id: shotData ? shotData.shot_id : null,
                zone_key: style.key, zone_label: style.tooltip||style.label||style.key,
                color: style.color, fillOpacity: style.opacity,
                weight: style.weight, dashArray: style.dash,
                radius_str: radiusStr, radius_m: approxR,
                urban_tag: urbanTag,
                canyon_deg: maskedZones.canyonAngle ? Math.round(maskedZones.canyonAngle) : null,
                weapon: shotData ? shotData.nazwa : null
            }
        });
    });
    if (features.length === 0) return;
    var zoneOrder = ['hazard','light','heavy','total'];
    features.sort(function(a,b) { return zoneOrder.indexOf(a.properties.zone_key) - zoneOrder.indexOf(b.properties.zone_key); });
    var geoLayer = L.geoJSON({ type: 'FeatureCollection', features: features }, {
        renderer: canvasRenderer,
        style: function(f) { return { color: f.properties.color, fillColor: f.properties.color, fillOpacity: f.properties.fillOpacity, weight: f.properties.weight, dashArray: f.properties.dashArray }; },
        onEachFeature: function(feature, layer) {
            var p = feature.properties;
            var cStr = p.canyon_deg ? ' | Canyon: ' + p.canyon_deg + '°' : '';
            layer.bindTooltip(p.zone_label + ' ~' + p.radius_str + p.urban_tag + cStr, { sticky: true });
        }
    }).addTo(map);
    shotLayers.push(geoLayer);
}

// ----------------------------------------------------------------
// RYSOWANIE 3D — Cesium polygony
// ----------------------------------------------------------------
function drawMaskedZones3D(impactLon, impactLat, maskedZones, isNuclear) {
    if (!cesiumViewer) return;

    var zoneStyles = isNuclear ? [
        { key: 'hazard', color: '#44ff88' },
        { key: 'light',  color: '#ffdd00' },
        { key: 'heavy',  color: '#ff8800' },
        { key: 'total',  color: '#ff0000' },
    ] : [
        { key: 'hazard', color: '#44ff88' },
        { key: 'light',  color: '#ffdd00' },
        { key: 'heavy',  color: '#ff8800' },
        { key: 'total',  color: '#ff4444' },
    ];

    zoneStyles.forEach(function(style) {
        var pts = maskedZones[style.key];
        if (!pts || pts.length < 3) return;

        // Konwertuj [lat,lon] → Cesium Cartesian
        var positions = pts.map(function(p) {
            return Cesium.Cartesian3.fromDegrees(p[1], p[0], 10); // 10m nad terenem
        });
        positions.push(positions[0]); // zamknij polygon

        cesiumViewer.entities.add({
            polygon: {
                hierarchy: new Cesium.PolygonHierarchy(
                    pts.map(function(p) { return Cesium.Cartesian3.fromDegrees(p[1], p[0]); })
                ),
                material: Cesium.Color.fromCssColorString(style.color).withAlpha(0.12),
                outline: true,
                outlineColor: Cesium.Color.fromCssColorString(style.color).withAlpha(0.8),
                outlineWidth: 2,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                classificationType: Cesium.ClassificationType.TERRAIN
            }
        });
    });
}

// ----------------------------------------------------------------
// PROGRESS UI — pokazuj postęp obliczeń
// ----------------------------------------------------------------
function showTerrainProgress(current, total, density) {
    var existing = document.getElementById('terrain-progress');
    if (!existing) {
        var div = document.createElement('div');
        div.id = 'terrain-progress';
        div.style.cssText = 'position:absolute;bottom:80px;left:50%;transform:translateX(-50%);'
            + 'background:rgba(13,17,23,0.95);border:1px solid #58a6ff;padding:10px 20px;'
            + 'font-family:monospace;font-size:11px;color:#c9d1d9;z-index:2000;'
            + 'min-width:280px;text-align:center;';
        div.innerHTML = '<div style="color:#58a6ff;margin-bottom:6px;">🏔️ TERRAIN MASKING</div>'
            + '<div id="tp-bar-wrap" style="width:100%;height:4px;background:#21262d;border-radius:2px;">'
            + '<div id="tp-bar" style="height:4px;background:#58a6ff;width:0%;border-radius:2px;transition:width 0.3s;"></div></div>'
            + '<div id="tp-status" style="color:#8b949e;margin-top:6px;font-size:10px;">Inicjalizacja...</div>';
        document.getElementById('map-container').appendChild(div);
    }
    var pct = (current / total * 100).toFixed(0);
    var bar = document.getElementById('tp-bar');
    var status = document.getElementById('tp-status');
    if (bar) bar.style.width = pct + '%';
    if (status) {
        var densityStr = density !== undefined
            ? (density > 0.6 ? '🏙️ URBAN' : density > 0.3 ? '🏘️ SUBURBAN' : '🌾 OPEN')
            : '...';
        status.textContent = 'Strefa ' + current + '/' + total + ' | Teren: ' + densityStr + ' | ' + pct + '%';
    }
    if (current >= total) {
        setTimeout(function() {
            var el = document.getElementById('terrain-progress');
            if (el) el.remove();
        }, 1500);
    }
}

// ----------------------------------------------------------------
// GŁÓWNA INTEGRACJA — zastępuje onImpact() i showResult() dla stref
// Wywołaj zamiast rysowania okręgów
// ----------------------------------------------------------------
async function drawTerrainAwareZones(d, latlng, impactLon, impactLat, shotLayers) {
    var bz = d.blast || {};
    if (!bz.type || bz.type === 'KE' || bz.type === 'SMOKE' || bz.type === 'CLUSTER') return false;

    var isNuclear = (bz.type === 'NUCLEAR');

    // Pokaż progress
    showTerrainProgress(0, 4, undefined);

    try {
        var maskedZones = await computeTerrainMaskedZones(
            impactLat, impactLon, bz, isNuclear,
            function(cur, tot, density) { showTerrainProgress(cur, tot, density); }
        );

        if (!maskedZones) return false;

        // Buduj terrain HTML
        var densityStr = maskedZones.urbanDensity > 0.6 ? '🏙️ Zurbanizowany' :
                         maskedZones.urbanDensity > 0.3 ? '🏘️ Podmiejski' : '🌾 Otwarty';
        var canyonInfo = '';
        if (urbanModeActive) {
            if (maskedZones.canyonAngle !== null && maskedZones.canyonAngle !== undefined) {
                canyonInfo = '<br><span style="color:#f0883e;">🏙️ Canyon: <b>'
                    + Math.round(maskedZones.canyonAngle) + '°</b>'
                    + ' siła: ' + (maskedZones.canyonStrength*100).toFixed(0) + '%</span>';
            } else {
                canyonInfo = '<br><span style="color:#484f58;">🏙️ Canyon: brak danych ulic</span>';
            }
        }
        var modeStr = maskedZones.skipTerrain
            ? 'SKIP &gt;50km | tylko urban canyon'
            : ((maskedZones.raysUsed||72) + ' promieni × ' + (maskedZones.stepsUsed||25) + ' próbek | Strefy nieregularne');
        var terrainHtml = '<div class="label" style="margin-top:6px;">🏔️ TERRAIN MASKING</div>'
            + '<div style="font-size:10px;color:#8b949e;line-height:1.7;">'
            + 'Teren: <b style="color:#58a6ff;">' + densityStr + '</b>'
            + ' (OSM: ' + (maskedZones.urbanDensity*100).toFixed(0) + '%)'
            + canyonInfo + '<br>' + modeStr + '<br>'
            + '<span style="color:#3fb950;">✓ Aktywne maskowanie terenowe</span>'
            + (urbanModeActive ? '<br><span style="color:#f0883e;">✓ Urban canyon aktywny</span>' : '')
            + '</div>';

        // Zapisz do store — NIE appenduj bezposrednio (race condition + duplikacja przy salwie)
        if (d && d.shot_id) {
            if (!shotDataStore[d.shot_id]) shotDataStore[d.shot_id] = d;
            shotDataStore[d.shot_id]._terrainHtml = terrainHtml;
        }

        drawMaskedZones2D(latlng, maskedZones, isNuclear, shotLayers, d);

        if (cesiumActive && cesiumViewer) {
            drawMaskedZones3D(impactLon, impactLat, maskedZones, isNuclear);
        }

        // Odswierz panel jesli pokazuje ten strzal
        // (updatePanel zostal wywolany przed zakonczeniem async terrain)
        var rb = document.getElementById('r-blast');
        if (rb && d && d.shot_id) {
            var existing = rb.innerHTML;
            if (existing.indexOf('TERRAIN MASKING') === -1) {
                rb.innerHTML += terrainHtml;
            }
        }

        return true;
    } catch (e) {
        console.error('[TerrainMasking] Error:', e);
        var el = document.getElementById('terrain-progress');
        if (el) el.remove();
        return false;
    }
}



// ================================================================
// OPAD RADIOAKTYWNY (Glasstone & Dolan) — tylko dla NUCLEAR
// ================================================================
function drawFallout(d, latlng, bz, shotLayers) {
    if (bz.type !== 'NUCLEAR') return;
    var windDir  = d.wiatr_dir || 0;
    var windSpd  = d.wiatr_v   || 1;
    var falloutDir = (windDir + 180) % 360;
    var windFactor = Math.max(windSpd / 5.0, 0.3);
    var isBurstAir = (bz.burst === 'air');
    var fo_intense  = bz.hazard * (isBurstAir ? 0.5  : 2.0)  * windFactor;
    var fo_moderate = bz.hazard * (isBurstAir ? 1.5  : 6.0)  * windFactor;
    var fo_light    = bz.hazard * (isBurstAir ? 4.0  : 15.0) * windFactor;
    var fo_width_i  = bz.hazard * (isBurstAir ? 0.15 : 0.3);
    var fo_width_m  = bz.hazard * (isBurstAir ? 0.30 : 0.6);
    var fo_width_l  = bz.hazard * (isBurstAir ? 0.50 : 1.0);

    function falloutPolygon(lat, lon, dirDeg, length, width, steps) {
        var pts = [];
        var R = 6371000;
        var dirRad = (90 - dirDeg) * Math.PI / 180;
        var perpRad = dirRad + Math.PI / 2;
        for (var i = 0; i <= steps; i++) {
            var t = i / steps;
            var dist_along = length * t;
            var half_w = width * Math.sin(Math.PI * t);
            var dxL = (dist_along * Math.cos(dirRad) + half_w * Math.cos(perpRad)) / R;
            var dyL = (dist_along * Math.sin(dirRad) + half_w * Math.sin(perpRad)) / R;
            pts.push([lat + dyL * 180/Math.PI, lon + dxL * 180/Math.PI / Math.cos(lat * Math.PI/180)]);
        }
        for (var i = steps; i >= 0; i--) {
            var t = i / steps;
            var dist_along = length * t;
            var half_w = width * Math.sin(Math.PI * t);
            var dxR = (dist_along * Math.cos(dirRad) - half_w * Math.cos(perpRad)) / R;
            var dyR = (dist_along * Math.sin(dirRad) - half_w * Math.sin(perpRad)) / R;
            pts.push([lat + dyR * 180/Math.PI, lon + dxR * 180/Math.PI / Math.cos(lat * Math.PI/180)]);
        }
        return pts;
    }

    if (fo_light > 0) {
        var ptsL = falloutPolygon(latlng.lat, latlng.lng, falloutDir, fo_light, fo_width_l, 20);
        shotLayers.push(L.polygon(ptsL, {
            color:'#ffff44', fillColor:'#ffff44', fillOpacity:0.08, weight:1, dashArray:'4 4'
        }).addTo(map).bindTooltip('Opad lekki: ' + (fo_light/1000).toFixed(0) + ' km'));
    }
    if (fo_moderate > 0) {
        var ptsM = falloutPolygon(latlng.lat, latlng.lng, falloutDir, fo_moderate, fo_width_m, 20);
        shotLayers.push(L.polygon(ptsM, {
            color:'#ff8800', fillColor:'#ff8800', fillOpacity:0.12, weight:1.5
        }).addTo(map).bindTooltip('Opad umiarkowany: ' + (fo_moderate/1000).toFixed(0) + ' km'));
    }
    if (fo_intense > 0) {
        var ptsI = falloutPolygon(latlng.lat, latlng.lng, falloutDir, fo_intense, fo_width_i, 20);
        shotLayers.push(L.polygon(ptsI, {
            color:'#ff2222', fillColor:'#ff2222', fillOpacity:0.18, weight:2
        }).addTo(map).bindTooltip('Opad intensywny: ' + (fo_intense/1000).toFixed(0) + ' km'));
    }

    // Strzałka wiatru
    var arrowLen = bz.hazard * 0.5;
    var arrowRad = (90 - falloutDir) * Math.PI / 180;
    var arrowLat = latlng.lat + (arrowLen * Math.sin(arrowRad)) / 6371000 * 180/Math.PI;
    var arrowLon = latlng.lng + (arrowLen * Math.cos(arrowRad)) / 6371000 * 180/Math.PI / Math.cos(latlng.lat * Math.PI/180);
    shotLayers.push(L.polyline([[latlng.lat, latlng.lng], [arrowLat, arrowLon]], {
        color:'#ffffff', weight:2, opacity:0.7
    }).addTo(map).bindTooltip('Wiatr: ' + windSpd.toFixed(1) + ' m/s \u2192 ' + Math.round(falloutDir) + '\u00b0'));

    // Info w panelu
    var falloutInfo = '<div class="label" style="margin-top:6px;">\u2622 OPAD RADIOAKTYWNY</div>'
        + '<div style="font-size:11px; line-height:1.8;">'
        + (isBurstAir ? '<span style="color:#58a6ff; font-size:10px;">Wybuch powietrzny \u2014 zmniejszony opad</span><br>' : '')
        + '<span style="color:#ff2222;">&#9632;</span> Intensywny: <b>' + (fo_intense/1000).toFixed(0) + ' km</b><br>'
        + '<span style="color:#ff8800;">&#9632;</span> Umiarkowany: <b>' + (fo_moderate/1000).toFixed(0) + ' km</b><br>'
        + '<span style="color:#ffff44;">&#9632;</span> Lekki: <b>' + (fo_light/1000).toFixed(0) + ' km</b><br>'
        + '<span style="color:#8b949e; font-size:10px;">Kierunek: ' + Math.round(falloutDir) + '\u00b0 | Wiatr: ' + windSpd.toFixed(1) + ' m/s</span>'
        + '</div>';
    if (d && d.shot_id && shotDataStore[d.shot_id]) {
        shotDataStore[d.shot_id]._falloutHtml = falloutInfo;
    }
    if (Object.keys(shotDataStore).length <= 1) {
        var rb = document.getElementById('r-blast');
        if (rb) rb.innerHTML += falloutInfo;
    }
}

var icons = {
    red:    L.icon({ iconUrl:'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',    iconSize:[25,41], iconAnchor:[12,41], popupAnchor:[1,-34] }),
    yellow: L.icon({ iconUrl:'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-yellow.png', iconSize:[25,41], iconAnchor:[12,41], popupAnchor:[1,-34] }),
    green:  L.icon({ iconUrl:'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',  iconSize:[25,41], iconAnchor:[12,41], popupAnchor:[1,-34] }),
};

var shooter = L.marker([{{lat}}, {{lon}}], {icon: icons.red}).addTo(map).bindPopup('<b>STRZELEC</b>');
var shotLayers   = [];
var pendingTargets = [];   // zaznaczone cele czekające na strzał
var pollTimer    = null;
var isFiring     = false;  // blokada podczas oczekiwania na wynik
var lastShotId   = null;

// Słownik systemów i amunicji (musi zgadzać się z Pythonem)
var SYSTEMY = {
    "1":  { name: "AHS KRAB (155mm)",      ammo: { "1": "M107 HE",      "2": "EXCALIBUR"  }},
    "2":  { name: "M120 RAK (120mm)",      ammo: { "1": "HE STD",       "2": "SMOKE"      }},
    "3":  { name: "LEOPARD 2 (120mm)",     ammo: { "1": "APFSDS",       "2": "HEAT"       }},
    "4":  { name: "ATACMS (MGM-140)",      ammo: { "1": "ATACMS-A", "2": "ATACMS-B", "3": "ATACMS-Cluster" }},
    "5":  { name: "HIMARS (GMLRS)",        ammo: { "1": "GMLRS",        "2": "GMLRS-ER"   }},
    "6":  { name: "PrSM (MGM-168)",        ammo: { "1": "PrSM"                            }},
    "7":  { name: "PATRIOT PAC-3",         ammo: { "1": "PAC-3 MSE"                       }},
    "8":  { name: "SM-3 (przechwytywacz)", ammo: { "1": "SM-3"                            }},
    "9":  { name: "Lance (MGM-52)",        ammo: { "1": "Lance"                           }},
    "10": { name: "ISKANDER-M",            ammo: { "1": "9M723",    "2": "9M723-Cluster"   }},
    "11": { name: "Tochka-U",              ammo: { "1": "Tochka-U", "2": "Tochka-Cluster"  }},
    "12": { name: "Scud-B (R-17)",         ammo: { "1": "Scud-B",   "2": "Scud-B-Cluster"  }},
    "13": { name: "Kinżał (MiG-31K)",      ammo: { "1": "Kinzal"                          }},
    "14": { name: "Kalibr (3M14)",         ammo: { "1": "Kalibr"                          }},
    "15": { name: "Oniks (P-800)",         ammo: { "1": "Oniks"                           }},
    "16": { name: "RS-26 Rubezh",          ammo: { "1": "Rubezh"                          }},
    "17": { name: "Sarmat (RS-28) ☢",      ammo: { "1": "Sarmat"                          }},
    "18": { name: "DF-11A (SRBM)",         ammo: { "1": "DF-11A"                          }},
    "19": { name: "DF-21D (ASBM)",         ammo: { "1": "DF-21D"                          }},
    "20": { name: "DF-17 (HGV)",           ammo: { "1": "DF-17"                           }},
    "21": { name: "DF-26 (IRBM) ☢",        ammo: { "1": "DF-26"                           }},
    "22": { name: "DF-41 (ICBM) ☢",        ammo: { "1": "DF-41"                           }},
    "23": { name: "KN-23 (SRBM)",          ammo: { "1": "KN-23"                           }},
    "24": { name: "Hwasong-12 (IRBM)",     ammo: { "1": "Hwasong-12"                      }},
    "25": { name: "Hwasong-17 (ICBM) ☢",   ammo: { "1": "Hwasong-17"                      }},
    "26": { name: "Fateh-110 (SRBM)",      ammo: { "1": "Fateh-110"                       }},
    "27": { name: "Zolfaghar (SRBM)",      ammo: { "1": "Zolfaghar"                       }},
    "28": { name: "Shahab-3 (MRBM)",       ammo: { "1": "Shahab-3",     "2": "Shahab-Cluster"          }},
    "29": { name: "Khorramshahr (MRBM)",   ammo: { "1": "Khorramshahr", "2": "Khorramshahr-Cluster" }},
    "30": { name: "Minuteman III ☢",        ammo: { "1": "Minuteman-III"                   }},
    "31": { name: "Trident II D5 ☢",        ammo: { "1": "Trident-II"                      }},
    "32": { name: "Jericho II (MRBM)",     ammo: { "1": "Jericho-II"                      }},
    "33": { name: "Jericho III (ICBM) ☢",  ammo: { "1": "Jericho-III"                     }},
    "34": { name: "Prithvi-II (SRBM)",     ammo: { "1": "Prithvi-II"                      }},
    "35": { name: "Agni-V (ICBM) ☢",       ammo: { "1": "Agni-V"                          }},
    "36": { name: "Shaheen-III (MRBM) ☢",  ammo: { "1": "Shaheen-III"                     }},
    "37": { name: "M51 (SLBM) ☢",          ammo: { "1": "M51"                             }},
    "38": { name: "Bulava (RSM-56) ☢",      ammo: { "1": "Bulava"                          }},
    "39": { name: "Sinewa (RSM-54) ☢",      ammo: { "1": "Sinewa"                          }},
    "40": { name: "Yars (RS-24) ☢",         ammo: { "1": "Yars"                            }},
    "41": { name: "Topol-M (RS-12M2) ☢",    ammo: { "1": "Topol-M"                         }},
    "42": { name: "Avangard (HGV) ☢",       ammo: { "1": "Avangard"                        }},
    "43": { name: "DF-5B (ICBM) ☢",         ammo: { "1": "DF-5B"                           }},
    "44": { name: "DF-31AG (ICBM) ☢",        ammo: { "1": "DF-31AG"                         }},
    "45": { name: "DF-4 (ICBM) ☢",           ammo: { "1": "DF-4"                            }},
    "46": { name: "DF-15B (SRBM)",           ammo: { "1": "DF-15B"                          }},
    "47": { name: "CJ-10 (Cruise)",          ammo: { "1": "CJ-10"                           }},
    "48": { name: "YJ-12 (ASM)",             ammo: { "1": "YJ-12"                           }},
    "49": { name: "DF-100 (Cruise)",         ammo: { "1": "DF-100"                          }},
    "50": { name: "9K720 Iskander-K",        ammo: { "1": "9K720"                           }},
    "51": { name: "Kh-47M2 Kinzhal ☢",       ammo: { "1": "Kh-47M2"                         }},
    "52": { name: "OTR-21 Tochka",           ammo: { "1": "OTR-21"                          }},
    "53": { name: "Tomahawk (BGM-109)",      ammo: { "1": "Tomahawk"                        }},
    "54": { name: "JASSM-ER",               ammo: { "1": "JASSM-ER"                        }},
    "55": { name: "LRASM (Navy)",            ammo: { "1": "LRASM"                           }},
    "56": { name: "Pershing II ☢",           ammo: { "1": "Pershing-II"                     }},
    "57": { name: "SM-6",                   ammo: { "1": "SM-6"                            }},
    "58": { name: "GLCM BGM-109G ☢",         ammo: { "1": "GLCM"                            }},
    "59": { name: "Storm Shadow (UK)",       ammo: { "1": "Storm-Shadow"                    }},
    "60": { name: "Trident II D5 (UK) ☢",   ammo: { "1": "Trident-II-UK"                   }},
    "61": { name: "Harpoon (UK)",            ammo: { "1": "Harpoon"                         }},
    "62": { name: "TAURUS KEPD 350",         ammo: { "1": "TAURUS"                          }},
    "63": { name: "SCALP-EG",               ammo: { "1": "SCALP"                           }},
    "64": { name: "APACHE",                 ammo: { "1": "APACHE"                          }},
    "65": { name: "SOM (Roketsan)",          ammo: { "1": "SOM"                             }},
    "66": { name: "Bora (MRBM)",            ammo: { "1": "Bora"                            }},
    "67": { name: "Kasirga (MRL)",           ammo: { "1": "Kasirga"                         }},
    "68": { name: "J-600T Yıldırım",        ammo: { "1": "J-600T"                          }},
    "69": { name: "TRG-300",                ammo: { "1": "TRG-300"                         }},
    "70": { name: "Hyunmoo-2C",             ammo: { "1": "Hyunmoo-2C"                      }},
    "71": { name: "Hyunmoo-3C (Cruise)",    ammo: { "1": "Hyunmoo-3C"                      }},
    "72": { name: "Hyunmoo-4",              ammo: { "1": "Hyunmoo-4"                       }},
    "73": { name: "Hyunmoo-5 (IRBM)",       ammo: { "1": "Hyunmoo-5"                       }},
    "74": { name: "Type-12 (Cruise)",        ammo: { "1": "Type-12"                         }},
    "75": { name: "ASM-3",                  ammo: { "1": "ASM-3"                           }},
    "76": { name: "Hsiung-Feng III",         ammo: { "1": "Hsiung-Feng-III"                 }},
    "77": { name: "Yun-Feng (LACM)",        ammo: { "1": "Yun-Feng"                        }},
    "78": { name: "CSS-5 (DF-21) ☢",        ammo: { "1": "CSS-5"                           }},
    "79": { name: "SS-300 Astros",           ammo: { "1": "SS-300"                          }},
    "80": { name: "Astros II MRL",           ammo: { "1": "Astros-II"                       }},
    "81": { name: "OTR-21 Tochka-U (UA)",   ammo: { "1": "OTR-21-UA"                       }},
    "82": { name: "Vilkha (Ukraina)",        ammo: { "1": "Vilkha"                          }},
    "83": { name: "Neptune (Cruise)",        ammo: { "1": "Neptune"                         }},
    "84": { name: "Grom-2",                 ammo: { "1": "Grom-2"                          }},
    "85": { name: "Hrim-2 (MRBM)",          ammo: { "1": "Hrim-2"                          }},
    "86": { name: "RBS-15 Mk3",             ammo: { "1": "RBS-15"                          }},
    "87": { name: "Scud-D (Egipt)",          ammo: { "1": "Scud-D"                          }},
    "88": { name: "M-600 (Syria)",           ammo: { "1": "M-600"                           }},
    "89": { name: "Tishreen (Syria)",        ammo: { "1": "Tishreen"                        }},
    "90": { name: "BADR-2000 (SA)",          ammo: { "1": "BADR-2000"                       }},
    "91": { name: "C-802 (eksport CN)",      ammo: { "1": "C-802"                           }},
    "92": { name: "C-705 (eksport CN)",      ammo: { "1": "C-705"                           }},
    "93": { name: "Emad (MRBM)",             ammo: { "1": "Emad"                            }},
    "94": { name: "Ghadr (MRBM)",            ammo: { "1": "Ghadr"                           }},
    "95": { name: "B61-12 (bomba) ☢",        ammo: { "1": "B61-12"                          }},
    "96": { name: "JASSM-ER (W80-4) ☢",      ammo: { "1": "W80-4"                           }},
    "97": { name: "Trident II (W76-2) ☢",    ammo: { "1": "W76-2"                           }},
    "98": { name: "F-35A (NATO) ☢",          ammo: { "1": "F35-B61"                         }},
    "99": { name: "B-2 Spirit (USA) ☢",       ammo: { "1": "B2-B61", "2": "B2-B83"           }},
    "100":{ name: "B-21 Raider (USA) ☢",      ammo: { "1": "B21-B61"                         }},
    "101":{ name: "F-15E Strike Eagle ☢",     ammo: { "1": "F15-B61"                         }},
    "102":{ name: "Tornado IDS (NATO) ☢",     ammo: { "1": "Tornado-B61"                     }},
    "103":{ name: "Tu-160 Blackjack ☢",       ammo: { "1": "Tu160-nuke"                      }},
    "104":{ name: "Tu-95 Bear ☢",             ammo: { "1": "Tu95-nuke"                       }},
    "105":{ name: "H-6K (Chiny) ☢",           ammo: { "1": "H6K-nuke"                        }},
    "106":{ name: "B-29 Superfortress ☢",      ammo: { "1": "LittleBoy", "2": "FatMan"         }},
    "107":{ name: "Zircon (3M22) 🇷🇺",          ammo: { "1": "Zircon"                           }},
    "108":{ name: "Burevestnik ☢ 🇷🇺",           ammo: { "1": "Burevestnik"                      }},
    "109":{ name: "Tu-22M Backfire ☢ 🇷🇺",       ammo: { "1": "Tu22M-nuke"                       }},
    "110":{ name: "B-52 Stratofortress ☢ 🇺🇸",   ammo: { "1": "B52-ALCM", "2": "B52-B61"        }},
    "111":{ name: "AGM-86 ALCM ☢ 🇺🇸",           ammo: { "1": "ALCM"                             }},
    "112":{ name: "THAAD 🇺🇸",                   ammo: { "1": "THAAD"                            }},
    "113":{ name: "DF-27 (IRBM) 🇨🇳",            ammo: { "1": "DF-27"                            }},
    "114":{ name: "DF-ZF (HGV) 🇨🇳",             ammo: { "1": "DF-ZF"                            }},
    "115":{ name: "Hwasong-18 (ICBM) ☢ 🇰🇵",     ammo: { "1": "Hwasong-18"                       }},
    "116":{ name: "Hwasong-15 (ICBM) ☢ 🇰🇵",     ammo: { "1": "Hwasong-15"                       }},
    "117":{ name: "Fattah (hiperson.) 🇮🇷",       ammo: { "1": "Fattah"                           }},
    "118":{ name: "Kheibar Shekan 🇮🇷",           ammo: { "1": "Kheibar"                          }},
    "119":{ name: "Agni-VI (ICBM) ☢ 🇮🇳",        ammo: { "1": "Agni-VI"                          }},
    "120":{ name: "BrahMos 🇮🇳",                  ammo: { "1": "BrahMos"                          }},
    "121":{ name: "Ababeel ☢ 🇵🇰",                ammo: { "1": "Ababeel"                          }},
    "122":{ name: "Ra'ad ALCM ☢ 🇵🇰",             ammo: { "1": "Raad"                             }},
    "123":{ name: "Kh-101 (cruise) 🇷🇺",           ammo: { "1": "Kh-101"                           }},
    "124":{ name: "Kh-102 ☢ (cruise) 🇷🇺",          ammo: { "1": "Kh-102"                           }},
    "125":{ name: "AGM-183 ARRW 🇺🇸",               ammo: { "1": "ARRW"                             }},
    "126":{ name: "B-1B Lancer ✈️ 🇺🇸",             ammo: { "1": "B1B-conv"                         }},
    "127":{ name: "JL-2 (SLBM) ☢ 🇨🇳",              ammo: { "1": "JL-2"                             }},
    "128":{ name: "JL-3 (SLBM) ☢ 🇨🇳",              ammo: { "1": "JL-3"                             }},
    "129":{ name: "Pukguksong-3 ☢ 🇰🇵",              ammo: { "1": "Pukguksong-3"                     }},
    "130":{ name: "K-4 (SLBM) ☢ 🇮🇳",               ammo: { "1": "K-4"                              }},
    "131":{ name: "K-15 Sagarika ☢ 🇮🇳",             ammo: { "1": "K-15"                             }},
    "132":{ name: "ASMP-A ☢ 🇫🇷",                    ammo: { "1": "ASMP-A"                           }},
    "133":{ name: "Rafale F3 ☢ ✈️ 🇫🇷",              ammo: { "1": "Rafale-ASMP"                      }},
    "134":{ name: "Avro Vulcan B2 ☢ ✈️ 🇬🇧",         ammo: { "1": "Vulcan-WE177"                     }},
    "135":{ name: "M109A7 Paladin 🇺🇸",               ammo: { "1": "M109-HE", "2": "M109-EXCAL"       }},
    "136":{ name: "PzH 2000 🇩🇪",                     ammo: { "1": "PzH-HE",  "2": "PzH-EXCAL"        }},
    "137":{ name: "AS-90 🇬🇧",                        ammo: { "1": "AS90-HE"                          }},
    "138":{ name: "CAESAR (155mm) 🇫🇷",               ammo: { "1": "CAESAR-HE", "2": "CAESAR-EXCAL"   }},
    "139":{ name: "Archer FH77BW 🇸🇪",                ammo: { "1": "Archer-HE", "2": "Archer-EXCAL"   }},
    "140":{ name: "K9 Thunder 🇰🇷",                   ammo: { "1": "K9-HE",   "2": "K9-EXCAL"         }},
    "141":{ name: "2S19 Msta-S 🇷🇺",                  ammo: { "1": "Msta-HE", "2": "Msta-Krasnopol"   }},
    "142":{ name: "2S3 Akacja 🇷🇺",                   ammo: { "1": "Akacja-HE"                        }},
    "143":{ name: "2S7 Pion 🇷🇺",                     ammo: { "1": "Pion-HE"                          }},
    "144":{ name: "2S35 Koalicja 🇷🇺",                ammo: { "1": "Koalicja-HE", "2": "Koalicja-Prec"}},
    "145":{ name: "PLZ-05 (155mm) 🇨🇳",               ammo: { "1": "PLZ05-HE"                         }},
    "146":{ name: "PCL-181 (155mm) 🇨🇳",              ammo: { "1": "PCL181-HE"                        }},
    "147":{ name: "ATHOS 2052 🇮🇱",                   ammo: { "1": "ATHOS-HE"                         }},
    "148":{ name: "Soltam M-71 🇮🇱",                  ammo: { "1": "Soltam-HE"                        }},
    "149":{ name: "T-155 Firtina 🇹🇷",                ammo: { "1": "Firtina-HE"                       }},
    "150":{ name: "ATAGS (155mm) 🇮🇳",                ammo: { "1": "ATAGS-HE"                         }},
    "151":{ name: "Dhanush (155mm) 🇮🇳",              ammo: { "1": "Dhanush-HE"                       }},
    "152":{ name: "Krab (155mm) 🇵🇱",                 ammo: { "1": "Krab2-HE", "2": "Krab2-EXCAL"     }},
    "153":{ name: "2S22 Bohdana 🇺🇦",                 ammo: { "1": "Bohdana-HE"                       }},
    "154":{ name: "Type 99 (155mm) 🇯🇵",              ammo: { "1": "Type99-HE"                        }},
    "155":{ name: "K55A1 (155mm) 🇰🇷",                ammo: { "1": "K55-HE"                           }},
    "156":{ name: "AS-90 Braveheart 🇦🇺",             ammo: { "1": "AS90AU-HE"                        }},
    "157":{ name: "M109 BR 🇧🇷",                      ammo: { "1": "M109BR-HE"                        }},
    "158":{ name: "Koksan M-1978 🇰🇵",                ammo: { "1": "Koksan-HE"                        }},
    "159":{ name: "Hoveyzeh (155mm) 🇮🇷",             ammo: { "1": "Hoveyzeh-HE"                      }},
    "160":{ name: "Raad (122mm) 🇮🇷",                 ammo: { "1": "Raad122-HE"                       }},
    "161":{ name: "M109 Pakistan 🇵🇰",                ammo: { "1": "M109PK-HE"                        }},
    "162":{ name: "M109 Saudi 🇸🇦",                   ammo: { "1": "M109SA-HE"                        }},
    "163":{ name: "T-69 (155mm) 🇹🇼",                 ammo: { "1": "T69-HE"                           }},
    "164":{ name: "PzH 2000 🇬🇷",                     ammo: { "1": "PzH2000GR-HE"                     }},
    "165":{ name: "K9 Thunder 🇳🇴",                   ammo: { "1": "K9NO-HE"                          }},
    "166":{ name: "K9 Thunder 🇫🇮",                   ammo: { "1": "K9FI-HE"                          }},
    "167":{ name: "M109A4 Canada 🇨🇦",                ammo: { "1": "M109CA-HE"                        }},
    "168":{ name: "2S1 Gvozdika 🇮🇶",                 ammo: { "1": "Gvozdika-HE"                      }},
    "169":{ name: "2S1 Gvozdika 🇷🇺",                 ammo: { "1": "Gvozdika2-HE"                     }},
    "170":{ name: "D-30 (122mm) 🇸🇾",                 ammo: { "1": "D30-HE"                           }},
    "171":{ name: "M198 (155mm) 🇺🇸",                 ammo: { "1": "M198-HE"                          }},
    "172":{ name: "FH-70 (155mm) 🇮🇹",                ammo: { "1": "FH70-HE"                          }},
    "173":{ name: "K9 Thunder 🇦🇺",                   ammo: { "1": "K9AU-HE"                          }},
    "174":{ name: "ZUZANA 2 🇸🇰",                     ammo: { "1": "Zuzana-HE"                        }},
    "175":{ name: "Dana M2 🇨🇿",                      ammo: { "1": "Dana-HE"                          }},
    "176":{ name: "Krab (UA) 🇺🇦",                    ammo: { "1": "KrabUA-HE"                        }},
};

function populateAmmo(sysKey) {
    var sel = document.getElementById('sel-ammo');
    sel.innerHTML = '';
    var ammos = SYSTEMY[sysKey].ammo;
    for (var k in ammos) {
        var opt = document.createElement('option');
        opt.value = k;
        opt.textContent = ammos[k];
        sel.appendChild(opt);
    }
}

function onSysChange() {
    var sysKey = document.getElementById('sel-sys').value;
    populateAmmo(sysKey);
    sendChange(sysKey, '1');
}

function onAmmoChange() {
    var sysKey  = document.getElementById('sel-sys').value;
    var ammoKey = document.getElementById('sel-ammo').value;
    sendChange(sysKey, ammoKey);
}

function sendChange(sysKey, ammoKey) {
    document.getElementById('sys-status').style.color = '#f0883e';
    document.getElementById('sys-status').textContent = '⌛ Zmiana...';
    fetch('/change_ammo', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-Fire-Token': TOKEN},
        body: JSON.stringify({sys: sysKey, ammo: ammoKey})
    }).then(r=>r.json()).then(d=>{
        if (d.status === 'ok') {
            document.getElementById('sys-status').style.color = '#3fb950';
            document.getElementById('sys-status').textContent = '✓ ' + d.sys + ' / ' + d.ammo;
        } else {
            document.getElementById('sys-status').style.color = '#f85149';
            document.getElementById('sys-status').textContent = '✗ Błąd zmiany';
        }
    }).catch(function() {
        document.getElementById('sys-status').style.color = '#f85149';
        document.getElementById('sys-status').textContent = '✗ Błąd połączenia';
    });
}

// Inicjalizacja dropdownów i pobranie aktualnego stanu z serwera
populateAmmo('1');
fetch('/sysinfo').then(r=>r.json()).then(d=>{
    document.getElementById('sel-sys').value = d.sys_key;
    populateAmmo(d.sys_key);
    document.getElementById('sel-ammo').value = d.ammo_key;
    document.getElementById('sys-status').textContent = '✓ ' + d.sys + ' / ' + d.ammo;
});

setTimeout(async function() { await initCesium(); console.log('[Cesium] Gotowy'); }, 3000);

var processorOnline = false;
async function checkHeartbeat() {
    try {
        var resp = await fetch('/health', { signal: AbortSignal.timeout(3000) });
        var data = await resp.json();
        processorOnline = data.processor === true;
        var el = document.getElementById('processor-status');
        if (el) {
            el.textContent = processorOnline ? '● Procesor online' : '● ' + (data.status === 'redis_offline' ? 'Redis offline' : 'Procesor C# offline');
            el.style.color = processorOnline ? '#3fb950' : '#f85149';
        }
        if (!processorOnline) {
            var btn = document.getElementById('btn-fire');
            if (btn && pendingTargets.length > 0) { btn.disabled = true; btn.style.opacity = '0.3'; btn.title = 'Procesor C# offline'; }
        }
    } catch(e) {
        processorOnline = false;
        var el = document.getElementById('processor-status');
        if (el) { el.textContent = '● Brak połączenia'; el.style.color = '#f85149'; }
    }
}
setInterval(checkHeartbeat, 3000);
checkHeartbeat();

map.on('click', function(e) {
    if (isFiring) return;
    var hits = [];
    shotLayers.forEach(function(layer) {
        if (!layer.getLayers) return;
        layer.getLayers().forEach(function(sub) {
            if (!sub.feature || !sub.feature.properties || !sub.feature.properties.shot_id) return;
            var bounds = sub.getBounds ? sub.getBounds() : null;
            if (bounds && !bounds.contains(e.latlng)) return;
            var lls = sub.getLatLngs ? sub.getLatLngs() : null;
            if (!lls) return;
            var ring = lls[0] || lls;
            if (leafletPIP(e.latlng, ring)) hits.push({ props: sub.feature.properties, layer: sub });
        });
    });
    if (hits.length === 0) return;
    hits.sort(function(a,b) { return a.props.radius_m - b.props.radius_m; });
    var best = hits[0];
    if (best.props.shot_id && shotDataStore[best.props.shot_id]) updatePanel(shotDataStore[best.props.shot_id]);
    best.layer.setStyle({ weight: (best.props.weight||1) + 3 });
    setTimeout(function() { try { best.layer.setStyle({ weight: best.props.weight||1 }); } catch(e2){} }, 1500);
    L.DomEvent.stopPropagation(e);
});

function leafletPIP(pt, ring) {
    var inside = false, x = pt.lat, y = pt.lng;
    for (var i = 0, j = ring.length-1; i < ring.length; j = i++) {
        var xi = ring[i].lat, yi = ring[i].lng, xj = ring[j].lat, yj = ring[j].lng;
        if (((yi>y) !== (yj>y)) && (x < (xj-xi)*(y-yi)/(yj-yi)+xi)) inside = !inside;
    }
    return inside;
}

// PPM = przesuń strzelca
map.on('contextmenu', function(e) {
    shooter.setLatLng(e.latlng);
    fetch('/update_pos', { method:'POST', headers:{'Content-Type':'application/json','X-Fire-Token':TOKEN}, body: JSON.stringify({lat:e.latlng.lat, lon:e.latlng.lng}) });
    // Przesuń też linie do aktualnych celów
    updatePendingLines();
});

// LPM = zaznacz cel (multi-select) — NIE strzela od razu
map.on('click', function(e) {
    if (isFiring) return;  // blokada gdy czekamy na wynik

    // Dodaj żółty znacznik celu do listy oczekujących
    var marker = L.marker(e.latlng, {icon: icons.yellow}).addTo(map)
        .bindPopup('<b>CEL #' + (pendingTargets.length+1) + '</b><br>' + e.latlng.lat.toFixed(5) + ', ' + e.latlng.lng.toFixed(5));
    var line = L.polyline([shooter.getLatLng(), e.latlng], {
        color:'#f0883e', weight:1, opacity:0.6, dashArray:'4 4'
    }).addTo(map);

    pendingTargets.push({ latlng: e.latlng, marker: marker, line: line });
    updateFireButton();
});

function updatePendingLines() {
    pendingTargets.forEach(function(t) {
        t.line.setLatLngs([shooter.getLatLng(), t.latlng]);
    });
}

function updateFireButton() {
    var btn = document.getElementById('btn-fire');
    if (pendingTargets.length === 0) {
        btn.textContent = 'OGIEŃ'; btn.disabled = true; btn.style.opacity = '0.4'; btn.title = '';
    } else if (!processorOnline) {
        btn.textContent = 'OGIEŃ  (' + pendingTargets.length + ')';
        btn.disabled = true; btn.style.opacity = '0.3';
        btn.title = 'Procesor C# offline';
    } else {
        btn.textContent = 'OGIEŃ  (' + pendingTargets.length + ')';
        btn.disabled = false; btn.style.opacity = '1'; btn.title = '';
    }
}

function cancelTargets() {
    pendingTargets.forEach(function(t) {
        map.removeLayer(t.marker);
        map.removeLayer(t.line);
    });
    pendingTargets = [];
    updateFireButton();
}

// Strzał do wszystkich zaznaczonych celów — równolegle
function fireAll() {
    if (pendingTargets.length === 0 || isFiring) return;
    isFiring = true;
    updateFireButton();
    document.getElementById('btn-fire').disabled = true;
    document.getElementById('btn-fire').style.opacity = '0.4';

    var targets = pendingTargets.slice(); // kopia
    var total   = targets.length;
    var done    = 0;

    // Usuń linie oczekujących
    pendingTargets.forEach(function(t) { map.removeLayer(t.line); });
    pendingTargets = [];
    updateFireButton();

    document.getElementById('waiting-msg').style.display = 'none';
    document.getElementById('result-content').style.display = 'none';
    document.getElementById('spinner').style.display = 'block';
    document.getElementById('spinner').textContent = 'Wysyłanie ' + total + ' strzałów...';

    // Wyślij wszystkie strzały jednocześnie
    targets.forEach(function(t, index) {
        fetch('/fire', {
            method:'POST',
            headers:{'Content-Type':'application/json','X-Fire-Token':TOKEN},
            body: JSON.stringify({lat: t.latlng.lat, lon: t.latlng.lng})
        })
        .then(r=>r.json()).then(d=>{
            if (d.status === 'ok') {
                // Polling dla każdego strzału niezależnie
                startPollingParallel(t.latlng, t.marker, d.shot_id, index+1, total, function() {
                    done++;
                    if (done >= total) {
                        isFiring = false;
                        updateFireButton();
                    }
                });
            } else {
                done++;
                if (done >= total) { isFiring = false; updateFireButton(); }
            }
        }).catch(function() {
            done++;
            if (done >= total) { isFiring = false; updateFireButton(); }
        });
    });
}

function startPollingParallel(latlng, tmpMarker, shotId, shotNum, total, onDone) {
    var attempts = 0;
    var timer = setInterval(function() {
        attempts++;
        fetch('/results?shot_id=' + shotId)
        .then(r=>r.json())
        .then(function(d) {
            if (d.status === 'ready') {
                clearInterval(timer);
                document.getElementById('spinner').textContent =
                    'Odebrano ' + shotNum + '/' + total;
                showResult(d, latlng, tmpMarker);
                if (typeof onDone === 'function') onDone();
            }
        })
        .catch(function() {});
        if (attempts > 60) {
            clearInterval(timer);
            if (typeof onDone === 'function') onDone();
        }
    }, 600);
}

function startPolling(latlng, tmpMarker, onDone) {
    if (pollTimer) clearInterval(pollTimer);
    var attempts = 0;
    var shotId = lastShotId;

    pollTimer = setInterval(function() {
        attempts++;
        fetch('/results?shot_id=' + shotId)
        .then(r=>r.json())
        .then(function(d) {
            if (d.status === 'ready') {
                clearInterval(pollTimer);
                pollTimer = null;
                showResult(d, latlng, tmpMarker);
                if (typeof onDone === 'function') onDone();
            }
        })
        .catch(function() {});

        if (attempts > 60) {  // 36s timeout
            clearInterval(pollTimer);
            pollTimer = null;
            document.getElementById('spinner').style.display = 'none';
            document.getElementById('waiting-msg').style.display = 'block';
            document.getElementById('waiting-msg').textContent = 'Timeout — brak odpowiedzi z procesora';
            isFiring = false;
            updateFireButton();
        }
    }, 600);
}

function showResult(d, latlng, tmpMarker) {
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('result-content').style.display = 'block';
    document.getElementById('r-unit').textContent    = d.pojazd + ' / ' + d.nazwa;
    document.getElementById('r-dist').textContent    = (d.dist/1000).toFixed(2) + ' km  (' + Math.round(d.dist) + ' m)';
    document.getElementById('r-az').textContent      = d.az.toFixed(1) + '°';
    // Kąt lufy — dla cruise pokazujemy typ toru
    if (d.trajectory === 'cruise') {
        document.getElementById('r-angle').textContent = 'MANEWRUJĄCA (płaski)';
    } else {
        document.getElementById('r-angle').textContent = d.angle.toFixed(2) + '°';
    }
    // Apogeum / wysokość przelotowa
    var apogeeEl    = document.getElementById('r-apogee');
    var apogeeLabel = apogeeEl.previousElementSibling;
    if (d.trajectory === 'cruise') {
        apogeeEl.style.display    = 'block';
        apogeeLabel.style.display = 'block';
        apogeeLabel.textContent   = 'WYSOKOŚĆ PRZELOTOWA';
        apogeeEl.textContent      = '~' + (d.cruise_alt || 100).toFixed(0) + ' m  (tor płaski)';
    } else if (d.apogee && d.apogee > 1000) {
        apogeeEl.style.display    = 'block';
        apogeeLabel.style.display = 'block';
        apogeeLabel.textContent   = 'APOGEUM';
        apogeeEl.textContent      = (d.apogee/1000).toFixed(1) + ' km';
    } else {
        apogeeEl.style.display    = 'none';
        apogeeLabel.style.display = 'none';
    }
    document.getElementById('r-tof').textContent = d.tof.toFixed(1) + ' s' + (d.tof > 60 ? ' (' + (d.tof/60).toFixed(1) + ' min)' : '');
    document.getElementById('r-drift').textContent   = Math.abs(d.drift).toFixed(1) + ' m (' + (d.drift >= 0 ? 'prawo' : 'lewo') + ')'
        + '  [W:' + (d.drift_wind||0).toFixed(1) + ' C:' + (d.drift_cor||0).toFixed(2) + ']';
    document.getElementById('r-ek').textContent      = d.ek.toFixed(2) + ' MJ  |  CEP: ' + d.cep + ' m';
    document.getElementById('r-weather').textContent = d.wiatr_v.toFixed(1) + ' m/s @ ' + Math.round(d.wiatr_dir) + '°  ρ=' + d.dens;

    // Strefy rażenia w panelu
    var bz = d.blast || {};
    var bzHtml = '';
    if (bz.type === 'HE' || bz.type === 'HEAT') {
        bzHtml = '<div class="label" style="margin-top:6px;">STREFY RAŻENIA</div>'
            + '<div style="font-size:11px; line-height:1.8;">'
            + '<span style="color:#ff4444;">&#9632;</span> Zniszczenie totalne: <b>' + (bz.total||0) + ' m</b><br>'
            + '<span style="color:#ff8800;">&#9632;</span> Ciężkie uszkodzenia: <b>' + (bz.heavy||0) + ' m</b><br>'
            + '<span style="color:#ffdd00;">&#9632;</span> Lekkie uszkodzenia:  <b>' + (bz.light||0) + ' m</b><br>'
            + '<span style="color:#44ff88;">&#9632;</span> Strefa zagrożenia:   <b>' + (bz.hazard||0) + ' m</b>'
            + '</div>';
    } else if (bz.type === 'SMOKE') {
        bzHtml = '<div class="label" style="margin-top:6px;">ZASŁONA DYMNA</div>'
            + '<div style="font-size:11px;"><span style="color:#aaaaaa;">&#9632;</span> Zasięg dymu: <b>' + (bz.hazard||0) + ' m</b></div>';
    } else if (bz.type === 'NUCLEAR') {
        bzHtml = '<div class="label" style="margin-top:6px;">☢ GŁOWICA JĄDROWA (Glasstone &amp; Dolan 1977)</div>'
            + '<div style="font-size:11px; line-height:1.8;">'
            + '<span style="color:#ff4444;">&#9632;</span> Kula ognia:         <b>' + (bz.total >= 1000 ? Math.round((bz.total||0)/1000) + ' km' : (bz.total||0) + ' m') + '</b><br>'
            + '<span style="color:#ff8800;">&#9632;</span> Ciężkie (20 psi):   <b>' + (bz.heavy >= 1000 ? Math.round((bz.heavy||0)/1000) + ' km' : (bz.heavy||0) + ' m') + '</b><br>'
            + '<span style="color:#ffdd00;">&#9632;</span> Lekkie (5 psi):     <b>' + (bz.light >= 1000 ? Math.round((bz.light||0)/1000) + ' km' : (bz.light||0) + ' m') + '</b><br>'
            + '<span style="color:#44ff88;">&#9632;</span> Oparzenia 1°:       <b>' + (bz.hazard >= 1000 ? Math.round((bz.hazard||0)/1000) + ' km' : (bz.hazard||0) + ' m') + '</b>'
            + '</div>'
            + '<div style="font-size:9px; color:#484f58; margin-top:3px;">Źródło: Glasstone &amp; Dolan, 1977 — wybuch naziemny</div>';
    } else if (bz.type === 'KE') {
        bzHtml = '<div class="label" style="margin-top:6px;">POCISK KINETYCZNY (KE)</div>'
            + '<div style="font-size:11px; color:#8b949e;">Brak strefy wybuchu.<br>Penetracja pancerza.</div>';
    }
    document.getElementById('r-blast').innerHTML = bzHtml;

    // Automatyczne przełączenie na Cesium — dla samolotów zawsze, dla rakiet >500km
    var aircraftNames = ['F35-B61','B2-B61','B2-B83','B21-B61','F15-B61',
                         'Tornado-B61','Tu160-nuke','Tu95-nuke','H6K-nuke',
                         'LittleBoy','FatMan','B61-12','W80-4',
                         'Tu22M-nuke','B52-ALCM','B52-B61',
                         'B1B-conv','Rafale-ASMP','Vulcan-WE177'];
    var isAircraftShot = aircraftNames.indexOf(d.nazwa) >= 0;
    if (d.dist > MISSILE_DIST_THRESHOLD || isAircraftShot) {
        autoSwitchView(d.dist);
        var sll = shooter.getLatLng();
        drawCesiumTrajectory(d, sll.lat, sll.lng, latlng.lat, latlng.lng);
    }

    if (tmpMarker) map.removeLayer(tmpMarker);

    // Popup znacznika
    var popup = '<b>' + d.nazwa + '</b><br>'
        + 'Dystans: <b>' + (d.dist/1000).toFixed(2) + ' km</b><br>'
        + 'Azymut: ' + d.az.toFixed(1) + '°<br>'
        + 'Kąt lufy: ' + d.angle.toFixed(2) + '°<br>'
        + 'Czas lotu: ' + d.tof.toFixed(1) + ' s<br>'
        + 'Dryft: ' + Math.abs(d.drift).toFixed(1) + ' m<br>'
        + 'CEP: ' + d.cep + ' m';
    if (bz.type === 'HE' || bz.type === 'HEAT') {
        popup += '<br><hr style="margin:4px 0; border-color:#444;">'
            + '<span style="color:#ff4444;">&#9679;</span> Totalne: ' + (bz.total||0) + ' m<br>'
            + '<span style="color:#ff8800;">&#9679;</span> Ciężkie: ' + (bz.heavy||0) + ' m<br>'
            + '<span style="color:#ffdd00;">&#9679;</span> Lekkie: '  + (bz.light||0) + ' m<br>'
            + '<span style="color:#44ff88;">&#9679;</span> Zagrożenie: ' + (bz.hazard||0) + ' m';
    }

    var marker = L.marker(latlng, {icon: icons.green}).addTo(map).bindPopup(popup).openPopup();
    shotLayers.push(marker);

    // ================================================================
    // TERRAIN MASKING + URBAN DAMAGE MODEL
    // ================================================================
    if (bz.type === 'SMOKE' && bz.hazard > 0) {
        shotLayers.push(L.circle(latlng, { radius: bz.hazard,
            color:'#aaaaaa', fillColor:'#aaaaaa', fillOpacity:0.15, weight:1.5, dashArray:'4 4'
        }).addTo(map).bindTooltip('Zasłona dymna: ' + bz.hazard + ' m'));
    } else if (bz.type === 'HE' || bz.type === 'HEAT' || bz.type === 'NUCLEAR') {
        (async function() {
            var terrainDone = await drawTerrainAwareZones(d, latlng, latlng.lng, latlng.lat, shotLayers);
            // Opad radioaktywny — zawsze rysowany niezależnie od terrain masking
            drawFallout(d, latlng, bz, shotLayers);
            if (!terrainDone) {
                var fallbackZones = bz.type === 'NUCLEAR' ? [
                    { r: bz.hazard, color:'#44ff88', opacity:0.04, w:1, dash:'6 3', tip:'Oparzenia 1°' },
                    { r: bz.light,  color:'#ffdd00', opacity:0.07, w:1.5, dash:null, tip:'Lekkie (5 psi)' },
                    { r: bz.heavy,  color:'#ff8800', opacity:0.12, w:2,   dash:null, tip:'Ciężkie (20 psi)' },
                    { r: bz.total,  color:'#ff4444', opacity:0.30, w:2,   dash:null, tip:'Kula ognia' },
                ] : [
                    { r: bz.hazard, color:'#44ff88', opacity:0.04, w:1, dash:'6 3', tip:'Strefa zagrożenia' },
                    { r: bz.light,  color:'#ffdd00', opacity:0.07, w:1.5, dash:null, tip:'Lekkie uszkodzenia' },
                    { r: bz.heavy,  color:'#ff8800', opacity:0.12, w:2,   dash:null, tip:'Ciężkie uszkodzenia' },
                    { r: bz.total,  color:'#ff4444', opacity:0.25, w:2,   dash:null, tip:'Zniszczenie totalne' },
                ];
                fallbackZones.forEach(function(z) {
                    if (!z.r || z.r <= 0) return;
                    shotLayers.push(L.circle(latlng, {
                        radius: z.r, color: z.color, fillColor: z.color,
                        fillOpacity: z.opacity, weight: z.w, dashArray: z.dash
                    }).addTo(map).bindTooltip(z.tip + ': ' + (z.r >= 1000 ? (z.r/1000).toFixed(1)+'km' : z.r+'m')));
                });
            }
        })();
        } else if (bz.type === 'CLUSTER') {
        var dispR  = bz.dispersion || 300;
        var subNum = bz.submunitions || 100;
        var subR   = bz.total || 5;

        // Kierunek lotu w radianach (matematyczny)
        var az_rad = (90 - d.az) * Math.PI / 180;

        // Elipsa: długość = 1.8x dispR w kierunku lotu, szerokość = 0.5x dispR
        var ellipseL = dispR * 1.8; // półoś długa (kierunek lotu)
        var ellipseW = dispR * 0.5; // półoś krótka (prostopadle)

        // Generuj punkty elipsy
        function ellipsePoints(lat, lon, semiL, semiW, azDeg, steps) {
            var pts = [];
            var R = 6371000;
            var az = (90 - azDeg) * Math.PI / 180;
            for (var i = 0; i <= steps; i++) {
                var t = (i / steps) * 2 * Math.PI;
                // Punkt na elipsie w układzie lokalnym
                var lx = semiL * Math.cos(t);
                var ly = semiW * Math.sin(t);
                // Obrót o kąt azymutu
                var rx = lx * Math.cos(az) - ly * Math.sin(az);
                var ry = lx * Math.sin(az) + ly * Math.cos(az);
                var dlat = (ry / R) * (180 / Math.PI);
                var dlon = (rx / R) * (180 / Math.PI) / Math.cos(lat * Math.PI / 180);
                pts.push([lat + dlat, lon + dlon]);
            }
            return pts;
        }

        // Rysuj elipsę rozrzutu
        var ellipsePts = ellipsePoints(latlng.lat, latlng.lng, ellipseL, ellipseW, d.az, 60);
        shotLayers.push(L.polygon(ellipsePts, {
            color:'#ff8800', fillColor:'#ff8800', fillOpacity:0.08, weight:2, dashArray:'4 4'
        }).addTo(map).bindTooltip('Strefa kasetowa: ' + subNum + ' szt., ' + dispR + 'm'));

        // Losowe submunitions wewnątrz elipsy
        var R_earth = 6371000;
        var displayed = Math.min(subNum, 150);
        var placed = 0;
        var attempts = 0;
        while (placed < displayed && attempts < displayed * 5) {
            attempts++;
            // Losowy punkt w elipsie (metoda odrzucania)
            var u = (Math.random() * 2 - 1) * ellipseL;
            var v = (Math.random() * 2 - 1) * ellipseW;
            if ((u*u)/(ellipseL*ellipseL) + (v*v)/(ellipseW*ellipseW) > 1) continue;
            // Obróć o azymut
            var az = (90 - d.az) * Math.PI / 180;
            var rx = u * Math.cos(az) - v * Math.sin(az);
            var ry = u * Math.sin(az) + v * Math.cos(az);
            var sub_lat = latlng.lat + (ry / R_earth) * (180 / Math.PI);
            var sub_lon = latlng.lng + (rx / R_earth) * (180 / Math.PI) / Math.cos(latlng.lat * Math.PI / 180);
            shotLayers.push(L.circle(L.latLng(sub_lat, sub_lon), {
                radius: subR, color:'#ffdd00', fillColor:'#ffdd00',
                fillOpacity:0.7, weight:1
            }).addTo(map));
            placed++;
        }

        // Strzałka kierunku lotu
        var arrowLen = ellipseL * 1.3;
        var arrowLat = latlng.lat + (arrowLen * Math.sin(az_rad)) / R_earth * (180/Math.PI);
        var arrowLon = latlng.lng + (arrowLen * Math.cos(az_rad)) / R_earth * (180/Math.PI) / Math.cos(latlng.lat * Math.PI/180);
        shotLayers.push(L.polyline([[latlng.lat, latlng.lng], [arrowLat, arrowLon]], {
            color:'#ff8800', weight:2, opacity:0.8
        }).addTo(map).bindTooltip('Kierunek lotu: ' + Math.round(d.az) + '°'));

        var clusterInfo = '<div class="label" style="margin-top:6px;">💥 GŁOWICA KASETOWA</div>'
            + '<div style="font-size:11px; line-height:1.8;">'
            + '<span style="color:#ff8800;">&#9632;</span> Submunitions: <b>' + subNum + ' szt.</b><br>'
            + '<span style="color:#ffdd00;">&#9632;</span> Rozrzut: <b>' + Math.round(ellipseL*2) + ' × ' + Math.round(ellipseW*2) + ' m</b><br>'
            + '<span style="color:#ff4444;">&#9632;</span> Rażenie każdej: <b>' + subR + ' m</b><br>'
            + '<span style="color:#8b949e; font-size:10px;">Kierunek: ' + Math.round(d.az) + '° | Pokazano: ' + placed + '/' + subNum + '</span>'
            + '</div>';
        document.getElementById('r-blast').innerHTML = clusterInfo;
    }

    // Linia strzelec → cel
    shotLayers.push(L.polyline([shooter.getLatLng(), latlng], {
        color:'#58a6ff', weight:1, opacity:0.4, dashArray:'6 4'
    }).addTo(map));

    addHistoryItem(d, latlng, marker);
}

function addHistoryItem(d, latlng, marker) {
    var list = document.getElementById('history-list');
    var item = document.createElement('div');
    item.className = 'hist-item';
    var now = new Date().toLocaleTimeString('pl-PL', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    var isNuke = d.blast && d.blast.type === 'NUCLEAR';
    item.innerHTML = '<div class="hi-top"><span class="hi-ammo">' + (isNuke ? '☢ ' : '') + d.nazwa + '</span><span class="hi-dist">' + (d.dist/1000).toFixed(2) + ' km</span></div><div class="hi-time">' + now + '  Az:' + d.az.toFixed(1) + '°  CEP:' + d.cep + 'm</div>';
    item.onclick = function() {
        // Przesuń mapę
        map.setView(latlng, 13);
        marker.openPopup();
        // Zaktualizuj panel wynikami tego strzału
        updatePanel(d);
    };
    list.insertBefore(item, list.firstChild);
}

function updatePanel(d) {
    document.getElementById('waiting-msg').style.display = 'none';
    document.getElementById('result-content').style.display = 'block';
    document.getElementById('r-unit').textContent    = d.pojazd + ' / ' + d.nazwa;
    document.getElementById('r-dist').textContent    = (d.dist/1000).toFixed(2) + ' km  (' + Math.round(d.dist) + ' m)';
    document.getElementById('r-az').textContent      = d.az.toFixed(1) + '°';
    if (d.trajectory === 'cruise') {
        document.getElementById('r-angle').textContent = 'MANEWRUJĄCA (płaski)';
    } else {
        document.getElementById('r-angle').textContent = d.angle.toFixed(2) + '°';
    }
    var apogeeEl    = document.getElementById('r-apogee');
    var apogeeLabel = apogeeEl.previousElementSibling;
    if (d.trajectory === 'cruise') {
        apogeeEl.style.display    = 'block';
        apogeeLabel.style.display = 'block';
        apogeeLabel.textContent   = 'WYSOKOŚĆ PRZELOTOWA';
        apogeeEl.textContent      = '~' + (d.cruise_alt || 100).toFixed(0) + ' m  (tor płaski)';
    } else if (d.apogee && d.apogee > 1000) {
        apogeeEl.style.display    = 'block';
        apogeeLabel.style.display = 'block';
        apogeeLabel.textContent   = 'APOGEUM';
        apogeeEl.textContent      = (d.apogee/1000).toFixed(1) + ' km';
    } else {
        apogeeEl.style.display    = 'none';
        apogeeLabel.style.display = 'none';
    }
    document.getElementById('r-tof').textContent     = d.tof.toFixed(1) + ' s' + (d.tof > 60 ? ' (' + (d.tof/60).toFixed(1) + ' min)' : '');
    document.getElementById('r-drift').textContent   = Math.abs(d.drift).toFixed(1) + ' m (' + (d.drift >= 0 ? 'prawo' : 'lewo') + ')  [W:' + (d.drift_wind||0).toFixed(1) + ' C:' + (d.drift_cor||0).toFixed(2) + ']';
    document.getElementById('r-ek').textContent      = d.ek.toFixed(2) + ' MJ  |  CEP: ' + d.cep + ' m';
    document.getElementById('r-weather').textContent = d.wiatr_v.toFixed(1) + ' m/s @ ' + Math.round(d.wiatr_dir) + '°  ρ=' + d.dens;

    var bz = d.blast || {};
    var bzHtml = '';
    if (bz.type === 'NUCLEAR') {
        bzHtml = '<div class="label" style="margin-top:6px;">☢ GŁOWICA JĄDROWA (Glasstone &amp; Dolan 1977)</div>'
            + '<div style="font-size:11px; line-height:1.8;">'
            + '<span style="color:#ff4444;">&#9632;</span> Kula ognia: <b>' + (bz.total >= 1000 ? Math.round(bz.total/1000) + ' km' : bz.total + ' m') + '</b><br>'
            + '<span style="color:#ff8800;">&#9632;</span> Ciężkie (20 psi): <b>' + (bz.heavy >= 1000 ? Math.round(bz.heavy/1000) + ' km' : bz.heavy + ' m') + '</b><br>'
            + '<span style="color:#ffdd00;">&#9632;</span> Lekkie (5 psi): <b>' + (bz.light >= 1000 ? Math.round(bz.light/1000) + ' km' : bz.light + ' m') + '</b><br>'
            + '<span style="color:#44ff88;">&#9632;</span> Oparzenia 1°: <b>' + (bz.hazard >= 1000 ? Math.round(bz.hazard/1000) + ' km' : bz.hazard + ' m') + '</b>'
            + '</div>';
    } else if (bz.type === 'HE' || bz.type === 'HEAT') {
        bzHtml = '<div class="label" style="margin-top:6px;">STREFY RAŻENIA</div>'
            + '<div style="font-size:11px; line-height:1.8;">'
            + '<span style="color:#ff4444;">&#9632;</span> Zniszczenie totalne: <b>' + (bz.total||0) + ' m</b><br>'
            + '<span style="color:#ff8800;">&#9632;</span> Ciężkie uszkodzenia: <b>' + (bz.heavy||0) + ' m</b><br>'
            + '<span style="color:#ffdd00;">&#9632;</span> Lekkie uszkodzenia: <b>' + (bz.light||0) + ' m</b><br>'
            + '<span style="color:#44ff88;">&#9632;</span> Strefa zagrożenia: <b>' + (bz.hazard||0) + ' m</b>'
            + '</div>';
    } else if (bz.type === 'CLUSTER') {
        bzHtml = '<div class="label" style="margin-top:6px;">💥 GŁOWICA KASETOWA</div>'
            + '<div style="font-size:11px;">Submunitions: <b>' + (bz.submunitions||0) + ' szt.</b> | Rozrzut: <b>' + (bz.dispersion||0) + ' m</b></div>';
    }
    document.getElementById('r-blast').innerHTML = bzHtml;
    if (d && d.shot_id && shotDataStore[d.shot_id]) {
        var _s = shotDataStore[d.shot_id];
        var rb = document.getElementById('r-blast');
        if (_s._terrainHtml) rb.innerHTML += _s._terrainHtml;
        if (_s._falloutHtml)  rb.innerHTML += _s._falloutHtml;
    }
}

function clearHistory() {
    if (!confirm('Wyczyścić historię i znaczniki?')) return;
    // Wyczyść mapę Leaflet 2D — tylko warstwy strzałów, nie strzelca
    shotLayers.forEach(function(l){ map.removeLayer(l); });
    shotLayers = [];
    // Wyczyść pending targets
    pendingTargets.forEach(function(t) {
        if (t.marker) map.removeLayer(t.marker);
        if (t.line)   map.removeLayer(t.line);
    });
    pendingTargets = [];
    // Reset przycisku OGIEŃ
    isFiring = false;
    var btn = document.getElementById('btn-fire');
    btn.disabled = true;
    btn.style.opacity = '0.4';
    btn.textContent = 'OGIEŃ';
    // Wyczyść encje Cesium 3D — tylko pociski, nie strzelca
    if (cesiumViewer) {
        cesiumViewer.entities.removeAll();
        // Zatrzymaj animację
        if (animTimer) clearInterval(animTimer);
        animPlaying = false;
        animStep = 0;
        animPoints = [];
        animData = null;
        missileEntity = null;
        // Usuń kontrolki animacji
        var ctrl = document.getElementById('anim-controls');
        if (ctrl) ctrl.remove();
        // Przywróć strzelca w Cesium
        if (shooter) {
            var sll = shooter.getLatLng();
            cesiumViewer.entities.add({
                position: Cesium.Cartesian3.fromDegrees(sll.lng, sll.lat, 0),
                point: { pixelSize: 14, color: Cesium.Color.fromCssColorString('#3fb950'),
                         outlineColor: Cesium.Color.WHITE, outlineWidth: 2 }
            });
        }
    }
    document.getElementById('history-list').innerHTML = '';
    document.getElementById('result-content').style.display = 'none';
    document.getElementById('waiting-msg').style.display = 'block';
    document.getElementById('waiting-msg').textContent = 'Oczekiwanie na strzał...';
    fetch('/clear_history', {method:'POST', headers:{'X-Fire-Token':TOKEN}});
    shotDataStore = {};
}

function exportPDF() { window.open('/export_pdf', '_blank'); }
</script>
</body>
</html>
"""

def require_token(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Fire-Token", "")
        if not secrets.compare_digest(token, SESSION_TOKEN):
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    html = MAP_TEMPLATE
    html = html.replace("{{lat}}", str(state["my_pos"]["lat"]))
    html = html.replace("{{lon}}", str(state["my_pos"]["lon"]))
    html = html.replace("{{token}}", SESSION_TOKEN)
    html = html.replace("{{cesium_token}}", CESIUM_TOKEN)
    return html

@app.route('/sysinfo')
def sysinfo():
    # Znajdź klucze aktywnego systemu i amunicji
    sys_key  = next((k for k,v in SYSTEMY.items() if v["n"] == state["active_sys"]["n"]),  "1") if state["active_sys"]  else "1"
    ammo_key = next((k for k,v in state["active_sys"]["a"].items() if v[0] == state["active_ammo"][0]), "1") if state["active_ammo"] else "1"
    return jsonify(
        sys=state["active_sys"]["n"]  if state["active_sys"]  else "—",
        ammo=state["active_ammo"][0]  if state["active_ammo"] else "—",
        sys_key=sys_key,
        ammo_key=ammo_key
    )


@app.route('/change_ammo', methods=['POST'])
@require_token
def change_ammo():
    data = request.json
    if not data or 'sys' not in data or 'ammo' not in data:
        return jsonify(status="error", reason="Brak danych"), 400
    sys_key  = data['sys']
    ammo_key = data['ammo']
    if sys_key not in SYSTEMY:
        return jsonify(status="error", reason="Nieznany system"), 400
    new_sys  = SYSTEMY[sys_key]
    if ammo_key not in new_sys['a']:
        return jsonify(status="error", reason="Nieznana amunicja"), 400
    state["active_sys"]  = new_sys
    state["active_ammo"] = new_sys['a'][ammo_key]
    print(f"[ZMIANA] {new_sys['n']} / {new_sys['a'][ammo_key][0]}")
    return jsonify(status="ok", sys=new_sys['n'], ammo=new_sys['a'][ammo_key][0])

@app.route('/update_pos', methods=['POST'])
@require_token
def update_pos():
    data = request.json
    if not data or 'lat' not in data or 'lon' not in data:
        return jsonify(status="error", reason="Brak danych pozycji"), 400
    state["my_pos"]["lat"] = float(data["lat"])
    state["my_pos"]["lon"] = float(data["lon"])
    print(f"[GPS] Strzelec: {state['my_pos']['lat']:.4f}, {state['my_pos']['lon']:.4f}")
    return jsonify(status="ok")

@app.route('/fire', methods=['POST'])
@require_token
def fire():
    if not state["active_ammo"]:
        return jsonify(status="error", reason="Nie wybrano amunicji"), 400
    t = request.json
    if not t or 'lat' not in t or 'lon' not in t:
        return jsonify(status="error", reason="Brak danych celu"), 400

    R = 6371000
    p1    = math.radians(state["my_pos"]["lat"])
    p2    = math.radians(t['lat'])
    d_lat = math.radians(t['lat'] - state["my_pos"]["lat"])
    d_lon = math.radians(t['lon'] - state["my_pos"]["lon"])
    a     = math.sin(d_lat/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(d_lon/2)**2
    dist  = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    try:
        w = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={state['my_pos']['lat']}&lon={state['my_pos']['lon']}"
            f"&appid={API_KEY_WEATHER}&units=metric", timeout=3
        ).json()
        wind_speed = w.get('wind', {}).get('speed', 0)
        wind_dir   = w.get('wind', {}).get('deg', 0)
        temp       = w.get('main', {}).get('temp', 15)
        press      = w.get('main', {}).get('pressure', 1013)
        dens       = round((press * 100) / (287.058 * (temp + 273.15)), 4)
    except Exception as e:
        print(f"[POGODA] Błąd: {e}")
        wind_speed, wind_dir, dens = 0, 0, 1.225

    ammo_name = state["active_ammo"][0]
    shot_id   = secrets.token_hex(8)
    blast     = BLAST_ZONES.get(ammo_name, {"total":0,"heavy":0,"light":0,"hazard":0,"type":"HE"})

    # Typ toru
    cruise_ammo = [
        "Kalibr", "Oniks",
        "CJ-10", "DF-100",          # Chiny cruise
        "BGM-109", "Tomahawk", "JASSM-ER", "LRASM", "GLCM",  # USA cruise
        "Storm-Shadow", "SCALP", "APACHE", "TAURUS", "KEPD-350",  # Europa cruise
        "SOM", "Roketsan-SOM",       # Turcja cruise
        "Hyunmoo-3C",               # Korea Płd cruise
        "Type-12",                  # Japonia cruise
        "Yun-Feng",                 # Tajwan cruise
        "Neptune",                  # Ukraina cruise
        "RBS-15",                   # Szwecja cruise
        "C-802", "C-705",           # Chiny eksport cruise
        "Harpoon",                  # NATO cruise
        "B61-12",                   # bomba grawitacyjna — tor płaski
        "F35-B61", "B2-B61", "B2-B83", "B21-B61", "F15-B61",
        "Tornado-B61", "Tu160-nuke", "Tu95-nuke", "H6K-nuke",
        "Tu22M-nuke", "B52-ALCM", "B52-B61",
        "LittleBoy", "FatMan",
        "Burevestnik", "ALCM", "Raad", "BrahMos", "Zircon",
        "Kh-101", "Kh-102",        # Rosja cruise strategiczny
        "ASMP-A",                  # Francja cruise nuklearny
        "B1B-conv", "Rafale-ASMP", "Vulcan-WE177",  # samoloty
        "ARRW",                    # USA hipersoniczny
    ]
    missile_ammo = [
        "ATACMS-A", "ATACMS-B", "9M723", "GMLRS", "GMLRS-ER", "PrSM",
        "Kinzal", "Sarmat", "Tochka-U", "Scud-B", "Rubezh",
        "DF-21D", "DF-41", "DF-17", "DF-11A", "DF-26",
        "Hwasong-12", "Hwasong-17", "KN-23",
        "Shahab-3", "Khorramshahr", "Fateh-110", "Zolfaghar",
        "Minuteman-III", "Trident-II", "Trident-II-UK",
        "Jericho-II", "Jericho-III",
        "Prithvi-II", "Agni-V",
        "Shaheen-III", "M51", "Lance",
        "Bulava", "Sinewa", "Yars", "Topol-M", "Avangard",
        # Nowe
        "DF-5B", "DF-31AG", "DF-4", "DF-15B", "YJ-12",
        "9K720", "Kh-47M2", "OTR-21", "OTR-21-UA",
        "Pershing-II", "SM-6",
        "Bora", "J-600T", "TRG-300", "Kasirga",
        "Hyunmoo-2C", "Hyunmoo-4", "Hyunmoo-5",
        "ASM-3", "Hsiung-Feng-III",
        "CSS-5", "SS-300", "Astros-II",
        "Grom-2", "Hrim-2", "Vilkha",
        "Scud-D", "M-600", "Tishreen", "BADR-2000",
        "RS-28-MIRVed", "MGM-52C", "GLCM",
        "Emad", "Ghadr",
        "B61-12", "W80-4", "W76-2",
        "Hwasong-18", "Hwasong-15",
        "DF-27", "DF-ZF",
        "Fattah", "Kheibar",
        "Agni-VI", "Ababeel",
        "THAAD",
        "JL-2", "JL-3", "Pukguksong-3",  # SLBM
        "K-4", "K-15",                    # Indie SLBM
        "Scud-B-Cluster", "9M723-Cluster", "ATACMS-Cluster",
        "Tochka-Cluster", "Shahab-Cluster", "Khorramshahr-Cluster",
    ]
    ke_ammo = ["APFSDS", "HEAT", "PAC-3 MSE", "SM-3"]
    if ammo_name in cruise_ammo:
        trajectory_type = "cruise"
    elif ammo_name in missile_ammo:
        trajectory_type = "ballistic_missile"
    elif ammo_name in ke_ammo:
        trajectory_type = "flat"
    else:
        trajectory_type = "artillery"

    payload = {
        "shot_id":    shot_id,
        "pojazd":     state["active_sys"]["n"],
        "nazwa":      ammo_name,
        "v0":         state["active_ammo"][2],
        "waga":       state["active_ammo"][1],
        "cd":         DRAG_COEFF.get(ammo_name, 0.40),
        "area":       AREA.get(ammo_name, 0.015),
        "cep":        CEP.get(ammo_name, 100),
        "blast":      blast,
        "trajectory": trajectory_type,
        "dist":       dist,
        "wiatr_v":   wind_speed,
        "wiatr_dir": wind_dir,
        "dens":      dens,
        "m_lat":     state["my_pos"]["lat"],
        "m_lon":     state["my_pos"]["lon"],
        "t_lat":     t['lat'],
        "t_lon":     t['lon'],
        "ts":        time.time()
    }

    state["r_client"].xadd("ballistics:stream", {"data": json.dumps(payload)}, maxlen=100)
    print(f"[FIRE] {ammo_name} | {dist/1000:.2f} km | id={shot_id}")
    return jsonify(status="ok", shot_id=shot_id, dist_km=f"{dist/1000:.2f}")

@app.route('/results')
def results():
    shot_id = request.args.get("shot_id", "")
    raw = state["r_client"].get(f"ballistics:result:{shot_id}")
    if not raw:
        return jsonify(status="pending")
    data = json.loads(raw)
    if not any(s.get("shot_id") == shot_id for s in state["shot_history"]):
        state["shot_history"].append(data)
    data["status"] = "ready"
    return jsonify(data)

@app.route('/health')
def health():
    try:
        last = state["r_client"].get("ballistics:processor:heartbeat")
        now = time.time()
        if last:
            age = now - float(last)
            ok = age < 5.0
        else:
            state["r_client"].ping()
            ok = False; age = 999
        return jsonify(status="ok" if ok else "processor_offline", processor=ok, ping_age_s=round(age,2) if last else None, redis="ok")
    except Exception as e:
        return jsonify(status="redis_offline", processor=False, redis="error", error=str(e)), 503

@app.route('/osm_urban')
def osm_urban():
    try:
        lat = float(request.args.get("lat",0))
        lon = float(request.args.get("lon",0))
        r   = min(int(request.args.get("r",3000)), 3000)
    except ValueError:
        return jsonify(error="invalid params"), 400
    cache_key = f"osm_urban:{lat:.3f}:{lon:.3f}:{r}"
    cached = state["r_client"].get(cache_key)
    if cached:
        d = json.loads(cached); d["cached"] = True; return jsonify(d)
    import concurrent.futures
    def fetch_b():
        q = f'[out:json][timeout:10];(way["building"](around:{r},{lat},{lon}););out count;'
        return requests.post("https://overpass-api.de/api/interpreter", data={"data":q}, timeout=10, headers={"User-Agent":"BalisticV5/1.0"}).json()
    def fetch_r():
        q = f'[out:json][timeout:10];(way["highway"~"^(primary|secondary|tertiary|trunk|motorway)$"](around:{r},{lat},{lon}););out geom;'
        return requests.post("https://overpass-api.de/api/interpreter", data={"data":q}, timeout=10, headers={"User-Agent":"BalisticV5/1.0"}).json()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            fb = ex.submit(fetch_b); fr = ex.submit(fetch_r)
            db2 = fb.result(timeout=12); dr = fr.result(timeout=12)
        bcount = int((db2.get("elements",[{}])[0].get("tags",{}).get("total",0)))
        angles = []
        for el in dr.get("elements",[]):
            geom = el.get("geometry",[])
            for i in range(len(geom)-1):
                dx = geom[i+1]["lon"]-geom[i]["lon"]; dy = geom[i+1]["lat"]-geom[i]["lat"]
                if dx==0 and dy==0: continue
                a = math.degrees(math.atan2(dx,dy))
                if a < 0: a += 180
                angles.append(a)
        canyon_angle = None; canyon_str = 0.0
        if len(angles) > 5:
            BINS = 36; bins = [0]*BINS
            for a in angles: bins[int(a/(180/BINS))%BINS] += 1
            sm = [(bins[(i-1)%BINS]+bins[i]+bins[(i+1)%BINS])/3 for i in range(BINS)]
            mi = sm.index(max(sm))
            canyon_angle = round(mi*(180/BINS)+(180/BINS/2), 1)
            canyon_str   = round(min(sm[mi]*3/len(angles)*2.5, 1.0), 3)
        result = {"density": round(min(bcount/300,1.0),3), "building_count": bcount, "road_segments": len(angles), "canyon_angle": canyon_angle, "canyon_strength": canyon_str, "cached": False}
        state["r_client"].setex(cache_key, 86400, json.dumps(result))
        print(f"[OSM] {lat:.3f},{lon:.3f} bld={bcount} rds={len(angles)} canyon={canyon_angle}")
        return jsonify(result)
    except Exception as e:
        print(f"[OSM] Error: {e}")
        return jsonify(density=0.5, building_count=0, road_segments=0, canyon_angle=None, canyon_strength=0, error=str(e))

@app.route('/clear_history', methods=['POST'])
@require_token
def clear_history():
    state["shot_history"].clear()
    return jsonify(status="ok")

@app.route('/export_pdf')
def export_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        return "Brak reportlab. Zainstaluj: pip install reportlab", 500

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('t', fontSize=16, fontName='Helvetica-Bold', spaceAfter=4)
    sub_s   = ParagraphStyle('s', fontSize=9,  fontName='Helvetica', textColor=colors.grey, spaceAfter=16)

    story = []
    story.append(Paragraph("RAPORT BALISTYCZNY — BALISTIC V5", title_s))
    story.append(Paragraph(
        f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
        f"System: {state['active_sys']['n'] if state['active_sys'] else '—'}  |  "
        f"Amunicja: {state['active_ammo'][0] if state['active_ammo'] else '—'}",
        sub_s))

    history = state["shot_history"]
    if not history:
        story.append(Paragraph("Brak danych strzałów w tej sesji.", styles['Normal']))
    else:
        headers = ["#", "Czas", "Pocisk", "Dystans", "Az°", "Kąt°", "Lot[s]", "Dryft[m]", "CEP[m]", "Tot[m]", "Cięż[m]", "Lekk[m]", "Zagr[m]"]
        rows = [headers]
        for i, s in enumerate(history, 1):
            bz = s.get("blast", {})
            is_nuclear = bz.get("type") == "NUCLEAR"
            nazwa = s.get("nazwa", "—")
            if is_nuclear:
                nazwa = "* " + nazwa  # * zamiast ☢ bo reportlab nie obsługuje emoji
            rows.append([
                str(i),
                datetime.fromtimestamp(s.get("ts", 0)).strftime("%H:%M:%S"),
                nazwa,
                f"{s.get('dist', 0)/1000:.2f} km",
                f"{s.get('az', 0):.1f}",
                f"{s.get('angle', 0):.2f}",
                f"{s.get('tof', 0):.1f}",
                f"{s.get('drift', 0):.1f}",
                str(s.get("cep", "—")),
                f"{bz.get('total', 0)/1000:.1f}km" if bz.get('total', 0) > 0 else "—",
                f"{bz.get('heavy', 0)/1000:.1f}km" if bz.get('heavy', 0) > 0 else "—",
                f"{bz.get('light', 0)/1000:.1f}km" if bz.get('light', 0) > 0 else "—",
                f"{bz.get('hazard', 0)/1000:.1f}km" if bz.get('hazard', 0) > 0 else "—",
            ])
        col_w = [0.5*cm, 1.8*cm, 2.8*cm, 2.2*cm, 1.4*cm, 1.4*cm, 1.4*cm, 1.8*cm, 1.3*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
            ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0),(-1,-1), 7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f5f5f5')]),
            ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#cccccc')),
            ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',  (0,0),(-1,-1), 3),
            ('BOTTOMPADDING',(0,0),(-1,-1), 3),
            # Kolorowanie nagłówków stref
            ('BACKGROUND',  (9,0),(9,0), colors.HexColor('#8b0000')),
            ('BACKGROUND',  (10,0),(10,0), colors.HexColor('#cc4400')),
            ('BACKGROUND',  (11,0),(11,0), colors.HexColor('#886600')),
            ('BACKGROUND',  (12,0),(12,0), colors.HexColor('#006622')),
        ]))
        story.append(t)

    doc.build(story)
    buf.seek(0)
    fname = f"balistic_raport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(buf, as_attachment=True, download_name=fname, mimetype='application/pdf')

def heartbeat_monitor():
    while True:
        try:
            last = state["r_client"].get("ballistics:processor:heartbeat")
            if last and time.time() - float(last) > 5:
                print(f"[WARN] Procesor C# offline! Ostatni ping: {time.time()-float(last):.1f}s temu")
        except: pass
        time.sleep(3)

def console():
    print("\n=== SYSTEM BALISTIC V5 ===")
    u = input("User: ")
    p = input("Pass: ")
    if USER_DB.get(u) != p:
        print("[!] Błędne dane logowania.")
        os._exit(1)
    # Domyślny system przy starcie — można zmienić w panelu mapy
    state["active_sys"]  = SYSTEMY["1"]
    state["active_ammo"] = SYSTEMY["1"]["a"]["1"]
    print(f"\n[OK] Domyślny system: {state['active_sys']['n']} / {state['active_ammo'][0]}")
    print("[OK] System i amunicję możesz zmienić w panelu na mapie.")
    print(f"[OK] Token: {SESSION_TOKEN}")
    print("[OK] Otwieram mapę...")
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Thread(target=console, daemon=True).start()
    threading.Thread(target=heartbeat_monitor, daemon=True).start()
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(port=5000, debug=False, use_reloader=False)
