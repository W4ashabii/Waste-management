"""Demo geography: approximate ward positions and collection stops.

Ward 17 (the demo ward) uses real Kathmandu places for its four routes. Other wards
get stops placed around an approximate ward centre. The centres come from the hex map
the KMC portal draws (src/data/kmc/hexLayout.json in the website), stretched over the
Kathmandu Metropolitan City area. They are good enough for a demo map, not for
navigation.
"""
import math

# Kathmandu Metropolitan City, roughly.
NORTH, SOUTH, WEST, EAST = 27.742, 27.672, 85.284, 85.360

# Same numbers as hexLayout.json: hex size, origin and rows of [count, offset].
HEX_SIZE, HEX_ORIGIN = 33, (34, 46)
HEX_ROWS = [(4, 2), (6, 1), (7, 0), (7, 0), (5, 1), (3, 2)]
HEX_VIEW = (470, 340)

# Ward 17's routes (route number -> waste type and stops in visiting order).
DEMO_ROUTES: dict[int, dict] = {
    1: {
        "waste": "Organic",
        "stops": [
            ("Koteshwor Chowk", 27.67880, 85.34930),
            ("Mahadevsthan Marg", 27.68150, 85.35260),
            ("Jadibuti", 27.67390, 85.35560),
            ("Kantipur Colony", 27.67620, 85.34600),
            ("Bhimsengola Road", 27.68000, 85.34390),
        ],
    },
    2: {
        "waste": "Inorganic",
        "stops": [
            ("Tinkune Chowk", 27.68610, 85.34680),
            ("Subidhanagar", 27.68420, 85.34160),
            ("Gairigaun", 27.68900, 85.34950),
            ("Airport Road", 27.69250, 85.35150),
            ("Sinamangal", 27.69560, 85.35330),
        ],
    },
    3: {
        "waste": "Organic",
        "stops": [
            ("New Baneshwor Chowk", 27.68870, 85.33590),
            ("Shankhamul Road", 27.68350, 85.33250),
            ("Buddhanagar", 27.68620, 85.33030),
            ("Bijulibazar", 27.69150, 85.32930),
            ("Mid-Baneshwor", 27.69250, 85.33800),
            ("Old Baneshwor", 27.69850, 85.34000),
            ("Battisputali", 27.70370, 85.34100),
        ],
    },
    4: {
        "waste": "Organic + Inorganic",
        "stops": [
            ("Gaushala Chowk", 27.70760, 85.34460),
            ("Pashupati Gate", 27.71030, 85.34790),
            ("Mitrapark", 27.71250, 85.34510),
            ("Chabahil Road", 27.71610, 85.34680),
            ("Jayabageshwori", 27.70590, 85.34960),
            ("Sinamangal Bridge", 27.70100, 85.35100),
        ],
    },
}


def _hex_centres() -> dict[int, tuple[float, float]]:
    w = math.sqrt(3) * HEX_SIZE
    centres, k = {}, 1
    for i, (count, offset) in enumerate(HEX_ROWS):
        for j in range(count):
            centres[k] = (HEX_ORIGIN[0] + (offset + j) * w + (i % 2) * w / 2, HEX_ORIGIN[1] + i * 1.5 * HEX_SIZE)
            k += 1
    return centres


def ward_centres() -> dict[int, tuple[float, float]]:
    """Ward number -> (lat, lng)."""
    out = {}
    for n, (x, y) in _hex_centres().items():
        out[n] = (round(NORTH - y / HEX_VIEW[1] * (NORTH - SOUTH), 5), round(WEST + x / HEX_VIEW[0] * (EAST - WEST), 5))
    return out


WARD_CENTRES = ward_centres()


def generated_stops(ward: int, route_n: int, count: int = 5) -> list[tuple[str, float, float]]:
    """A loop of stops around the ward centre; each route of the ward gets its own direction."""
    lat0, lng0 = WARD_CENTRES.get(ward, ((NORTH + SOUTH) / 2, (WEST + EAST) / 2))
    start = route_n * 1.7
    stops = []
    for i in range(count):
        a = start + i * 0.9
        r = 0.0025 + 0.0012 * (i % 3)  # about 250-500 m
        stops.append((f"Ward {ward} zone {route_n} · point {i + 1}", round(lat0 + r * math.sin(a), 5), round(lng0 + r * math.cos(a), 5)))
    return stops
