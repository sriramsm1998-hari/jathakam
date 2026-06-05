"""
jathakam.py

Basic framework for computing South Indian-style Jathakam
(using sidereal zodiac) with placeholders that you can adapt
to Vakya Panchangam table data.

Implements:
- Sunrise determination (approx)
- Udayadhi Nazhigai calculation
- Lagna calculation
- Nakshatra calculation
- Planetary positions (approx)
- Rasi chart
- Navamsa chart
- Dasha balance (Vimshottari)
- Simple Yoga analysis (very basic examples)
- Skeleton Prediction (rule-based placeholder)

NOTE:
This is an educational/reference implementation.
For religious/astrological use, you MUST validate against
trusted panchangam and replace approximations with
Vakya Panchangam table lookups where needed.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---------------------------------------------------
# Basic constants and utilities
# ---------------------------------------------------

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

# Planets we will consider for basic charts
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# Nakshatra spans (13°20' = 13.333... degrees each)
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati"
]

# Dasha years for Vimshottari
DASHA_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]


@dataclass
class BirthDetails:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    timezone_offset_hours: float   # e.g. +5.5 for IST
    latitude_deg: float
    longitude_deg: float           # East positive, West negative


@dataclass
class PlanetPosition:
    name: str
    longitude: float  # Sidereal longitude in degrees (0–360)
    sign: int         # 1–12
    nakshatra: str
    pada: int         # 1–4


@dataclass
class Chart:
    rasi: Dict[int, List[str]]      # sign -> list of planet names
    navamsa: Dict[int, List[str]]   # navamsa sign -> list of planet names


# ---------------------------------------------------
# Time conversions
# ---------------------------------------------------

def julian_day(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """
    Compute Julian Day Number for given Gregorian date and UT hour.
    Formula from Meeus, can handle modern dates.
    """
    if month <= 2:
        year -= 1
        month += 12

    A = year // 100
    B = 2 - A + (A // 4)

    jd_day = int(365.25 * (year + 4716))
    jd_month = int(30.6001 * (month + 1))

    jd = jd_day + jd_month + day + B - 1524.5 + hour / 24.0
    return jd


def lst_from_jd(jd: float, longitude_deg: float) -> float:
    """
    Local Sidereal Time (in degrees) for given JD and geographic longitude.
    longitude_deg: East positive.
    Approx formula adequate for astrology use; refine if needed.
    """
    T = (jd - 2451545.0) / 36525.0
    # GMST in seconds
    GMST_sec = (
        67310.54841
        + (876600.0 * 3600 + 8640184.812866) * T
        + 0.093104 * T * T
        - 6.2e-6 * T * T * T
    )
    GMST_deg = (GMST_sec / 240.0) % 360.0
    LST = (GMST_deg + longitude_deg) % 360.0
    return LST


# ---------------------------------------------------
# Sunrise calculation (approx, using solar longitude and declination)
# ---------------------------------------------------

def solar_coordinates_approx(jd: float) -> Tuple[float, float]:
    """
    Rough solar longitude and declination (tropical).
    For Vakya Panchangam, you will replace with table/exact method.
    Returns (lambda_sun_deg, declination_deg)
    """
    T = (jd - 2451545.0) / 36525.0
    # Mean anomaly of Sun
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360.0
    # Mean longitude
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360.0
    # Equation of center
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(DEG2RAD * M)
        + (0.019993 - 0.000101 * T) * math.sin(DEG2RAD * 2 * M)
        + 0.000289 * math.sin(DEG2RAD * 3 * M)
    )
    lambda_sun = (L0 + C) % 360.0
    # Obliquity of ecliptic
    epsilon = 23.439291 - 0.0130042 * T
    # Convert to declination
    lambda_rad = lambda_sun * DEG2RAD
    epsilon_rad = epsilon * DEG2RAD
    sin_delta = math.sin(epsilon_rad) * math.sin(lambda_rad)
    declination = math.asin(sin_delta) * RAD2DEG
    return lambda_sun, declination


def sunrise_utc(jd_date: float, latitude_deg: float, longitude_deg: float) -> float:
    """
    Approximate sunrise time (fractional day in UT) for given date (JD at 0h UT)
    and location.
    Returns JD of sunrise.
    """
    # initial guess: noon
    jd_noon = jd_date + 0.5
    _, decl = solar_coordinates_approx(jd_noon)

    lat_rad = latitude_deg * DEG2RAD
    dec_rad = decl * DEG2RAD

    # Sun altitude at sunrise ~ -0.833 deg (refraction + radius)
    h0 = -0.833 * DEG2RAD
    cos_H0 = (math.sin(h0) - math.sin(lat_rad) * math.sin(dec_rad)) / (math.cos(lat_rad) * math.cos(dec_rad))

    # If cos_H0 abs > 1, sun never rises/sets (polar region) – handle simply
    if cos_H0 <= -1:
        H0 = math.pi  # 12h
    elif cos_H0 >= 1:
        H0 = 0.0
    else:
        H0 = math.acos(cos_H0)

    # Local sidereal time of transit
    # (we just approximate transit as local noon, refined by longitude)
    # For simple implementation, compute LST at noon and adjust.
    LST_noon = lst_from_jd(jd_noon, longitude_deg)
    # hour angle in degrees
    H0_deg = H0 * RAD2DEG

    # convert H0 in degrees to time in days
    delta_t = H0_deg / 360.0

    # sunrise approx: transit time - delta_t
    jd_sunrise = jd_noon - delta_t
    return jd_sunrise


def local_time_from_jd(jd: float, timezone_offset_hours: float) -> Tuple[int, int, int]:
    """
    Convert JD to local time (hour, minute, second) for given timezone offset.
    """
    jd_local = jd + timezone_offset_hours / 24.0
    frac_day = (jd_local + 0.5) % 1.0  # since JD starts at noon
    total_seconds = frac_day * 86400.0
    hour = int(total_seconds // 3600)
    minute = int((total_seconds % 3600) // 60)
    second = int(total_seconds % 60)
    return hour, minute, second


# ---------------------------------------------------
# Udayadhi Nazhigai calculation
# ---------------------------------------------------

def nazhi_from_time(hours: float) -> float:
    """
    1 day = 60 nazhi; 1 nazhi = 24 minutes.
    Convert hours to nazhi.
    """
    return hours * 2.5  # because 1 hour = 60/24 = 2.5 nazhi


def compute_udayadhi_nazhigai(birth: BirthDetails) -> float:
    """
    Udayadhi Nazhigai: time elapsed from local sunrise to birth time, in nazhi.
    """
    # JD of 0h UT on that date
    jd0 = julian_day(birth.year, birth.month, birth.day, 0.0)

    # sunrise JD (UT)
    sunrise_jd_utc = sunrise_utc(jd0, birth.latitude_deg, birth.longitude_deg)

    # birth local time -> UT hour
    birth_local_hour = birth.hour + birth.minute / 60.0 + birth.second / 3600.0
    birth_ut_hour = birth_local_hour - birth.timezone_offset_hours
    birth_jd_utc = jd0 + birth_ut_hour / 24.0

    # elapsed since sunrise in days
    delta_days = birth_jd_utc - sunrise_jd_utc
    delta_hours = delta_days * 24.0

    return nazhi_from_time(delta_hours)


# ---------------------------------------------------
# Sidereal conversion (Ayanamsa)
# ---------------------------------------------------

def lahiri_ayanamsa(jd: float) -> float:
    """
    Rough Lahiri ayanamsa (approx).
    Replace with Vakya Panchangam ayanamsa if needed.
    """
    # base ~22 deg 27' at epoch; simple linear approx
    T = (jd - 2451545.0) / 36525.0
    # approx annual increase ~50.29 arcseconds
    ayan_seconds = 5029.0966 * T
    ayan_deg = 22.460148 + ayan_seconds / 3600.0
    return ayan_deg % 360.0


def tropical_to_sidereal(longitude_tropical: float, jd: float) -> float:
    """
    Convert tropical longitude to sidereal using ayanamsa.
    """
    aya = lahiri_ayanamsa(jd)
    sid = (longitude_tropical - aya) % 360.0
    return sid


# ---------------------------------------------------
# Planetary positions (approximate)
# ---------------------------------------------------

def mean_longitude_approx(jd: float, planet: str) -> float:
    """
    Very rough mean longitude for planets (tropical).
    This is deliberately simple and NOT high-precision.
    Replace with:
    - JPL ephemeris, or
    - Vakya Panchangam tables.

    The numbers below are not authoritative, only structural.
    """
    # Days since J2000
    d = jd - 2451545.0

    # Approx mean motion (deg/day) and reference longitude at J2000
    data = {
        "Sun":     (0.98564736, 280.460),
        "Moon":    (13.176396, 218.316),
        "Mars":    (0.524021,  355.453),
        "Mercury": (4.092385,  60.750),
        "Jupiter": (0.083086,  34.404),
        "Venus":   (1.602130,  88.265),
        "Saturn":  (0.033459,  50.077),
        "Rahu":    (-0.052954,  180.0),  # retrograde; relative approx
    }

    if planet not in data:
        raise ValueError(f"No data for planet {planet}")

    n, L0 = data[planet]
    L = (L0 + n * d) % 360.0
    return L


def compute_planetary_positions(jd: float) -> Dict[str, float]:
    """
    Compute sidereal longitudes (0–360) of planets at given JD (UT).
    Uses approx mean longitudes and a simple ayanamsa.
    """
    longitudes_sidereal: Dict[str, float] = {}
    for p in PLANETS:
        if p == "Ketu":
            # Ketu is opposite Rahu
            rahu_lon_trop = mean_longitude_approx(jd, "Rahu")
            ketu_lon_trop = (rahu_lon_trop + 180.0) % 360.0
            longitudes_sidereal["Ketu"] = tropical_to_sidereal(ketu_lon_trop, jd)
        else:
            trop = mean_longitude_approx(jd, p)
            longitudes_sidereal[p] = tropical_to_sidereal(trop, jd)

    return longitudes_sidereal


# ---------------------------------------------------
# Sign, Nakshatra, Navamsa helpers
# ---------------------------------------------------

def zodiac_sign(longitude: float) -> int:
    """
    0–360 -> 1..12 (Mesha=1 ... Meena=12)
    """
    return int(longitude // 30) + 1


def nakshatra_pada(longitude: float) -> Tuple[str, int]:
    """
    Given sidereal longitude (0–360), return (nakshatra name, pada 1..4).
    Each nakshatra = 13°20' = 13.333333 deg.
    Each pada = 3°20' = 3.333333 deg.
    """
    nak_deg = 13.3333333333
    pada_deg = nak_deg / 4.0

    index = int(longitude // nak_deg) % 27
    nak_name = NAKSHATRAS[index]

    # Relative within current nakshatra
    rel = longitude - index * nak_deg
    pada = int(rel // pada_deg) + 1

    return nak_name, pada


def navamsa_sign(longitude: float) -> int:
    """
    Navamsa sign calculation:
    - Each navamsa is 3°20' = 3.333333 deg.
    - For a sign, 9 navamsas. Starting scheme depends on sign.
    Traditional rule:
      Aries navamsa 1 starts at Aries, fixed sequence of signs.
    """
    # Which sign in rasi
    rasi = zodiac_sign(longitude)
    # position within sign
    pos_in_sign = longitude % 30.0
    nav_index = int(pos_in_sign // 3.3333333333)  # 0..8
    # For rasi 1, sequence starts at Aries (1); each navamsa steps one sign.
    # General rule: starting sign for odd signs is same as rasi,
    # for even signs it's the 9th from it.
    if rasi % 2 == 1:
        start_sign = rasi
    else:
        start_sign = (rasi + 8) % 12 + 1  # 9th from even sign

    nav_sign = ((start_sign - 1 + nav_index) % 12) + 1
    return nav_sign


# ---------------------------------------------------
# Lagna calculation
# ---------------------------------------------------

def compute_lagna(jd: float, latitude_deg: float, longitude_deg: float) -> float:
    """
    Compute sidereal Lagna (Ascendant) longitude.
    Uses approximate formula:
    - Get local sidereal time.
    - Compute ecliptic longitude of intersection of ecliptic with horizon.
    """
    LST_deg = lst_from_jd(jd, longitude_deg)
    epsilon = 23.439291  # obliquity; better to compute with T
    epsilon_rad = epsilon * DEG2RAD

    lat_rad = latitude_deg * DEG2RAD
    H = LST_deg * DEG2RAD  # local sidereal angle

    # Formula for ascendant longitude lambda:
    # tan(lambda) = 1 / [cos(eps) * tan(phi) - sin(eps) * sin(H) / cos(H)]
    # but numeric stability is tricky; here is a standard form:
    term1 = math.sin(H)
    term2 = math.cos(H) * math.cos(epsilon_rad) + math.tan(lat_rad) * math.sin(epsilon_rad)
    lambda_rad = math.atan2(term1, term2)
    lambda_deg = (lambda_rad * RAD2DEG) % 360.0

    # Convert to sidereal
    lagna_sidereal = tropical_to_sidereal(lambda_deg, jd)
    return lagna_sidereal


# ---------------------------------------------------
# Rasi chart, Navamsa chart
# ---------------------------------------------------

def build_charts(planet_positions: Dict[str, float]) -> Chart:
    """
    Create Rasi and Navamsa charts as dicts: sign -> list of planet names.
    """
    rasi: Dict[int, List[str]] = {i: [] for i in range(1, 13)}
    nav: Dict[int, List[str]] = {i: [] for i in range(1, 13)}

    for pname, lon in planet_positions.items():
        sgn = zodiac_sign(lon)
        rasi[sgn].append(pname)

        nav_sgn = navamsa_sign(lon)
        nav[nav_sgn].append(pname)

    return Chart(rasi=rasi, navamsa=nav)


# ---------------------------------------------------
# Nakshatra of Moon, Dasha balance (Vimshottari)
# ---------------------------------------------------

def get_moon_nakshatra(moon_longitude: float) -> Tuple[str, int, float]:
    """
    Return Moon's nakshatra, pada, and fractional position (0..1) within nakshatra.
    """
    nak, pada = nakshatra_pada(moon_longitude)
    nak_deg = 13.3333333333
    index = NAKSHATRAS.index(nak)
    start_deg = index * nak_deg
    pos = moon_longitude - start_deg
    frac = pos / nak_deg
    return nak, pada, frac


def nakshatra_lord(nakshatra_name: str) -> str:
    """
    Vimshottari dasha lord for nakshatra.
    Sequence repeats every 9 nakshatras.
    """
    sequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    idx = NAKSHATRAS.index(nakshatra_name)
    lord = sequence[idx % 9]
    return lord


def compute_dasha_balance(moon_longitude: float) -> Tuple[str, float]:
    """
    Compute starting Mahadasha lord and remaining years at birth
    (Vimshottari, rough).
    Returns (current_dasha_lord, remaining_years).
    """
    nak_name, _, frac = get_moon_nakshatra(moon_longitude)
    lord = nakshatra_lord(nak_name)
    total_years = DASHA_YEARS[lord]
    # fraction elapsed in nakshatra => fraction elapsed in dasha
    elapsed_years = total_years * frac
    remaining = total_years - elapsed_years
    return lord, remaining


# ---------------------------------------------------
# Simple Yoga analysis (placeholders)
# ---------------------------------------------------

def analyze_yogas(planet_positions: Dict[str, float]) -> List[str]:
    """
    Very minimal yoga detection, as examples.
    You should extend based on classical texts.
    """
    yogas = []

    # Helper: get sign mapping
    sign_map: Dict[str, int] = {p: zodiac_sign(lon) for p, lon in planet_positions.items()}

    # Gajakesari Yoga: Moon and Jupiter in kendras (1, 4, 7, 10) from Lagna.
    # Here we approximate by checking Moon-Jupiter angular relationships.
    if "Moon" in sign_map and "Jupiter" in sign_map:
        moon_sign = sign_map["Moon"]
        jup_sign = sign_map["Jupiter"]
        diff = (jup_sign - moon_sign) % 12
        if diff in (0, 3, 6, 9):  # same or kendra
            yogas.append("Gajakesari Yoga (approx)")

    # Rajayoga example: Lord of kendra in trikon, etc. – VERY simplified
    # Just example: Sun and Jupiter mutual kendras
    if "Sun" in sign_map and "Jupiter" in sign_map:
        sun_sign = sign_map["Sun"]
        jup_sign = sign_map["Jupiter"]
        diff = (jup_sign - sun_sign) % 12
        if diff in (3, 9):
            yogas.append("Simple Raja Yoga (Sun-Jupiter in mutual kendras)")

    # Add more yogas as per your tradition

    return yogas


# ---------------------------------------------------
# Simple prediction skeleton
# ---------------------------------------------------

def basic_prediction(planet_positions: Dict[str, float], lagna_longitude: float) -> List[str]:
    """
    Rule-based placeholder for prediction.
    Extend with robust logic and classical rules.
    """
    predictions = []

    lagna_sign = zodiac_sign(lagna_longitude)
    sign_names = {
        1: "Aries", 2: "Taurus", 3: "Gemini", 4: "Cancer",
        5: "Leo", 6: "Virgo", 7: "Libra", 8: "Scorpio",
        9: "Sagittarius", 10: "Capricorn", 11: "Aquarius", 12: "Pisces"
    }

    predictions.append(f"Lagna is in {sign_names[lagna_sign]} sign.")

    # Example: If Moon in kendra from Lagna – mental strength, prominence
    moon_sign = zodiac_sign(planet_positions["Moon"])
    diff = (moon_sign - lagna_sign) % 12
    if diff in (0, 3, 6, 9):
        predictions.append("Moon is in kendra from Lagna – indicates mental strength and visibility.")

    # Example: If many planets in 10th sign from Lagna – career focus
    tenth_sign = ((lagna_sign + 8) % 12) + 1
    count_10th = sum(1 for p, lon in planet_positions.items() if zodiac_sign(lon) == tenth_sign)
    if count_10th >= 2:
        predictions.append("Strong focus on profession and public life (multiple planets in 10th from Lagna).")

    # Add more rule-based predictions as needed
    return predictions


# ---------------------------------------------------
# Main computation wrapper
# ---------------------------------------------------

def compute_jathakam(birth: BirthDetails) -> Dict:
    """
    Compute all requested components and return a structured dict.

    Returns dict with keys:
      - sunrise_local (h, m, s)
      - udayadhi_nazhigai
      - lagna_longitude
      - lagna_sign
      - planetary_positions (list of PlanetPosition)
      - rasi_chart
      - navamsa_chart
      - dasha_balance (lord, years_remaining)
      - yogas (list of strings)
      - predictions (list of strings)
    """
    # 1. Sunrise
    jd0 = julian_day(birth.year, birth.month, birth.day, 0.0)
    sunrise_jd_utc = sunrise_utc(jd0, birth.latitude_deg, birth.longitude_deg)
    sunrise_h, sunrise_m, sunrise_s = local_time_from_jd(sunrise_jd_utc, birth.timezone_offset_hours)

    # 2. Udayadhi Nazhigai
    udayadhi_nazhigai = compute_udayadhi_nazhigai(birth)

    # 3. Birth moment JD (UT)
    birth_local_hour = birth.hour + birth.minute / 60.0 + birth.second / 3600.0
    birth_ut_hour = birth_local_hour - birth.timezone_offset_hours
    birth_jd = jd0 + birth_ut_hour / 24.0

    # 4. Planetary positions (sidereal)
    planet_lons = compute_planetary_positions(birth_jd)

    # 5. Lagna
    lagna_lon = compute_lagna(birth_jd, birth.latitude_deg, birth.longitude_deg)
    lagna_sign = zodiac_sign(lagna_lon)

    # 6. Detailed planet data
    planet_data: List[PlanetPosition] = []
    for p in PLANETS:
        lon = planet_lons[p]
        sign = zodiac_sign(lon)
        nak, pada = nakshatra_pada(lon)
        planet_data.append(PlanetPosition(name=p, longitude=lon, sign=sign, nakshatra=nak, pada=pada))

    # 7. Charts
    chart = build_charts(planet_lons)

    # 8. Dasha balance (Moon)
    moon_lon = planet_lons["Moon"]
    dasha_lord, dasha_years_remaining = compute_dasha_balance(moon_lon)

    # 9. Yoga analysis
    yogas = analyze_yogas(planet_lons)

    # 10. Predictions
    preds = basic_prediction(planet_lons, lagna_lon)

    return {
        "sunrise_local": (sunrise_h, sunrise_m, sunrise_s),
        "udayadhi_nazhigai": udayadhi_nazhigai,
        "lagna_longitude": lagna_lon,
        "lagna_sign": lagna_sign,
        "planetary_positions": planet_data,
        "rasi_chart": chart.rasi,
        "navamsa_chart": chart.navamsa,
        "dasha_balance": {
            "mahadasha_lord": dasha_lord,
            "years_remaining": dasha_years_remaining,
        },
        "yogas": yogas,
        "predictions": preds,
    }


# ---------------------------------------------------
# Example usage (you can remove this when using as a library)
# ---------------------------------------------------

if __name__ == "__main__":
    # Example birth: 1990-01-01, 06:30 IST, Chennai (13.0827 N, 80.2707 E)
    birth = BirthDetails(
        year=1990,
        month=1,
        day=1,
        hour=6,
        minute=30,
        second=0,
        timezone_offset_hours=5.5,
        latitude_deg=13.0827,
        longitude_deg=80.2707,
    )

    data = compute_jathakam(birth)

    print("Sunrise (local): %02d:%02d:%02d" % data["sunrise_local"])
    print("Udayadhi Nazhigai:", data["udayadhi_nazhigai"])
    print("Lagna:", data["lagna_longitude"], "deg, sign", data["lagna_sign"])
    print("\nPlanetary positions (sidereal):")
    for p in data["planetary_positions"]:
        print(
            f"{p.name:7s} {p.longitude:8.3f}°  Rasi {p.sign:2d}  "
            f"Nakshatra {p.nakshatra:15s} Pada {p.pada}"
        )

    print("\nRasi chart (sign -> planets):")
    for s in range(1, 13):
        print(f"Sign {s:2d}: {', '.join(data['rasi_chart'][s])}")

    print("\nNavamsa chart (sign -> planets):")
    for s in range(1, 13):
        print(f"Sign {s:2d}: {', '.join(data['navamsa_chart'][s])}")

    print("\nDasha balance:")
    print(data["dasha_balance"])

    print("\nYogas detected:")
    for y in data["yogas"]:
        print("-", y)

    print("\nBasic predictions:")
    for pr in data["predictions"]:
        print("-", pr)
