"""
Unit IV — Knowledge-Based Agent: Propositional + First-Order Logic,
Forward/Backward Chaining, Resolution (CS23533).
Encodes the 9 IOGP Life-Saving Rules as Horn clauses.
Forward chaining derives rule violations from extracted facts.
Backward chaining produces proof trees used as the 'why' explanation.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("riskradar.ai_core.knowledge_base")

TECHNIQUE_BADGE = "Forward/Backward Chaining (Unit IV)"

# ---------------------------------------------------------------------------
# Horn Clause Representation
# ---------------------------------------------------------------------------

@dataclass
class HornClause:
    """body ⊢ head  (if all body literals are true, conclude head)"""
    head: str
    body: List[str]
    rule_id: str
    description: str


@dataclass
class Fact:
    name: str
    value: Any = True
    evidence_quote: str = ""
    source: str = "extraction"


@dataclass
class ProofNode:
    goal: str
    satisfied: bool
    rule_used: Optional[str] = None
    children: List["ProofNode"] = field(default_factory=list)
    evidence_quote: str = ""


# ---------------------------------------------------------------------------
# IOGP 9 Life-Saving Rules as Horn Clauses
# ---------------------------------------------------------------------------

IOGP_HORN_CLAUSES = [
    HornClause(
        head="violates(ENERGY_ISOLATION)",
        body=["energy_present", "not isolation_verified", "worker_exposed"],
        rule_id="ENERGY_ISOLATION",
        description="Energy present, isolation not verified, worker exposed → Energy Isolation violation",
    ),
    HornClause(
        head="violates(CONFINED_SPACE)",
        body=["confined_space_entry", "not gas_test_done"],
        rule_id="CONFINED_SPACE",
        description="Confined space entry without gas test → Confined Space violation",
    ),
    HornClause(
        head="violates(CONFINED_SPACE)",
        body=["confined_space_entry", "not permit_issued"],
        rule_id="CONFINED_SPACE",
        description="Confined space entry without permit → Confined Space violation",
    ),
    HornClause(
        head="violates(WORKING_AT_HEIGHT)",
        body=["work_at_height", "not fall_protection_verified"],
        rule_id="WORKING_AT_HEIGHT",
        description="Working at height without verified fall protection → Working at Height violation",
    ),
    HornClause(
        head="violates(HOT_WORK)",
        body=["hot_work_activity", "not fire_watch_present"],
        rule_id="HOT_WORK",
        description="Hot work without fire watch → Hot Work violation",
    ),
    HornClause(
        head="violates(HOT_WORK)",
        body=["hot_work_activity", "not hot_work_permit"],
        rule_id="HOT_WORK",
        description="Hot work without permit → Hot Work violation",
    ),
    HornClause(
        head="violates(LINE_OF_FIRE)",
        body=["worker_in_line_of_fire", "energy_present"],
        rule_id="LINE_OF_FIRE",
        description="Worker in line of fire with energy present → Line of Fire violation",
    ),
    HornClause(
        head="violates(BYPASSING_SAFETY_CONTROLS)",
        body=["safety_control_bypassed"],
        rule_id="BYPASSING_SAFETY_CONTROLS",
        description="Safety control bypassed → Bypassing Safety Controls violation",
    ),
    HornClause(
        head="violates(WORK_AUTHORISATION)",
        body=["high_risk_work", "not permit_issued"],
        rule_id="WORK_AUTHORISATION",
        description="High-risk work without permit → Work Authorisation violation",
    ),
    HornClause(
        head="violates(SAFE_MECHANICAL_LIFTING)",
        body=["lifting_operation", "not lift_plan_verified"],
        rule_id="SAFE_MECHANICAL_LIFTING",
        description="Lifting operation without verified lift plan → Safe Mechanical Lifting violation",
    ),
    HornClause(
        head="violates(DRIVING)",
        body=["vehicle_operation", "not journey_management"],
        rule_id="DRIVING",
        description="Vehicle operation without journey management → Driving violation",
    ),
    # SIF precursor derived fact
    HornClause(
        head="sif_precursor",
        body=["energy_present", "barrier_failed_or_missing", "worker_exposed"],
        rule_id="SIF_PRECURSOR",
        description="Energy + failed barrier + exposure = SIF precursor",
    ),
    HornClause(
        head="sif_precursor",
        body=["high_energy_present", "not isolation_verified"],
        rule_id="SIF_PRECURSOR",
        description="High energy without isolation verification = SIF precursor",
    ),
]


# ---------------------------------------------------------------------------
# Fact extraction from pipeline output
# ---------------------------------------------------------------------------

def _extraction_to_facts(extraction: Dict[str, Any]) -> List[Fact]:
    """Convert an extraction dict to a list of Facts for KB reasoning."""
    if hasattr(extraction, "model_dump"):
        extraction = extraction.model_dump()

    facts: List[Fact] = []

    energy_level = extraction.get("energy_level", 0) or 0
    if energy_level > 0:
        facts.append(Fact("energy_present", True, f"energy_level={energy_level}"))
    if energy_level >= 3:
        facts.append(Fact("high_energy_present", True, f"energy_level={energy_level}"))

    # Barriers
    barriers = extraction.get("barriers") or []
    barrier_failed = False
    barrier_missing = False
    isolation_verified = True

    for b in barriers:
        if hasattr(b, "model_dump"):
            b = b.model_dump()
        bs = str(b.get("barrier_status", "UNVERIFIED")).upper()
        name = str(b.get("name", "")).lower()
        quote = b.get("evidence_quote", "")
        if bs in ("FAILED", "BYPASSED"):
            barrier_failed = True
            facts.append(Fact("barrier_failed", True, quote))
            if "safety control" in name or "bypass" in name.lower():
                facts.append(Fact("safety_control_bypassed", True, quote))
        if bs in ("MISSING",):
            barrier_missing = True
        if "isolation" in name.lower() and bs in ("UNVERIFIED", "DEGRADED", "FAILED", "BYPASSED"):
            isolation_verified = False
            facts.append(Fact("not isolation_verified", True, quote))
        if "isolation" in name.lower() and bs == "VERIFIED_INTACT":
            isolation_verified = True
            facts.append(Fact("isolation_verified", True, quote))

    if barrier_failed or barrier_missing:
        facts.append(Fact("barrier_failed_or_missing", True))
    if isolation_verified and not any(f.name == "not isolation_verified" for f in facts):
        facts.append(Fact("isolation_verified", True))

    # Exposure
    exp = extraction.get("exposure") or {}
    if hasattr(exp, "model_dump"):
        exp = exp.model_dump()
    if exp and exp.get("present", False):
        facts.append(Fact("worker_exposed", True, str(exp.get("evidence_quote", ""))))

    # Activity-based facts
    activity = str(extraction.get("activity", "")).lower()
    report_text = str(extraction.get("narrative_text", "") or extraction.get("activity", "")).lower()
    if any(w in report_text for w in ["confined space", "vessel entry", "tank entry"]):
        facts.append(Fact("confined_space_entry", True))
    if any(w in report_text for w in ["welding", "cutting", "hot work", "grinding near flammables"]):
        facts.append(Fact("hot_work_activity", True))
    if any(w in report_text for w in ["working at height", "elevated work", "scaffold", "roof", "mast"]):
        facts.append(Fact("work_at_height", True))
    if any(w in report_text for w in ["crane", "lift", "hoisting", "lifting"]):
        facts.append(Fact("lifting_operation", True))
    if any(w in report_text for w in ["driving", "vehicle", "journey", "road"]):
        facts.append(Fact("vehicle_operation", True))

    # Permit
    if any(w in report_text for w in ["permit issued", "ptw issued", "permit to work issued"]):
        facts.append(Fact("permit_issued", True))
    else:
        facts.append(Fact("not permit_issued", True))

    # High-risk work
    if any(w in report_text for w in ["high risk", "high-risk", "critical task"]):
        facts.append(Fact("high_risk_work", True))

    return facts


def _fact_set(facts: List[Fact]) -> Set[str]:
    return {f.name for f in facts if f.value is True}


# ---------------------------------------------------------------------------
# Forward Chaining
# ---------------------------------------------------------------------------

def forward_chain(facts: List[Fact], clauses: List[HornClause] = IOGP_HORN_CLAUSES) -> Tuple[List[Fact], List[str]]:
    """
    Forward chaining: repeatedly apply Horn clauses to the fact base until no new facts.
    Returns (derived_facts, fired_rule_ids).
    """
    known = _fact_set(facts)
    derived = list(facts)
    fired_rules: List[str] = []
    changed = True

    while changed:
        changed = False
        for clause in clauses:
            if clause.head in known:
                continue
            # Check all body literals
            satisfied = all(
                (lit in known) if not lit.startswith("not ") else (lit[4:] not in known)
                for lit in clause.body
            )
            if satisfied:
                derived.append(Fact(clause.head, True, source=f"rule:{clause.rule_id}"))
                known.add(clause.head)
                fired_rules.append(clause.rule_id)
                changed = True

    return derived, fired_rules


# ---------------------------------------------------------------------------
# Backward Chaining
# ---------------------------------------------------------------------------

def backward_chain(goal: str, facts: List[Fact],
                   clauses: List[HornClause] = IOGP_HORN_CLAUSES,
                   depth: int = 0, max_depth: int = 10) -> ProofNode:
    """
    Backward chaining: prove a goal by finding a clause whose head matches,
    then recursively proving each body literal. Returns a proof tree.
    """
    known = _fact_set(facts)

    # Base: goal is a known fact
    if goal in known:
        quote = next((f.evidence_quote for f in facts if f.name == goal), "")
        return ProofNode(goal=goal, satisfied=True, evidence_quote=quote)

    # Negation as failure
    if goal.startswith("not "):
        inner = goal[4:]
        satisfied = inner not in known
        return ProofNode(goal=goal, satisfied=satisfied)

    if depth >= max_depth:
        return ProofNode(goal=goal, satisfied=False)

    # Try each applicable clause
    for clause in clauses:
        if clause.head != goal:
            continue
        children = []
        all_sat = True
        for lit in clause.body:
            child = backward_chain(lit, facts, clauses, depth + 1, max_depth)
            children.append(child)
            if not child.satisfied:
                all_sat = False
                break
        if all_sat:
            return ProofNode(
                goal=goal, satisfied=True,
                rule_used=clause.rule_id,
                children=children,
                evidence_quote=clause.description,
            )

    return ProofNode(goal=goal, satisfied=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class KBAnalysis:
    violations: List[str]
    fired_rules: List[str]
    derived_facts: List[str]
    proof_trees: Dict[str, Any]
    sif_precursor_proven: bool
    explanation: str
    technique_badge: str


def proof_node_to_dict(node: ProofNode) -> Dict[str, Any]:
    return {
        "goal": node.goal,
        "satisfied": node.satisfied,
        "rule_used": node.rule_used,
        "evidence_quote": node.evidence_quote,
        "children": [proof_node_to_dict(c) for c in node.children],
    }


def analyse(extraction: Dict[str, Any]) -> KBAnalysis:
    """
    Main entry point: derive IOGP rule violations and SIF precursor status
    from the extraction result using forward + backward chaining.
    """
    facts = _extraction_to_facts(extraction)
    derived_facts, fired_rules = forward_chain(facts)

    # Collect unique violations
    violations = sorted({
        f.name.replace("violates(", "").rstrip(")")
        for f in derived_facts
        if f.name.startswith("violates(")
    })

    # Backward chain for proof tree on each violation
    proof_trees = {}
    for v in violations:
        goal = f"violates({v})"
        pt = backward_chain(goal, derived_facts)
        proof_trees[v] = proof_node_to_dict(pt)

    # Also backward chain on sif_precursor
    sif_pt = backward_chain("sif_precursor", derived_facts)
    proof_trees["SIF_PRECURSOR"] = proof_node_to_dict(sif_pt)
    sif_proven = any(f.name == "sif_precursor" for f in derived_facts)

    derived_names = [f.name for f in derived_facts if f.name not in _fact_set(facts)]

    explanation = (
        f"Forward chaining derived {len(derived_names)} new facts, "
        f"fired rules: {', '.join(set(fired_rules)) or 'none'}. "
        f"Violations: {', '.join(violations) or 'none'}. "
        f"SIF precursor: {'YES' if sif_proven else 'NO'}."
    )

    return KBAnalysis(
        violations=violations,
        fired_rules=list(set(fired_rules)),
        derived_facts=derived_names,
        proof_trees=proof_trees,
        sif_precursor_proven=sif_proven,
        explanation=explanation,
        technique_badge=TECHNIQUE_BADGE,
    )


# Module-level singleton
safety_kb = type("SafetyKB", (), {
    "analyse": staticmethod(analyse),
    "forward_chain": staticmethod(forward_chain),
    "backward_chain": staticmethod(backward_chain),
    "TECHNIQUE_BADGE": TECHNIQUE_BADGE,
})()
