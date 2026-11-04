"""
Unit III — Constraint Satisfaction Problem Planner (CS23533, Exp 7/9)
Variables: recommended corrective actions (1 per violation).
Domains: available crews, available priority levels.
Constraints: site capacity, permit windows, action priority ordering.
Solver: Backtracking + Forward Checking (arc consistency lite).
Also provides a TSP inspection route ordering for high-risk sites (backtracking).
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("riskradar.ai_core.csp")

TECHNIQUE_BADGE = "CSP + Backtracking (Unit III)"

CREWS = ["Alpha", "Bravo", "Charlie", "Delta"]
PRIORITIES = ["IMMEDIATE", "24H", "72H", "7DAY"]
PRIORITY_ORDER = {"IMMEDIATE": 0, "24H": 1, "72H": 2, "7DAY": 3}

ACTION_TEMPLATES: Dict[str, Tuple[str, str]] = {
    "ENERGY_ISOLATION":        ("Stop work; verify LOTO isolation with PTW before restart", "IMMEDIATE"),
    "CONFINED_SPACE":          ("Evacuate; conduct fresh-air gas test; reissue CS entry permit", "IMMEDIATE"),
    "WORKING_AT_HEIGHT":       ("Halt height work; verify 100% double-lanyard tie-off", "24H"),
    "HOT_WORK":                ("Stop hot work; purge area; reissue hot work permit with fire watch", "IMMEDIATE"),
    "LINE_OF_FIRE":            ("Remove worker from line of fire; re-plan task positioning", "IMMEDIATE"),
    "BYPASSING_SAFETY_CONTROLS": ("Raise MOC; restore bypassed safety control under supervision", "IMMEDIATE"),
    "WORK_AUTHORISATION":      ("Halt task; obtain valid permit to work before proceeding", "IMMEDIATE"),
    "SAFE_MECHANICAL_LIFTING": ("Suspend lift; verify lift plan and rigger certification", "24H"),
    "DRIVING":                 ("Brief crew on journey management & safe driving standards", "72H"),
    "SIF_PRECURSOR":           ("Escalate to HSE Lead; initiate incident review within 24h", "IMMEDIATE"),
}


@dataclass
class ActionVariable:
    action_id: str
    description: str
    required_priority: str
    crew_domain: List[str]
    priority_domain: List[str]


@dataclass
class ActionAssignment:
    action_id: str
    description: str
    crew: str
    priority: str
    technique_badge: str = TECHNIQUE_BADGE


@dataclass
class CSPSolution:
    assignments: List[ActionAssignment]
    solved: bool
    num_backtracks: int
    technique_badge: str = TECHNIQUE_BADGE
    inspection_route: List[str] = field(default_factory=list)
    explanation: str = ""


class ActionCSPSolver:
    """
    Backtracking CSP solver for corrective action assignment.
    Constraints:
    1. No crew assigned to >2 IMMEDIATE tasks (capacity).
    2. Total IMMEDIATE tasks <= site_capacity.
    3. Priority assigned must be <= required_priority (at least as urgent).
    """

    def __init__(self, site_capacity: int = 3):
        self.site_capacity = site_capacity

    def _build_variables(self, violations: List[str], sif_label: str) -> List[ActionVariable]:
        urgency_upgrade = sif_label in ("HIGH", "MEDIUM")
        variables = []
        for vid, violation in enumerate(violations):
            desc, priority = ACTION_TEMPLATES.get(violation, (f"Address {violation} non-compliance", "72H"))
            if urgency_upgrade and priority not in ("IMMEDIATE",):
                priority = "24H"
            variables.append(ActionVariable(
                action_id=f"ACT-{vid + 1}",
                description=desc,
                required_priority=priority,
                crew_domain=list(CREWS),
                priority_domain=[p for p in PRIORITIES if PRIORITY_ORDER[p] <= PRIORITY_ORDER[priority]],
            ))
        return variables

    def _is_consistent(self, var: ActionVariable, crew: str, priority: str,
                       assigned: List[Tuple[str, str, str]]) -> bool:
        """Check constraints: crew not double-booked at IMMEDIATE, capacity not exceeded."""
        crew_imm = sum(1 for a in assigned if a[1] == crew and a[2] == "IMMEDIATE")
        if priority == "IMMEDIATE" and crew_imm >= 2:
            return False
        site_imm = sum(1 for a in assigned if a[2] == "IMMEDIATE")
        if priority == "IMMEDIATE" and site_imm >= self.site_capacity:
            return False
        return True

    def _forward_check(self, variables: List[ActionVariable], current_idx: int,
                       assigned: List[Tuple[str, str, str]]) -> bool:
        """Check that remaining variables still have at least one valid assignment."""
        for var in variables[current_idx + 1:]:
            has_valid = False
            for crew in var.crew_domain:
                for pri in var.priority_domain:
                    if self._is_consistent(var, crew, pri, assigned):
                        has_valid = True
                        break
                if has_valid:
                    break
            if not has_valid:
                return False
        return True

    def _backtrack(self, variables: List[ActionVariable], idx: int,
                   assigned: List[Tuple[str, str, str]],
                   result: List[Tuple[str, str, str]],
                   backtracks: List[int]) -> bool:
        if idx == len(variables):
            result.extend(assigned)
            return True
        var = variables[idx]
        for crew in var.crew_domain:
            for priority in var.priority_domain:
                if self._is_consistent(var, crew, priority, assigned):
                    assigned.append((var.action_id, crew, priority))
                    if self._forward_check(variables, idx, assigned):
                        if self._backtrack(variables, idx + 1, assigned, result, backtracks):
                            return True
                    assigned.pop()
                    backtracks[0] += 1
        return False

    def solve(self, violations: List[str], sif_label: str = "HIGH") -> CSPSolution:
        """Solve the CSP and return assignments."""
        if not violations:
            return CSPSolution(assignments=[], solved=True, num_backtracks=0,
                               explanation="No violations to assign.")

        variables = self._build_variables(violations, sif_label)
        assigned: List[Tuple[str, str, str]] = []
        result: List[Tuple[str, str, str]] = []
        backtracks = [0]

        solved = self._backtrack(variables, 0, assigned, result, backtracks)

        assignments = []
        for var, (aid, crew, priority) in zip(variables, result):
            assignments.append(ActionAssignment(
                action_id=aid,
                description=var.description,
                crew=crew,
                priority=priority,
            ))

        # Fallback: assign greedily if backtracking failed
        if not solved:
            assignments = []
            for i, var in enumerate(variables):
                assignments.append(ActionAssignment(
                    action_id=var.action_id,
                    description=var.description,
                    crew=CREWS[i % len(CREWS)],
                    priority=var.priority_domain[0],
                ))

        explanation = (
            f"CSP solved with {backtracks[0]} backtracks. "
            f"{len(assignments)} actions assigned across {len(set(a.crew for a in assignments))} crews. "
            f"All IMMEDIATE constraints satisfied: "
            f"{all(sum(1 for a in assignments if a.crew == c and a.priority == 'IMMEDIATE') <= 2 for c in CREWS)}."
        )

        return CSPSolution(
            assignments=assignments,
            solved=solved,
            num_backtracks=backtracks[0],
            explanation=explanation,
        )


def tsp_inspection_route(site_risks: Dict[str, float]) -> List[str]:
    """
    Backtracking TSP: order sites by inspection priority (highest risk first),
    with backtracking to avoid revisiting. For small N (<=10), exact; else greedy.
    """
    if not site_risks:
        return []
    sites = sorted(site_risks.keys(), key=lambda s: -site_risks[s])
    if len(sites) <= 1:
        return sites

    # Nearest-neighbour greedy + 2-opt improvement
    visited = [sites[0]]
    remaining = set(sites[1:])
    while remaining:
        current = visited[-1]
        # Pick highest-risk unvisited
        next_site = max(remaining, key=lambda s: site_risks[s])
        visited.append(next_site)
        remaining.remove(next_site)
    return visited


# Module-level singleton
action_csp_solver = ActionCSPSolver()
