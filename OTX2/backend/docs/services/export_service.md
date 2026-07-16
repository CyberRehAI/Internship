# export_service.py — Export Service

**File:** `app/services/export_service.py`  
**Class:** `ExportService`

## What is this file for?

After IOCs are dumped, analysts often need a **file** they can open in Excel, import into a SIEM, or share.

This service:

1. Takes a list of IOC records (from the dumper or frontend).
2. Writes them to **CSV**, **JSON**, or **Excel (.xlsx)**.
3. Saves the file in the `backend/exports/` folder.
4. Returns a download link for the frontend.
5. Can **delete old files** so disk does not fill up.

## Folder: `backend/exports/`

- Each export gets a unique filename: `{uuid}.csv` (or `.json` / `.xlsx`).
- Files are temporary — cleaned up after `EXPORT_RETENTION_HOURS` (default 24h).
- Cleanup runs when the server **starts** (`main.py` lifespan).

## Export modes

### Basic mode

Three columns only:

- IOC Type  
- IOC Value  
- Description  

Good for quick block lists.

### Extended mode

Basic columns **plus**:

- Pulse Name  
- Author  
- Created Date  
- Tags  
- References  
- Malware Family  
- MITRE ATT&CK Mapping  
- TLP  

Good for full threat intelligence reports.

List fields (tags, references, etc.) are joined with `"; "` in CSV/Excel cells.

## Code walkthrough

### `__init__(export_dir, retention_hours)`

- Remembers where to save files (`exports/`).
- Remembers how long to keep them.
- Creates the export folder if it does not exist.

### `_columns(mode)`

Returns which database fields map to which column headers.  
Internal format: `[("Column Title", "field_name"), ...]`.

### `_row_for_columns(item, columns)`

Builds one row of text values for a single IOC:

- Plain strings as-is.
- Lists (tags, references) → joined with `"; "`.
- Missing values → empty string.

### `export(iocs, mode, export_format)`

Main method:

1. Generate a UUID for the file name.
2. Pick columns based on `mode` (basic vs extended).
3. Write the file:
   - **csv** — Python `csv` module, UTF-8
   - **json** — array of objects, pretty-printed
   - **xlsx** — `openpyxl` workbook with header row + data rows
4. Return metadata:

```json
{
  "export_id": "uuid-here",
  "filename": "uuid-here.csv",
  "format": "csv",
  "mode": "extended",
  "ioc_count": 142,
  "created_at": "2026-07-08T...",
  "download_url": "/api/exports/{uuid}/download"
}
```

### `get_export_path(export_id)`

- Tries `.csv`, `.json`, `.xlsx` extensions.
- Returns the `Path` if the file exists, else `None`.
- Used by the download route.

### `cleanup_old_exports()`

- Lists all files in `exports/`.
- Compares file modification time to `retention_hours`.
- Deletes files older than the threshold.
- Returns how many files were removed.

## Who uses this?

| Caller | Endpoint |
|---|---|
| `exports.py` route | `POST /api/iocs/export` |
| `exports.py` route | `GET /api/exports/{id}/download` |
| `main.py` lifespan | cleanup on startup |

## Flow example

```
1. Frontend dumps IOCs → gets JSON list
2. User clicks "Export CSV (Extended)"
3. POST /api/iocs/export with iocs + mode + format
4. ExportService.export() writes exports/abc-123.csv
5. Frontend shows download link
6. GET /api/exports/abc-123/download → browser downloads file
```

## Error cases

- Unsupported `format` → raises `ValueError` (should not happen if frontend sends valid values).
- Download unknown `export_id` → route returns HTTP 404.
- File expired after retention → 404; user must export again.

## Dependencies

- **csv**, **json** — built into Python  
- **openpyxl** — Excel support (`requirements.txt`)
