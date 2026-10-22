---
marp: true
title: MISP Workbench in 5 minutes
description: A lightning talk presenting MISP Workbench
paginate: true
size: 16:9
style: |
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
  section {
    background: #F5F4EF;
    color: #101A2B;
    font-family: 'IBM Plex Sans', Arial, sans-serif;
    font-size: 26px;
    padding: 56px 64px;
    justify-content: flex-start;
  }
  h1, h2 { color: #101A2B; font-weight: 700; letter-spacing: -0.5px; }
  h2 { font-size: 44px; margin: 0 0 20px; }
  strong { color: #101A2B; }
  code { font-family: 'JetBrains Mono', monospace; background: #ECEAE2; color: #101A2B; border-radius: 6px; padding: 1px 6px; font-size: 0.85em; }
  ul { margin: 0; padding-left: 1.1em; }
  li { margin: 6px 0; line-height: 1.35; }
  li::marker { color: #F08A3E; }
  table { font-size: 22px; border-collapse: collapse; }
  th { background: #101A2B; color: #F5F4EF; text-align: left; }
  th, td { padding: 8px 14px; border: none; }
  tr:nth-child(even) td { background: #ECEAE2; }
  tr:nth-child(odd) td { background: #F5F4EF; }
  .kicker { font-family: 'JetBrains Mono', monospace; color: #C2410C; font-size: 18px; letter-spacing: 2px; margin: 0 0 6px; }
  .muted { color: #4A5568; }
  .cols { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }
  .card { background: #FFFFFD; border: 1px solid #DCD9CE; border-radius: 14px; padding: 18px 22px; }
  .card h3 { margin: 0 0 8px; font-size: 26px; color: #C2410C; }
  .card p { margin: 0; font-size: 21px; line-height: 1.4; color: #4A5568; }
  .flow { display: flex; align-items: center; gap: 14px; margin: 18px 0 26px; }
  .flow span { background: #101A2B; color: #F5F4EF; border-radius: 12px; padding: 14px 20px; font-weight: 600; font-size: 24px; }
  .flow b { color: #F08A3E; font-size: 30px; }
  section::after { color: #8A94A6; font-size: 16px; }
  section.dark { background: #101A2B; color: #F5F4EF; }
  section.dark h1, section.dark h2, section.dark strong { color: #F5F4EF; }
  section.dark .kicker { color: #F08A3E; }
  section.dark .muted { color: #C9D3E0; }
  section.dark code { background: #1C2A42; color: #F5F4EF; }
  section.title { justify-content: center; align-items: center; text-align: center; }
  section.tight li { margin: 3px 0; font-size: 23px; }
  section.tight h2 { margin-bottom: 12px; }
  .shot { margin-top: 14px; }
  .shot img { max-height: 210px; width: auto; max-width: 100%; border-radius: 8px; border: 1px solid #DCD9CE; }
  .stack { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-top: 8px; }
  .stack .card p { font-size: 22px; }
  .stack-shot { margin-top: 22px; text-align: center; }
  .stack-shot img { max-height: 290px; border-radius: 8px; border: 1px solid #DCD9CE; }
  .try { display: flex; gap: 48px; align-items: center; margin-top: 8px; }
  .try .qr { background: #F5F4EF; border-radius: 16px; padding: 14px; line-height: 0; flex: none; }
  .try p { margin: 0 0 14px; font-size: 24px; line-height: 1.4; }
  section.dark .try a { color: #F08A3E; }
  .q code { font-size: 0.78em; white-space: nowrap; }
  section.title p.tagline { font-size: 32px; line-height: 1.4; max-width: 980px; color: #C9D3E0; margin: 28px auto 0; }
---

<!-- _class: dark title -->
<!-- _paginate: false -->

![w:360](../../docs/images/misp-workbench-verti-white.svg)

<p class="tagline">A MISP-compatible threat intelligence platform for ingesting, curating and sharing IOCs, built on OpenSearch.</p>

<!--
One sentence to remember: everything MISP does with indicators, on a search engine, with the curation and sharing a SOC needs to actually use them. Five minutes, nine features.
-->

---

<p class="kicker">WHY ANOTHER PLATFORM</p>

## MISP-compatible, rebuilt on a search engine

| | MISP | MISP Workbench |
|---|---|---|
| Backend | PHP · CakePHP | Python · FastAPI |
| Storage | MySQL / MariaDB | PostgreSQL + **OpenSearch** |
| Background jobs | background workers | Celery + Redis, scheduled with RedBeat |
| Frontend | server-rendered + jQuery | Vue 3 single-page app |

<p class="muted">It still speaks MISP: syncs with MISP servers, reads MISP feeds, writes MISP JSON, and answers MISP's restSearch.</p>

<!--
Not a fork and not a replacement for MISP communities: it sits next to them. The big change is the data store. Events, attributes, indicators and correlations all live in OpenSearch, so search, aggregation and ingest pipelines come for free.
-->

---

![bg right:48% contain](../../docs/screenshots/explore/misp-workbench-1_explore.png)

<p class="kicker">EXPLORE</p>

## Lucene over everything

- One query, four tabs: **events**, **attributes**, **indicators**, **correlations**
- <span class="q">`type.keyword:ip* AND tlp:amber`</span>
- <span class="q">`expanded.ip2geo.country_iso_code:RU`</span>
- Time range and a timeline histogram
- Save any search as a **hunt** or an **export**

<!--
Explore is the front door. Anything indexed is searchable with Lucene, including enriched fields like GeoIP. A query that answers a question once can be kept: as a hunt that reruns it, or as an export that ships its results.
-->

---

![bg right:48% contain](../../docs/screenshots/hunts/misp-workbench-3_hunts_view-opensearch-hunt.png)

<p class="kicker">HUNTS</p>

## Saved searches that run on a schedule

| Type | Asks |
|---|---|
| **OpenSearch** | a Lucene query over events, attributes or correlations |
| **CPE** | CVEs affecting a product, via vulnerability.circl.lu |
| **Rulezet** | detection rules for a CVE, via rulezet.org |
| **MITRE ATT&CK** | what is tagged with these techniques |

<p class="muted">Each run is kept, and new matches raise a notification.</p>

<!--
Hunts turn a question into a watch. Two of the four types reach outside the platform: CPE asks CIRCL's vulnerability-lookup which CVEs hit a product you run, and Rulezet fetches the detection rules published for a CVE.
-->

---

<!-- _class: tight -->

<p class="kicker">INGEST</p>

## Multiple sources and formats supported

- **MISP servers**: pull and push, with rules · **Feeds**: MISP, CSV, JSON (NDJSON, dot paths), freetext
- From a **URL on a schedule**, an **uploaded file**, the **REST API**, or a pasted report
- **CSV mapping**: type from a column with a mapping table, every property fixed or from a column, with a preview
- **Normalisation**: defanged values refanged, problems flagged, never dropped
- **Source quality**: hit rate, false positives and overlap per source, to set its trust

<div class="shot">

![Source quality](../../docs/screenshots/indicators/misp-workbench-5_indicators_source-quality.png)

</div>

<!--
Source quality is the part people don't have elsewhere: for every feed, server and organisation, how often its values were actually hit, how often they were reported benign, and how much it overlaps with other sources. That's the evidence for trusting a feed, instead of its reputation.
-->

---

![bg right:50% contain](../../docs/screenshots/indicators/misp-workbench-2_indicators_detail.png)

<p class="kicker">INDICATORS</p>

## One record per indicator, with a score that decays

- Every attribute holding a value, merged: sources, TLP, sightings
- **Base** by source, **+5** per corroborating source
- **Sightings** add, **false positives** subtract
- **Warninglisted** −50 · **validation issue** −40
- **Decay**: halves every 30 days for IPs and URLs, 90 for domains, never for hashes

<p class="muted">A C2 from two years ago fades out of block lists; a malware hash keeps its value.</p>

<!--
The score is readable: every part shows in the breakdown, every number is a runtime setting, and each source has its own modifier and cap. Decay counts from last seen, and a positive sighting moves last seen, so what is still being hit stays alive.
-->

---

<!-- _class: tight -->

<p class="kicker">SHARE</p>

## Every control gets its own format

- **Detection profiles**: say once what goes to a control; every output can use it
- **Exports**: MISP JSON, STIX 2.1, CSV, NDJSON incremental feeds, **Suricata**, **Zeek**, **DNS RPZ**, **Wazuh CDB**
- **Firewall lists**: PAN-OS, FortiGate, Check Point, Cisco, Squid
- **Sinks**: Splunk HEC, GELF, syslog/CEF, webhooks · Sentinel, Defender, Elastic *(beta)*
- **APIs**: `/lookup`, restSearch, streaming exports, an **MCP** server for AI assistants

<div class="shot">

![Sinks](../../docs/screenshots/sinks/misp-workbench-1_sinks_list.png)

</div>

<!--
The point: no conversion scripts. A firewall pulls its list, the IDS gets rules, the resolver gets a zone, the SIEM gets pushed events, all from the same profile, with an approval queue in front of what blocks traffic.
-->

---

<p class="kicker">CLOSE THE LOOP</p>

## SIEM alerts come back as sightings

<div class="flow"><span>SIEM alert</span><b>→</b><span>Alert webhook</span><b>→</b><span>Sighting</span><b>→</b><span>Score</span><b>→</b><span>Next share</span></div>

- Presets for **Splunk**, **Elastic / Kibana**, **Graylog**, **Wazuh**, **Microsoft Sentinel**, generic JSON
- No code on the sender's side: paste the URL into its webhook action
- A Sentinel incident closed as *False positive* reports a false positive
- **Hit-rate expiry** drops what no sensor has hit, so block lists shrink

<!--
This is the step most SOCs skip, and why their block lists only ever grow. A hit raises a value's score and keeps it alive; a false positive lowers it and can push it out of every profile.
-->

---

<p class="kicker">TECH LAB</p>

## Analyse, automate, transform

<div class="stack">
<div class="card"><h3>Analyst notebooks</h3><p>Python with the <code>mwlab</code> SDK: retro-hunts, campaign reports, source reviews. Rerun, share, export to PDF.</p></div>
<div class="card"><h3>Reactor scripts</h3><p>Python that runs when an event is published, an attribute created or a sighting arrives: tag, enrich, forward. Sandboxed, with a write quota.</p></div>
<div class="card"><h3>Transformation servos</h3><p>Your own OpenSearch ingest pipelines, on every attribute as it is indexed: parse, normalise, enrich.</p></div>
</div>

<!--
Notebooks are the pull side: an analyst asks. Reactor scripts are the push side: the platform reacts. Servos act before any of it, as data is indexed. Everything they do is audited under the user's identity.
-->

---

<!-- _class: dark -->
<!-- _paginate: false -->

<p class="kicker">TRY IT</p>

## Docs, and a hands-on workshop on Friday

<div class="try">
<div class="qr">

![w:200](qr-docs.svg)

</div>
<div>

**misp-workbench.readthedocs.io**

**From Feed to Firewall** · Friday 23 October · 10:15 · Hollenfels

<span class="muted">90 minutes, hands-on: ingest, curate and share IOCs with a firewall, an IDS, a DNS resolver and a SIEM.</span>

<span class="muted">Bring a laptop with Docker · github.com/MISP/misp-workbench</span>

</div>
</div>

<!--
Leave this up during questions. The QR code opens the documentation. Friday's workshop builds the whole pipeline from this talk on the attendees' own machines: bring a laptop with Docker, and run the setup in the guide before the session if you can.
-->
