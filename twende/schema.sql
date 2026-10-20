-- Twende: matatu route and fare finder
-- Four tables: stops (stages), routes, route_stops (ordered stops on a route), fare_reports (rider-submitted fares).

CREATE TABLE IF NOT EXISTS stops (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    lat  REAL NOT NULL,
    lng  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS routes (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    rate_per_km REAL NOT NULL,      -- KES charged per km before rounding
    min_fare    INTEGER NOT NULL,   -- the least a konda will accept on this route
    min_per_km  REAL NOT NULL,      -- how slowly this road moves (minutes per km)
    circuity    REAL NOT NULL DEFAULT 1.3, -- road length divided by straight line length
    color       TEXT NOT NULL       -- matatu paint colour used in the UI
);

CREATE TABLE IF NOT EXISTS route_stops (
    route_id INTEGER NOT NULL REFERENCES routes(id),
    seq      INTEGER NOT NULL,
    stop_id  INTEGER NOT NULL REFERENCES stops(id),
    PRIMARY KEY (route_id, seq)
);

CREATE TABLE IF NOT EXISTS fare_reports (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id         INTEGER NOT NULL REFERENCES routes(id),
    board_stop_id    INTEGER NOT NULL REFERENCES stops(id),
    alight_stop_id   INTEGER NOT NULL REFERENCES stops(id),
    fare             INTEGER NOT NULL CHECK (fare BETWEEN 10 AND 1000),
    travel_condition TEXT NOT NULL DEFAULT 'normal'
                     CHECK (travel_condition IN ('normal', 'rush', 'rain')),
    note             TEXT,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_lookup ON fare_reports (route_id, travel_condition);
