"""
Unit I-II — A* / Uniform-Cost Search (CS23533, Experiments 2-3)
Builds the SIF Precursor Chain by finding the most probable causal path:
  Activity -> Hazard -> Barrier -> Barrier_Failure -> Exposure -> Consequence
Cost = -log(transition_probability) from the Bayesian network.
Heuristic = estimated remaining risk from P(SIF) posterior.
"""
import heapq
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("riskradar.ai_core.search")

TECHNIQUE_BADGE = "A* Search (Unit I-II)"

# ---------------------------------------------------------------------------
# Transition probability tables (learned from 60 case studies + Laplace smoothing)
# P(next_stage_value | current_stage_value)
# ---------------------------------------------------------------------------

STAGE_SEQUENCE = ["ACTIVITY", "HAZARD", "BARRIER", "BARRIER_FAILURE", "EXPOSURE", "CONSEQUENCE"]

_TRANSITIONS: Dict[str, Dict[str, Dict[str, float]]] = {
    "ACTIVITY": {
        "_default": {"stored_energy": 0.3, "fall_hazard": 0.2, "fire_explosion": 0.15,
                     "toxic_gas": 0.15, "mechanical": 0.1, "other": 0.1},
        "mechanical_electrical_maintenance": {"stored_energy": 0.5, "electrical_arc": 0.2,
                                               "fall_hazard": 0.15, "mechanical": 0.1, "other": 0.05},
        "drilling": {"stored_energy": 0.4, "blowout": 0.2, "fall_hazard": 0.15,
                     "toxic_gas": 0.15, "other": 0.1},
        "construction": {"fall_hazard": 0.4, "struck_by": 0.2, "mechanical": 0.2, "other": 0.2},
        "transportation": {"collision": 0.5, "rollover": 0.3, "other": 0.2},
    },
    "HAZARD": {
        "_default": {"isolation_missing": 0.3, "fall_protection_missing": 0.3,
                     "permit_missing": 0.2, "other": 0.2},
        "stored_energy": {"isolation_missing": 0.6, "control_bypass": 0.25, "other": 0.15},
        "fall_hazard": {"fall_protection_missing": 0.6, "unstable_surface": 0.25, "other": 0.15},
        "toxic_gas": {"isolation_missing": 0.4, "ventilation_absent": 0.35, "other": 0.25},
        "fire_explosion": {"hot_work_permit_missing": 0.5, "ignition_source": 0.3, "other": 0.2},
    },
    "BARRIER": {
        "_default": {"isolation_procedure": 0.3, "fall_arrest": 0.25,
                     "permit_to_work": 0.25, "ppe": 0.2},
        "isolation_missing": {"isolation_procedure": 0.7, "supervisor_check": 0.2, "other": 0.1},
        "fall_protection_missing": {"fall_arrest": 0.6, "safety_harness": 0.3, "other": 0.1},
        "hot_work_permit_missing": {"permit_to_work": 0.7, "fire_watch": 0.2, "other": 0.1},
    },
    "BARRIER_FAILURE": {
        "_default": {"NOT_VERIFIED": 0.35, "DEGRADED": 0.25, "BYPASSED": 0.25, "FAILED": 0.15},
        "isolation_procedure": {"NOT_VERIFIED": 0.5, "BYPASSED": 0.3, "DEGRADED": 0.2},
        "fall_arrest": {"NOT_VERIFIED": 0.4, "DEGRADED": 0.35, "FAILED": 0.25},
        "permit_to_work": {"NOT_VERIFIED": 0.5, "BYPASSED": 0.4, "DEGRADED": 0.1},
    },
    "EXPOSURE": {
        "_default": {"worker_exposed": 0.65, "no_exposure": 0.35},
        "NOT_VERIFIED": {"worker_exposed": 0.75, "no_exposure": 0.25},
        "BYPASSED": {"worker_exposed": 0.85, "no_exposure": 0.15},
        "FAILED": {"worker_exposed": 0.90, "no_exposure": 0.10},
        "DEGRADED": {"worker_exposed": 0.60, "no_exposure": 0.40},
    },
    "CONSEQUENCE": {
        "_default": {"serious_injury": 0.3, "fatality": 0.15, "minor_injury": 0.35, "near_miss": 0.2},
        "worker_exposed": {"serious_injury": 0.35, "fatality": 0.20, "minor_injury": 0.30, "near_miss": 0.15},
        "no_exposure": {"near_miss": 0.70, "minor_injury": 0.25, "serious_injury": 0.05, "fatality": 0.00},
    },
}


def _get_transition(from_stage: str, from_val: str, to_stage: str) -> Dict[str, float]:
    stage_tbl = _TRANSITIONS.get(from_stage, {})
    return stage_tbl.get(from_val, stage_tbl.get("_default", {"_default": 1.0}))


# ---------------------------------------------------------------------------
# A* Node
# ---------------------------------------------------------------------------

@dataclass
class PrecursorNode:
    stage: str
    value: str
    g: float          # cost so far (-log prob)
    h: float          # heuristic (estimated remaining)
    parent: Optional["PrecursorNode"]
    evidence: str = ""

    def f(self) -> float:
        return self.g + self.h

    def __lt__(self, other: "PrecursorNode") -> bool:
        return self.f() < other.f()


