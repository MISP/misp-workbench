# misp-workbench — Workshop: From Feed to Firewall

A 90-minute, hands-on workshop on getting indicators of compromise (IOCs) **into** misp-workbench, **curating** them until they are safe to act on, and **sharing** them with the security products a SOC runs: firewalls, IDS, DNS resolvers and SIEMs. It ends by closing the loop: detections come back as sightings and change what is shared next.

> **Scenario.** You are on the SOC team at *ACME Bank*. A phishing campaign is targeting the treasury team. Threat intel arrives from an unverified blocklist someone found on a paste site, and from a vendor report your analyst just read. By the end of the session you must block confirmed command-and-control (C2) infrastructure at the perimeter, sink phishing domains in DNS, give the IDS rules for the campaign and alert in the SIEM. You must **not** block Google DNS, a Tor exit your users rely on, or ACME's own VPN.

By the end you will have:

1. **Ingested** a blocklist feed and an incident report, and seen how normalisation cleans them.
2. Read an indicator's **confidence score** and set a feed's **trust**.
3. Protected your own infrastructure with an **organisation warninglist**.
4. Built a **detection profile** for perimeter blocking, with a human **approval** step.
5. Fed four controls from that one profile: a **Palo Alto EDL**, **Suricata** rules, a **DNS RPZ** zone and a live **Wazuh** manager.
6. Turned a **Wazuh alert** into a **sighting** through a webhook, and watched it change the score.
7. *(Bonus)* Retro-hunted the campaign in an **analyst notebook**, and tagged its infrastructure on arrival with a **reactor script**.

| Time | Module | Tasks |
|---|---|---|
| 0:00 | Intro: the SOC problem, the pipeline, the scenario | — |
| 0:10 | **1. Ingest** | 1a–1c, 15 min |
| 0:30 | **2. Curate** | 2a–2e, 15 min |
| 0:55 | **3. Share** | 3a–3c, 20 min |
| 1:20 | **4. Close the loop** | 4, 5 min |
| 1:25 | Wrap-up and questions | — |
| *+20 min* | ***5. Bonus: analyse and automate*** | *5a–5b* |

The slides that go with this guide follow the same order. The setup (section 0) is done **before** the session.

### How each task reads

| Part | What it tells you |
|---|---|
| **Goal** | Why the task matters to the SOC |
| **Do** | The steps, with the exact values to enter |
| **Outcome** | What you should see when it worked: check it before moving on |
| **Hints** | Shortcuts, the API way, real-life advice and what to do if it didn't work |

Tasks marked **Extra** are optional. If you fall behind, skip them: no later task depends on them.

---

## 0. Before you start

Do this **before** the session: the demo seed takes a few minutes.

### Task 0a — Start the stack and load the demo data

**Goal.** Everyone works on the same data: a Cobalt Strike campaign, a recurring Tor exit, overlapping partner events and values that are on MISP warninglists on purpose.

**Do.**

1. From the repo root:

   ```bash
   cp .env.dev.dist .env.dev          # set OPENSEARCH_INITIAL_ADMIN_PASSWORD at minimum
   cp frontend/.env.dist frontend/.env
   docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file=".env.dev" up --build
   ```

2. When the stack is up, seed the walkthrough dataset:

   ```bash
   docker compose exec api poetry run python -m app.cli seed-demo
   ```

3. Open **http://localhost:3000/login** and sign in as `admin@admin.test` / `admin`.

**Outcome.** You are logged in, and **Intel → Warninglists** lists the MISP warninglists (about 225).

**Hints.**
- The seed is additive and safe to run twice. Don't skip the warninglists (about two minutes): Lab 2 needs them.
- It loads disabled sample feeds, servers and sinks, and fetches no live feed, which would bury the curated data under thousands of unrelated values.
- The API is at **http://localhost:8080**, with its reference at http://localhost:8080/docs.
- The top bar groups pages by task. This workshop uses four menus: **Ingest** (Feeds, Alert webhooks), **Intel** (Indicators, Review queue, Warninglists), **Share** (Detection profiles, Exports, Sinks, External dynamic lists) and **Admin** (Runtime settings, Tasks). Press **Ctrl+K** (⌘K on a Mac) to jump to a page, or paste a value to search it.

### Task 0b — Create an API key

**Goal.** The labs call the API the way a SIEM would, with a key that can do no more than a SIEM needs.

**Do.**

1. Account menu (top right) → **My API keys** → **New API key**.
2. Click **SIEM integration preset**, then set **Name** to `workshop`.
3. Create it, copy the key, and keep it in your shell:

   ```bash
   export API=http://localhost:8080
   export KEY=<your 40-character key>
   ```

![SIEM preset](screenshots/workshop/00-api-key-siem-preset.png)

**Outcome.** `curl -s -H "Authorization: $KEY" "$API/events/?size=1"` answers with an event, not a `401`.

**Hints.**
- The preset grants `events:read`, `attributes:read`, `exports:read`, `sightings:create` and `warninglists:read`: all this workshop's API calls need.
- The key is **shown once**. Lost it? Create another; the old one keeps working until you delete it.
- The preset fills the name when it is empty, so click it first and name the key after.

### Task 0c — Get the lab files

**Goal.** Two realistic sources for the campaign, each with traps a careless pipeline would fall into.

**Do.** Copy `tutorial/files/` to a folder `workshop/`, or save the two files below in it.

**`c2-blocklist.txt`** is the unverified blocklist from the paste site. It is defanged, has a duplicate, and contains a value that must never be blocked:

```text
# C2 list found on a paste site, 2026-10-14. Unverified.
c2.example-cobalt[.]net
beacon-relay.example-cobalt[.]net
stage.example-cobalt.net
hxxp://update-service[.]test/agent/setup.exe
185.220.101[.]42
185.220.101.42
8.8.8.8
```

**`vendor-report.txt`** holds the IOCs from the vendor report your analyst read. Like most reports, it mixes the attacker's infrastructure with the victim's (`10.20.30.40` is the treasury workstation):

```text
c2.example-cobalt[.]net
invoice-portal[.]test
hxxps://invoice-portal[.]test/download/48812
billing@invoice-portal[.]test
hxxp://update-service[.]test/agent/setup.exe
9f2b8c1d4e5a67380b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f708192a3b4c5d6
185.220.101[.]42
10.20.30.40
```

**Outcome.** `workshop/c2-blocklist.txt` and `workshop/vendor-report.txt` exist.

### Task 0d — A Wazuh manager *(for Labs 3c and 4)*

**Goal.** In Lab 3c a live SIEM pulls the curated list and alerts on it; in Lab 4 it reports its hits back.

**Do.** Have a **Wazuh manager** (4.x) ready, with a root shell on it, that can reach the misp-workbench API on port 8080. A single-node install, or Wazuh's Docker deployment, is enough.

