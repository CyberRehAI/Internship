# AlienVault OTX Threat Intelligence Workbench

A lightweight **Threat Intelligence Platform (TIP)** for searching, investigating, filtering, and exporting threat data from [AlienVault Open Threat Exchange (OTX)](https://otx.alienvault.com).

Instead of a raw API client, this workbench gives SOC analysts, students, and security researchers a clean web interface to work with OTX pulses and Indicators of Compromise (IOCs) in one place.

---

## What Does This Application Do?

The OTX Threat Intelligence Workbench connects to AlienVault OTX and lets you:

1. **Search** for threat intelligence using IPs, domains, URLs, file hashes, CVEs, malware names, threat actors, or keywords.
2. **Investigate** OTX Pulses — curated threat reports that bundle IOCs with context such as tags, TLP, MITRE ATT&CK mappings, and references.
3. **Dump IOCs** from one or many pulses, merge the results, remove duplicates, and filter by indicator type.
4. **Export** the results to CSV, JSON, or Excel for use in SIEMs, firewalls, EDR, or offline analysis.

The backend talks to OTX through the official Python SDK (`OTXv2`). The frontend provides a modern dashboard for day-to-day threat intel workflows.

---

## Who Is This For?

| Audience | Use case |
|---|---|
| **SOC analysts** | Quickly pull IOCs from relevant pulses and export them for blocking or detection rules |
| **Students** | Learn how threat intelligence platforms work with a hands-on OTX integration |
| **Security researchers** | Search indicators, explore pulse metadata, and bulk-export IOC sets for analysis |

---

## Key Features

### Global Search
- Accepts IPs, domains, URLs, MD5/SHA1/SHA256 hashes, CVEs, and free-text keywords.
- **Automatically detects** the input type and routes the query to the right OTX endpoint.
- Returns matching pulses plus indicator enrichment (reputation, passive DNS, geolocation where available).

### Pulse Viewer
- Browse and inspect OTX pulses with enriched metadata:
  - Author, description, tags, TLP
  - MITRE ATT&CK mapping
  - Malware families and references
  - Indicator counts

### IOC Dumper
- Dump all IOCs from a **single pulse** or **multiple selected pulses**.
- Search by **keyword, tag, or malware family** and dump IOCs from all matching pulses.
- **Merge and deduplicate** results automatically.
- Track cross-pulse IOC relationships (`related_pulses`, `related_pulse_count`) for better analyst context.
- Filter dumped IOCs by type:
  - IP Addresses
  - Domains
  - URLs
  - File Hashes
  - CVEs
  - Email Addresses
  - YARA
  - All

### Export
Two export modes:

| Mode | Fields |
|---|---|
| **Basic** | IOC Type, IOC Value, Description |
| **Extended** | Basic fields + Pulse Name, Author, Created Date, Tags, References, Malware Family, MITRE ATT&CK Mapping, TLP |

Supported formats: **CSV**, **JSON**, **Excel (.xlsx)**

### Extra Intelligence Context in Frontend
- The frontend gets extra context from `POST /api/iocs/dump` in the same response as IOC rows.
- Backend now returns:
  - `iocs[]` with `related_pulses` and `related_pulse_count`
  - `pulse_contexts[]` with `immediate_threat`, `threat_summary`, `adversary`, `targeted_countries`, `attack_ids`, `malware_families`, `references`, `tlp`
- Type definitions are mapped in `frontend/src/types/otx.ts`:
  - `IOCRecord`
  - `PulseIntelligenceContext`
  - `IOCDumpResponse`
- API client (`frontend/src/api/client.ts`) returns this enriched payload through `dumpIOCs(...)`.
- IOC Dumper page (`frontend/src/pages/IocDumperPage.tsx`) passes both collections into `IocPreview`:
  - `iocs={dumped.iocs}`
  - `pulseContexts={dumped.pulse_contexts}`
- Rendering happens in `frontend/src/components/IocPreview.tsx`:
  - **Pulse Intelligence Context** cards show threat-level details per pulse.
  - IOC table shows multi-pulse overlap using `related_pulse_count` and related pulse tooltips.
  - Indicator detail modal lists all related pulses for the selected IOC.
- Why some values can still be `Unknown` / `Unclassified`:
  - OTX does not guarantee every field on every pulse.
  - The app intentionally uses safe fallbacks when data is missing.

### Dashboard and History
- API connection status indicator
- IOC statistics with charts (counts by type)
- Recent searches (stored in browser localStorage)
- Export history with re-download links

---

## How It Works

```
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│   React Frontend    │  HTTP   │   FastAPI Backend   │  REST   │   AlienVault OTX    │
│   (Vite + Tailwind) │ ──────► │   (Python)          │ ──────► │   API               │
│                     │         │                     │         │                     │
│  • Dashboard        │         │  • Search service   │         │  • Pulses           │
│  • Global Search    │         │  • IOC dumper       │         │  • Indicators       │
│  • Pulse Viewer     │         │  • Export service   │         │  • Reputation       │
│  • IOC Dumper       │         │  • TTL caching      │         │  • Passive DNS      │
│  • Export History   │         │  • Retry + logging  │         │  • Geolocation      │
└─────────────────────┘         └─────────────────────┘         └─────────────────────┘
```

1. You enter a search term or pulse ID in the frontend.
2. The backend detects the input type and queries OTX.
3. Results are normalized, cached, and returned as JSON.
4. For IOC dumps, the backend fetches indicators from multiple pulses, deduplicates them, and applies filters.
5. Exports are generated server-side and downloaded through the browser.

Your OTX API key stays on the server in a `.env` file and is never exposed to the browser.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python), OTXv2 SDK, Pydantic, openpyxl |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| State / data | TanStack Query, browser localStorage |
| Charts | Recharts |

