import csv
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook


class ExportService:
    def __init__(self, export_dir: Path, retention_hours: int) -> None:
        self.export_dir = export_dir
        self.retention_hours = retention_hours
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _columns(self, mode: str) -> list[tuple[str, str]]:
        basic = [
            ("IOC Type", "type"),
            ("IOC Value", "value"),
            ("Description", "description"),
        ]
        if mode == "basic":
            return basic
        return basic + [
            ("Pulse Name", "pulse_name"),
            ("Author", "author"),
            ("Created Date", "created"),
            ("Tags", "tags"),
            ("References", "references"),
            ("Malware Family", "malware_families"),
            ("MITRE ATT&CK Mapping", "attack_ids"),
            ("TLP", "tlp"),
        ]

    def _row_for_columns(self, item: dict, columns: list[tuple[str, str]]) -> list[str]:
        row: list[str] = []
        for _, key in columns:
            value = item.get(key, "")
            if isinstance(value, list):
                row.append("; ".join(str(v) for v in value))
            else:
                row.append(str(value or ""))
        return row

    def export(self, iocs: list[dict], mode: str, export_format: str) -> dict:
        export_id = str(uuid.uuid4())
        filename = f"{export_id}.{export_format}"
        file_path = self.export_dir / filename
        columns = self._columns(mode)
        headers = [header for header, _ in columns]

        if export_format == "csv":
            with file_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                for item in iocs:
                    writer.writerow(self._row_for_columns(item, columns))
        elif export_format == "json":
            json_rows = [dict(zip(headers, self._row_for_columns(item, columns))) for item in iocs]
            file_path.write_text(json.dumps(json_rows, indent=2), encoding="utf-8")
        elif export_format == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(headers)
            for item in iocs:
                sheet.append(self._row_for_columns(item, columns))
            workbook.save(file_path)
        else:
            raise ValueError("Unsupported export format")

        created_at = datetime.now(UTC)
        return {
            "export_id": export_id,
            "filename": filename,
            "format": export_format,
            "mode": mode,
            "ioc_count": len(iocs),
            "created_at": created_at,
            "download_url": f"/api/exports/{export_id}/download",
        }

    def get_export_path(self, export_id: str) -> Path | None:
        for ext in ("csv", "json", "xlsx"):
            candidate = self.export_dir / f"{export_id}.{ext}"
            if candidate.exists():
                return candidate
        return None

    def cleanup_old_exports(self) -> int:
        threshold = datetime.now(UTC) - timedelta(hours=self.retention_hours)
        removed = 0
        for file in self.export_dir.glob("*.*"):
            modified = datetime.fromtimestamp(file.stat().st_mtime, tz=UTC)
            if modified < threshold:
                file.unlink(missing_ok=True)
                removed += 1
        return removed
