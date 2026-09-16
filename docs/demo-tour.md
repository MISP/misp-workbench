# Demo Tour

A presenter's route through misp-workbench for people seeing it for the first
time. Roughly 15 minutes at a walking pace, or 6 if you stop after the fourth
stop.

It assumes the instance has been seeded with
[`seed-demo`](development.md#seeding-a-demo-instance). Every number quoted
below is what that dataset actually produces — if you see something different,
the seed did not run.

```bash
docker compose exec api poetry run python -m app.cli seed-demo
```

Log in as `admin@admin.test` / `admin`.

!!! tip "Re-seed between runs"
    `seed-demo` is additive and safe to repeat. Run it again before a second
    demo so the hunt history is re-timed to today and anything you changed
    live is reset.

---

## The through-line

The tour follows one indicator — the IP `185.220.101.42` — from a search box,
through the events that share it, to the correlation that ties them together.
Everything else hangs off that thread. Say the IP out loud at stop 1 and call
back to it at stops 3 and 4; it is what makes the demo feel like an
investigation rather than a feature list.

---

## 1. Explore — "one search box over everything"

**Go to** `explore`. **Type** `185.220.101.42` and press Enter.

**What they see:** a timeline histogram, and three tabs — **Events 0**,
**Attributes 3**, **Correlations 6** — opened on **Attributes**, because that
is the first tab with results.

**Say:** every event, attribute, object, correlation and sighting is in one
search index. This is Lucene syntax, not a fixed form: `type:"ip-src" AND
tags.name:"tlp:clear"` works, and so does a bare value.

Searching a bare indicator matches attributes rather than events — an event
does not carry the value in its own fields — so the view lands on the tab that
has something in it. Search `Cobalt Strike` instead and it opens on **Events**.
Clicking a tab yourself always wins; the view only chooses when the tab you are
on came back empty.

**Also worth showing:** the date filter defaults to **Last 30 days**; the save
icon beside the search box stores a query in **search history**.

---

## 2. An event, and the graph

**Go to** the event *Emotet delivery chain — phishing to C2*, then the
**Graph** tab.

**What they see:** 15 nodes — the event at the centre, three objects
(`domain-ip`, `file`, `email`), their attributes, and a threat-actor galaxy
node. Edges are labelled with the real relationships: *communicates with*,
*contains*.

**Say:** this is MISP's own object model, not a bespoke schema. The graph is
fed by `GET /events/{uuid}/misp-json` — the same serialisation used to push to
a remote MISP server.

**Do:** drag a node, then switch **Detailed → Grouped → Relations**. Double-click
a node to open it.

This is the strongest visual in the product. Give it a moment.

**Also on this event:** the **Overview** tab carries a written incident report
in Markdown — summary, delivery chain, an indicator table, actions taken and
open questions. Worth showing to anyone who asks whether the platform is only
for machine-readable data.

---

## 3. Correlations — "what did we already know?"

**Go to** `correlations`.

**What they see:** *18 correlations across the index*. Under **Most correlated
attributes**, `185.220.101.42` appears three times — once per event that
carries it. Under **Most correlating events**, the Cobalt Strike event and the
partner report both score 5.

**Say:** nobody wrote these down. Three analysts logged the same address in
three unrelated submissions and the platform tied them together.

**Do:** switch **Rankings → Graph** for the visual version.

This is the payoff for stop 1. Point back at the IP explicitly.

---

## 4. Hunts — "tell me when this changes"

**Go to** `hunts` → *IP and domain indicators*.

**What they see:** a 90-day heatmap with three visible spikes, a sparkline of
the same runs, and below it **8 total matches** with a **last run results**
badge.

**Say:** a hunt is a saved query that re-runs on a schedule and tells you when
its answer changes — not a search you have to remember to repeat.

**Do:** press **Run Now** to execute it live, then **Open in Explore** to show
the results land back in the search view.

The other three hunts show the range of hunt types: `cpe` against vulnerability
data (246 matches), `rulezet` detection rules (8), and MITRE ATT&CK by
technique (2).

!!! note "The MITRE hunt is deliberately small"
    Two matches, because only two seeded events carry the T1566.001 technique
    tag. If someone asks why, that is the honest answer — it is matching a
    galaxy tag, not doing text search.

---

## 5. Tech Lab — the part people do not expect

**Go to** `tech-lab` → **transformation servos**.

**What they see:** two tabs — **Custom servos** (4, two enabled) and **System
pipelines** (6, read-only).

**Say:** these are OpenSearch ingest pipelines you author from the UI. They run
on every attribute as it is indexed, so the work happens once at write time
rather than on every search.

**Do:** open **URL parts**, press **dry run**. Then show the result on a real
attribute — the URL `https://Portal.Example-Cobalt.NET:8443/load/stage2` in the
follow-up event comes back with `expanded.url.domain`, `expanded.url.port` and
a lowercased `expanded.canonical`. That is a field you can search and aggregate,
produced automatically at ingestion.

**If there is time:** **reactor scripts** (Python that reacts to events —
one active, one paused) and **notebooks** (a Jupyter environment against the
live data).

!!! warning "Notebooks need the lab worker"
    Executing a notebook cell requires the `lab-worker` container. If the stack
    is partially up, show the notebook source and do not press Run.

---

## 6. Notifications — "what does the analyst wake up to?"

**Go to** the bell, or `notifications`.

**What they see:** correlation hits, a hunt whose match count jumped, a
sighting from another organisation, a new event from a partner.

**Say:** this is the output of everything in the previous five stops. The
analyst does not go looking; the platform tells them what changed.

Close here. It is the natural end of the story that started with one IP.

---

## Optional stops

Use these to answer questions, not as part of the main route.

| Ask | Go to | Point |
|---|---|---|
| "Where does data come from?" | `sources` → feeds | Three OSINT feeds are configured. **They are disabled on purpose** — see the warning below |
| "Can I get data out?" | `exports` | Scheduled exports in MISP JSON, CSV, STIX |
| "Is it auditable?" | `internals` → audit logs | Every write, with actor and IP |
| "Can analysts annotate?" | Cobalt Strike event → **Analyst Data** | Notes and opinions, with a confidence score |
| "Does it have an API?" | `/docs` on the API host | The full OpenAPI spec |
| "Can I drive it from an LLM?" | [MCP server](features/mcp/index.md) | Claude Code talking to the instance |

!!! danger "Do not fetch a feed live"
    The seeded feeds are disabled deliberately. Fetching reaches the network
    and pulls whatever is live that day — slow, unpredictable, and it buries
    your curated demo data under thousands of real indicators. If you want to
    demo ingestion, do it on a throwaway instance beforehand.

---

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Explore returns nothing | Date filter is outside the data | Set it to **Last 30 days**; re-run `seed-demo` to re-time events |
| Hunt shows a chart but no results | `hunt:results:*` cache is cold | Press **Run Now**, or re-run `seed-demo` |
| Heatmap is blank on the right | More than 90 stored runs for that hunt | Re-run `seed-demo`; see the note in the [development guide](development.md#hunt-history-and-the-90-row-limit) |
| A servo is not transforming | Servo disabled, or the attribute predates it | Servos only affect attributes indexed **after** they are enabled |
| Everything is empty | Seed never ran, or the API test suite wiped the instance | Re-run `seed-demo` |

---

## Timing

| Stop | Minutes |
|---|---|
| 1 Explore | 2 |
| 2 Event + graph | 3 |
| 3 Correlations | 2 |
| 4 Hunts | 3 |
| 5 Tech Lab | 4 |
| 6 Notifications | 1 |

Stops 1–4 are the core. If you have six minutes, do those and stop.
