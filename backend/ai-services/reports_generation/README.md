# Reports Generation Module

**Module:** `reports_generation/`  
**Task:** 3 — Automated Reports Generation  
**Owner:** Abdallah Waleed (AI & Analytics Lead)  
**Status:** ✅ Complete — 57 tests passing

---

## Purpose

Generates automated PDF, Excel, and JSON safety and operational reports for factory management. Reuses `WorkforceAnalyticsService` from Task 1 — no calculation duplication.

---

## Architecture

```
reports_generation/
├── config.py                   ← DATABASE_URL, storage paths, defaults
├── exceptions.py               ← ReportBaseException hierarchy
├── schemas.py                  ← ReportType, ReportFormat, ReportMetadata, all data models
├── repositories.py             ← ReportRepository (read-only DB queries)
├── services/
│   ├── report_data_service.py  ← Fetches & assembles domain data (reuses WorkforceAnalyticsService)
│   ├── report_export_service.py← Dispatches to PDF/Excel/JSON generators
│   └── report_service.py       ← ReportService facade + get_report_service() singleton
├── generators/
│   ├── pdf_generator.py        ← ReportLab 4.4.10 PDF generation for all 4 report types
│   └── excel_generator.py      ← openpyxl Excel generation for all 4 report types
├── api_contracts/
│   ├── requests.py             ← GenerateReportRequest, ReportFilterParams
│   └── responses.py            ← GenerateReportResponse, ReportListResponse, ReportDownloadResponse
└── tests/                      ← 57 unit tests (no DB required)
```

---

## Supported Report Types

| Report Type | Enum Value | Description |
|---|---|---|
| Workforce | `workforce` | Attendance, productivity (proxy), incident correlation |
| Incident | `incident` | Severity breakdown, resolution rates, incident list |
| Camera Coverage | `camera_coverage` | Active cameras, coverage %, unobserved gaps |
| Comprehensive Safety | `comprehensive_safety` | Composite health score across all domains |

## Supported Formats

| Format | MIME Type |
|---|---|
| `pdf` | `application/pdf` |
| `excel` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `json` | `application/json` |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | from `.env` | PostgreSQL connection string |
| `DEFAULT_FACTORY_ID` | `aaaaaaaa-0001-0001-0001-000000000001` | Default factory scope |
| `REPORTS_STORAGE_DIR` | `storage/reports/` | Where generated files are written |
| `DEFAULT_REPORT_FORMAT` | `pdf` | Default format when none specified |

---

## Usage

```python
from reports_generation.services.report_service import get_report_service
from reports_generation.schemas import ReportType, ReportFormat
from uuid import UUID

svc = get_report_service()
meta = svc.generate_report(
    report_type=ReportType.WORKFORCE,
    format=ReportFormat.PDF,
    factory_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
    date_from=date(2027, 1, 1),
    date_to=date(2027, 1, 31),
)

print(f"Generated: {meta.file_name} ({meta.file_size_bytes / 1024:.1f} KB)")
print(f"Saved to:  {meta.file_path}")
```

---

## API Contracts (for Seif — FastAPI Integration)

### POST `/api/v1/reports/generate`
```json
// Request body
{
  "report_type": "workforce",
  "format": "pdf",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "date_from": "2027-01-01",
  "date_to": "2027-01-31"
}

// Response: GenerateReportResponse
{
  "success": true,
  "message": "Report generated successfully.",
  "data": {
    "report_id": "REP-20270115-A1B2C3",
    "report_type": "workforce",
    "format": "pdf",
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "title": "Workforce Report",
    "generated_at": "2027-01-15T10:00:00+00:00",
    "date_from": "2027-01-01",
    "date_to": "2027-01-31",
    "file_name": "workforce_REP-20270115-A1B2C3.pdf",
    "file_size_bytes": 48320,
    "mime_type": "application/pdf",
    "has_proxy_metrics": true,
    "disclaimer": "DISCLAIMER: Attendance and productivity indicators..."
  }
}
```

### GET `/api/v1/reports`
```python
# Seif: use ReportListResponse
from reports_generation.api_contracts.responses import ReportListResponse
from reports_generation.api_contracts.requests import ReportFilterParams
```

### GET `/api/v1/reports/{report_id}/download`
```python
# Seif: use ReportDownloadResponse to get the file path, then stream it
meta = svc.get_report(report_id)
file_path = svc.get_report_file_path(report_id)
# return FileResponse(path=str(file_path), media_type=meta.mime_type, filename=meta.file_name)
```

---

## Taqi — Frontend Integration Examples

```typescript
// Generate a workforce PDF report
const response = await fetch('/api/v1/reports/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    report_type: 'workforce',
    format: 'pdf',
    factory_id: 'aaaaaaaa-0001-0001-0001-000000000001',
    date_from: '2027-01-01',
    date_to: '2027-01-31',
  }),
});
const { data } = await response.json();
// data.report_id → use for download
// data.file_name → display to user

// Download the report
window.open(`/api/v1/reports/${data.report_id}/download`);
```

---

## Proxy Metric Disclaimer

> **DISCLAIMER:** Attendance and productivity indicators in this report are proxy metrics algorithmically estimated from safety incident interaction telemetry and supervisor resolution logs. They do NOT constitute verified timecard attendance, biometric records, or mechanical output tracking.

All report models with proxy data include `has_proxy_metrics: true` and the full `disclaimer` text.

---

## Security Notes

- Reports are written to `storage/reports/` which is in `.gitignore` — never committed.
- No user-supplied filenames are used; filenames are generated from `{report_type}_{report_id}.{ext}`.
- DB queries are read-only (SELECT only). No INSERT/UPDATE/DELETE in repositories.

---

## Running Tests

```powershell
# From backend/ai-services/
$env:PYTHONPATH="."
C:\Users\AbdallahWaleed\AppData\Local\Programs\Python\Python314\python.exe -m unittest discover -s reports_generation/tests -p "test_*.py" -v
```

## Running the Demo

```powershell
# Requires real DB connection
$env:PYTHONPATH="."
C:\Users\AbdallahWaleed\AppData\Local\Programs\Python\Python314\python.exe integration/reports_demo.py
```
