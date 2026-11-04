from typing import List, Dict, Any, Optional
from datetime import datetime
from app.telemetry.state_vector import calculate_safety_state_vector, SafetyStateVector
from app.telemetry.drift import calculate_risk_drift, StateDelta
from app.telemetry.explanation import generate_trajectory_explanation

def compute_site_telemetry(reports: List[Any], site_name: str, activity_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Processes all reports for a specific site over time to produce:
    1. Chronological Safety State Sequence
    2. Inter-report State Deltas (Risk Drift)
    3. Trajectory Status (🟢 STABLE, 🟡 EMERGING, 🟠 DETERIORATING, 🔴 CRITICAL)
    4. Causal Explanation & What is changing
    """
    def _get_field(r: Any, field: str, default: Any = "") -> Any:
        """Helper to get a field from either a dict or an object."""
        if isinstance(r, dict):
            return r.get(field, default) or default
        return getattr(r, field, default) or default

    # 1. Filter reports for site (case-insensitive partial match)
    site_lower = site_name.lower()
    site_reports = [
        r for r in reports
        if site_lower in _get_field(r, "site").lower()
    ]

    if activity_filter and activity_filter.strip():
        site_reports = [
            r for r in site_reports
            if _get_field(r, "activity").lower() == activity_filter.lower()
        ]

    if not site_reports:
        all_for_site = [r for r in reports if site_lower in _get_field(r, "site").lower()]
        if all_for_site:
            site_reports = all_for_site
        else:
            return {
                "site": site_name,
                "trajectory_status": "STABLE",
                "trajectory_badge": "🟢 STABLE",
                "risk_drift_label": "CONTROLLED",
                "color": "#059669",
                "total_points": 0,
                "timeline": [],
                "explanation": {
                    "summary": f"Zero historical safety observations found for site '{site_name}'. Baseline risk remains stable and controlled.",
                    "primary_driver": "No active observations recorded",
                    "causal_chain": ["Baseline verification intact", "Zero precursor incidents logged"],
                    "recommended_focus": "Maintain regular scheduled HSE observation patrols"
                }
            }

    # 2. Sort chronologically
    def parse_date(r):
        d_str = _get_field(r, "report_date", "2026-01-01")
        try:
            return datetime.strptime(str(d_str)[:10], "%Y-%m-%d")
        except Exception:
            return datetime(2026, 1, 1)

    sorted_reports = sorted(site_reports, key=parse_date)

    timeline_points = []
    prev_vector: Optional[SafetyStateVector] = None
    cumulative_drift = 0.0

    for idx, r in enumerate(sorted_reports):
        state_vec = calculate_safety_state_vector(r)
        delta = calculate_risk_drift(state_vec, prev_vector)
        cumulative_drift += delta.risk_drift_score

        # Format timeline label
        d_str = _get_field(r, "report_date", "2026-01-01")
        label = f"W{idx+1}" if len(sorted_reports) <= 8 else str(d_str)[5:10]

        # Extract barrier info — supports both dict and object reports
        barrier_name = "Isolation Barrier"
        barrier_status = "UNVERIFIED"
        ext = r.get("extraction", {}) if isinstance(r, dict) else getattr(r, "extraction", None)
        if isinstance(ext, dict):
            barriers_list = ext.get("barriers") or []
            if barriers_list and isinstance(barriers_list[0], dict):
                barrier_name = barriers_list[0].get("barrier_type") or barriers_list[0].get("barrier") or "Isolation Barrier"
                barrier_status = barriers_list[0].get("barrier_status", "UNVERIFIED")
            elif ext.get("barrier"):
                barrier_name = ext.get("barrier", "Isolation Barrier")
                barrier_status = ext.get("barrier_failure_type", "UNVERIFIED")
        elif ext and hasattr(ext, "barriers") and ext.barriers:
            barrier_name = ext.barriers[0].barrier_type or "Positive Isolation"
            barrier_status = ext.barriers[0].barrier_status or "UNVERIFIED"

        # Extract hazard info
        hazard_name = "Hazardous Energy"
        if isinstance(ext, dict):
            hazards_list = ext.get("hazards") or []
            if hazards_list and isinstance(hazards_list[0], dict):
                hazard_name = hazards_list[0].get("display_name") or hazards_list[0].get("hazard_type") or "Operational Hazard"
            elif ext.get("hazard"):
                hazard_name = str(ext.get("hazard", "Hazardous Energy"))
        elif ext and hasattr(ext, "hazards") and ext.hazards:
            hazard_name = ext.hazards[0].display_name or "Stored Pressure"

        # Assessment fields — supports both dict and object
        assessment = r.get("assessment", {}) if isinstance(r, dict) else getattr(r, "assessment", {})
        if isinstance(assessment, dict):
            sif_score = float(assessment.get("raw_score", 5.0) or 5.0)
            sif_label_raw = assessment.get("sif_potential_label", "LOW")
            sif_label = sif_label_raw.value if hasattr(sif_label_raw, "value") else str(sif_label_raw)
            confidence = float(assessment.get("confidence", 0.94) or 0.94)
        elif assessment:
            sif_score = float(getattr(assessment, "raw_score", 5.0) or 5.0)
            lbl_attr = getattr(assessment, "sif_potential_label", "LOW")
            sif_label = lbl_attr.value if hasattr(lbl_attr, "value") else str(lbl_attr)
            confidence = float(getattr(assessment, "confidence", 0.94) or 0.94)
        else:
            sif_score, sif_label, confidence = 5.0, "LOW", 0.94

        narrative = _get_field(r, "narrative_text", "")

        timeline_points.append({
            "point_id": f"pt-{idx+1}",
            "time_label": label,
            "date": str(d_str),
            "report_id": _get_field(r, "report_id", f"R-{idx+1}"),
            "external_ref": _get_field(r, "external_ref", f"DOC-{idx+1}"),
            "activity": _get_field(r, "activity", "Maintenance").replace("_", " ").title(),
            "hazard": str(hazard_name).replace("_", " ").title(),
            "barrier": str(barrier_name),
            "barrier_status": str(barrier_status),
            "sif_score": sif_score,
            "sif_label": sif_label,
            "confidence": confidence,
            "narrative_excerpt": str(narrative)[:120] + "...",
            "state_vector": state_vec.model_dump(),
            "delta": delta.model_dump(),
            "composite_risk": state_vec.composite_risk_index
        })

        prev_vector = state_vec

    # 3. Classify Trajectory
    # Based on composite trajectory slope, final barrier health, and risk drift
    avg_risk = sum(p["composite_risk"] for p in timeline_points) / max(1, len(timeline_points))
    recent_points = timeline_points[-3:] if len(timeline_points) >= 3 else timeline_points
    recent_risk = sum(p["composite_risk"] for p in recent_points) / max(1, len(recent_points))
    last_barrier_health = timeline_points[-1]["state_vector"]["barrier_health"] if timeline_points else 50.0

    net_shift = recent_risk - timeline_points[0]["composite_risk"] if timeline_points else 0.0

    if recent_risk >= 70.0 and (last_barrier_health <= 25.0 or net_shift >= 25.0):
        trajectory_status = "CRITICAL"
        trajectory_badge = "🔴 CRITICAL TRAJECTORY"
        risk_drift_label = "CRITICAL"
        color = "#dc2626"
    elif net_shift >= 15.0 or recent_risk >= 60.0:
        trajectory_status = "DETERIORATING"
        trajectory_badge = "🟠 DETERIORATING"
        risk_drift_label = "HIGH"
        color = "#ea580c"
    elif net_shift >= 6.0 or recent_risk >= 45.0:
        trajectory_status = "EMERGING"
        trajectory_badge = "🟡 EMERGING"
        risk_drift_label = "MODERATE"
        color = "#d97706"
    else:
        trajectory_status = "STABLE"
        trajectory_badge = "🟢 STABLE"
        risk_drift_label = "CONTROLLED"
        color = "#059669"

    explanation = generate_trajectory_explanation(trajectory_status, timeline_points, cumulative_drift)

    return {
        "site": site_name,
        "trajectory_status": trajectory_status,
        "trajectory_badge": trajectory_badge,
        "risk_drift_label": risk_drift_label,
        "color": color,
        "total_points": len(timeline_points),
        "timeline": timeline_points,
        "explanation": explanation
    }
