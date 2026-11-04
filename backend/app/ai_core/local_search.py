"""
Unit II — Local / Heuristic Search (CS23533)
Tunes the SIF scoring weights using Hill Climbing and Simulated Annealing
to maximise F2 score (recall-biased) on a labeled training set.
Stores tuned weights to config/tuned_weights.json.
"""
import json
import math
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("riskradar.ai_core.local_search")

TECHNIQUE_BADGE = "Hill Climbing / SA (Unit II)"

DEFAULT_WEIGHTS = {
    "exposure": 2.0,
    "energy": 1.0,
    "barrier": 1.2,
    "proximity": 1.0,
    "activity": 0.8,
}

WEIGHT_BOUNDS = {
    "exposure": (0.5, 4.0),
    "energy": (0.5, 3.0),
    "barrier": (0.5, 3.0),
    "proximity": (0.5, 2.5),
    "activity": (0.3, 2.0),
}

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "config", "tuned_weights.json"
)

# ---------------------------------------------------------------------------
# Scoring simulation (pure arithmetic, mirrors sif_engine.py logic)
# ---------------------------------------------------------------------------

def _score_with_weights(record: Dict[str, Any], weights: Dict[str, float]) -> float:
    """Compute a raw numeric risk score from a labeled record using given weights."""
    ext = record.get("extraction") or {}
    if hasattr(ext, "model_dump"):
        ext = ext.model_dump()

    energy = min(3, max(0, int(ext.get("energy_level") or 0)))
    barriers = ext.get("barriers") or []
    barrier_score = 2  # default unverified
    if barriers:
        b = barriers[0]
        if hasattr(b, "model_dump"):
            b = b.model_dump()
        bs_map = {"VERIFIED_INTACT": 0, "DEGRADED": 1, "UNVERIFIED": 2,
                  "WEAK": 2, "MISSING": 3, "FAILED": 3, "BYPASSED": 3}
        barrier_score = bs_map.get(str(b.get("barrier_status", "UNVERIFIED")).upper(), 2)
    exp = ext.get("exposure") or {}
    if hasattr(exp, "model_dump"):
        exp = exp.model_dump()
    exposure = 1 if (exp and exp.get("present", True)) else 0
    proximity = min(2, max(0, int((exp.get("proximity") if exp else None) or 0)))
    activity = min(2, max(0, int(ext.get("activity_criticality") or 0)))

    return (
        weights["exposure"] * exposure
        + weights["energy"] * energy
        + weights["barrier"] * barrier_score
        + weights["proximity"] * proximity
        + weights["activity"] * activity
    )


def _predict_label(score: float, threshold_high: float = 5.5, threshold_med: float = 3.0) -> str:
    if score >= threshold_high:
        return "HIGH"
    elif score >= threshold_med:
        return "MEDIUM"
    return "LOW"


def _compute_f2(records: List[Dict[str, Any]], weights: Dict[str, float],
                threshold_high: float = 5.5) -> float:
    """
    F2 = (1 + 4) * P * R / (4P + R) with beta=2 (recall-biased).
    SIF_POTENTIAL = True means the record should be flagged (HIGH or MEDIUM).
    """
    tp = fp = fn = 0
    for rec in records:
        gt = rec.get("sif_confirmed") or rec.get("ground_truth_sif", False)
        actual_sif = gt is True or str(gt).upper() in ("TRUE", "YES", "SIF_POTENTIAL", "HIGH")
        score = _score_with_weights(rec, weights)
        predicted_sif = score >= threshold_high * 0.9  # slightly lower threshold for recall
        if actual_sif and predicted_sif:
            tp += 1
        elif not actual_sif and predicted_sif:
            fp += 1
        elif actual_sif and not predicted_sif:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    beta2 = 4.0
    if precision + recall == 0:
        return 0.0
    return (1 + beta2) * precision * recall / (beta2 * precision + recall)


def _clamp_weights(weights: Dict[str, float]) -> Dict[str, float]:
    return {
        k: max(WEIGHT_BOUNDS[k][0], min(WEIGHT_BOUNDS[k][1], v))
        for k, v in weights.items()
    }


