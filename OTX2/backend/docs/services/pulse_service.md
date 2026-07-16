# pulse_service.py — Pulse Service

**File:** `app/services/pulse_service.py`  
**Class:** `PulseService`  
**Helper:** `normalize_pulse()`

## What is this file for?

In OTX, a **Pulse** is a threat report: a bundle of IOCs plus context (tags, author, MITRE IDs, TLP, etc.).

This service:

1. Asks `OTXClient` for pulse data.
2. **Cleans and standardizes** the response so the rest of the app always gets the same field names.

Routes and `IOCDumperService` use `PulseService` instead of talking to `OTXClient` directly.

## `normalize_pulse(pulse)` — helper function

OTX sometimes returns slightly different shapes (e.g. author as object vs string). This function builds one consistent dictionary:

| Field | Meaning |
|---|---|
| `id` | Pulse ID (24-character string) |
| `name` | Pulse title |
| `description` | What the threat is about |
| `author_name` | Who published it |
| `created` / `modified` | Timestamps |
| `tags` | Keywords (ransomware, apt, etc.) |
| `TLP` | Traffic Light Protocol (sharing level) |
| `attack_ids` | MITRE ATT&CK IDs |
| `malware_families` | Related malware names |
| `references` | External links |
| `indicator_count` | How many IOCs are in the pulse |
| `adversary` | Threat actor/adversary label if present |
| `targeted_countries` | Countries normalized to a list |

**Author handling:** tries `author_name` first; if missing, reads `author.username` from nested object.

**Adversary handling:** accepts alternate field names like `adversaries`, `threat_actor`, or `actor`, then flattens list values into a readable string.

**Targeted countries handling:** accepts `targeted_countries`, `targeted_country`, `countries`, or `country` and normalizes them to a list so downstream code always gets the same type.

## `PulseService` class

### `__init__(self, otx_client)`

Stores a reference to `OTXClient` for all OTX calls.

### `search(query, limit=25)`

**What it does:** Find pulses whose text matches a keyword.

**Steps:**

1. Call `otx_client.search_pulses(query, max_results=limit)`.
2. Loop through `results`.
3. Run each through `normalize_pulse()`.
4. Return a list of clean pulse dicts.

**Used by:** Global search (keyword path), pulse search route, IOC dumper (keyword search).

### `get_details(pulse_id)`

**What it does:** Get full metadata for one pulse by ID.

**Steps:**

1. Call `otx_client.get_pulse_details(pulse_id)` (may come from cache).
2. Return `normalize_pulse(...)`.

**Used by:** Pulse detail route, IOC dumper (when pulse IDs are provided).

### `get_indicators(pulse_id, limit=1000)`

**What it does:** Get all IOCs inside a pulse.

**Steps:**

1. Call `otx_client.get_pulse_indicators(pulse_id, limit)` (may come from cache).
2. Return raw indicator list (type, indicator value, description, etc.).

**Note:** Indicators are **not** normalized here — that happens in `IOCDumperService` when building IOC records and pulse intelligence context in `/api/iocs/dump`.

**Used by:** Pulse indicators route, IOC dumper.

## Flow example: search for "emotet"

```
Frontend: GET /api/pulses/search?q=emotet
    → pulses.py route
    → pulse_service.search("emotet", 25)
    → otx_client.search_pulses("emotet", 25)
    → OTX API
    ← list of normalized pulses
```

## Why a separate service?

- **Single place** for pulse field naming — frontend always sees the same JSON shape.
- **Easier testing** — mock `OTXClient` without touching routes.
- **Clear layering** — `OTXClient` = raw OTX; `PulseService` = pulse domain logic.
