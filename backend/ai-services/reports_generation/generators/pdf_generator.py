"""
reports_generation/generators/pdf_generator.py
Industrial-grade PDF report generator for Operix Safety Platform using ReportLab.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..exceptions import ReportExportError
from ..schemas import (
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
    IncidentReportData,
    WorkforceReportData,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))

        # Footer line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 45, 572, 45)

        # Footer text
        footer_text = "Operix Industrial AI Safety Platform — Confidential"
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(40, 32, footer_text)
        self.drawRightString(572, 32, page_str)
        self.restoreState()


class PDFReportGenerator:
    """Generates styled industrial safety PDF reports."""

    PRIMARY_COLOR = colors.HexColor("#1A365D")    # Dark Navy
    SECONDARY_COLOR = colors.HexColor("#2B6CB0")  # Industrial Blue
    ACCENT_COLOR = colors.HexColor("#C53030")     # Warning Red
    NEUTRAL_DARK = colors.HexColor("#2D3748")
    NEUTRAL_LIGHT = colors.HexColor("#F7FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        self.styles.add(
            ParagraphStyle(
                name="OperixTitle",
                parent=self.styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=self.PRIMARY_COLOR,
                spaceAfter=4,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="OperixSubtitle",
                parent=self.styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#4A5568"),
                spaceAfter=12,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeading",
                parent=self.styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                textColor=self.SECONDARY_COLOR,
                spaceBefore=10,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="DisclaimerText",
                parent=self.styles["Normal"],
                fontName="Helvetica-Oblique",
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#742A2A"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="TableCell",
                parent=self.styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=self.NEUTRAL_DARK,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=self.styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=12,
                textColor=colors.white,
            )
        )

    def _build_header(self, title: str, subtitle: str) -> List[Any]:
        elements: List[Any] = [
            Paragraph(f"OPERIX // {title.upper()}", self.styles["OperixTitle"]),
            Paragraph(subtitle, self.styles["OperixSubtitle"]),
            HRFlowable(width="100%", thickness=1.5, color=self.SECONDARY_COLOR, spaceAfter=14),
        ]
        return elements

    def _build_disclaimer_box(self, disclaimer_text: str) -> Table:
        p = Paragraph(f"<b>NOTE / PROXY DISCLAIMER:</b> {disclaimer_text}", self.styles["DisclaimerText"])
        t = Table([[p]], colWidths=[532])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),
                ("BORDER", (0, 0), (-1, -1), 0.75, colors.HexColor("#FEB2B2")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        return t

    def _build_meta_table(self, factory_name: str, generated_at: str, date_span: str) -> Table:
        data = [
            [
                Paragraph("<b>Plant Facility:</b>", self.styles["TableCell"]),
                Paragraph(factory_name, self.styles["TableCell"]),
                Paragraph("<b>Report Generated:</b>", self.styles["TableCell"]),
                Paragraph(generated_at, self.styles["TableCell"]),
            ],
            [
                Paragraph("<b>Reporting Period:</b>", self.styles["TableCell"]),
                Paragraph(date_span, self.styles["TableCell"]),
                Paragraph("<b>Platform Status:</b>", self.styles["TableCell"]),
                Paragraph("Operational (Verified DB)", self.styles["TableCell"]),
            ],
        ]
        t = Table(data, colWidths=[110, 160, 110, 152])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), self.NEUTRAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )
        return t

    def generate_workforce_pdf(self, data: WorkforceReportData, target_path: Path) -> Path:
        """Render Workforce report to PDF."""
        try:
            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=55,
            )
            story: List[Any] = []

            # Header
            date_span = f"{data.date_from or 'All-Time'} to {data.date_to or 'Present'}"
            story.extend(self._build_header("Workforce Analytics Report", "Factory Labor & Safety Operational Overview"))

            # Meta Table
            story.append(self._build_meta_table(data.factory_info.name, data.generated_at.strftime("%Y-%m-%d %H:%M UTC"), date_span))
            story.append(Spacer(1, 12))

            # Disclaimer
            story.append(self._build_disclaimer_box(data.disclaimer))
            story.append(Spacer(1, 14))

            # 1. Workforce Distribution
            story.append(Paragraph("1. Workforce Distribution & Headcount", self.styles["SectionHeading"]))
            overview = data.overview
            wf_table_data = [
                [Paragraph("Metric", self.styles["TableHeader"]), Paragraph("Count / Value", self.styles["TableHeader"]), Paragraph("Description", self.styles["TableHeader"])],
                [Paragraph("Total Registered Users", self.styles["TableCell"]), Paragraph(str(overview.get("total_users", "-")), self.styles["TableCell"]), Paragraph("Total platform user accounts", self.styles["TableCell"])],
                [Paragraph("Active Workers", self.styles["TableCell"]), Paragraph(str(overview.get("active_workers", "-")), self.styles["TableCell"]), Paragraph("Workers currently eligible for shifts", self.styles["TableCell"])],
                [Paragraph("Active Admins", self.styles["TableCell"]), Paragraph(str(overview.get("active_admins", "-")), self.styles["TableCell"]), Paragraph("System and plant administrative leads", self.styles["TableCell"])],
                [Paragraph("Active Managers", self.styles["TableCell"]), Paragraph(str(overview.get("active_managers", "-")), self.styles["TableCell"]), Paragraph("Operational supervisors and coordinators", self.styles["TableCell"])],
                [Paragraph("Inactive / Disabled Users", self.styles["TableCell"]), Paragraph(str(overview.get("inactive_users", "-")), self.styles["TableCell"]), Paragraph("Dormant or decommissioned records", self.styles["TableCell"])],
            ]
            t_wf = Table(wf_table_data, colWidths=[180, 100, 252])
            t_wf.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.NEUTRAL_LIGHT]),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_wf)
            story.append(Spacer(1, 14))

            # 2. Attendance & Productivity Proxy Summary
            story.append(Paragraph("2. Operational Indicators (Proxy Derivations)", self.styles["SectionHeading"]))
            att = data.attendance_proxy
            prod = data.productivity_proxy
            proxy_table_data = [
                [Paragraph("Proxy Indicator", self.styles["TableHeader"]), Paragraph("Observed Value", self.styles["TableHeader"]), Paragraph("Algorithmic Basis", self.styles["TableHeader"])],
                [Paragraph("Activity Proxy Rate", self.styles["TableCell"]), Paragraph(f"{att.get('activity_rate', 0.0)}%", self.styles["TableCell"]), Paragraph("Interaction events / eligible active members", self.styles["TableCell"])],
                [Paragraph("Average Actions / Worker", self.styles["TableCell"]), Paragraph(str(prod.get("avg_actions_per_worker", "-")), self.styles["TableCell"]), Paragraph("Mean safety resolutions per worker", self.styles["TableCell"])],
                [Paragraph("Low Activity Workers Flagged", self.styles["TableCell"]), Paragraph(str(len(prod.get("low_performers", []))), self.styles["TableCell"]), Paragraph("Under configurable threshold", self.styles["TableCell"])],
            ]
            t_proxy = Table(proxy_table_data, colWidths=[180, 100, 252])
            t_proxy.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.SECONDARY_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.NEUTRAL_LIGHT]),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_proxy)

            doc.build(story, canvasmaker=NumberedCanvas)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Workforce PDF: {exc}") from exc

    def generate_incident_pdf(self, data: IncidentReportData, target_path: Path) -> Path:
        """Render Incident report to PDF."""
        try:
            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=55,
            )
            story: List[Any] = []

            date_span = f"{data.date_from or 'All-Time'} to {data.date_to or 'Present'}"
            story.extend(self._build_header("Incident Analytics Report", "Safety Violations, Intrusions & Resolution Audits"))
            story.append(self._build_meta_table(data.factory_info.name, data.generated_at.strftime("%Y-%m-%d %H:%M UTC"), date_span))
            story.append(Spacer(1, 14))

            # Key KPI Summary
            story.append(Paragraph("1. Incident Summary KPI Matrix", self.styles["SectionHeading"]))
            kpi_data = [
                [Paragraph("Total Logged Incidents", self.styles["TableHeader"]), Paragraph("Resolution Rate", self.styles["TableHeader"]), Paragraph("Avg Resolution Time", self.styles["TableHeader"])],
                [
                    Paragraph(f"<b>{data.total_incidents}</b>", self.styles["TableCell"]),
                    Paragraph(f"<b>{data.resolution_rate * 100.0:.1f}%</b>", self.styles["TableCell"]),
                    Paragraph(f"<b>{data.avg_resolution_time_minutes:.1f} mins</b>", self.styles["TableCell"]),
                ],
            ]
            t_kpi = Table(kpi_data, colWidths=[177, 177, 178])
            t_kpi.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ("BACKGROUND", (0, 1), (-1, 1), self.NEUTRAL_LIGHT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t_kpi)
            story.append(Spacer(1, 14))

            # Severity Breakdown
            story.append(Paragraph("2. Severity Classification Breakdown", self.styles["SectionHeading"]))
            sev_rows = [
                [Paragraph("Severity Tier", self.styles["TableHeader"]), Paragraph("Incident Count", self.styles["TableHeader"]), Paragraph("Risk Impact", self.styles["TableHeader"])],
            ]
            for sev, count in sorted(data.severity_breakdown.items()):
                sev_rows.append([
                    Paragraph(sev.upper(), self.styles["TableCell"]),
                    Paragraph(str(count), self.styles["TableCell"]),
                    Paragraph("Immediate Action Required" if sev in ("critical", "high") else "Standard Protocol", self.styles["TableCell"]),
                ])
            t_sev = Table(sev_rows, colWidths=[180, 100, 252])
            t_sev.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.SECONDARY_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.NEUTRAL_LIGHT]),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_sev)
            story.append(Spacer(1, 14))

            # Recent Incidents Table
            if data.incidents_list:
                story.append(Paragraph("3. Logged Incident History (Sample)", self.styles["SectionHeading"]))
                rec_rows = [
                    [Paragraph("ID", self.styles["TableHeader"]), Paragraph("Type", self.styles["TableHeader"]), Paragraph("Severity", self.styles["TableHeader"]), Paragraph("State", self.styles["TableHeader"]), Paragraph("Opened At", self.styles["TableHeader"])],
                ]
                for inc in data.incidents_list[:12]:
                    rec_rows.append([
                        Paragraph(inc["incident_id"], self.styles["TableCell"]),
                        Paragraph(inc["type"], self.styles["TableCell"]),
                        Paragraph(inc["severity"].upper(), self.styles["TableCell"]),
                        Paragraph(inc["state"], self.styles["TableCell"]),
                        Paragraph(inc["opened_at"], self.styles["TableCell"]),
                    ])
                t_rec = Table(rec_rows, colWidths=[90, 130, 80, 90, 142])
                t_rec.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                    ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.NEUTRAL_LIGHT]),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t_rec)

            doc.build(story, canvasmaker=NumberedCanvas)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Incident PDF: {exc}") from exc

    def generate_camera_coverage_pdf(self, data: CameraCoverageReportData, target_path: Path) -> Path:
        """Render Camera Coverage report to PDF."""
        try:
            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=55,
            )
            story: List[Any] = []

            story.extend(self._build_header("Camera Coverage & Blindspot Audit", "Surveillance Telemetry & Unobserved Gap Analysis"))
            story.append(self._build_meta_table(data.factory_info.name, data.generated_at.strftime("%Y-%m-%d %H:%M UTC"), "Current Snapshot"))
            story.append(Spacer(1, 14))

            # Coverage KPI
            story.append(Paragraph("1. Surveillance Asset Health", self.styles["SectionHeading"]))
            kpi_data = [
                [Paragraph("Total Provisioned Cameras", self.styles["TableHeader"]), Paragraph("Active Streaming", self.styles["TableHeader"]), Paragraph("Coverage Rate", self.styles["TableHeader"])],
                [
                    Paragraph(f"<b>{data.total_cameras}</b>", self.styles["TableCell"]),
                    Paragraph(f"<b>{data.active_cameras}</b>", self.styles["TableCell"]),
                    Paragraph(f"<b>{data.coverage_percentage:.1f}%</b>", self.styles["TableCell"]),
                ],
            ]
            t_kpi = Table(kpi_data, colWidths=[177, 177, 178])
            t_kpi.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ("BACKGROUND", (0, 1), (-1, 1), self.NEUTRAL_LIGHT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t_kpi)
            story.append(Spacer(1, 14))

            # Camera Table
            story.append(Paragraph("2. Camera Inventory & Operational Status", self.styles["SectionHeading"]))
            cam_rows = [
                [Paragraph("Camera Name", self.styles["TableHeader"]), Paragraph("Status", self.styles["TableHeader"]), Paragraph("Active State", self.styles["TableHeader"])],
            ]
            for cam in data.per_camera_status:
                cam_rows.append([
                    Paragraph(cam.get("name", "Unknown"), self.styles["TableCell"]),
                    Paragraph(str(cam.get("status", "unknown")).upper(), self.styles["TableCell"]),
                    Paragraph("ONLINE" if cam.get("is_active") else "OFFLINE", self.styles["TableCell"]),
                ])
            t_cam = Table(cam_rows, colWidths=[200, 160, 172])
            t_cam.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.SECONDARY_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.NEUTRAL_LIGHT]),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_cam)

            doc.build(story, canvasmaker=NumberedCanvas)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Camera Coverage PDF: {exc}") from exc

    def generate_comprehensive_safety_pdf(self, data: ComprehensiveSafetyReportData, target_path: Path) -> Path:
        """Render Comprehensive Safety report to PDF."""
        try:
            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=55,
            )
            story: List[Any] = []

            date_span = f"{data.date_from or 'All-Time'} to {data.date_to or 'Present'}"
            story.extend(self._build_header("Comprehensive Safety Audit", "Plant-Wide Safety Health, Incidents & Surveillance Synthesis"))
            story.append(self._build_meta_table(data.factory_info.name, data.generated_at.strftime("%Y-%m-%d %H:%M UTC"), date_span))
            story.append(Spacer(1, 12))

            # Disclaimer
            story.append(self._build_disclaimer_box(data.disclaimer))
            story.append(Spacer(1, 14))

            # Composite Safety Score
            story.append(Paragraph("1. Plant Safety Health Index", self.styles["SectionHeading"]))
            score_color = colors.HexColor("#22543D") if data.safety_health_score >= 80 else colors.HexColor("#742A2A")
            score_data = [
                [Paragraph("Composite Safety Index", self.styles["TableHeader"]), Paragraph("Active Safety Rules", self.styles["TableHeader"]), Paragraph("Evaluation", self.styles["TableHeader"])],
                [
                    Paragraph(f"<font size=14 color='{score_color}'><b>{data.safety_health_score}/100</b></font>", self.styles["TableCell"]),
                    Paragraph(f"<b>{data.active_safety_rules_count} Rules</b>", self.styles["TableCell"]),
                    Paragraph("High Compliance" if data.safety_health_score >= 80 else "Attention Recommended", self.styles["TableCell"]),
                ],
            ]
            t_score = Table(score_data, colWidths=[177, 177, 178])
            t_score.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ("BACKGROUND", (0, 1), (-1, 1), self.NEUTRAL_LIGHT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t_score)
            story.append(Spacer(1, 14))

            # Cross-Domain Summary Table
            story.append(Paragraph("2. Operational Subsystems Snapshot", self.styles["SectionHeading"]))
            wf = data.workforce_overview
            inc = data.incident_analytics
            cov = data.camera_coverage
            matrix_data = [
                [Paragraph("Subsystem", self.styles["TableHeader"]), Paragraph("Key Indicator", self.styles["TableHeader"]), Paragraph("Status / Volume", self.styles["TableHeader"])],
                [Paragraph("Surveillance Coverage", self.styles["TableCell"]), Paragraph(f"{cov.get('active_cameras', 0)}/{cov.get('total_cameras', 0)} cameras online", self.styles["TableCell"]), Paragraph(f"{cov.get('coverage_percentage', 0)}% coverage", self.styles["TableCell"])],
                [Paragraph("Incident Management", self.styles["TableCell"]), Paragraph(f"{inc.get('total_incidents', 0)} logged incidents", self.styles["TableCell"]), Paragraph(f"{inc.get('resolution_rate', 0.0) * 100:.1f}% resolved", self.styles["TableCell"])],
                [Paragraph("Workforce Base", self.styles["TableCell"]), Paragraph(f"{wf.get('active_workers', 0)} active workers", self.styles["TableCell"]), Paragraph(f"{wf.get('total_users', 0)} total users", self.styles["TableCell"])],
            ]
            t_matrix = Table(matrix_data, colWidths=[180, 180, 172])
            t_matrix.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.SECONDARY_COLOR),
                ("BOX", (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.NEUTRAL_LIGHT]),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t_matrix)

            doc.build(story, canvasmaker=NumberedCanvas)
            return target_path
        except Exception as exc:
            raise ReportExportError(f"Failed to generate Comprehensive Safety PDF: {exc}") from exc
