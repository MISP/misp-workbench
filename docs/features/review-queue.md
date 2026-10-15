# Review queue

Synced data can't all go to security controls on its own, but reviewing all
of it by hand doesn't scale. The review queue sits between the two: a
[detection profile](detection-profiles.md) that **requires approval** only
sends what is approved, and everything else it would send waits for an
analyst. **Auto-approve** profiles cover the trusted bulk, so the queue holds
what actually needs a decision.

Under ***Intel*** → ***Review queue***.

<img src="../../screenshots/review-queue/misp-workbench-1_review-queue_pending.png#only-light" alt="The review queue, with an indicator's context" style="max-width: 100%; height: auto;">
<img src="../../screenshots/review-queue/misp-workbench-1_review-queue_pending-dark.png#only-dark" alt="The review queue, with an indicator's context" style="max-width: 100%; height: auto;">

## What waits

An indicator is **pending** when a profile requiring approval would select
it once approved, and it is not:

- **approved** by an analyst;
- **approved automatically**: selected by an auto-approve profile;
- **rejected** by an analyst;
- **snoozed**, until the snooze is over.

Without a profile requiring approval, nothing waits. Each pending indicator
lists the profiles it waits for, so you know where an approval sends it.

### Auto-approve profiles

Mark a detection profile **auto-approve what it selects** and its rules
become a rule of the queue. The migration adds one, *Auto-approve: trusted
sources*: flagged for IDS, scored 70 or more, from a feed or server with a
[score modifier](indicators.md#source-trust) of 10 or more, not warninglisted,
without validation issues. Edit it, or add others: a profile for your own
organisation's events, for one trusted partner, for hashes from a sandbox.

Auto-approval is evaluated, not stored: an indicator is approved while an
auto-approve profile selects it, and goes back to waiting when its score
decays or its source loses trust. An analyst's rejection always beats it.

## Deciding

Click an indicator for its context: its score and how it was reached, its
sources and organisations, sightings, warninglist hits, validation issues,
tags and events, the decisions taken on it before, and the enrichment
modules that take its type (run on demand; nothing is written to an event).

Then, for the selected indicators, or the highlighted one:

| Action | Shortcut | Effect |
|---|---|---|
| **Approve** | `a` | Profiles requiring approval send it, as long as their other rules select it |
| **Reject…** | `r` | No profile requiring approval or leaving out rejected sends it. Asks why |
| **Snooze** | `s` (7 days) | Out of the queue for 1, 7 or 30 days, then back |
| **Reopen** | `u` | Takes a decision back (in the snoozed, approved and rejected tabs) |

Move with `j` and `k` (or the arrows), select with `x` (`shift + x` for the
page), open the context with `enter`, switch tabs with `1`–`4`. `?` lists the
shortcuts.

The **snoozed**, **approved** and **rejected** tabs list decisions, newest
first, with who took them and why. Who decided is audit data: the analyst's
email is shown to their own organisation and to audit admins
(`audit_logs:admin`); others see the organisation.

<img src="../../screenshots/review-queue/misp-workbench-3_review-queue_rejected.png#only-light" alt="Rejected indicators, with who rejected them and why" style="max-width: 100%; height: auto;">
<img src="../../screenshots/review-queue/misp-workbench-3_review-queue_rejected-dark.png#only-dark" alt="Rejected indicators, with who rejected them and why" style="max-width: 100%; height: auto;">

### Decisions are remembered

A decision is on the **value**: the type and value of the indicator, whatever
sources report it. A value rejected today and reported again next month by
another feed is still rejected, even after its indicator was removed and
built again.

Every decision is also in the [audit log](api/audit-logs.md)
(`indicator_review.approved`, `.rejected`, `.snoozed`, `.reopened`).

### Rejecting onto a warninglist

Rejecting only keeps a value out of the profiles that read decisions.
**Also add to the *Rejected in review* warninglist** puts it on that
[warninglist](warninglists.md) too: it is then warninglisted everywhere,
for every profile and output that leaves warninglisted values out, and its
score drops. Any later decision on it takes it off the list again.

<img src="../../screenshots/review-queue/misp-workbench-2_review-queue_reject.png#only-light" alt="Rejecting onto a warninglist" style="height: 360px;">
<img src="../../screenshots/review-queue/misp-workbench-2_review-queue_reject-dark.png#only-dark" alt="Rejecting onto a warninglist" style="height: 360px;">

## Where decisions apply

Decisions are carried on the indicators (`review`), so every output reading
a profile honours them: exports and feeds, sinks, membership deltas (an
indicator leaving a profile because it was rejected is a `remove` with reason
`rejected`; one no longer approved, `pending`), `/lookup` and restSearch. A
value too new to have an indicator yet is judged on its stored decision.

## API

| Endpoint | Scope | Use |
|---|---|---|
| `GET /indicators/review` | `attributes:read` | Pending indicators, each with `pending_for`. Filters: `profile_id`, `q`, `type`, `source`, `min_score`, `max_score`, `sort` |
| `GET /indicators/review/summary` | `attributes:read` | Pending and decided counts, and the profiles involved |
| `GET /indicators/review/decisions?status=` | `attributes:read` | Approved, rejected or (still) snoozed indicators, with who and why |
| `POST /indicators/review/decisions` | `indicators:review` | Decide on up to 500 indicators: `{"indicators": [uuid…], "action": "approve" \| "reject" \| "snooze" \| "reopen", "reason", "snooze_days", "warninglist"}` |
| `GET /indicators/{uuid}/review` | `attributes:read` | The decision on one indicator, and every decision before it |

Org Admin and Publisher have `indicators:review`; every role that reads
attributes can see the queue.