---

## Project Structure

```
OTX/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # REST endpoints (health, search, pulses, iocs, exports)
│   │   ├── core/             # Logging, exception handling
│   │   ├── models/           # Pydantic request/response schemas
│   │   └── services/         # OTX client, indicator detector, IOC dumper, export
│   ├── exports/              # Ephemeral export files (auto-cleaned)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/              # Axios API client
│       ├── components/       # Layout, tables, status badge, charts
│       ├── hooks/            # localStorage persistence
│       ├── pages/            # Dashboard, Search, Pulse Viewer, IOC Dumper, Export History
│       └── types/            # TypeScript interfaces
├── otx_retrieval.py          # Legacy CLI script (uses .env for API key)
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An AlienVault OTX account and API key

### 1. Obtain an OTX API Key

1. Sign in at [https://otx.alienvault.com](https://otx.alienvault.com).
2. Go to **Settings** → **API Integration** (or your account API section).
3. Copy your API key.

### 2. Backend Setup

```bash
cd backend
python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` and set your key:

```env
OTX_API_KEY=your_key_here
```

Start the API server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### 3. Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Usage Walkthrough

### Search for a threat indicator

1. Open **Global Search**.
2. Enter an IP, domain, hash, CVE, or keyword (e.g. `emotet` or `8.8.8.8`).
3. The app auto-detects the input type and shows matching pulses and indicator details.

### Investigate a pulse

1. Open **Pulse Viewer**.
2. Search for a topic (e.g. `ransomware`).
3. Review pulse metadata: author, tags, TLP, MITRE ATT&CK IDs, and indicator count.

### Dump and export IOCs

1. Open **IOC Dumper**.
2. Enter one or more pulse IDs and/or a keyword search.
3. Choose a type filter (e.g. `ip`, `domains`, `all`).
4. Click **Dump IOCs** to preview the merged, deduplicated results.
5. Export as CSV, JSON, or Excel in Basic or Extended mode.
6. Re-download past exports from **Export History**.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Check OTX API connection status |
| `GET` | `/api/search?q=...` | Global search with auto-detection |
| `GET` | `/api/pulses/search?q=...` | Search OTX pulses |
| `GET` | `/api/pulses/{id}` | Get pulse details |
| `GET` | `/api/pulses/{id}/indicators` | List indicators in a pulse |
| `POST` | `/api/iocs/dump` | Dump, merge, dedupe, and filter IOCs |
| `POST` | `/api/iocs/export` | Generate CSV/JSON/Excel export |
| `GET` | `/api/exports/{id}/download` | Download a generated export file |

---

## Configuration

All backend settings are in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `OTX_API_KEY` | *(required)* | Your AlienVault OTX API key |
| `OTX_SERVER` | `https://otx.alienvault.com` | OTX API base URL |
| `CACHE_TTL_SECONDS` | `600` | How long to cache OTX responses (seconds) |
| `EXPORT_RETENTION_HOURS` | `24` | How long export files are kept before cleanup |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **API Error / Invalid key** | Verify `OTX_API_KEY` in `backend/.env` and restart the backend |
| **No pulses or IOCs returned** | Try broader search terms or confirm the pulse ID is valid (24-character hex) |
| **Rate limit errors** | Wait a moment and retry; the SDK retries automatically on 429/5xx |
| **Export download not found** | Export files are ephemeral; re-run the export if the retention period has passed |
| **CORS errors** | Ensure the frontend URL matches `CORS_ORIGINS` in `.env` |

---

## License

This project is for educational and research purposes. AlienVault OTX data is subject to [OTX terms of use](https://otx.alienvault.com).
