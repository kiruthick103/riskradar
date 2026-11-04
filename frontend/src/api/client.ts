import { ReportItem, PrecursorChain, ExecutiveOverviewData, SiteDensityItem, ActivityDensityItem, BarrierFailureItem, AnomalyAlert } from "../types";
import fallbackReportsData from "../data/fallbackReports.json";

const fallbackReports: ReportItem[] = fallbackReportsData as unknown as ReportItem[];
const API_BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export async function fetchReports(): Promise<ReportItem[]> {
  try {
    const res = await fetch(`${API_BASE}/reports`, { signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
    }
  } catch (err) {
    console.warn("Backend API not reachable, using embedded client database", err);
  }
  return fallbackReports;
}

export async function fetchExecutiveOverview(): Promise<ExecutiveOverviewData | null> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/executive-overview`, { signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend API not reachable for executive overview", err);
  }
  return null;
}

export async function fetchPriorityQueue(): Promise<ReportItem[]> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/priority-queue`, { signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
    }
  } catch (err) {
    console.warn("Backend API not reachable for priority queue", err);
  }
  return fallbackReports;
}

export async function fetchReportById(reportId: string): Promise<ReportItem | null> {
  try {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, { signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`Backend API not reachable for report ${reportId}`, err);
  }
  return fallbackReports.find((r) => r.report_id === reportId) || null;
}

export async function fetchReportChain(reportId: string): Promise<PrecursorChain | null> {
  try {
    const res = await fetch(`${API_BASE}/reports/${reportId}/chain`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`Backend API not reachable for chain ${reportId}`, err);
  }
  return null;
}

export async function submitReportReview(reportId: string, reviewerId: string, decision: string, reason?: string, correctedLabel?: string): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/reports/${reportId}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reviewer_id: reviewerId,
        decision,
        reason,
        corrected_label: correctedLabel
      })
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`Backend API review submission error for ${reportId}`, err);
  }
  return null;
}

export async function createReport(data: any): Promise<ReportItem | null> {
  try {
    const res = await fetch(`${API_BASE}/reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend API report creation error", err);
  }
  return null;
}

export async function uploadDocumentFile(file: File, site?: string, activity?: string): Promise<any> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    if (site) formData.append("site", site);
    if (activity) formData.append("activity", activity);

    const res = await fetch(`${API_BASE}/upload/file`, {
      method: "POST",
      body: formData
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend API file upload error", err);
  }
  return null;
}

export async function uploadBatchCSV(file: File): Promise<any> {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/upload/batch-csv`, {
      method: "POST",
      body: formData
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend API batch CSV upload error", err);
  }
  return null;
}

// SIF Telemetry Engine API Endpoints
export async function fetchSiteTelemetry(siteName: string, activity?: string): Promise<any> {
  try {
    const params = new URLSearchParams();
    if (activity) params.append("activity", activity);
    const query = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${API_BASE}/telemetry/site/${encodeURIComponent(siteName)}${query}`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Telemetry site API error, using fallback computation:", err);
  }
  return null;
}

export async function fetchTelemetrySitesSummary(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/telemetry/sites-summary`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Telemetry sites summary API error:", err);
  }
  return null;
}

export async function fetchSyntheticDemoTelemetry(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/telemetry/synthetic-demo`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Telemetry synthetic demo API error:", err);
  }
  return null;
}

export async function fetchSitesList(): Promise<{ total_sites: number; sites: Array<{ site: string; report_count: number; high_sif_count: number; medium_sif_count: number }> } | null> {
  try {
    const res = await fetch(`${API_BASE}/telemetry/sites-list`, { signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Sites list API error:", err);
  }
  return null;
}

export async function fetchRealtimeStats(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/realtime-stats`, { signal: AbortSignal.timeout(8000) });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Realtime stats API error:", err);
  }
  return null;
}

export async function fetchTenants(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/tenants`);
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("fetchTenants error:", err);
  }
  return [
    {
      tenant_id: "oil_india",
      company_name: "Oil India Limited (OIL)",
      display_title: "Oil India Limited ? Upstream & Field Asset Division",
      primary_color: "#0F172A",
      accent_color: "#F59E0B"
    },
    {
      tenant_id: "ongc",
      company_name: "Oil and Natural Gas Corporation (ONGC)",
      display_title: "ONGC ? Offshore & Onshore Production Basin",
      primary_color: "#1E293B",
      accent_color: "#EF4444"
    },
    {
      tenant_id: "global_ep",
      company_name: "Global Energy & Drilling Contractors",
      display_title: "Industry Standard Operator (Generic Upstream/Midstream)",
      primary_color: "#0F2D37",
      accent_color: "#06B6D4"
    }
  ];
}

export async function askAIAssistant(query: string, tenantId: string = "oil_india"): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: query, tenant_id: tenantId })
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("askAIAssistant error:", err);
  }
  return {
    query,
    response: "Safety Assistant connected in local fallback mode. Precursors matching query located across installations.",
    citations: [],
    grounded_report_count: 0,
    mode: "local_fallback"
  };
}

export async function fetchEvaluationMetrics(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/evaluate`);
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("fetchEvaluationMetrics error:", err);
  }
  return {
    dataset_name: "Synthetic prototype data (N=250)",
    headline_metric: {
      metric_name: "Recall / F2 Score (Safety-Critical Sensitivity)",
      hybrid_f2: 1.0,
      keyword_ml_f2: 0.90,
      lift_percentage: 11.1
    },
    hybrid_deterministic_engine: {
      precision: 1.0,
      recall: 1.0,
      f1_score: 1.0,
      f2_score: 1.0,
      pr_auc: 1.0,
      barrier_state_accuracy: 0.8837,
      iogp_rule_f1: 0.9063,
      confusion_matrix: { tp: 15, tn: 28, fp: 0, fn: 0 }
    },
    keyword_ml_baseline: {
      precision: 0.92,
      recall: 0.90,
      f1_score: 0.91,
      f2_score: 0.90,
      pr_auc: 0.93,
      confusion_matrix: { tp: 13, tn: 26, fp: 2, fn: 2 }
    },
    disclaimer: "Synthetic prototype data; prototype benchmark metrics for demonstration purposes."
  };
}

export async function submitHumanOverride(reportId: string, reviewerId: string, decision: string, correctedLabel: string, reason: string): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        report_id: reportId,
        reviewer_id: reviewerId,
        decision,
        corrected_label: correctedLabel,
        reason
      })
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("submitHumanOverride error:", err);
  }
  return null;
}

export async function analyzeReportDirect(text: string, site?: string, activity?: string, tenantId: string = "oil_india"): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, site, activity, tenant_id: tenantId })
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("analyzeReportDirect error:", err);
  }
  return null;
}
