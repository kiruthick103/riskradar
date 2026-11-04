from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.db.repository import repository
from app.telemetry.trajectory import compute_site_telemetry
from app.telemetry.synthetic_scenario import get_synthetic_demonstration_scenario

router = APIRouter(prefix="/telemetry", tags=["SIF Telemetry Engine"])

@router.get("/synthetic-demo")
def get_synthetic_demo():
    """
    Returns the controlled 6-week progressive deterioration scenario.
    Clearly labelled as Prototype / Synthetic Demonstration Data.
    """
    return get_synthetic_demonstration_scenario()

@router.get("/sites-summary")
def get_all_sites_telemetry_summary():
    """
    Returns cross-site trajectory classifications for comparison across all OIL installations.
    Site list is derived dynamically from actual reports in the DB — no hardcoding.
    """
    reports = repository.list_reports(limit=1000)

    # Dynamically extract all unique sites from the actual report database
    site_set: Dict[str, int] = {}
    for r in reports:
        site = (r.get("site") or "") if isinstance(r, dict) else (getattr(r, "site", "") or "")
        if site and site.strip():
            s = site.strip()
            site_set[s] = site_set.get(s, 0) + 1

    # Sort by report count (most active sites first), take top 12
    ranked_sites = sorted(site_set.items(), key=lambda x: x[1], reverse=True)[:12]
    site_names = [s for s, _ in ranked_sites]

    summaries = []
    for s in site_names:
        telem = compute_site_telemetry(reports, s)
        summaries.append({
            "site": s,
            "trajectory_status": telem["trajectory_status"],
            "trajectory_badge": telem["trajectory_badge"],
            "risk_drift_label": telem["risk_drift_label"],
            "color": telem["color"],
            "total_points": telem["total_points"],
            "report_count": site_set.get(s, 0),
            "primary_driver": telem["explanation"]["primary_driver"],
            "hse_recommendation": telem["explanation"]["hse_recommendation"]
        })

    # Sort by risk severity
    severity_order = {"CRITICAL": 4, "DETERIORATING": 3, "EMERGING": 2, "STABLE": 1}
    summaries.sort(key=lambda x: severity_order.get(x["trajectory_status"], 0), reverse=True)

    return {
        "total_sites": len(summaries),
        "total_reports_analyzed": len(reports),
        "summaries": summaries
    }

@router.get("/sites-list")
def get_sites_list():
    """
    Returns all unique site names present in the current DB with their report counts.
    Used by the frontend to dynamically populate the site selector dropdown.
    """
    reports = repository.list_reports(limit=1000)
    site_stats: Dict[str, Dict[str, Any]] = {}

    for r in reports:
        site = (r.get("site") or "") if isinstance(r, dict) else (getattr(r, "site", "") or "")
        if not site or not site.strip():
            continue
        site = site.strip()
        if site not in site_stats:
            site_stats[site] = {"count": 0, "high": 0, "medium": 0}
        site_stats[site]["count"] += 1

        a = r.get("assessment", {}) if isinstance(r, dict) else {}
        if isinstance(a, dict):
            lbl = a.get("sif_potential_label", "LOW")
        else:
            lbl = getattr(getattr(a, "sif_potential_label", None), "value", None) or str(getattr(a, "sif_potential_label", "LOW"))
        if lbl == "HIGH":
            site_stats[site]["high"] += 1
        elif lbl == "MEDIUM":
            site_stats[site]["medium"] += 1

    sites = [
        {"site": s, "report_count": v["count"], "high_sif_count": v["high"], "medium_sif_count": v["medium"]}
        for s, v in site_stats.items()
    ]
    sites.sort(key=lambda x: (x["high_sif_count"] + x["medium_sif_count"], x["report_count"]), reverse=True)

    return {
        "total_sites": len(sites),
        "sites": sites
    }

@router.get("/site/{site_name}")
def get_site_telemetry(site_name: str, activity: Optional[str] = None):
    """
    Returns detailed telemetry timeline, Safety State Vectors, and explainable trajectory for a site.
    Computed entirely from authentic DB reports — no synthetic data unless demo site is requested.
    """
    if "synthetic" in site_name.lower() or "rig 7" in site_name.lower():
        return get_synthetic_demonstration_scenario()

    reports = repository.list_reports(limit=1000)
    telemetry = compute_site_telemetry(reports, site_name, activity_filter=activity)
    return telemetry
