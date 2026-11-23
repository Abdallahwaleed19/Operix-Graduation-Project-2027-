"""
reports_generation/generators/excel_generator.py
Structured Excel workbook generator for Operix Safety Platform using openpyxl.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..exceptions import ReportExportError
from ..schemas import (
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
    IncidentReportData,
    WorkforceReportData,
)


class ExcelReportGenerator:
    """Generates styled multi-tab industrial safety Excel workbooks."""

    # Brand Colors
    HEADER_FILL = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    SUBHEADER_FILL = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    DISCLAIMER_FILL = PatternFill(start_color="FFF5F5", end_color="FFF5F5", fill_type="solid")

    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Calibri", size=16, bold=True, color="1A365D")
    SECTION_FONT = Font(name="Calibri", size=13, bold=True, color="2B6CB0")
    DISCLAIMER_FONT = Font(name="Calibri", size=9, italic=True, color="742A2A")
    REGULAR_FONT = Font(name="Calibri", size=10)
    BOLD_FONT = Font(name="Calibri", size=10, bold=True)

    THIN_BORDER = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    def _auto_fit_columns(self, ws: Any) -> None:
        """Adjust column widths dynamically."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                # Skip merged or very long title/disclaimer cells when measuring
                if len(val) < 60:
                    max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    def _apply_disclaimer(self, ws: Any, row: int, text: str) -> int:
        """Render disclaimer banner spanning columns A-E."""
        ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=5)
        cell = ws.cell(row=row, column=1)
        cell.value = f"NOTE / PROXY DISCLAIMER: {text}"
        cell.font = self.DISCLAIMER_FONT
        cell.fill = self.DISCLAIMER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        return row + 3

    def generate_workforce_excel(self, data: WorkforceReportData, target_path: Path) -> Path:
        """Render Workforce report to Excel workbook."""
        try:
            wb = openpyxl.Workbook()
            ws_summary = wb.active
            ws_summary.title = "Workforce Summary"
            ws_summary.views.sheetView[0].showGridLines = True

            # Title Block
            ws_summary["A1"] = f"OPERIX // WORKFORCE REPORT — {data.factory_info.name.upper()}"
            ws_summary["A1"].font = self.TITLE_FONT
            ws_summary["A2"] = f"Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M UTC')} | Period: {data.date_from or 'All-Time'} to {data.date_to or 'Present'}"
            ws_summary["A2"].font = self.BOLD_FONT

            # Disclaimer
            cur_row = self._apply_disclaimer(ws_summary, 4, data.disclaimer)

            # Workforce Distribution
            ws_summary.cell(row=cur_row, column=1, value="Workforce Headcount Distribution").font = self.SECTION_FONT
            cur_row += 1

            headers = ["Metric Name", "Value / Count", "Description"]
            for col_idx, h in enumerate(headers, 1):
                c = ws_summary.cell(row=cur_row, column=col_idx, value=h)
                c.fill = self.HEADER_FILL
                c.font = self.HEADER_FONT
                c.alignment = Alignment(horizontal="center")
            cur_row += 1

            overview = data.overview
            rows = [
                ("Total Registered Users", overview.get("total_users", 0), "Platform database user accounts"),
                ("Active Workers", overview.get("active_workers", 0), "Workers eligible for factory floor shifts"),
                ("Active Administrators", overview.get("active_admins", 0), "System administrators"),
                ("Active Managers", overview.get("active_managers", 0), "Floor supervisors and department heads"),
                ("Inactive / Disabled Accounts", overview.get("inactive_users", 0), "Dormant user records"),
            ]
            for metric, val, desc in rows:
                ws_summary.cell(row=cur_row, column=1, value=metric).font = self.REGULAR_FONT
                ws_summary.cell(row=cur_row, column=2, value=val).font = self.BOLD_FONT
                ws_summary.cell(row=cur_row, column=3, value=desc).font = self.REGULAR_FONT
                for col_idx in range(1, 4):
                    ws_summary.cell(row=cur_row, column=col_idx).border = self.THIN_BORDER
                cur_row += 1

            cur_row += 2
            # Proxy Metrics Block
            ws_summary.cell(row=cur_row, column=1, value="Operational Proxy Indicators").font = self.SECTION_FONT
            cur_row += 1

            headers_proxy = ["Indicator", "Observed Value", "Proxy Basis"]
            for col_idx, h in enumerate(headers_proxy, 1):
                c = ws_summary.cell(row=cur_row, column=col_idx, value=h)
                c.fill = self.SUBHEADER_FILL
                c.font = self.HEADER_FONT
                c.alignment = Alignment(horizontal="center")
            cur_row += 1

            att = data.attendance_proxy
            prod = data.productivity_proxy
            proxy_rows = [
                ("Activity Proxy Rate", f"{att.get('activity_rate', 0.0)}%", "Calculated from safety incident interactions"),
                ("Average Actions per Worker", prod.get("avg_actions_per_worker", 0.0), "Mean safety resolution tasks per active member"),
                ("Low Activity Workers Flagged", len(prod.get("low_performers", [])), "Below threshold volume"),
            ]
            for ind, val, basis in proxy_rows:
                ws_summary.cell(row=cur_row, column=1, value=ind).font = self.REGULAR_FONT
                ws_summary.cell(row=cur_row, column=2, value=val).font = self.BOLD_FONT
                ws_summary.cell(row=cur_row, column=3, value=basis).font = self.REGULAR_FONT
                for col_idx in range(1, 4):
                    ws_summary.cell(row=cur_row, column=col_idx).border = self.THIN_BORDER
                cur_row += 1

            self._auto_fit_columns(ws_summary)
            wb.save(target_path)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Workforce Excel: {exc}") from exc

    def generate_incident_excel(self, data: IncidentReportData, target_path: Path) -> Path:
        """Render Incident report to Excel workbook with Summary & Detail tabs."""
        try:
            wb = openpyxl.Workbook()

            # Sheet 1: Summary
            ws1 = wb.active
            ws1.title = "Incident Summary"
            ws1.views.sheetView[0].showGridLines = True

            ws1["A1"] = f"OPERIX // INCIDENT REPORT — {data.factory_info.name.upper()}"
            ws1["A1"].font = self.TITLE_FONT
            ws1["A2"] = f"Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
            ws1["A2"].font = self.BOLD_FONT

            # KPIs
            headers = ["Total Incidents", "Resolution Rate", "Avg Resolution Time (Minutes)"]
            for idx, h in enumerate(headers, 1):
                c = ws1.cell(row=4, column=idx, value=h)
                c.fill = self.HEADER_FILL
                c.font = self.HEADER_FONT
            ws1.cell(row=5, column=1, value=data.total_incidents).font = self.BOLD_FONT
            ws1.cell(row=5, column=2, value=f"{data.resolution_rate * 100:.1f}%").font = self.BOLD_FONT
            ws1.cell(row=5, column=3, value=round(data.avg_resolution_time_minutes, 1)).font = self.BOLD_FONT
            for idx in range(1, 4):
                ws1.cell(row=5, column=idx).border = self.THIN_BORDER

            # Severity Breakdown
            ws1.cell(row=7, column=1, value="Severity Distribution").font = self.SECTION_FONT
            ws1.cell(row=8, column=1, value="Severity").fill = self.SUBHEADER_FILL
            ws1.cell(row=8, column=1).font = self.HEADER_FONT
            ws1.cell(row=8, column=2, value="Incident Count").fill = self.SUBHEADER_FILL
            ws1.cell(row=8, column=2).font = self.HEADER_FONT

            row = 9
            for sev, count in sorted(data.severity_breakdown.items()):
                ws1.cell(row=row, column=1, value=sev.upper()).font = self.REGULAR_FONT
                ws1.cell(row=row, column=2, value=count).font = self.BOLD_FONT
                ws1.cell(row=row, column=1).border = self.THIN_BORDER
                ws1.cell(row=row, column=2).border = self.THIN_BORDER
                row += 1

            self._auto_fit_columns(ws1)

            # Sheet 2: Incident Detail Records
            ws2 = wb.create_sheet(title="Incident Records")
            ws2.views.sheetView[0].showGridLines = True
            rec_headers = ["Incident Reference", "Incident Type", "Severity", "State", "Opened Timestamp"]
            for idx, h in enumerate(rec_headers, 1):
                c = ws2.cell(row=1, column=idx, value=h)
                c.fill = self.HEADER_FILL
                c.font = self.HEADER_FONT

            row2 = 2
            for inc in data.incidents_list:
                ws2.cell(row=row2, column=1, value=inc.get("incident_id")).font = self.REGULAR_FONT
                ws2.cell(row=row2, column=2, value=inc.get("type")).font = self.REGULAR_FONT
                ws2.cell(row=row2, column=3, value=str(inc.get("severity")).upper()).font = self.BOLD_FONT
                ws2.cell(row=row2, column=4, value=inc.get("state")).font = self.REGULAR_FONT
                ws2.cell(row=row2, column=5, value=inc.get("opened_at")).font = self.REGULAR_FONT
                for col_i in range(1, 6):
                    ws2.cell(row=row2, column=col_i).border = self.THIN_BORDER
                row2 += 1

            self._auto_fit_columns(ws2)
            wb.save(target_path)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Incident Excel: {exc}") from exc

    def generate_camera_coverage_excel(self, data: CameraCoverageReportData, target_path: Path) -> Path:
        """Render Camera Coverage report to Excel workbook."""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Camera Coverage"
            ws.views.sheetView[0].showGridLines = True

            ws["A1"] = f"OPERIX // CAMERA COVERAGE AUDIT — {data.factory_info.name.upper()}"
            ws["A1"].font = self.TITLE_FONT

            ws.cell(row=3, column=1, value="Total Cameras").fill = self.HEADER_FILL
            ws.cell(row=3, column=1).font = self.HEADER_FONT
            ws.cell(row=3, column=2, value="Active Streaming").fill = self.HEADER_FILL
            ws.cell(row=3, column=2).font = self.HEADER_FONT
            ws.cell(row=3, column=3, value="Coverage Percentage").fill = self.HEADER_FILL
            ws.cell(row=3, column=3).font = self.HEADER_FONT

            ws.cell(row=4, column=1, value=data.total_cameras).font = self.BOLD_FONT
            ws.cell(row=4, column=2, value=data.active_cameras).font = self.BOLD_FONT
            ws.cell(row=4, column=3, value=f"{data.coverage_percentage:.1f}%").font = self.BOLD_FONT
            for col_i in range(1, 4):
                ws.cell(row=4, column=col_i).border = self.THIN_BORDER

            # Inventory Table
            ws.cell(row=6, column=1, value="Surveillance Camera Inventory").font = self.SECTION_FONT
            cam_headers = ["Camera Name", "Status", "Stream State"]
            for idx, h in enumerate(cam_headers, 1):
                c = ws.cell(row=7, column=idx, value=h)
                c.fill = self.SUBHEADER_FILL
                c.font = self.HEADER_FONT

            r = 8
            for cam in data.per_camera_status:
                ws.cell(row=r, column=1, value=cam.get("name")).font = self.REGULAR_FONT
                ws.cell(row=r, column=2, value=str(cam.get("status")).upper()).font = self.BOLD_FONT
                ws.cell(row=r, column=3, value="ONLINE" if cam.get("is_active") else "OFFLINE").font = self.REGULAR_FONT
                for col_i in range(1, 4):
                    ws.cell(row=r, column=col_i).border = self.THIN_BORDER
                r += 1

            self._auto_fit_columns(ws)
            wb.save(target_path)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Camera Coverage Excel: {exc}") from exc

    def generate_comprehensive_safety_excel(self, data: ComprehensiveSafetyReportData, target_path: Path) -> Path:
        """Render Comprehensive Safety report to Excel workbook."""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Safety Health Audit"
            ws.views.sheetView[0].showGridLines = True

            ws["A1"] = f"OPERIX // COMPREHENSIVE SAFETY AUDIT — {data.factory_info.name.upper()}"
            ws["A1"].font = self.TITLE_FONT

            cur_row = self._apply_disclaimer(ws, 3, data.disclaimer)

            ws.cell(row=cur_row, column=1, value="Plant Safety Index").font = self.SECTION_FONT
            cur_row += 1

            ws.cell(row=cur_row, column=1, value="Safety Index Score").fill = self.HEADER_FILL
            ws.cell(row=cur_row, column=1).font = self.HEADER_FONT
            ws.cell(row=cur_row, column=2, value="Active Safety Rules").fill = self.HEADER_FILL
            ws.cell(row=cur_row, column=2).font = self.HEADER_FONT
            cur_row += 1

            ws.cell(row=cur_row, column=1, value=f"{data.safety_health_score}/100").font = self.BOLD_FONT
            ws.cell(row=cur_row, column=2, value=data.active_safety_rules_count).font = self.BOLD_FONT
            ws.cell(row=cur_row, column=1).border = self.THIN_BORDER
            ws.cell(row=cur_row, column=2).border = self.THIN_BORDER

            self._auto_fit_columns(ws)
            wb.save(target_path)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Comprehensive Safety Excel: {exc}") from exc