def _neighbour(weights: Dict[str, float], step: float = 0.1) -> Dict[str, float]:
    """Generate a random neighbour by perturbing one weight."""
    key = random.choice(list(weights.keys()))
    delta = random.uniform(-step, step)
    new_weights = dict(weights)
    new_weights[key] = new_weights[key] + delta
    return _clamp_weights(new_weights)


# ---------------------------------------------------------------------------
# Hill Climbing
# ---------------------------------------------------------------------------

def hill_climb(labeled_records: List[Dict[str, Any]],
               initial_weights: Optional[Dict[str, float]] = None,
               max_iter: int = 200,
               step: float = 0.15) -> Tuple[Dict[str, float], float, List[float]]:
    """
    Steepest-ascent hill climbing to maximise F2.
    Returns (best_weights, best_f2, f2_history).
    """
    if not labeled_records:
        return dict(DEFAULT_WEIGHTS), 0.0, []

    current = dict(initial_weights or DEFAULT_WEIGHTS)
    current_f2 = _compute_f2(labeled_records, current)
    history = [current_f2]

    for i in range(max_iter):
        # Try all neighbours (perturbations of each weight)
        best_neighbour = None
        best_f2 = current_f2
        for key in current:
            for delta in [step, -step]:
                candidate = dict(current)
                candidate[key] = _clamp_weights({key: candidate[key] + delta})[key]
                f2 = _compute_f2(labeled_records, candidate)
                if f2 > best_f2:
                    best_f2 = f2
                    best_neighbour = dict(candidate)
        if best_neighbour is None:
            break  # local optimum
        current = best_neighbour
        current_f2 = best_f2
        history.append(current_f2)

    return current, current_f2, history


# ---------------------------------------------------------------------------
# Simulated Annealing
# ---------------------------------------------------------------------------

def simulated_annealing(labeled_records: List[Dict[str, Any]],
                        initial_weights: Optional[Dict[str, float]] = None,
                        max_iter: int = 500,
                        T_start: float = 1.0,
                        T_end: float = 0.01,
                        step: float = 0.2) -> Tuple[Dict[str, float], float, List[float]]:
    """
    Simulated annealing to maximise F2 (avoids local optima).
    Returns (best_weights, best_f2, f2_history).
    """
    if not labeled_records:
        return dict(DEFAULT_WEIGHTS), 0.0, []

    random.seed(42)
    current = dict(initial_weights or DEFAULT_WEIGHTS)
    current_f2 = _compute_f2(labeled_records, current)
    best = dict(current)
    best_f2 = current_f2
    history = [current_f2]

    for i in range(max_iter):
        T = T_start * ((T_end / T_start) ** (i / max_iter))
        candidate = _neighbour(current, step=step)
        candidate_f2 = _compute_f2(labeled_records, candidate)
        delta = candidate_f2 - current_f2

        if delta > 0 or random.random() < math.exp(delta / max(T, 1e-10)):
            current = candidate
            current_f2 = candidate_f2

        if current_f2 > best_f2:
            best = dict(current)
            best_f2 = current_f2

        history.append(best_f2)

    return best, best_f2, history


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_weights(weights: Dict[str, float], path: Optional[str] = None) -> None:
    path = path or WEIGHTS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"weights": weights, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}, f, indent=2)
    logger.info(f"Tuned weights saved to {path}")


def load_weights(path: Optional[str] = None) -> Dict[str, float]:
    path = path or WEIGHTS_PATH
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            return data.get("weights", DEFAULT_WEIGHTS)
        except Exception as e:
            logger.warning(f"Could not load tuned weights: {e}")
    return dict(DEFAULT_WEIGHTS)


def tune_and_save(labeled_records: List[Dict[str, Any]],
                  method: str = "sa",
                  path: Optional[str] = None) -> Dict[str, float]:
    """
    Main entry: tune weights using hill climbing or SA, save result.
    method: 'hc' for hill climbing, 'sa' for simulated annealing.
    """
    logger.info(f"Starting weight tuning ({method}) on {len(labeled_records)} labeled records...")
    if method == "hc":
        weights, f2, history = hill_climb(labeled_records)
    else:
        weights, f2, history = simulated_annealing(labeled_records)
    logger.info(f"Tuning complete. Best F2={f2:.4f}. Weights: {weights}")
    save_weights(weights, path)
    return weights
