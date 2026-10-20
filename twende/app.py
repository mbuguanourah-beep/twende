"""Twende: a matatu route and fare finder for Nairobi."""

import os
import random
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

from helpers import (
    CONDITIONS,
    find_journeys,
    load_network,
    resolve_stop,
    route_profile,
)
from seed import seed_database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "twende.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

KONDA_TIPS = [
    "Rain means higher nauli. Keep a few extra notes ready.",
    "Rush hour starts earlier than you think. Leave 30 minutes ahead.",
    "Keep your phone zipped away at the stage. Pickpockets love distracted riders.",
    "Small notes make the konda happy. Big notes make the whole matatu wait.",
    "Tell the konda your stage early so you are not swept past it.",
    "Sit near the door if your stage is coming up soon.",
]

_network = None  # the stops and routes rarely change, so we load them once


# ---------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and load the sample data the first time the app runs."""
    db = sqlite3.connect(DATABASE)
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    if db.execute("SELECT COUNT(*) FROM stops").fetchone()[0] == 0:
        seed_database(db)
    db.close()


def get_network():
    global _network
    if _network is None:
        _network = load_network(get_db())
    return _network


def community_fare(db, route_id, board_id, alight_id, condition):
    """Average of what riders say they paid for this leg in these conditions."""
    row = db.execute(
        """
        SELECT ROUND(AVG(fare)) AS avg_fare, COUNT(*) AS n
        FROM fare_reports
        WHERE route_id = ? AND travel_condition = ?
          AND ((board_stop_id = ? AND alight_stop_id = ?)
            OR (board_stop_id = ? AND alight_stop_id = ?))
        """,
        (route_id, condition, board_id, alight_id, alight_id, board_id),
    ).fetchone()
    if row["n"]:
        return {"avg": int(row["avg_fare"]), "n": row["n"]}
    return None


# ------------------------------------------------------------------ pages
@app.route("/")
def index():
    net = get_network()
    stops = sorted(net["stops"].values(), key=lambda s: s["name"])
    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    condition = request.args.get("condition", "normal")
    if condition not in CONDITIONS:
        condition = "normal"

    journeys = None
    error = None

    if origin or destination:
        origin_id = resolve_stop(origin, net["stops"])
        dest_id = resolve_stop(destination, net["stops"])
        if not origin:
            error = "Tell us where you are starting from."
        elif not destination:
            error = "Tell us where you are headed."
        elif origin_id is None:
            error = f"We could not find a stage called \"{origin}\". Pick one from the suggestions."
        elif dest_id is None:
            error = f"We could not find a stage called \"{destination}\". Pick one from the suggestions."
        elif origin_id == dest_id:
            error = "Your start and destination are the same stage. You have already arrived!"
        else:
            db = get_db()
            journeys = find_journeys(net, origin_id, dest_id, condition)
            for journey in journeys:
                for leg in journey["legs"]:
                    leg["community"] = community_fare(
                        db, leg["route_id"], leg["board_id"], leg["alight_id"], condition
                    )
            origin = net["stops"][origin_id]["name"]
            destination = net["stops"][dest_id]["name"]

    return render_template(
        "index.html",
        stops=stops,
        origin=origin,
        destination=destination,
        condition=condition,
        conditions=CONDITIONS,
        journeys=journeys,
        error=error,
        tip=random.choice(KONDA_TIPS),
    )


@app.route("/routes")
def routes():
    net = get_network()
    cards = []
    for route in net["routes"].values():
        names = [net["stops"][s]["name"] for s in route["stop_ids"]]
        cards.append({**route, "stop_names": names})
    return render_template("routes.html", routes=cards)


@app.route("/routes/<int:route_id>")
def route_detail(route_id):
    net = get_network()
    route = net["routes"].get(route_id)
    if route is None:
        abort(404)
    reports = get_db().execute(
        """
        SELECT fr.fare, fr.travel_condition, fr.note, fr.created_at,
               b.name AS board, a.name AS alight
        FROM fare_reports fr
        JOIN stops b ON b.id = fr.board_stop_id
        JOIN stops a ON a.id = fr.alight_stop_id
        WHERE fr.route_id = ?
        ORDER BY fr.id DESC LIMIT 10
        """,
        (route_id,),
    ).fetchall()
    return render_template(
        "route_detail.html",
        route=route,
        profile=route_profile(net, route_id),
        conditions=CONDITIONS,
        reports=reports,
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    net = get_network()
    db = get_db()

    if request.method == "POST":
        try:
            route_id = int(request.form["route_id"])
            board_id = int(request.form["board_id"])
            alight_id = int(request.form["alight_id"])
            fare = int(request.form["fare"])
        except (KeyError, ValueError):
            flash("Fill in every field with valid numbers, then try again.", "error")
            return redirect(url_for("report"))

        condition = request.form.get("condition", "normal")
        note = request.form.get("note", "").strip()[:140]
        route = net["routes"].get(route_id)

        if route is None or board_id not in route["stop_ids"] or alight_id not in route["stop_ids"]:
            flash("Both stages must be on the route you picked.", "error")
        elif board_id == alight_id:
            flash("Panda and Shuka stages must be different.", "error")
        elif not 10 <= fare <= 1000:
            flash("Nauli must be between KES 10 and KES 1000.", "error")
        elif condition not in CONDITIONS:
            flash("Pick a valid travel condition.", "error")
        else:
            db.execute(
                "INSERT INTO fare_reports (route_id, board_stop_id, alight_stop_id, fare, "
                "travel_condition, note) VALUES (?, ?, ?, ?, ?, ?)",
                (route_id, board_id, alight_id, fare, condition, note or None),
            )
            db.commit()
            flash("Asante! Your nauli report is in.", "success")
        return redirect(url_for("report"))

    recent = db.execute(
        """
        SELECT fr.fare, fr.travel_condition, fr.note, fr.created_at,
               r.name AS route, b.name AS board, a.name AS alight
        FROM fare_reports fr
        JOIN routes r ON r.id = fr.route_id
        JOIN stops b ON b.id = fr.board_stop_id
        JOIN stops a ON a.id = fr.alight_stop_id
        ORDER BY fr.id DESC LIMIT 8
        """
    ).fetchall()
    route_stops = {
        rid: [{"id": s, "name": net["stops"][s]["name"]} for s in r["stop_ids"]]
        for rid, r in net["routes"].items()
    }
    selected_route = request.args.get("route_id", type=int)
    return render_template(
        "report.html",
        routes=list(net["routes"].values()),
        route_stops=route_stops,
        selected_route=selected_route,
        conditions=CONDITIONS,
        recent=recent,
    )


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
