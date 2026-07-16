# otx_client.py — OTX API Client

**File:** `app/services/otx_client.py`  
**Class:** `OTXClient`

## What is this file for?

This is the **main connection** between our backend and AlienVault OTX. It wraps the official `OTXv2` Python SDK and adds:

- Error handling (bad API key, not found, network errors)
- Caching for pulse data
- Retries when OTX is busy or returns server errors
- A larger HTTP connection pool for heavy IOC dumps

Other services should not call the SDK directly — they go through `OTXClient`.

## How it works (simple)

```
Your code  →  OTXClient  →  OTXv2 SDK  →  otx.alienvault.com
```

Every OTX call goes through `_execute()`, which catches SDK errors and turns them into app errors the API can return to the frontend.

## Code walkthrough

### `__init__(self, settings)`

When the client is created it:

1. Reads API key and server URL from `Settings` (`.env`).
2. Creates the `OTXv2` SDK instance.
3. Creates a `TTLCache` for pulse-related data.
4. Calls `_configure_connection_pool()` to tune HTTP connections.

### `_configure_connection_pool()`

- Gets the SDK’s `requests` session.
- Sets pool size to **20** connections (default SDK pool is 10, which caused “connection pool is full” warnings during big dumps).
- Adds **retry** logic: up to 5 tries on status codes 429, 500, 502, 503, 504 with backoff.

### `_execute(self, fn, *args, **kwargs)`

Wrapper around any SDK function:

| SDK raises | App raises |
|---|---|
| `InvalidAPIKey` | `OTXInvalidApiKeyError` → HTTP 401 |
| `NotFound` | `OTXNotFoundError` → HTTP 404 |
| `BadRequest` | `OTXBadRequestError` → HTTP 400 |
| Network error | `RuntimeError` → HTTP 502 |

### `get_user_me()`

- Calls OTX `GET /api/v1/users/me`.
- Used by **health check** to prove the API key works and get the username.

### `search_pulses(query, max_results=25)`

- Searches OTX pulses matching a keyword (e.g. `ransomware`).
- Returns raw SDK response with a `results` list.
- **Not cached.**

### `get_pulse_details(pulse_id)`

- Fetches one pulse’s metadata (name, tags, author, etc.).
- **Cached** under key `pulse:{pulse_id}`.

### `get_pulse_indicators(pulse_id, limit=1000)`

- Fetches all IOCs inside a pulse.
- **Cached** under key `pulse-indicators:{pulse_id}:{limit}`.

### `get_indicator_details_full(indicator_type, value)`

- Fetches full OTX intelligence for one indicator (IP, domain, hash, CVE, etc.).
- Used by **global search** when the input is a known IOC type.
- **Not cached.**

## Who uses this class?

| Consumer | Methods used |
|---|---|
| `health.py` route | `get_user_me()` |
| `search.py` route | `get_indicator_details_full()` |
| `pulse_service.py` | `search_pulses()`, `get_pulse_details()`, `get_pulse_indicators()` |

## Flow example: get pulse indicators

```
1. pulse_service.get_indicators("abc123")
2. otx_client.get_pulse_indicators("abc123")
3. Check cache → miss
4. _execute(client.get_pulse_indicators, "abc123")
5. SDK calls OTX API
6. Save result in cache
7. Return list of indicators
```

## Configuration

From `.env` via `Settings`:

- `OTX_API_KEY` — required
- `OTX_SERVER` — default `https://otx.alienvault.com`
- `CACHE_TTL_SECONDS` — how long cache entries live