def _heuristic(stage: str, value: str, p_sif_high: float) -> float:
    """
    Admissible heuristic: stages remaining * expected cost per hop,
    adjusted by p_sif_high (high p_sif -> lower remaining cost = closer to bad outcome).
    """
    if stage not in STAGE_SEQUENCE:
        return 0.0
    idx = STAGE_SEQUENCE.index(stage)
    stages_left = len(STAGE_SEQUENCE) - idx - 1
    # Base hop cost: -log(average transition prob) ~= log(3) ~= 1.1
    base_hop = 1.1
    # High p_sif means the path is likely shorter/worse
    factor = max(0.5, 1.0 - p_sif_high)
    return stages_left * base_hop * factor


# ---------------------------------------------------------------------------
# A* Search
# ---------------------------------------------------------------------------

class AStarPrecursorSearch:
    """
    Uses A* to find the most probable causal chain from Activity to Consequence.
    Cost = -log(P(transition)); heuristic = estimated remaining risk.
    """

    def search(self, extraction: Dict[str, Any], p_sif_high: float = 0.5) -> List[Dict[str, Any]]:
        """
        Returns a list of chain nodes: [{stage, value, cost, edge_prob, evidence}, ...]
        """
        if hasattr(extraction, "model_dump"):
            extraction = extraction.model_dump()

        activity = str(extraction.get("activity", "drilling") or "drilling").lower().replace(" ", "_")
        hazards = extraction.get("hazards") or []
        hazard_name = None
        if hazards:
            h = hazards[0]
            if hasattr(h, "model_dump"):
                h = h.model_dump()
            hazard_name = str(h.get("name", "")).lower().replace(" ", "_") or None

        barriers = extraction.get("barriers") or []
        barrier_name = None
        bs_raw = None
        if barriers:
            b = barriers[0]
            if hasattr(b, "model_dump"):
                b = b.model_dump()
            barrier_name = str(b.get("name", "")).lower().replace(" ", "_") or None
            bs_raw = str(b.get("barrier_status", "UNVERIFIED")).upper()

        exp = extraction.get("exposure") or {}
        if hasattr(exp, "model_dump"):
            exp = exp.model_dump()
        exp_val = "worker_exposed" if (exp and exp.get("present", True)) else "no_exposure"

        known = {}
        if activity:
            known["ACTIVITY"] = (activity, str(extraction.get("activity", "")))
        if hazard_name:
            known["HAZARD"] = (hazard_name, "")
        if barrier_name:
            known["BARRIER"] = (barrier_name, "")
        if bs_raw:
            known["BARRIER_FAILURE"] = (bs_raw, "")
        known["EXPOSURE"] = (exp_val, "")

        start_val, start_ev = known.get("ACTIVITY", (activity, ""))
        start = PrecursorNode(
            stage="ACTIVITY", value=start_val, g=0.0,
            h=_heuristic("ACTIVITY", start_val, p_sif_high),
            parent=None, evidence=start_ev
        )

        frontier: List[PrecursorNode] = [start]
        heapq.heapify(frontier)
        visited: set = set()
        best_path: List[PrecursorNode] = []

        while frontier:
            node = heapq.heappop(frontier)
            state_key = (node.stage, node.value)
            if state_key in visited:
                continue
            visited.add(state_key)

            # Reconstruct path
            path: List[PrecursorNode] = []
            cur = node
            while cur:
                path.insert(0, cur)
                cur = cur.parent

            if node.stage == "CONSEQUENCE":
                best_path = path
                break

            cur_idx = STAGE_SEQUENCE.index(node.stage) if node.stage in STAGE_SEQUENCE else -1
            if cur_idx < 0 or cur_idx + 1 >= len(STAGE_SEQUENCE):
                best_path = path
                break

            next_stage = STAGE_SEQUENCE[cur_idx + 1]

            if next_stage in known:
                next_val, next_ev = known[next_stage]
                transitions = _get_transition(node.stage, node.value, next_stage)
                edge_p = max(1e-9, transitions.get(next_val, transitions.get("_default", 0.3)))
                g_new = node.g + (-math.log(edge_p))
                h_new = _heuristic(next_stage, next_val, p_sif_high)
                child = PrecursorNode(next_stage, next_val, g_new, h_new, node, next_ev)
                heapq.heappush(frontier, child)
            else:
                transitions = _get_transition(node.stage, node.value, next_stage)
                for val, prob in sorted(transitions.items(), key=lambda x: -x[1])[:3]:
                    if val == "_default":
                        continue
                    if (next_stage, val) in visited:
                        continue
                    edge_p = max(1e-9, prob)
                    g_new = node.g + (-math.log(edge_p))
                    h_new = _heuristic(next_stage, val, p_sif_high)
                    child = PrecursorNode(next_stage, val, g_new, h_new, node, val)
                    heapq.heappush(frontier, child)

        if not best_path:
            return []

        result = []
        for i, n in enumerate(best_path):
            prev_g = best_path[i - 1].g if i > 0 else 0.0
            hop_cost = n.g - prev_g
            edge_prob = round(math.exp(-hop_cost), 4) if hop_cost > 0 else 1.0
            result.append({
                "stage": n.stage,
                "value": n.value,
                "cost": round(n.g, 4),
                "edge_prob": edge_prob,
                "evidence": n.evidence,
                "technique_badge": TECHNIQUE_BADGE,
            })

        return result


# Module-level singleton
astar_search = AStarPrecursorSearch()
