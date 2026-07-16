# Backend Services Documentation

This folder explains each file in `backend/app/services/` in simple words.

Services hold the **business logic** of the API. Routes only receive HTTP requests and call these services.

## How services connect

```
API Routes
    │
    ├── indicator_detector  →  figures out what the user searched for
    ├── pulse_service       →  works with OTX pulses (reports)
    │       └── otx_client  →  talks to AlienVault OTX API
    │               └── cache  →  saves recent answers in memory
    ├── ioc_dumper          →  collects and cleans up IOCs
    │       └── pulse_service
    └── export_service      →  saves IOCs to CSV / JSON / Excel files
```

## Service files

| File | What it does | Read more |
|---|---|---|
| [`cache.py`](cache.md) | Short-term memory to avoid repeating slow API calls | [cache.md](cache.md) |
| [`otx_client.py`](otx_client.md) | Main bridge to AlienVault OTX | [otx_client.md](otx_client.md) |
| [`pulse_service.py`](pulse_service.md) | Search and read OTX pulses in a clean format | [pulse_service.md](pulse_service.md) |
| [`indicator_detector.py`](indicator_detector.md) | Guess if input is IP, hash, domain, CVE, etc. | [indicator_detector.md](indicator_detector.md) |
| [`ioc_dumper.py`](ioc_dumper.md) | Pull IOCs from pulses, merge, remove duplicates, and build pulse intelligence context | [ioc_dumper.md](ioc_dumper.md) |
| [`export_service.py`](export_service.md) | Write IOC lists to downloadable files | [export_service.md](export_service.md) |

## Suggested reading order

1. `cache.md` — smallest, easy to understand
2. `otx_client.md` — foundation for everything else
3. `pulse_service.md` — builds on the client
4. `indicator_detector.md` — used by global search
5. `ioc_dumper.md` — main IOC workflow
6. `export_service.md` — file export at the end
