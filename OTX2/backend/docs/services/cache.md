# cache.py — TTL Memory Cache

**File:** `app/services/cache.py`  
**Class:** `TTLCache`

## What is this file for?

When the app asks OTX for the same pulse or indicators again, it can answer from **memory** instead of calling the internet every time. That makes the API faster and reduces load on OTX.

TTL means **Time To Live** — cached data expires after a set number of seconds (from `CACHE_TTL_SECONDS` in `.env`, default 600 = 10 minutes).

## How it works (simple)

Think of it like a notepad:

1. You look up a key (e.g. `pulse:abc123`).
2. If the note exists and is still fresh → return the saved value.
3. If the note is missing or too old → return nothing; the caller fetches from OTX and writes a new note.

## Code walkthrough

### `__init__(self, ttl_seconds=600)`

- Stores how long each cache entry should live (`ttl_seconds`).
- Creates an empty dictionary `_store` to hold cached items.

### `get(self, key)`

1. Look for `key` in `_store`.
2. If not found → return `None` (cache miss).
3. If found, check the timestamp:
   - If older than `ttl_seconds` → delete it and return `None`.
   - If still valid → return the stored value.

### `set(self, key, value)`

- Saves `value` under `key` with the current time.
- Next `get()` for that key will return this value until it expires.

## Where is it used?

Only inside **`otx_client.py`**, for:

- Pulse details: key `pulse:{pulse_id}`
- Pulse indicators: key `pulse-indicators:{pulse_id}:{limit}`

Search and indicator lookups are **not** cached (they change more often or are one-off queries).

## Example

```python
cache = TTLCache(ttl_seconds=600)
cache.set("pulse:abc", {"name": "Ransomware Campaign"})
cache.get("pulse:abc")  # → {"name": "Ransomware Campaign"}
# ... 11 minutes later ...
cache.get("pulse:abc")  # → None (expired)
```

## Notes

- Cache lives **only in RAM** — restarting the server clears it.
- There is no Redis or database; one cache per running app process.
- This is intentional: simple and enough for a local analyst workbench.
