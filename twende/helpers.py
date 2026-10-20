"""The brains of Twende: fares, distances and the journey finder.

How it works, in short:
1. Every route is an ordered list of stops. For any two stops on the same route
   we can work out a leg: distance, time and fare.
2. Every possible leg becomes an edge in a graph whose nodes are stops.
3. Dijkstra's algorithm searches that graph. Changing matatu costs extra waiting
   time, and each new matatu means paying a new fare.
4. We run the search three times with different priorities (cheapest, fastest,
   fewest changes) and show the distinct answers.
"""

import heapq
import itertools
import math

TRANSFER_WAIT_MIN = 8     # average wait when you change matatu
DWELL_MIN_PER_STOP = 1.0  # time a matatu spends picking up and dropping off

# Weather and time of day change the nauli. Multiplier is applied to each leg.
CONDITIONS = {
    "normal": {"label": "Normal day", "multiplier": 1.0},
    "rush": {"label": "Rush hour", "multiplier": 1.3},
    "rain": {"label": "Mvua (rain)", "multiplier": 1.6},
}

# Each mode ranks journeys by (fare, minutes, legs) in a different order.
# Index 0 = fare, 1 = minutes, 2 = number of matatus.
MODES = {
    "cheapest": ((0, 1, 2), "Cheapest"),
    "fastest": ((1, 0, 2), "Fastest"),
    "fewest": ((2, 0, 1), "Fewest changes"),
}

ALIASES = {"town": "nairobi cbd (kencom)", "cbd": "nairobi cbd (kencom)"}


def roundup10(amount):
    """Matatu fares come in tens of shillings."""
    return int(math.ceil(amount / 10.0) * 10)


def surged(base_fare, multiplier):
    return base_fare if multiplier == 1 else roundup10(base_fare * multiplier)


