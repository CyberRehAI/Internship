# indicator_detector.py — Indicator Type Detector

**File:** `app/services/indicator_detector.py`  
**Function:** `detect_input_type(value)`  
**Dataclass:** `DetectionResult`

## What is this file for?

When a user types something in **Global Search**, we need to know **what kind of thing** it is before calling OTX.

Examples:

- `8.8.8.8` → IP address
- `evil.com` → domain
- `d41d8cd98f00b204e9800998ecf8427e` → MD5 hash
- `emotet` → generic keyword

This file runs simple rules (regex and IP parsing) to classify the input and pick the right OTX lookup strategy.

## `DetectionResult` — what we return

| Field | Meaning |
|---|---|
| `input_value` | Trimmed search text |
| `detected_type` | Short label: `ip`, `md5`, `domain`, `keyword`, etc. |
| `search_strategy` | What the search route should do next |
| `indicator_type` | OTX SDK type object (only for real IOCs) |

### Search strategies

| Strategy | Meaning |
|---|---|
| `indicator_details` | Look up this value as an IOC in OTX (IP, hash, domain, URL, CVE) |
| `pulse_lookup` | Treat input as a 24-char pulse ID and load that pulse |
| `pulse_search` | Search pulses by keyword (email, free text) |

## Detection order (important!)

Checks run **top to bottom**. First match wins.

```
1. IP address     (IPv4 or IPv6)
2. MD5 hash       (32 hex characters)
3. SHA1 hash      (40 hex characters)
4. SHA256 hash    (64 hex characters)
5. CVE            (CVE-2024-1234)
6. URL            (starts with http:// or https://)
7. Email          (user@domain.tld)
8. Domain         (hostname like evil.com)
9. Pulse ID       (exactly 24 alphanumeric chars)
10. Keyword       (anything else)
```

## Patterns used

Defined at the top of the file:

- `HASH_PATTERNS` — regex for MD5 / SHA1 / SHA256 lengths
- `CVE_PATTERN` — `CVE-YYYY-NNNN+`
- `EMAIL_PATTERN` — basic email shape
- `URL_PATTERN` — `http://` or `https://`
- `DOMAIN_PATTERN` — valid-looking hostname
- `PULSE_ID_PATTERN` — 24-char OTX pulse ID

IPs use Python’s `ipaddress.ip_address()` instead of regex (more accurate).

## `detect_input_type(value)` — step by step

1. **Strip** whitespace from input.
2. Try each rule in order (see list above).
3. For IOC types, attach the matching `IndicatorTypes.*` object from the OTX SDK (needed for `get_indicator_details_full`).
4. If nothing matches → return `detected_type="keyword"` and `search_strategy="pulse_search"`.

## Examples

| Input | detected_type | search_strategy |
|---|---|---|
| `192.168.1.1` | `ip` | `indicator_details` |
| `abc...` (32 hex) | `md5` | `indicator_details` |
| `CVE-2024-3400` | `cve` | `indicator_details` |
| `https://bad.site/x` | `url` | `indicator_details` |
| `6a47950711440db76d84e5de` | `pulse_id` | `pulse_lookup` |
| `lockbit` | `keyword` | `pulse_search` |

## Who uses this?

Only **`search.py`** route (`GET /api/search`):

```python
detection = detect_input_type(q)

if detection.search_strategy == "indicator_details":
    # fetch indicator intel + related pulses
elif detection.search_strategy == "pulse_lookup":
    # load one pulse by ID
else:
    # search pulses by keyword
```

The frontend shows `detected_type` so the analyst knows how the query was interpreted.

## Design notes

- **No network calls** — pure Python logic, very fast.
- **Conservative domain regex** — unusual inputs may fall through to `keyword`, which is still useful.
- **Email uses pulse search** — OTX does not expose full email indicator details the same way as IPs; we search related pulses instead.