**Outcome.** From the manager, `curl -s http://<workbench-host>:8080/docs` answers.

**Hints.** No Wazuh? Follow Labs 3c and 4 on the projector, and use the `curl` in Task 4's hints to play Wazuh's part.

---

## 1. Ingest

misp-workbench takes intelligence in three main ways:

| Source | SOC use case | Where |
|---|---|---|
| **Feeds** | Daily OSINT blocklists (abuse.ch, CIRCL OSINT) | **Ingest → Feeds**: MISP, CSV, JSON or freetext, fetched from a URL or uploaded |
| **MISP servers** | Curated events from your ISAC or a partner CERT | **Ingest → MISP servers**, with pull rules (see [tutorial.md](tutorial.md#1-connect-a-remote-misp-server)) |
| **Batch import** | The report an analyst just read | An event → **Import Data** |

Whatever the path, every value is **normalised** as it is written. Defanged values are refanged (`hxxps://evil[.]com` → `https://evil.com`), hostnames and hashes are lower-cased, and IPs are made canonical. The value as received is kept, and problems are **flagged, never dropped**.

### Task 1a — Upload the blocklist as an offline feed

**Goal.** Bring the paste-site list in as a feed, so its values are tracked as coming from that one, unverified source.

**Do.**

1. **Ingest → Feeds** → **+ Add Feed**, and choose the **Freetext** card: the list has one indicator per line.
2. In **Feed Settings**:

   | Field | Value |
   |---|---|
   | **Name** | `Paste-site C2 list` |
   | **Provider** | `pastebin (unverified)` |
   | **Input source** | **Upload file** |
   | **File** | `workshop/c2-blocklist.txt` (click the dropzone, or drag the file in) |
   | **Fixed Event** | on |

3. In **Freetext Settings**, set **Attribute type detection** to automatic.
4. Click **Preview** and check the parsed lines, then click **Add Feed**.

![Freetext feed](screenshots/workshop/01-freetext-feed-upload.png)

**Outcome.**
- The preview reads `c2.example-cobalt[.]net` as a **domain** and `hxxp://update-service[.]test/…` as a **url**, and the comment line is gone.
- A few seconds after **Add Feed**, **Hunt → Explore** finds `value:"beacon-relay.example-cobalt.net"`, in the feed's event, with the provider as its source.

**Hints.**
- **Provider** becomes the indicators' source name, so make it say what the source is.
- **Fixed Event** puts every ingestion of this feed in one event, instead of one per fetch.
- Choose **Fixed type** instead of automatic when a file holds one kind of value only, say a list of IPs.
- The ingestion runs in the background: watch it under **Admin → Tasks**.
- **Uploads are one-shot.** An uploaded feed never runs on a schedule. When the paste site posts a new version: the feed's edit page → **Replace** next to the file name → **Save**, then **Fetch** (the download icon) in the feed list.
- **On a live instance** the same feed would use **Network (fetch from URL)** with a real source (abuse.ch's URLhaus, say) and an **Update interval** of **Daily**. We upload so the lab works offline.
- Every format accepts uploads: freetext (`.txt`, `.csv`), CSV (`.csv`, `.txt`), JSON (`.json`, `.ndjson`), and MISP feeds as a `.zip` or `.tar.gz` with `manifest.json` at the root, up to 2 GB.
- **The API way** takes two calls and a key with `feeds:create` (the SIEM preset doesn't grant it):

  ```bash
  export FEEDS_KEY=<a key with feeds:create>
  curl -s -X POST "$API/feeds/upload" -H "Authorization: $FEEDS_KEY" \
    -F file=@workshop/c2-blocklist.txt -F source_format=freetext
  # → {"key": "feed-uploads/<uuid>", "filename": "c2-blocklist.txt", ...}
  ```

  Then `POST /feeds/` with the returned `key` as `url` and `"input_source": "local"`; see [feeds/local-files.md](../docs/features/feeds/local-files.md).

### Task 1b — Import the vendor report

**Goal.** Record the incident as an event of your own, with the report's IOCs as its attributes: your own evidence counts for more than an unverified feed.

**Do.**

1. **+ New Event** (top right): **info** `Phishing: ACME treasury`, threat level **High**, **Create**.
2. On the event, click **Import Data** (the import icon in its toolbar) and paste the contents of `vendor-report.txt`.
3. Check the detected types, then click **Import**.

![Batch import](screenshots/workshop/02-batch-import.png)

**Outcome.** The summary reads **8 lines · 8 valid**, with badges for domains, URLs, an email, a sha256 and IPs, and the import toast says *Imported 8 out of 8 attributes*.

**Hints.**
- Defanged lines are recognised as what they refang to, but sent as pasted: the platform refangs them and keeps the original, which Task 1c shows.
- Each line has **type** and **category** dropdowns to correct a guess, and **Override detected type & category** sets one for every line.

### Task 1c — See what normalisation did

**Goal.** Trust the data before acting on it: know what was rewritten, what was flagged, and what overlaps across sources.

**Do.**

1. Open the event's **Attributes** tab, and hover a **normalised** badge.
2. In **Hunt → Explore**, run:

   | Query | Finds |
   |---|---|
   | `value:"185.220.101.42"` | One value, from the feed **and** the event, despite the defanging and the duplicate |
   | `validation_issues:*` | `10.20.30.40`, flagged `private-ip`: the victim's workstation |
   | `_exists_:warninglist_hits` | `8.8.8.8` and `185.220.101.42`, which sit on MISP warninglists |

3. In **Intel → Warninglists → Check values**, check `185.220.101.42`.

![Normalised attributes](screenshots/workshop/03-normalised-attributes.png)

**Outcome.** You can answer:
- What did `hxxp://update-service[.]test/agent/setup.exe` become? (`http://update-service.test/agent/setup.exe`; the badge shows the original.)
- Why is `10.20.30.40` flagged and not deleted? (It is evidence for the investigation, but it must never reach a block list. Flagging lets curation keep it out.)
- Which warninglist is `185.220.101.42` on?

**Hints.** Normalisation settings are under **Admin → Runtime settings → normalisation**.

### Extra 1d — A CSV feed with a type column

**Goal.** Ingest a source that names its own types, in its own vocabulary.

**Do.** Upload a **CSV** feed with a header like `indicator,type,comment`. Set **Type strategy** to **Column**, and map the file's type names onto MISP's.

**Outcome.** The preview shows each row with the MISP type you mapped it to.

**Hints.** Every optional property (`comment`, `tags`, `to_ids`, `first_seen`…) can be fixed or read from a column; see [feeds/csv.md](../docs/features/feeds/csv.md).

### Extra 1e — Strip tracking parameters

**Goal.** Stop `utm_*` parameters from turning one phishing URL into a dozen different values.

**Do.**

1. **Admin → Runtime settings → normalisation**: switch on **Strip tracking parameters**, and save.
2. On your event, **Import Data** and paste `hxxps://invoice-portal[.]test/login?utm_source=mail&id=7`.

**Outcome.** The attribute is stored as `https://invoice-portal.test/login?id=7`, and its **normalised** badge shows the URL as pasted.

**Hints.** The **Tracking parameters** list takes one name per line; a trailing `*` matches a prefix, like `utm_*`. It applies to values written from then on; **Apply to existing** rewrites those already stored.

---

## 2. Curate

misp-workbench keeps one **indicator** per type and value, merging every attribute that holds it: its sources, first and last seen, the strictest TLP, sightings and warninglist hits. Each indicator gets a **confidence score** from 0 to 100, built from parts you can read:

| Part | Default |
|---|---|
| **Base**, by source | local 70 · MISP server 60 · feed 50 |
| **Corroboration** | +5 per further independent source, up to +15 |
| **Sightings** | +5 / +10 / +15 at 1 / 3 / 7+ |
| **False positives** | −20 each, down to −60 |
| **Warninglist** | −50 |
| **Validation issue** | −40 |
| **Decay** | the score halves every 30 days for IPs and URLs, 90 for domains, never for hashes, counted from last seen |

Every number is editable in **Admin → Runtime settings → scoring**. Below 30 an indicator counts as decayed.

### How a score is computed, and when it changes

The score belongs to the **indicator**, never to an attribute: attributes are stored as they arrived, and an event's attribute list only shows its indicator's score. It is computed in this order:

1. **Base**: of all the sources reporting the value, the one with the highest *base + score modifier* wins. Its base and its modifier are added.
2. **Organisation trust**: the most favourable modifier among the organisations that reported it.
3. **Corroboration**: +5 per further source, up to +15.
4. **Decay**: what the first three steps add up to halves every half-life of the value's type, counted from **last seen**. A positive sighting moves *last seen*, so values still being hit don't decay.
5. **Sightings** and **false positives**, then the **warninglist** and **validation** penalties.
6. Clamped to 0–100, then the **cap**: it holds only when **every** source reporting the value is capped. A capped feed can't hold down a value another, uncapped source reports too.
7. An **expiration** sighting newer than any positive one caps the score at 10.

**One modifier, two values.** Here is what Task 2b's modifier of −10 and cap of 60 on the paste-site feed do to two values the lab ingests:

| | `beacon-relay.example-cobalt.net` | `c2.example-cobalt.net` |
|---|---|---|
| Sources | the feed only | the feed and your event (local) |
| Best source | the feed: 50 − 10 = 40 | your event: 70 + 0 beats the feed's 40 |
| Cap of 60 | applies, but 40 is under it | doesn't apply: your event isn't capped |
| Score | 50 → **40** | **70** before and after |

A source's trust changes the score of a value only when that source is its best one. If it caps the value, it must also be the only source.

**What recomputes a score, and when.**

| Trigger | What is recomputed | When |
|---|---|---|
| An attribute is created, changed or deleted; a sighting arrives; an event's tags, organisation or source change | Those values only | The **sync**, every **15 seconds** |
| The clock | Every indicator, decay included | The **rebuild**, every **hour** |
| A feed's, MISP server's or organisation's **score modifier** or **cap** is saved; the **scoring** settings are saved | Every indicator | A **full rebuild**, queued at once |

Each run reads the scoring settings and every source's trust when it **starts**. An attribute ingested after you change a modifier is scored with the new value straight away, at the next sync.

**After you change a source's modifier, step by step:**

1. **Save** queues a full rebuild of the indicators. Nothing is rewritten in the request itself, and **no attribute changes**. Several saves in a row are merged into one rebuild, since it reads the latest trust when it starts.
2. The rebuild recomputes every indicator with the new trust. On the lab's data that takes seconds; on an instance with hundreds of thousands of indicators, minutes. If a sync or another rebuild is running, it waits for it, retrying every 30 seconds.
3. It **stores every score that moved**, however little: a modifier of −3, or a cap of 60 on a value at 62, both take effect.
4. What reads the stored score sees it as soon as it is written: **Intel → Indicators**, the **review queue**, a profile's count and **Changes** page, `POST /lookup`, and the streaming exports (Task 3c's Wazuh pull).
5. Outputs that build ahead pick it up on their own schedule: an **external dynamic list** at its next rebuild (or **Rebuild now**), a **scheduled export** at its next run, and a sink kept in step with a profile within **5 minutes**.

A save made **while** that rebuild runs queues another one after it, so no change is applied with trust read too early.

**Why some scores lag behind the clock.** The hourly rebuild, which applies decay, stores a score only when it moved by **5 points or more** (the scoring setting `refresh_step`) or crossed the decayed threshold of 30. Decay alone doesn't rewrite every indicator every hour, so incremental feeds carry only real changes. A stored score can therefore trail its exact, decayed value by up to 4 points. Trust and scoring changes aren't held back this way: their rebuild writes every move.

**Hints.**
- An indicator's breakdown shows every step that applied, including **source_trust**, **cap** and **decay**. `scored_at` in its API response says when it was last computed.
- `GET /indicators/status` shows when the last rebuild finished (`built_at`) and the last sync ran (`synced_at`).
- To apply a change at once, an admin can run a rebuild by hand. It waits up to ten minutes for a running sync or rebuild:

  ```bash
  docker compose exec api poetry run python -m app.cli rebuild-indicators
  ```

### Task 2a — Read a score

**Goal.** Know why a value is trusted before deciding to block it.

**Do.**

1. **Intel → Indicators**, search `value:*cobalt*`.
2. Click **c2.example-cobalt.net** and read its score breakdown.
3. Compare it with **beacon-relay.example-cobalt.net**.

![Indicator detail](screenshots/workshop/04-indicator-detail.png)

**Outcome.** `c2.example-cobalt.net` scores **70**: base 70 (your own event), +5 because the paste-site feed reports it too, +15 for its sightings and −20 for one false positive in the seed data. `beacon-relay`, which only the feed reported, scores **50**.

**Hints.**
- Indicators sync every 15 seconds. A value you just imported may need a moment and a new search.
- **IDS only** is on by default; switch it off to see values not flagged for IDS.

### Task 2b — Trust the feed for what it is

**Goal.** An unverified source shouldn't count as much as a vetted one, and should never be enough on its own to block something.

**Do.** **Ingest → Feeds** → edit **Paste-site C2 list** → under **Indicator scoring**:

| Field | Value | Effect |
|---|---|---|
| **Score modifier** | `-10` | Its values start at 40 instead of 50 |
| **Score cap** | `60` | A value only this feed reports never scores above 60 |

Then **Save**.

**Outcome.** Within a minute or so, **beacon-relay** drops to **40**, while **c2.example-cobalt.net** stays at 70, because your own event reports it too.

![Source quality](screenshots/workshop/05-source-quality.png)

**Hints.**
- **Intel → Source quality** shows, per feed and server, how many of its indicators were ever hit by a sighting, how many were reported false positives, and how many decayed. Set trust from that evidence, not from reputation.
- A trust change is applied by a full rebuild, queued when you save. If a score didn't move, the source may not be the value's best one; see [How a score is computed, and when it changes](#how-a-score-is-computed-and-when-it-changes).

### Task 2c — Protect your own infrastructure

**Goal.** MISP warninglists cover the public internet: resolvers, top sites, cloud and CDN ranges, Tor exits. Your own VPN, mail relay and domains need a list of your own, so no feed can ever get them blocked.

**Do.**

1. **Intel → Warninglists** → **Your organisation's lists** → **+ New list**:

   | Field | Value |
   |---|---|
   | **Name** | `ACME own infrastructure` |
   | **Description** | `Egress, VPN and corporate domains. Never block.` |
   | **Entries** | **Manual** |

2. Open the list and paste into **Import**, then click **Import**:

   ```text
   203.0.113.0/24     # VPN egress
   198.51.100.10      # mail relay
   *.acme-bank.test   # corporate domains
   ```

![Organisation list](screenshots/workshop/06-organisation-warninglist.png)

**Outcome.** The list shows **3 entries**: an address range, an exact value, and a domain with its subdomains.

**Hints.**
- One entry per line, `entry # comment`. A CIDR is a range, `*.domain` covers a domain and its subdomains, `/regex/` is a regex, anything else an exact value.
- An organisation list is **private**: it does nothing until a profile attaches it, which you do in Task 2d.

### Extra 2c+ — A list synced from a URL: Cloudflare's ranges

**Goal.** Keep a list current without maintaining it by hand: here, Cloudflare's published IP ranges, so a phishing kit hosted behind Cloudflare never gets half the internet's sites blocked.

**Do.**

1. **Admin → Runtime settings → warninglists**: in its JSON, set `"source_hosts": ["www.cloudflare.com"]`, and **Save**. *(An admin's step: which hosts a list may sync from is the operator's call.)*
2. **Intel → Warninglists** → **+ New list**:

   | Field | Value |
   |---|---|
   | **Name** | `Cloudflare IPv4` |
   | **Entries** | **Remote** |
   | **URL** | `https://www.cloudflare.com/ips-v4/` |

3. Open the list, and attach it to your profile in Task 2d (**Organisation warninglists**).

**Outcome.** The list syncs at once and fills with Cloudflare's ranges, one entry per CIDR. Its page shows when it last synced.

**Hints.**
- A remote list re-syncs **daily**, and each sync replaces the entries the previous one brought. **Sync now** on its page syncs on demand, and shows the error if the source can't be read.
- The source must be a **plain list**, one entry per line, like `https://www.cloudflare.com/ips-v4/` (and `https://www.cloudflare.com/ips-v6/` for IPv6). A JSON API such as `https://api.cloudflare.com/client/v4/ips` can't be read by a list sync.
- Don't ingest such a source as a **feed** instead: a feed turns every value into an IOC, the opposite of an allowlist.
- Redirects aren't followed, so give the final URL. Inside your network, a CMDB export works the same way once its host is allowed.

### Task 2d — A detection profile for perimeter blocking

**Goal.** Say once what is safe enough to block at the perimeter, so every output (firewall lists, IDS rules, DNS zones, SIEM lists) sends the same values.

**Do.** **Share → Detection profiles** → **New**, name it `Perimeter block`, set these rules and **Create profile**:

| Rule | Value | Why |
|---|---|---|
| **Types** | `ip-src`, `ip-dst`, `domain`, `hostname`, `url` | What a firewall can act on |
| **Only flagged for IDS** | on | Analysts marked them as detection-worthy |
| **Minimum score** | `60` | Corroborated or vetted values only |
| **Last seen within** | `30` days | No stale infrastructure |
| **TLP ceiling** | `amber` | Nothing `tlp:red` leaves the SOC |
| **Leave out warninglisted** | on | Google DNS, Tor exits, CDNs |
| **Leave out validation issues** | on | No private or malformed values |
| **Organisation warninglists** | `ACME own infrastructure` | Never your own ranges |
| **Require approval** | on | A human signs off each value |

Then open the profile's **Changes** page.

![Profile editor](screenshots/workshop/07-detection-profile-editor.png)

**Outcome.**
- While you set the rules, the **live match count** drops, and `8.8.8.8`, `185.220.101.42`, `10.20.30.40` and `beacon-relay…` fall out of the samples.
- The **Changes** page lists what the profile's next run would add, by type, source and reason, with **risk flags**.

![Change preview](screenshots/workshop/08-profile-changes.png)

**Hints.**
- The count shows **0** once **Require approval** is on. That is expected: the profile then selects only approved values, and none are yet. They wait in the review queue (Task 2e). The queue only reads **saved** profiles, so create the profile first.
- Two profiles are built in: **SIEM alerting** and **Firewall block list**. Start from those for your own SOC.
- **Real life:** for a blocking profile, turn on **Hold large or risky changes** too. A partner who suddenly shares 40,000 values, or a cloud range that slipped into a feed, then waits for approval instead of landing on the firewall at 3 a.m.

### Task 2e — Approve what goes out

**Goal.** Make a human the last check before anything is blocked.

**Do.**

1. **Intel → Review queue**, and pick **Perimeter block** in the profile filter.
2. Tick `c2.example-cobalt.net`, `invoice-portal.test` and `http://update-service.test/agent/setup.exe`, and click **Approve**.
3. Tick `https://invoice-portal.test/download/48812`, click **Reject…**, give a reason, and tick **Also add to the *Rejected in review* warninglist**.
4. Snooze one more value for 7 days (**snooze 7d**).

![Review queue](screenshots/workshop/09-review-queue.png)

**Outcome.**
- The profile now holds only what you approved, and `8.8.8.8` is not among it.
- The rejected URL is on the **Rejected in review** list (**Intel → Warninglists**), and the snoozed value is under the queue's **snoozed** tab.

![Reject](screenshots/workshop/10-review-reject.png)

**Hints.**
- Click a row for its full context: score breakdown, sources, sightings and warninglist hits.
- Keyboard: `j`/`k` move, `x` ticks, `a` approves, `r` rejects, `s` snoozes, `?` shows them all. With nothing ticked, an action applies to the highlighted row.
- Adding a rejection to the warninglist makes it apply everywhere, not only to this profile.
- A snoozed value comes back to pending when its snooze ends.
- **Real life:** reviewing every value doesn't scale. Pair the approval rule with an **auto-approve** profile for sources you trust. One is built in, **Auto-approve: trusted sources** (IDS, score ≥ 70, from a feed or server with a score modifier of at least +10, clean), so analysts only review the long tail.

### Extra 2f — Let block lists shrink

**Goal.** Drop what nobody has seen for a while, so block lists don't only ever grow.

**Do.** Edit **Perimeter block** and turn on **Expire what sensors don't hit** (hit-rate expiry).

**Outcome.** The profile's **Changes** page lists what would expire, with the reason.

**Hints.** A value leaves after a window with no positive sighting and no new report. It needs sensors that report their hits, which Task 4 sets up. Without them, everything older than the window expires.

### Extra 2g — Tune the decay

**Goal.** See how much a half-life decides what is still blockable.

**Do.** **Admin → Runtime settings → scoring**: change the domain half-life, and save.

**Outcome.** Saving rescores every indicator; **Intel → Indicators** shows the domains' scores move.

---

## 3. Share

Every control can take the **Perimeter block** profile, so the firewall, the resolver and the IDS agree on what is malicious:

| Control | Gets | Where |
|---|---|---|
| **Firewall** | A list it fetches every few minutes | **Share → External dynamic lists** |
| **IDS** | Suricata rules or a Zeek Intel file | **Share → Exports**, format `suricata` or `zeek` |
| **DNS resolver** | A Response Policy Zone | **Share → Exports**, format `rpz` |
| **SIEM** | An IOC list its rules look up, pushed events, or a feed to poll | Wazuh CDB lists (format `cdb`); **Share → Sinks** (Splunk HEC, GELF, syslog/CEF, webhook); incremental feeds |
| **EDR, cloud SIEM** | Vendor indicators via API | Sinks: Sentinel, Defender, Elastic *(beta)* |
| **SOAR, scripts** | "Is this value known?" | `POST /lookup`, restSearch, streaming exports |

Safety nets are built in: firewall lists and IDS/DNS formats never write networks broader than a /16, special-purpose addresses, or public suffixes like `co.uk`.

### Task 3a — A Palo Alto external dynamic list

**Goal.** Give the firewall a list of the approved C2 domains that it fetches by itself, every few minutes.

**Do.**

1. **Share → External dynamic lists** → **+ New EDL**:

   | Field | Value |
   |---|---|
   | **Name** | `Perimeter block: domains` |
   | **Detection profile** | `Perimeter block` |
   | **Vendor** | Palo Alto PAN-OS |
   | **Holds** | Domains |
   | **Rebuilt every (minutes)** | `15` |

2. On the list's page, under **Tokens**, create one named `fw-edge-01`, and copy its URL.
3. Fetch it as the firewall would:

   ```bash
   curl -s http://localhost:8080/edl/<token>
   ```

**Outcome.** The **As served** preview, and the `curl`, list the domains you approved in Task 2e, one per line, and nothing you didn't.

**Hints.**
- Leave **Subdomains too** off: it is greyed out for PAN-OS, which covers subdomains with the list's own setting instead (below).
- Empty list? It is rebuilt on its schedule: click **Rebuild now**.
- The token URL is **shown once**. Each firewall gets its own token, so revoking one doesn't break the others. In production, set **Only from** to the firewall's management IP. Every fetch is audited (`edl.fetched`).
- **On a real PAN-OS:** **Objects → External Dynamic Lists → Add**, type *Domain List*, source the URL, tick **Automatically expand to include subdomains**, repeat *Five Minute*, **Test Source URL**, then use the list in a security policy and commit.

### Task 3b — Suricata rules and a DNS RPZ zone

**Goal.** Give the IDS rules for the campaign, and the DNS resolver a zone that sinks its domains, from the same approved values.

**Do.** **Share → Exports** → **+ New Export**, twice:

| Field | Suricata export | RPZ export |
|---|---|---|
| **Name** | `ids-perimeter-block` | `dns-firewall` |
| **Detection profile** | `Perimeter block` | `Perimeter block` |
| **Lucene Query** | `*` | `*` |
| **Format** | **Suricata rules** | **DNS RPZ zone** |
| **Format options** | **Rule action**: `alert` | **Answer**: *Walled garden (CNAME)* → `blocked.acme-bank.test` |
| **Run on a schedule** | **Hourly** | **Hourly** |

When both show **completed**, **Download** them.

![New export](screenshots/workshop/11-new-export-suricata.png)

**Outcome.**
- **Suricata:** each approved domain gets DNS, TLS SNI and HTTP Host rules covering its subdomains, each with a **stable SID** and metadata carrying the indicator's uuid, score and source.
- **RPZ:** each domain becomes `name` and `*.name` records answered with your walled garden.

**Hints.**
- The SID is derived from what a rule matches, so suppressions keep working across rebuilds. The zone's serial increases with every run.
- The `https://` URL gets no Suricata rule: its path is encrypted where a sensor can't see it.
- Picking a detection profile fills the query with `*`: the profile does the selecting.
- Load them as the engines would, if you have the tools:

  ```bash
  suricata -T -c /etc/suricata/suricata.yaml -S "$PWD/ids-perimeter-block.rules"
  docker run --rm -v "$PWD":/d:ro --entrypoint named-checkzone \
    internetsystemsconsortium/bind9:9.20 rpz.local /d/dns-firewall.rpz
  ```

- The same output, without storing a file, straight from the API:

  ```bash
  curl -s -H "Authorization: $KEY" "$API/indicators/export?format=suricata&profile=Perimeter%20block"
  ```

### Task 3c — Wazuh: match your logs against the profile

**Goal.** Make the SIEM alert when a log mentions an approved campaign value, with no conversion script in between.

Wazuh matches log fields against IOC lists in its own format, **CDB lists** (`key:value`, one per line). misp-workbench writes the **Perimeter block** profile in that format (`cdb`), so the manager pulls the list straight from the API.

**Do.** On the Wazuh manager, as root:

1. Pull the profile as a CDB list:

   ```bash
   export WB_API=http://<workbench-host>:8080      # as seen from the Wazuh manager
   export KEY=<your SIEM-preset API key>
   curl -fsS -H "Authorization: $KEY" \
     "$WB_API/indicators/export?format=cdb&profile=Perimeter%20block" \
     -o /var/ossec/etc/lists/misp-perimeter
   chown wazuh:wazuh /var/ossec/etc/lists/misp-perimeter
   ```

2. Load the list: in `/var/ossec/etc/ossec.conf`, add it to the `<ruleset>` section, next to the lists already there:

   ```xml
   <ruleset>
     <!-- ... the existing <decoder_dir>, <rule_dir> and <list> entries ... -->
     <list>etc/lists/misp-perimeter</list>
   </ruleset>
   ```

3. Add a rule that looks values up in it, in `/var/ossec/etc/rules/local_rules.xml`:

   ```xml
   <group name="misp,threat_intel,">
     <rule id="100900" level="12">
       <decoded_as>json</decoded_as>
       <list field="url" lookup="match_key">etc/lists/misp-perimeter</list>
       <description>misp-workbench: $(url) is on the Perimeter block profile</description>
     </rule>
   </group>
   ```

4. Restart the manager: `systemctl restart wazuh-manager`.
5. Run `/var/ossec/bin/wazuh-logtest` and paste these two proxy-log lines, one at a time:

   ```json
   {"lab": "proxy", "srcip": "10.20.30.40", "url": "c2.example-cobalt.net"}
   {"lab": "proxy", "srcip": "10.20.30.41", "url": "dns.google"}
   ```

**Outcome.**
- `cat /var/ossec/etc/lists/misp-perimeter` shows one approved value per line, with its type as the CDB value:

  ```text
  c2.example-cobalt.net:domain
  "http://update-service.test/agent/setup.exe":url
  invoice-portal.test:domain
  ```

  `8.8.8.8`, `185.220.101.42`, `10.20.30.40` and anything you didn't approve are not there.
- The first log line ends in **rule 100900, level 12**: `misp-workbench: c2.example-cobalt.net is on the Perimeter block profile`. The second matches no rule of yours.

**Hints.**
- From the manager, `localhost` is not misp-workbench: use the address of the machine running the stack.
- Keys containing `:` (URLs, IPv6) are quoted, as Wazuh expects.
- The rule fires when a JSON log's `url` field is a key of the list. In production, write one rule per log source and field: `data.dns.question.name` for DNS logs, `data.url` for a proxy, `srcip` / `dstip` with `lookup="address_match_key"` for firewall logs.
- Rule 100900 doesn't fire? The manager wasn't restarted after the list or rule changed, or the log's field isn't named `url`. Empty list? Nothing is approved yet (Task 2e), or the manager reached the wrong host: `curl` from the manager, not your laptop.
- **Keep it current** with a root crontab entry. Downloading to a temporary file first means a failed pull never leaves Wazuh with an empty list:

  ```cron
  */15 * * * * curl -fsS -H "Authorization: <key>" "<workbench>/indicators/export?format=cdb&profile=Perimeter%20block" -o /var/ossec/etc/lists/misp-perimeter.new && mv /var/ossec/etc/lists/misp-perimeter.new /var/ossec/etc/lists/misp-perimeter && systemctl restart wazuh-manager
  ```

- **Real life:** a scheduled **Wazuh CDB list** export in **Share → Exports** works too (`GET /exports/{id}/download`, answered `304` when nothing changed). Wazuh can also be **pushed to**: a **Syslog / CEF** sink sends each published event's indicators to the manager's syslog port. Splunk has an HEC sink; Microsoft Sentinel, Defender for Endpoint and Elastic Security have vendor API sinks (beta).

### Extra 3d — See a real Wazuh alert *(needed for Task 4)*

**Goal.** Raise a real alert, not a `wazuh-logtest` dry run: Task 4 needs one to report back.

**Do.**

1. Make an agent (or the manager itself) read a JSON log file: add to its `ossec.conf`, then restart it:

   ```xml
   <localfile>
     <log_format>json</log_format>
     <location>/var/log/lab-proxy.json</location>
   </localfile>
   ```

2. Append the first log line of Task 3c to `/var/log/lab-proxy.json`.

**Outcome.** The alert shows in the Wazuh dashboard under **Threat Hunting**: filter on `rule.id:100900`.

### Extra 3e — "Is this value known?"

**Goal.** Answer a SOAR playbook's triage question in one call: are any of these values known, and how confident are we?

**Do.**

```bash
curl -s -X POST "$API/lookup" -H "Authorization: $KEY" -H "Content-Type: application/json" \
  -d '{"values": ["c2.example-cobalt.net", "8.8.8.8", "10.20.30.40", "unknown.example"], "include_indicators": true}'
```

**Outcome.** `c2.example-cobalt.net` and `10.20.30.40` come back, the latter with its `private-ip` validation issue. `8.8.8.8` is left out because it is warninglisted, and the last value is unknown.

**Hints.** Add `"profile": "Perimeter block"` to ask "would we block it?" instead: then only the approved C2 domain comes back.

---

## 4. Close the loop

Sightings are the feedback loop. A positive sighting raises a value's score and keeps it alive under hit-rate expiry; a false positive lowers it, and can drop it out of a profile. **Alert webhooks** take SIEM and SOAR alerts in their own shape, so no custom code is needed on the sender's side.

### Task 4 — Wazuh reports its hits back

**Goal.** Turn the SIEM's detection into a sighting, so what is actually being hit gains confidence and stays on the block lists.

**Do.**

1. **Ingest → Alert webhooks** → **+ New webhook**, then **Create**:

   | Field | Value |
   |---|---|
   | **Name** | `Wazuh: perimeter hits` |
   | **Sender** | **Wazuh integration** |
   | **Only values an attribute holds** | on |
   | **Only from** | the Wazuh manager's address |

2. Copy the URL from the green box.
3. On the Wazuh manager, add to `/var/ossec/etc/ossec.conf`, then `systemctl restart wazuh-manager`:

   ```xml
   <integration>
     <name>shuffle</name>
     <hook_url>http://<workbench-host>:8080/webhooks/alerts/awh_…</hook_url>
     <rule_id>100900</rule_id>
     <alert_format>json</alert_format>
   </integration>
   ```

4. Simulate the treasury workstation reaching the C2 through the proxy (needs the log file of Extra 3d):

   ```bash
   echo '{"lab": "proxy", "srcip": "10.20.30.40", "url": "c2.example-cobalt.net"}' >> /var/log/lab-proxy.json
   ```

**Outcome.**
- **Ingest → Alert webhooks → Wazuh: perimeter hits** shows **1 request**, when it arrived and where from.
- **Last received** → **Try it** → **Read it**: the mapping reads `c2.example-cobalt.net` and `10.20.30.40` from the alert's `data` fields, with the rule's description as source.
- **Intel → Indicators → c2.example-cobalt.net** has a new positive sighting, from *misp-workbench: c2.example-cobalt.net is on the Perimeter block profile*, and a higher score.

**Hints.**
- The URL is **shown once**, and the token in it is the only credential: Wazuh's integrations send no `Authorization` header. A request from any address not in **Only from** gets a `403`.
- `shuffle` is an integration Wazuh ships: it posts each matching alert as JSON to any URL, wrapped in an `all_fields` object, which the preset reads wrapped or not. `<rule_id>` sends only rule 100900's alerts; use `<level>` to send everything above a severity.
- `wazuh-logtest` raises no real alert: append the line to the monitored log file.
- Nothing arrived? `grep -i integrat /var/ossec/logs/ossec.log` on the manager, and check it can reach the misp-workbench host. The webhook's page shows the last request it refused, and why. A `404` means the URL was copied wrong, or **New URL** replaced it.
- The webhook answers only how many records it read (`{"records": 1}`), never which values are known, so whoever holds the token learns nothing about your intel.
- **No Wazuh in the room?** Post the same alert yourself, in the shape Wazuh's integration sends:

  ```bash
  export WEBHOOK='http://localhost:8080/webhooks/alerts/awh_…'
  curl -s -XPOST "$WEBHOOK" -H 'Content-Type: application/json' -d '{
    "rule_id": "100900",
    "all_fields": {
      "timestamp": "'"$(date -u +%Y-%m-%dT%H:%M:%S.000+0000)"'",
      "rule": {"id": "100900", "level": 12,
               "description": "misp-workbench: c2.example-cobalt.net is on the Perimeter block profile"},
      "agent": {"id": "001", "name": "proxy-01"},
      "data": {"srcip": "10.20.30.40", "url": "c2.example-cobalt.net"}
    }
  }'
  # → {"records":1}
  ```

- **Discuss:** the treasury workstation `10.20.30.40` got a sighting too, because the vendor report put it in an attribute. It is evidence that the host is compromised, not an indicator to block, and the profile keeps it out of every control anyway (validation issue). With **Only values an attribute holds** off, every internal address in every alert would become a sighting.

### Extra 4b — Report a false positive

**Goal.** Feed an analyst's verdict back: Wazuh reports hits, not verdicts.

**Do.** Report the value as a false positive through the sightings API, as a SOAR would when an analyst closes the alert as benign:

```bash
curl -s -X POST "$API/sightings/" -H "Authorization: $KEY" -H "Content-Type: application/json" \
  -d '[{"value": "c2.example-cobalt.net", "type": "false-positive", "observer": {"source": "soc-triage"}}]'
```

**Outcome.** The indicator loses 20 points. If it falls below 60, the **Perimeter block** profile's **Changes** page shows it as a removal with reason `score`, and the EDL, rules and zone drop it on their next build.

**Hints.** A Microsoft Sentinel incident classified *False positive* reports one through its webhook preset, with no API call.

---

## 5. Bonus — Analyse and automate (20 minutes)

Run this module when the room has time left, or as a follow-up session. It reuses the event and values from Labs 1 and 2.

| Tool | Runs | SOC use |
|---|---|---|
| **Notebooks** | When you run a cell | Ad-hoc analysis you can rerun and share: retro-hunts, campaign reports, source reviews |
| **Reactor scripts** | When something happens: an event is published, an attribute is created, a sighting arrives… | Small automations that would otherwise be a cron job or a tired analyst: tagging, enrichment, forwarding |

Notebooks are the *pull* side (you ask) and reactor scripts the *push* side (the platform reacts). Notebooks only read, apart from enrichment and sending to a sink; reactor scripts write within a quota. Everything both do is audited under your identity.

### Task 5a — Notebook: has this campaign hit us before?

**Goal.** Before anyone writes "new campaign" in the incident report, find where the vendor report's values already appear: partner events, old feeds, past incidents.

**Do.**

1. **Tech lab → Notebooks** → in **Personal**, click **+** (New notebook), name it `Retro-hunt: ACME treasury`, **Create**.
2. For each cell below: **Add → Code**, paste it, **Shift+Enter** to run it.

**Cell 1: where does each campaign value appear?**

```python
campaign = [
    "c2.example-cobalt.net",
    "invoice-portal.test",
    "http://update-service.test/agent/setup.exe",
    "9f2b8c1d4e5a67380b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f708192a3b4c5d6",
    "185.220.101.42",
]

rows = []
for value in campaign:
    for attr in mwlab.search_attributes(value=value, size=200):
        if attr.get("value") != value:
            continue  # the search is full-text; keep exact hits only
        event = mwlab.get_event(attr["event_uuid"]) or {}
        rows.append({
            "value": value,
            "type": attr.get("type"),
            "event": event.get("info"),
            "event_uuid": attr["event_uuid"],
            "date": event.get("date"),
            "warninglisted": bool(attr.get("warninglist_hits")),
        })

hits = mwlab.dataframe(rows)
hits.sort_values(["value", "date"])
```

![Notebooks workspace](screenshots/workshop/12-notebook-retro-hunt.png)

**Cell 2: which values are not new?**

```python
hits.groupby("value")["event_uuid"].nunique().sort_values(ascending=False)
```

**Cell 3: which events share infrastructure with this one?**

```python
shared = hits.groupby(["event_uuid", "event"])["value"].nunique()
shared[shared >= 2].sort_values(ascending=False)
```

**Cell 4: the story as a timeline.**

```python
from IPython.display import HTML
events = [mwlab.get_event(u) for u in hits["event_uuid"].unique()]
HTML(render.timeline([e for e in events if e]))
```

![Notebook timeline](screenshots/workshop/13-notebook-timeline.png)

**Outcome.** You can say which campaign values were already known, since when, and from which events. With the seeded data, the Cobalt Strike infrastructure (`c2.example-cobalt.net`) and the Tor exit appear in earlier events too.

**Hints.**
- `mwlab` is already bound to your identity: no key to set.
- A value in more than one event has history: the campaign reuses infrastructure. Events sharing two or more values are probably the same actor; open them from **Hunt → Explore** and read their tags and galaxies. That is your attribution lead.
- **Real life:** save the notebook, then **Publish to global** so the rest of the SOC can rerun it with the next campaign's values, or **Export** it as a PDF for the incident ticket. A notebook can also enrich (`mwlab.enrich(value, type, module)`) and send its findings to a sink (`mwlab.send_to_sink(...)`), both audited.

### Task 5b — Reactor script: tag campaign infrastructure on arrival

**Goal.** Recognise campaign infrastructure the moment it arrives, from any source, so profiles, exports and Wazuh can route it by tag without an analyst spotting it first.

**Do.**

1. **Tech lab → Reactor scripts** → **+ New Reactor Script**:

   | Field | Value |
   |---|---|
   | **Name** | `Tag ACME treasury campaign infrastructure` |
   | **Trigger** | resource `attribute`, action `created` |
   | **Filters** | **Types**: `domain`, `hostname`, `url` |
   | **Max writes / run** | `10` (the default) |

2. Replace the code with:

   ```python
   # Infrastructure known to belong to the ACME treasury campaign.
   CAMPAIGN_DOMAINS = ("example-cobalt.net", "invoice-portal.test", "update-service.test")
   TAGS = (
       'misp-galaxy:tool="Cobalt Strike"',
       "kill-chain:Command and Control",
       'campaign:"acme-treasury"',
   )


   def handle(ctx, payload, trigger):
       value = (payload.get("value") or "").lower()
       hit = next((d for d in CAMPAIGN_DOMAINS if d in value), None)
       if hit is None:
           return
       for tag in TAGS:
           ctx.tag_attribute(payload["attribute_uuid"], tag)
       ctx.log("tagged", value, "as ACME treasury infrastructure (matched", hit + ")")
   ```

3. Test it in the **Test sandbox**: pick the trigger, **Load sample** → *attribute*, set the payload's `value` to `cdn.example-cobalt.net` and its `attribute_uuid` to one of your event's domain attributes, then **Run**.
4. Let it fire for real: event **Phishing: ACME treasury** → **Import Data** → paste `cdn.example-cobalt[.]net` → **Import**.

**Outcome.**
- The sandbox shows a successful run, **3 writes** and the log line.
- Within seconds of the import, the script's **Run history** shows a run, and the new attribute carries the three campaign tags.
- **Hunt → Explore** for `tags.name.keyword:"campaign:\"acme-treasury\""` finds every campaign value, whichever source brought it.

**Hints.**
- Each `tag_attribute` counts against the write quota: three per run, under the 10 allowed. Tags that don't exist yet, like `campaign:"acme-treasury"`, are created.
- The sandbox writes for real: the attribute you pointed it at now carries the tags too.
- Copy an attribute's uuid from its page.
- **Only with tags** `campaign:*` on the **Perimeter block** profile would turn it into a campaign-specific block list.
- **Real life:** the same pattern covers most SOC glue: enrich new domains with passive DNS as they arrive (`ctx.enrich(...)`, counted against the quota), forward a trusted partner's IDS values to the SIEM at once instead of at publish (`ctx.send_to_sink(...)`), or react to a `sighting` trigger when Wazuh reports a hit. Every write is in the audit log as `reactor.write.<verb>`, under the script owner's identity.

---

## Wrap-up

What you built, as a checklist for your own SOC:

| ✅ | Practice | Task |
|---|---|---|
| ☐ | Every feed has a **score modifier** that matches its track record (Source quality) | 2b |
| ☐ | Your own ranges and domains are on an **organisation warninglist**, synced from their source where one exists | 2c |
| ☐ | **One detection profile per control**, block lists stricter than alerting | 2d |
| ☐ | Blocking profiles **require approval** or **hold risky changes**, with auto-approve for trusted sources | 2d, 2e |
| ☐ | Controls **pull** (EDLs, exports, feeds) or are **pushed** to (sinks): no conversion scripts | 3 |
| ☐ | Alerts come back as **sightings**, and stale values **expire** (hit-rate expiry) | 4, 2f |

### Clean up

On the Wazuh manager, remove the `misp-perimeter` list and the `shuffle` integration from `ossec.conf`, rule 100900 from `local_rules.xml`, the lab's `<localfile>` and the crontab entry, then restart it.

Delete the workshop's EDL tokens, exports, webhook, notebook and reactor script from their pages. To remove the demo data: `docker compose exec api poetry run python -m app.cli seed-demo --reset` (it removes only its own rows).

---

## Facilitator notes

- **Before the session.** Run section 0 on every machine, or on one shared instance with one user per attendee. Check that **Intel → Warninglists** lists the MISP lists; the seed loads them. For Extra 2c+, allow `www.cloudflare.com` under **source_hosts** beforehand, and check the instance can reach it.
- **Timing.** Lab 2 is the longest and the one that matters most. If the room is slow, demo Tasks 2b and 2c on the projector and let attendees do 2d and 2e.
- **Common snags.**
  - *The profile counts zero values to send.* Expected until values are approved in the review queue: that is the point of **Require approval**.
  - *The review queue is empty.* The profile wasn't saved with **Require approval** on: the queue reads saved profiles only.
  - *A score didn't change.* Indicators sync every 15 seconds, and a trust change waits for its rebuild: wait a moment and search again. Still the same? The source you changed isn't the value's best source, or a cap doesn't apply because another source reports the value uncapped. The indicator's breakdown shows which.
  - *The EDL is empty.* It is rebuilt on its schedule; use **Rebuild now** on its page.
  - *A remote list didn't sync.* Its host isn't in **source_hosts**, the source redirects, or it isn't a plain list. **Sync now** on the list's page shows the error.
  - *The Wazuh list is empty.* Nothing in the profile is approved yet (Task 2e), or the manager reached the wrong host: `curl` from the manager, not from your laptop.
  - *`wazuh-logtest` doesn't fire rule 100900.* The manager wasn't restarted after the list or rule changed, or the log's field isn't named `url`.
  - *The webhook answered 404.* The URL was copied wrong, or **New URL** replaced it.
  - *Wazuh's alert never arrived.* `wazuh-logtest` raises no real alert: append the line to the monitored log file. Then check the manager's `ossec.log` for the integration, and that the manager can reach the misp-workbench host. A `403` means **Only from** doesn't list the manager's address.
- **Going further.** MISP servers (pulling from an ISAC) and incremental NDJSON feeds for SIEMs are good follow-ups; see the links below.

## Where to go next

| Topic | Docs |
|---|---|
| Feeds in depth | [../docs/features/feeds/index.md](../docs/features/feeds/index.md) |
| Normalisation | [../docs/features/normalisation.md](../docs/features/normalisation.md) |
| Indicators and scoring | [../docs/features/indicators.md](../docs/features/indicators.md) |
| Warninglists | [../docs/features/warninglists.md](../docs/features/warninglists.md) |
| Detection profiles, change preview, hit-rate expiry | [../docs/features/detection-profiles.md](../docs/features/detection-profiles.md) |
| Review queue | [../docs/features/review-queue.md](../docs/features/review-queue.md) |
| External dynamic lists | [../docs/features/edl.md](../docs/features/edl.md) |
| Suricata, Zeek and RPZ | [../docs/features/detection-formats.md](../docs/features/detection-formats.md) |
| Exports and incremental feeds | [../docs/features/exports.md](../docs/features/exports.md) |
| Sinks, including vendor APIs | [../docs/features/sinks.md](../docs/features/sinks.md) |
| Alert webhooks and sightings | [../docs/features/alert-webhooks.md](../docs/features/alert-webhooks.md), [../docs/features/sightings.md](../docs/features/sightings.md) |
| Lookup, restSearch, streaming exports | [../docs/features/api/lookup.md](../docs/features/api/lookup.md), [../docs/features/api/rest-search.md](../docs/features/api/rest-search.md), [../docs/features/api/streaming-exports.md](../docs/features/api/streaming-exports.md) |
| Notebooks and the `mwlab` SDK | [../docs/features/tech-lab/notebooks.md](../docs/features/tech-lab/notebooks.md) |
| Reactor scripts and `ctx` | [../docs/features/tech-lab/reactor.md](../docs/features/tech-lab/reactor.md) |
| Hunts, enrichment, MCP | [tutorial.md](tutorial.md) |

You now have the whole loop: intel **in** from feeds and reports, **curated** by score, warninglists, profiles and review, **out** to the firewall, IDS, resolver and SIEM, and **back** as sightings that decide what goes out next.