def haversine_km(lat1, lng1, lat2, lng2):
    """Straight line distance between two coordinates, in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_network(db):
    """Read stops and routes from SQLite into plain dicts the algorithms can use."""
    stops = {row["id"]: dict(row) for row in db.execute("SELECT id, name, lat, lng FROM stops")}
    routes = {}
    for row in db.execute("SELECT * FROM routes ORDER BY id"):
        routes[row["id"]] = {**dict(row), "stop_ids": []}
    for row in db.execute("SELECT route_id, stop_id FROM route_stops ORDER BY route_id, seq"):
        routes[row["route_id"]]["stop_ids"].append(row["stop_id"])
    return {"stops": stops, "routes": routes}


def resolve_stop(text, stops):
    """Turn whatever the rider typed into a stop id (or None)."""
    t = text.strip().lower()
    if not t:
        return None
    t = ALIASES.get(t, t)
    for stop in stops.values():
        if stop["name"].lower() == t:
            return stop["id"]
    matches = [s["id"] for s in stops.values() if t in s["name"].lower()]
    return matches[0] if len(matches) == 1 else None


def leg_stats(network, route, i, j):
    """Distance (km), time (minutes) and base fare for riding from index i to j on a route."""
    lo, hi = sorted((i, j))
    ids = route["stop_ids"][lo:hi + 1]
    km = 0.0
    for a, b in zip(ids, ids[1:]):
        sa, sb = network["stops"][a], network["stops"][b]
        km += haversine_km(sa["lat"], sa["lng"], sb["lat"], sb["lng"])
    km *= route["circuity"]  # roads are longer than straight lines
    minutes = km * route["min_per_km"] + (hi - lo) * DWELL_MIN_PER_STOP
    fare = max(route["min_fare"], roundup10(km * route["rate_per_km"]))
    return km, minutes, fare


def build_graph(network, multiplier=1.0):
    """Every ordered pair of stops on a route becomes a directed edge."""
    graph = {stop_id: [] for stop_id in network["stops"]}
    for route in network["routes"].values():
        ids = route["stop_ids"]
        for i, a in enumerate(ids):
            for j, b in enumerate(ids):
                if i == j:
                    continue
                km, minutes, base = leg_stats(network, route, i, j)
                graph[a].append({
                    "to": b, "route_id": route["id"], "i": i, "j": j,
                    "km": km, "minutes": minutes, "fare": surged(base, multiplier),
                })
    return graph


def _best_path(graph, origin, dest, order):
    """Dijkstra over (fare, minutes, legs) compared in the given priority order."""
    counter = itertools.count()
    start = (0, 0.0, 0)
    best = {origin: start}
    prev = {}
    heap = [(tuple(start[k] for k in order), next(counter), origin, start)]

    while heap:
        _, _, node, vec = heapq.heappop(heap)
        if vec != best.get(node):
            continue  # stale entry, a better way here was already found
        if node == dest:
            break
        for edge in graph[node]:
            wait = TRANSFER_WAIT_MIN if node != origin else 0
            new_vec = (vec[0] + edge["fare"], vec[1] + edge["minutes"] + wait, vec[2] + 1)
            key = tuple(new_vec[k] for k in order)
            old = best.get(edge["to"])
            if old is None or key < tuple(old[k] for k in order):
                best[edge["to"]] = new_vec
                prev[edge["to"]] = (node, edge)
                heapq.heappush(heap, (key, next(counter), edge["to"], new_vec))

    if dest not in best:
        return None
    legs, node = [], dest
    while node != origin:
        node, edge = prev[node]
        legs.append(edge)
    legs.reverse()
    return legs


def _describe(network, legs):
    """Turn raw edges into something a template can show."""
    out = []
    for e in legs:
        route = network["routes"][e["route_id"]]
        ids = route["stop_ids"]
        path = ids[e["i"]:e["j"] + 1] if e["j"] > e["i"] else ids[e["j"]:e["i"] + 1][::-1]
        names = [network["stops"][s]["name"] for s in path]
        out.append({
            "route_id": route["id"], "route_name": route["name"], "color": route["color"],
            "board_id": path[0], "board": names[0],
            "alight_id": path[-1], "alight": names[-1],
            "via": names[1:-1], "stops": len(path) - 1,
            "km": round(e["km"], 1), "minutes": round(e["minutes"]), "fare": e["fare"],
            "community": None,
        })
    transfers = len(out) - 1
    return {
        "legs": out,
        "fare": sum(leg["fare"] for leg in out),
        "minutes": sum(leg["minutes"] for leg in out) + TRANSFER_WAIT_MIN * transfers,
        "transfers": transfers,
        "km": round(sum(leg["km"] for leg in out), 1),
        "badges": [],
    }


def find_journeys(network, origin, dest, condition="normal"):
    """Return the distinct best journeys (cheapest, fastest, fewest changes)."""
    if origin == dest:
        return []
    graph = build_graph(network, CONDITIONS[condition]["multiplier"])
    journeys, seen = [], {}
    for _, (order, label) in MODES.items():
        legs = _best_path(graph, origin, dest, order)
        if not legs:
            continue
        journey = _describe(network, legs)
        signature = tuple((l["route_id"], l["board_id"], l["alight_id"]) for l in journey["legs"])
        if signature in seen:
            seen[signature]["badges"].append(label)
        else:
            journey["badges"] = [label]
            seen[signature] = journey
            journeys.append(journey)
    return journeys


def route_profile(network, route_id):
    """Km, minutes and fares from the first stage to every other stage on a route."""
    route = network["routes"][route_id]
    rows = []
    for idx, stop_id in enumerate(route["stop_ids"]):
        name = network["stops"][stop_id]["name"]
        if idx == 0:
            rows.append({"name": name, "km": 0.0, "minutes": 0, "fares": None})
            continue
        km, minutes, base = leg_stats(network, route, 0, idx)
        rows.append({
            "name": name, "km": round(km, 1), "minutes": round(minutes),
            "fares": {key: surged(base, c["multiplier"]) for key, c in CONDITIONS.items()},
        })
    return rows
