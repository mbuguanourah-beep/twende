"""Sample data for Twende.

IMPORTANT: coordinates are approximate and routes/fares are simplified examples,
not an official matatu directory. The point is to give the pathfinder a realistic
network to work on. Edit these lists (or add rows through SQL) to improve the map.
"""

# (id, name, latitude, longitude)
STOPS = [
    (1, "Nairobi CBD (Kencom)", -1.2864, 36.8250),
    (2, "Westlands", -1.2676, 36.8108),
    (3, "Kangemi", -1.2670, 36.7450),
    (4, "Uthiru", -1.2740, 36.7110),
    (5, "Kikuyu", -1.2467, 36.6628),
    (6, "Adams Arcade", -1.3000, 36.7800),
    (7, "Prestige Plaza", -1.3010, 36.7690),
    (8, "Dagoretti Corner", -1.2985, 36.7470),
    (9, "Karen", -1.3185, 36.7116),
    (10, "Ngong Town", -1.3631, 36.6540),
    (11, "Kawangware", -1.2850, 36.7430),
    (12, "Pangani", -1.2667, 36.8333),
    (13, "Ruaraka", -1.2410, 36.8730),
    (14, "Roysambu", -1.2190, 36.8870),
    (15, "Githurai 45", -1.1960, 36.9120),
    (16, "Ruiru", -1.1470, 36.9600),
    (17, "Juja", -1.1050, 37.0130),
    (18, "Thika", -1.0333, 37.0693),
    (19, "Makadara", -1.2960, 36.8530),
    (20, "Donholm", -1.2960, 36.8900),
    (21, "Umoja", -1.2800, 36.9040),
    (22, "Kayole", -1.2750, 36.9170),
    (23, "Nyayo Stadium", -1.3030, 36.8250),
    (24, "South C", -1.3180, 36.8250),
    (25, "Imara Daima", -1.3290, 36.8760),
    (26, "JKIA", -1.3192, 36.9275),
    (27, "Syokimau", -1.3600, 36.9400),
    (28, "Athi River", -1.4550, 36.9780),
    (29, "Nairobi West", -1.3140, 36.8160),
    (30, "Lang'ata (Carnivore)", -1.3400, 36.7950),
    (31, "Galleria", -1.3440, 36.7600),
    (32, "Ongata Rongai", -1.3917, 36.7616),
]

# (id, name, rate_per_km, min_fare, min_per_km, circuity, colour, [stop ids in order])
ROUTES = [
    (1, "Rongai Express", 4.3, 30, 2.6, 1.3, "#ff2e88", [1, 29, 30, 31, 32]),
    (2, "Ngong Road Nganya", 3.5, 30, 2.7, 1.3, "#ffd500", [1, 6, 7, 8, 9, 10]),
    (3, "Waiyaki Way Rocket", 4.0, 30, 2.4, 1.3, "#00c853", [1, 2, 3, 4, 5]),
    (4, "Kawangware Kasuku", 5.0, 30, 3.0, 1.3, "#00d1ff", [11, 8, 7, 6, 1]),
    (5, "Thika Road Superhighway", 3.3, 30, 1.5, 1.1, "#ff3b30", [1, 12, 13, 14, 15, 16, 17, 18]),
    (6, "Jogoo Road Link", 5.0, 30, 3.0, 1.3, "#ff8a00", [1, 19, 20, 21, 22]),
    (7, "Mombasa Road Jet", 3.0, 30, 2.0, 1.15, "#a46bff", [1, 23, 24, 25, 26, 27, 28]),
    (8, "Westlands to Pangani Shuttle", 6.0, 30, 3.0, 1.3, "#4d8dff", [2, 12]),
    (9, "Lang'ata to Karen Feeder", 5.0, 30, 2.8, 1.3, "#00e5a8", [30, 9]),
    (10, "Rongai to Ngong Feeder", 4.5, 30, 2.8, 1.2, "#ff6bd6", [32, 10]),
]


def seed_database(db):
    """Insert the sample stops and routes into an open sqlite3 connection."""
    db.executemany("INSERT INTO stops (id, name, lat, lng) VALUES (?, ?, ?, ?)", STOPS)
    for route_id, name, rate, min_fare, min_per_km, circuity, color, stop_ids in ROUTES:
        db.execute(
            "INSERT INTO routes (id, name, rate_per_km, min_fare, min_per_km, circuity, color) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (route_id, name, rate, min_fare, min_per_km, circuity, color),
        )
        db.executemany(
            "INSERT INTO route_stops (route_id, seq, stop_id) VALUES (?, ?, ?)",
            [(route_id, seq, stop_id) for seq, stop_id in enumerate(stop_ids)],
        )
    db.commit()
