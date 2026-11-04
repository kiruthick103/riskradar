"""
Unit I — Goal-Based & Utility-Based Agent (CS23533)
Structures the entire RiskRadar pipeline as a rational agent:
  PERCEPT: Incoming safety report narrative
  REASON:  LLM extraction -> taxonomy -> Bayesian -> logic -> scoring  
  ACT:     ESCALATE | HUMAN_REVIEW | ROUTINE_LOG
  UTILITY: Expected cost of wrong action weighted by severity
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("riskradar.ai_core.agent")

_UTILITY_MATRIX = {
    "ESCALATE":     (0.95, 0.30),
    "HUMAN_REVIEW": (0.75, 0.65),
    "ROUTINE_LOG":  (0.00, 0.95),
}

def _expected_utility(action: str, p_sif: float) -> float:
    u1, u0 = _UTILITY_MATRIX[action]
    return p_sif * u1 + (1.0 - p_sif) * u0

@dataclass
class Percept:
    report_id: str
    narrative_text: str
    site: str
    activity: str
    received_at: float = field(default_factory=time.time)

@dataclass
class ReasoningStep:
    stage: str
    duration_ms: float
    output_summary: str
    confidence: float
    technique_badge: str

@dataclass
class AgentDecision:
    action: str
    utility: float
    sif_label: str
    confidence: float
    reasoning_steps: List[ReasoningStep]
    explanation: str
    percept_summary: str
    total_duration_ms: float

class SafetyIntelligenceAgent:
    """Goal-based / utility-based rational agent for safety precursor detection."""
    name = "RiskRadar Safety Intelligence Agent"
    goal = "Detect every genuine SIF precursor; never auto-clear as safe."

    def perceive(self, narrative: str, report_id: str, site: str, activity: str) -> Percept:
        return Percept(report_id=report_id, narrative_text=narrative, site=site, activity=activity)

    def act(self, percept: Percept, pipeline_result: Dict[str, Any],
            reasoning_steps: Optional[List[ReasoningStep]] = None) -> AgentDecision:
        t0 = time.perf_counter()
        steps = reasoning_steps or []
        assessment = pipeline_result.get("assessment", {})
        if hasattr(assessment, "model_dump"):
            assessment = assessment.model_dump()
        raw_lbl = assessment.get("sif_potential_label", "LOW")
        label_str = raw_lbl.value if hasattr(raw_lbl, "value") else str(raw_lbl)
        label = label_str.upper().replace("SIFPOTENTIALLABEL.", "").strip()
        conf  = float(assessment.get("confidence", 0.5))
        p_map = {"HIGH": 0.90, "MEDIUM": 0.60, "LOW": 0.15, "INSUFFICIENT_EVIDENCE": 0.50}
        p_sif = p_map.get(label, 0.15) * conf + p_map.get(label, 0.15) * (1 - conf) * 0.4
        best_action, best_eu = max(
            ((a, _expected_utility(a, p_sif)) for a in _UTILITY_MATRIX), key=lambda x: x[1])
        if label == "HIGH" and conf >= 0.7:
            best_action = "ESCALATE"
        elif label in ("HIGH", "MEDIUM") and conf < 0.65:
            best_action = "HUMAN_REVIEW"
        elif label == "INSUFFICIENT_EVIDENCE":
            best_action = "HUMAN_REVIEW"
        reasons = assessment.get("reasons", [])
        explanation = (f"Agent selected {best_action} (EU={best_eu:.3f}). "
                       f"P(SIF)~={p_sif:.2f} [{label}, conf={conf:.2f}]. "
                       + " ".join(reasons[:2]))
        total_ms = (time.perf_counter() - t0) * 1000 + sum(s.duration_ms for s in steps)
        return AgentDecision(action=best_action, utility=best_eu, sif_label=label,
                             confidence=conf, reasoning_steps=steps, explanation=explanation,
                             percept_summary=f"{percept.report_id}@{percept.site}: {percept.narrative_text[:80]}",
                             total_duration_ms=total_ms)

    def trace_dict(self, decision: AgentDecision) -> Dict[str, Any]:
        return {
            "technique": "Goal-Based & Utility-Based Agent (Unit I)",
            "agent_name": self.name, "goal": self.goal,
            "percept_summary": decision.percept_summary,
            "decision": decision.action, "utility": round(decision.utility, 4),
            "sif_label": decision.sif_label, "confidence": round(decision.confidence, 4),
            "explanation": decision.explanation,
            "reasoning_steps": [{"stage": s.stage, "duration_ms": round(s.duration_ms, 2),
                                  "output": s.output_summary, "confidence": round(s.confidence, 4),
                                  "badge": s.technique_badge} for s in decision.reasoning_steps],
            "total_duration_ms": round(decision.total_duration_ms, 2),
        }

safety_agent = SafetyIntelligenceAgent()
