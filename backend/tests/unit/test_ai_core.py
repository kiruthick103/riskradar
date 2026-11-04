"""
Unit tests for backend/app/ai_core modules (CS23533 Foundations of AI).
Tests:
  1. Agent (Unit I)
  2. Local Search (Unit II)
  3. CSP Planner (Unit III)
  4. Knowledge Base (Unit IV)
  5. Bayesian Network & Naive Bayes (Unit V)
  6. A* Search (Unit I-II)
"""
import pytest
from app.ai_core.agent import safety_agent, Percept
from app.ai_core.bayesian_network import infer_p_sif, naive_bayes_classifier
from app.ai_core.knowledge_base import safety_kb, Fact, HornClause, forward_chain, backward_chain
from app.ai_core.search_precursor import astar_search
from app.ai_core.csp_planner import action_csp_solver, tsp_inspection_route
from app.ai_core.local_search import hill_climb, simulated_annealing, load_weights, DEFAULT_WEIGHTS

# 1. Unit I: Goal-Based Agent
def test_agent_escalates_on_high_sif():
    percept = Percept(report_id="TEST-1", narrative_text="Stored pressure blowout", site="Well 84", activity="drilling")
    result = {
        "assessment": {
            "sif_potential_label": "HIGH",
            "confidence": 0.95,
            "reasons": ["Stored energy 14 bar", "Isolation not verified"]
        }
    }
    decision = safety_agent.act(percept, result)
    assert decision.action == "ESCALATE"
    assert decision.utility > 0.0
    assert "ESCALATE" in decision.explanation

def test_agent_human_review_on_ambiguous():
    percept = Percept(report_id="TEST-2", narrative_text="Scaffold tag green but clamp loose", site="Naharkatiya", activity="height")
    result = {
        "assessment": {
            "sif_potential_label": "HIGH",
            "confidence": 0.50,
            "reasons": ["Conflicting tag vs physical inspection"]
        }
    }
    decision = safety_agent.act(percept, result)
    assert decision.action == "HUMAN_REVIEW"

# 2. Unit V: Bayesian Network
def test_bayesian_network_high_risk():
    res = infer_p_sif(energy_level=3, barrier_status=3, exposure=1, proximity=2, activity_criticality=2)
    assert res["p_sif_high"] > 0.90
    assert res["technique_badge"] == "Bayesian Network (Unit V)"

def test_bayesian_network_marginalization():
    # Only energy_level known; others marginalized
    res = infer_p_sif(energy_level=3)
    assert 0.0 <= res["p_sif_high"] <= 1.0
    assert "exposure" in res["marginalized_features"]
    assert "energy_level=3" in res["used_features"]

def test_naive_bayes_baseline():
    pred = naive_bayes_classifier.predict("Stored pressure release, positive isolation not verified")
    assert pred["label"] == "SIF_POTENTIAL"
    assert len(pred["sif_keywords_found"]) >= 1

# 3. Unit IV: Knowledge Base (Horn Clauses)
def test_kb_forward_chaining_energy_isolation():
    ext = {
        "energy_level": 3,
        "barriers": [{"name": "isolation valve", "barrier_status": "FAILED", "evidence_quote": "not verified"}],
        "exposure": {"present": True, "evidence_quote": "worker at manifold"},
        "narrative_text": "work without permit"
    }
    analysis = safety_kb.analyse(ext)
    assert "ENERGY_ISOLATION" in analysis.violations
    assert analysis.sif_precursor_proven is True
    assert "ENERGY_ISOLATION" in analysis.proof_trees

def test_kb_backward_chaining_proof_tree():
    facts = [Fact("energy_present", True), Fact("not isolation_verified", True), Fact("worker_exposed", True)]
    proof = backward_chain("violates(ENERGY_ISOLATION)", facts)
    assert proof.satisfied is True
    assert proof.rule_used == "ENERGY_ISOLATION"

# 4. Unit I-II: A* Search
def test_astar_search_produces_path():
    ext = {
        "activity": "drilling",
        "hazards": [{"name": "stored_energy"}],
        "barriers": [{"name": "isolation_procedure", "barrier_status": "FAILED"}],
        "exposure": {"present": True}
    }
    path = astar_search.search(ext, p_sif_high=0.95)
    assert len(path) >= 4
    stages = [n["stage"] for n in path]
    assert stages[0] == "ACTIVITY"
    assert "CONSEQUENCE" in stages

# 5. Unit III: CSP Planner & TSP Route
def test_csp_planner_allocates_crews():
    violations = ["ENERGY_ISOLATION", "WORKING_AT_HEIGHT", "CONFINED_SPACE"]
    solution = action_csp_solver.solve(violations, sif_label="HIGH")
    assert solution.solved is True
    assert len(solution.assignments) == 3
    # Check crew IMMEDIATE capacity constraint
    immediate_crew_counts = {}
    for a in solution.assignments:
        if a.priority == "IMMEDIATE":
            immediate_crew_counts[a.crew] = immediate_crew_counts.get(a.crew, 0) + 1
            assert immediate_crew_counts[a.crew] <= 2

def test_tsp_inspection_route():
    risks = {"Site A": 0.85, "Site B": 0.32, "Site C": 0.95, "Site D": 0.50}
    route = tsp_inspection_route(risks)
    assert len(route) == 4
    assert route[0] == "Site C"  # highest risk first

# 6. Unit II: Local Search Weight Tuning
def test_local_search_weights():
    weights = load_weights()
    assert "exposure" in weights
    assert "energy" in weights
    assert weights["exposure"] >= 0.5
