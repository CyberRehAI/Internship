# ioc_dumper.py — IOC Dumper Service

**File:** `app/services/ioc_dumper.py`  
**Class:** `IOCDumperService`

## What is this file for?

This is the **core IOC extraction engine**. It:

1. Finds which OTX pulses to use (by ID and/or keyword search).
2. Downloads all indicators from those pulses.
3. Attaches pulse context (author, tags, TLP, MITRE, etc.) to each IOC.
4. **Tracks related pulses** for each unique IOC.
5. **Removes duplicates** when the same IOC appears in multiple pulses.
6. **Filters** by type (IP only, domains only, hashes only, etc.).
7. Returns statistics (counts per type) and pulse-level intelligence context.

The frontend **IOC Dumper** page calls this through `POST /api/iocs/dump`.

## Inputs (`dump` method)

| Parameter | Meaning |
|---|---|
| `pulse_ids` | List of specific pulse IDs to dump |
| `search_query` | Optional keyword — find more pulses (e.g. `emotet`) |
| `tags` | Optional — only keep search results that have these tags |
| `type_filter` | `all`, `ip`, `domains`, `urls`, `file_hashes`, `cves`, `email_addresses`, `yara` |
| `max_search_pulses` | Max pulses from keyword search (from `.env`, default 25) |

You can pass **both** pulse IDs and a search query — results are merged.

## Outputs

Returns a tuple of four things:

1. **`iocs`** — list of IOC records (dicts)
2. **`stats`** — `{ by_type: {...}, total: N, unique: N }`
3. **`pulses_processed`** — how many pulses were included
4. **`pulse_contexts`** — per-pulse threat context for the frontend context panel

## Pipeline (step by step)

### Step 1 — Build pulse map

```text
pulse_map = {}
```

- For each ID in `pulse_ids` → fetch pulse details and store in `pulse_map`.
- If `search_query` is set → search pulses (up to `max_search_pulses`).
  - Skip pulses that don’t match `tags` (if tags were provided).
  - Add each matching pulse to `pulse_map` (key = pulse ID).

Using a **map** means the same pulse ID is never processed twice.

Before fetching, pulse IDs are validated with:

- Must be exactly 24 characters
- Must be alphanumeric

Invalid IDs raise `OTXBadRequestError` with a clear message.

### Step 2 — Collect indicators

For every pulse in `pulse_map`:

1. Call `pulse_service.get_indicators(pulse_id)`.
2. For each indicator, build a **record**:

| Record field | Source |
|---|---|
| `type`, `value`, `description` | From indicator |
| `pulse_id`, `pulse_name`, `author`, `created` | From pulse |
| `tags`, `references`, `malware_families`, `attack_ids`, `tlp` | From pulse |

### Step 3 — Track related pulses + deduplicate

Duplicate key: `(indicator_type, lowercase_value)`.

- Every IOC occurrence adds a `related_pulses` entry (`pulse_id`, `pulse_name`) under that key.
- If IOC is new → save it.
- If IOC already exists → keep the version with **more references** (richer metadata).

This way `1.2.3.4` from three pulses appears once in the final list.

After dedupe, each IOC gets:

- `related_pulses`: unique list of pulses containing that IOC
- `related_pulse_count`: number of related pulses

### Step 4 — Filter by type

`FILTER_MAP` maps filter names to OTX indicator types:

| Filter | Includes |
|---|---|
| `ip` | IPv4, IPv6, CIDR |
| `domains` | domain, hostname |
| `urls` | URL, URI |
| `file_hashes` | FileHash-MD5, SHA1, SHA256 |
| `cves` | CVE |
| `email_addresses` | email |
| `yara` | YARA |
| `all` | No filtering |

### Step 5 — Statistics

Uses Python `Counter` to count IOCs per type and builds the `stats` dict.

### Step 6 — Build pulse intelligence context

The service also builds `pulse_contexts` for every resolved pulse. Each context includes:

- `pulse_id`
- `immediate_threat` (defaults to pulse name when no dedicated field exists)
- `threat_summary` (pulse description)
- `pulse_name`, `author`, `created`, `tlp`
- `tags`, `adversary`, `targeted_countries`
- `malware_families`, `attack_ids`, `references`

This is what powers the frontend "extra pulse intelligence context" section.

## Example flow

**Request:**

```json
{
  "pulse_ids": [],
  "search_query": "ransomware",
  "tags": [],
  "type_filter": "ip"
}
```

**What happens:**

1. Search OTX for pulses matching `ransomware` (max 25).
2. For each pulse, download indicators (many API calls — can take time).
3. Merge all IOCs, dedupe.
4. Keep only IP-type indicators.
5. Return filtered list + stats.

## Performance tips

- **Selecting specific pulse IDs** is faster than a broad keyword dump.
- Caching in `OTXClient` helps if you dump the same pulses again within 10 minutes.
- `DUMP_MAX_SEARCH_PULSES` in `.env` limits how many pulses a keyword search can pull.

## Output shape notes

Each IOC record now contains:

- Base IOC fields (`type`, `value`, `description`)
- Pulse attribution fields (`pulse_id`, `pulse_name`, `author`, `created`, `tlp`, etc.)
- Cross-pulse relationship fields (`related_pulses`, `related_pulse_count`)

The route (`/api/iocs/dump`) returns these IOC rows plus `pulse_contexts` in the same response.

## Who calls this?

- Route: `app/api/routes/iocs.py` → `POST /api/iocs/dump`
- Frontend: IOC Dumper page → `dumpIOCs()` in `api/client.ts`

Exported IOCs are sent later to `export_service.py` by the frontend (separate request).
