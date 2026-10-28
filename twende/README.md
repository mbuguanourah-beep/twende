# Twende: a matatu route and fare finder


Twende (Swahili for "let's go") helps a rider in Nairobi answer the two questions they ask before every trip: *which matatus do I take?* and *how much nauli will I pay?* You type where you are starting and where you are headed, and Twende finds the cheapest, the fastest and the fewest-changes way to get there, including where to change matatu. Riders can also report what they actually paid, and those reports appear next to the estimate for the next person.

## Run it in VS Code

1. Open the `twende` folder in VS Code (File, Open Folder).
2. Open a terminal (Terminal, New Terminal) and create a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - macOS or Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
   - If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` first.
3. Install Flask: `pip install -r requirements.txt`
4. Start the app: `python app.py`
5. Open http://127.0.0.1:5000 in your browser.

The database (`twende.db`) is created and filled with sample data automatically the first time you run the app. Delete the file to reset everything. You can also press F5 in VS Code and choose "Twende (Flask)" to run with the debugger.

## What the app does

- **Safiri (home):** pick a start and a destination (the boxes suggest stages as you type, and the swap button flips them). Choose the conditions: normal day, rush hour or rain. Results show up to three distinct journeys, each tagged Cheapest, Fastest and/or Fewest changes, with every leg showing where to *panda* (board) and *shuka* (alight), the stages passed, the nauli, the time and the distance.
- **Njia (routes):** browse every route and open one to see a table of nauli from the first stage under normal, rush hour and rain prices.
- **Report nauli:** submit what you paid on a route. Reports are averaged and shown on matching search results (same route, same stages, same conditions).

## How the journey finder works

All of the logic is in `helpers.py`.

1. **Fares and times from geography.** Each stage has a latitude and longitude. For any two stages on the same route, the haversine formula gives the straight line distance along the stages in between, which is multiplied by a per-route "circuity" factor because roads are longer than straight lines. Fare is `max(minimum fare, distance x rate)` rounded up to the next KES 10, since matatu fares come in tens. Time is distance x minutes per km for that road, plus a minute per stage for pick ups.
2. **A graph.** Every possible ride (stage A to stage B on one route, in either direction) becomes an edge. Riding past a stage without getting off is just one longer edge, so fares are charged once per matatu, not per stage.
3. **Dijkstra's algorithm.** Each edge has three costs: fare, minutes and one matatu used. Changing matatu adds about 8 minutes of waiting. I run Dijkstra three times, comparing costs in a different priority order each time: fare first, minutes first, or number of matatus first. Comparing cost tuples in order works because costs only ever add up and are never negative, which is what Dijkstra needs. Identical answers are merged, so one journey can carry several badges.
4. **Conditions.** Rush hour multiplies every leg's fare by 1.3 and rain by 1.6 (rounded up to KES 10), which is how nauli behaves in real life.

## Files

| File | What it does |
| --- | --- |
| `app.py` | The Flask app: the four pages, form validation, SQLite connection, and the community fare lookup. |
| `helpers.py` | Distance, fare and time calculations, building the graph, Dijkstra, and turning results into something the templates can show. |
| `schema.sql` | The four tables: `stops`, `routes`, `route_stops` and `fare_reports`. |
| `seed.py` | Sample stages and routes loaded the first time the app runs. |
| `templates/` | `layout.html` (shared page frame), `index.html`, `routes.html`, `route_detail.html`, `report.html`, `404.html`. |
| `static/style.css` | The matatu "nganya night" theme. |
| `static/app.js` | The swap button on the home page. |
| `requirements.txt` | Just Flask. |
| `.vscode/launch.json` | One click debug configuration for VS Code. |

## Design choices

- **Theme.** The look borrows from matatu culture: a night colour scheme with neon pink, yellow and cyan, the Kenyan flag stripe across the top, LED destination boards for route names (DotGothic16), a painted signage font for headings (Bungee) and marker handwriting for the "Konda says" tips (Permanent Marker). Labels use a little Swahili (panda, shuka, nauli, njia).
- **Why compute fares instead of storing them.** Storing a fare for every pair of stages on every route would mean hundreds of rows to keep correct. Computing them from distance keeps the data small, and the community reports exist to correct the estimate where it is wrong.
- **Why per-route settings.** Thika Road is a straight highway and Ngong Road winds around, so each route has its own rate, speed and circuity.
- **Simplification I made on purpose.** All routes meet at one stage called "Nairobi CBD (Kencom)". In real life the CBD has many termini and changing matatu can mean a walk.
- **Sample data.** Stage coordinates are approximate and the routes and rates are simplified examples, not an official directory. Always confirm the nauli with the konda.
- **Safety.** All database queries use placeholders, and user text is escaped by Jinja when displayed.

## Ideas for next steps

- Load real route data from an open dataset such as Digital Matatus.
- Add accounts, so reports can be voted up or removed.
- Show the routes on a map.
- Add walking transfers between nearby stages.
