"""
llm/remediation_engine.py
Agentic Remediation & Action Proposal Engine for Operix Industrial Safety Platform.

Analyzes retrieved industrial context, telemetry anomalies, and incident records
to synthesize actionable remediation steps (Human-in-the-Loop Actions).
"""
from __future__ import annotations

import re
from typing import List, Optional
from uuid import uuid4

from ..schemas.contracts import ProposedAction, RetrievedChunk


class RemediationEngine:
    """
    Intelligent rule-and-context driven remediation engine.
    Detects operational problems and proposes executable mitigations.
    """

    @classmethod
    def evaluate_actions(
        cls,
        question: str,
        retrieved_chunks: List[RetrievedChunk],
        language: str = "en",
    ) -> List[ProposedAction]:
        """
        Synthesize relevant ProposedAction objects from retrieved knowledge and user intent.
        """
        actions: List[ProposedAction] = []
        q_lower = question.lower()

        # Combine all chunk content for pattern detection
        full_content = " ".join([c.content for c in retrieved_chunks]).lower()

        # -------------------------------------------------------------------
        # 1. Camera Downtime & Maintenance Actions
        # -------------------------------------------------------------------
        camera_maintenance_detected = any(
            re.search(pattern, full_content)
            for pattern in [r"status:\s*inactive", r"maintenance", r"camera.*down", r"stream.*offline"]
        ) or any(w in q_lower for w in ["camera", "inactive", "maintenance", "كاميرا", "معطلة", "صيانة", "توقف"])

        if camera_maintenance_detected and any("camera" in c.content.lower() for c in retrieved_chunks):
            # Extract camera ID or name if available
            cam_match = re.search(r"camera\s+(?:name|telemetry)?:\s*([a-zA-Z0-9_\-]+)", full_content, re.IGNORECASE)
            cam_name = cam_match.group(1) if cam_match else "Maint-CAM-01"

            if language == "ar":
                actions.append(
                    ProposedAction(
                        action_id=f"act-maint-{uuid4().hex[:6]}",
                        action_type="maintenance",
                        title=f"إنشاء تذكرة صيانة عاجلة للكاميرا ({cam_name})",
                        description=f"إصدار إشعار تكليف فوري لقسم الصيانة والشبكات لفحص عطل الكاميرا {cam_name} وإعادة تشغيل البث.",
                        severity="high",
                        parameters={"camera_name": cam_name, "department": "Maintenance", "priority": "High"},
                    )
                )
                actions.append(
                    ProposedAction(
                        action_id=f"act-alert-{uuid4().hex[:6]}",
                        action_type="alert",
                        title=f"توجيه كاميرا مجاورة لتغطية فجوة المراقبة",
                        description="تعديل زاوية الرؤية للكاميرا الاحتياطية لتغطية المنطقة غير المراقبة مؤقتاً لحين انتهاء الصيانة.",
                        severity="medium",
                        parameters={"target_camera": cam_name, "backup_action": "fov_reassignment"},
                    )
                )
            else:
                actions.append(
                    ProposedAction(
                        action_id=f"act-maint-{uuid4().hex[:6]}",
                        action_type="maintenance",
                        title=f"Dispatch Urgent Maintenance Ticket for Camera ({cam_name})",
                        description=f"Generate an immediate work order for the field maintenance crew to inspect {cam_name} and restore telemetry.",
                        severity="high",
                        parameters={"camera_name": cam_name, "department": "Maintenance", "priority": "High"},
                    )
                )
                actions.append(
                    ProposedAction(
                        action_id=f"act-alert-{uuid4().hex[:6]}",
                        action_type="alert",
                        title=f"Reassign Adjacent Camera to Cover Blindspot",
                        description="Adjust field of view on adjacent surveillance assets to monitor the unobserved gap until maintenance completes.",
                        severity="medium",
                        parameters={"target_camera": cam_name, "backup_action": "fov_reassignment"},
                    )
                )

        # -------------------------------------------------------------------
        # 2. PPE Violations & Safety Rules In Welding / Hazardous Zones
        # -------------------------------------------------------------------
        ppe_detected = any(
            w in full_content for w in ["ppe violation", "welding", "goggles", "helmet", "boots", "ppe_violation"]
        ) or any(w in q_lower for w in ["ppe", "welding", "goggles", "وقاية", "لحام", "خوذة", "نظارات"])

        if ppe_detected and any("ppe" in c.content.lower() or "welding" in c.content.lower() for c in retrieved_chunks):
            if language == "ar":
                actions.append(
                    ProposedAction(
                        action_id=f"act-alert-ppe-{uuid4().hex[:6]}",
                        action_type="alert",
                        title="إطلاق تنبيه صوتي وضوئي لمخالفات الـ PPE في منطقة اللحام",
                        description="بث تنبيه آلي في لوحة المشرف الميداني وشاشات العنبر لإلزام العاملين بارتداء نظارات اللحام والخوذة.",
                        severity="high",
                        parameters={"zone_name": "Welding Restricted Zone", "alert_type": "audio_visual_ppe"},
                    )
                )
                actions.append(
                    ProposedAction(
                        action_id=f"act-dispatch-{uuid4().hex[:6]}",
                        action_type="dispatch",
                        title="إرسال مسؤول السلامة الميداني لتفتيش الموقع فوراً",
                        description="تكليف مسؤول السلامة الميداني المناوب بالتحقق من تطبيق بروتوكول الوقاية وإيقاف الأعمال المخالفة.",
                        severity="medium",
                        parameters={"zone_name": "Welding Restricted Zone", "task": "onsite_ppe_audit"},
                    )
                )
            else:
                actions.append(
                    ProposedAction(
                        action_id=f"act-alert-ppe-{uuid4().hex[:6]}",
                        action_type="alert",
                        title="Broadcast Audio-Visual PPE Warning in Welding Zone",
                        description="Trigger automated visual alerts on shop-floor displays enforcing mandatory welding goggles and helmets.",
                        severity="high",
                        parameters={"zone_name": "Welding Restricted Zone", "alert_type": "audio_visual_ppe"},
                    )
                )
                actions.append(
                    ProposedAction(
                        action_id=f"act-dispatch-{uuid4().hex[:6]}",
                        action_type="dispatch",
                        title="Dispatch Floor Safety Supervisor for On-Site Inspection",
                        description="Instruct the on-duty safety officer to inspect the welding bay and halt non-compliant operations.",
                        severity="medium",
                        parameters={"zone_name": "Welding Restricted Zone", "task": "onsite_ppe_audit"},
                    )
                )

        # -------------------------------------------------------------------
        # 3. Critical Incidents & Restricted Zone Intrusions
        # -------------------------------------------------------------------
        intrusion_detected = any(
            w in full_content for w in ["intrusion", "restricted zone", "fall", "fatigue", "critical"]
        ) or any(w in q_lower for w in ["intrusion", "incident", "accident", "fall", "حادث", "اختراق", "تسلل", "سقوط"])

        if intrusion_detected and any("incident" in c.content.lower() or "zone" in c.content.lower() for c in retrieved_chunks):
            if language == "ar":
                actions.append(
                    ProposedAction(
                        action_id=f"act-escl-{uuid4().hex[:6]}",
                        action_type="escalation",
                        title="تصعيد تقرير الحادث لإدارة السلامة العامة والمصنع",
                        description="إرسال تقرير فوري ببيانات الحادث وزمن الاستجابة إلى مدير السلامة للتحقيق واعتماد الإجراءات التصحيحية.",
                        severity="critical",
                        parameters={"target_role": "factory_manager", "escalation_level": "Level-2"},
                    )
                )
            else:
                actions.append(
                    ProposedAction(
                        action_id=f"act-escl-{uuid4().hex[:6]}",
                        action_type="escalation",
                        title="Escalate Incident Report to Plant Safety Management",
                        description="Transmit real-time telemetry and incident timeline to the plant director for root-cause review.",
                        severity="critical",
                        parameters={"target_role": "factory_manager", "escalation_level": "Level-2"},
                    )
                )

        return actions[:3]  # Return top 3 most actionable recommendations
