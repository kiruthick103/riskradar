"""
Unit Tests for RiskRadar Fine-Tuned Model Inference Service & Pipeline Integration.
"""

import os
import sys
import pytest

# Ensure root paths are in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml_model.serve.inference import extract, is_exact_substring, get_extractor_mode
from app.pipeline import pipeline

SAMPLE_NARRATIVE = (
    "During scheduled maintenance on a hydrocarbon transfer line, work began after the upstream "
    "valve was closed. Positive isolation was not verified with a pressure test before flange "
    "breaking commenced. Residual pressure was present in the line. The worker stepped back immediately."
)

def test_inference_schema_validity():
    """Verify that fine-tuned extractor outputs complete schema."""
    res = extract(SAMPLE_NARRATIVE)
    assert isinstance(res, dict)
    required = [
        "report_type", "activity", "hazard", "energy_type", "energy_level",
        "exposure_present", "proximity", "barrier", "barrier_status",
        "potential_consequence", "life_saving_rules"
    ]
    for key in required:
        assert key in res, f"Missing required key: {key}"
    assert res["model_provenance"] == "RiskRadar-Extractor v1 (fine-tuned)"

def test_exact_substring_grounding():
    """Verify that every extracted evidence quote exists verbatim in input text."""
    res = extract(SAMPLE_NARRATIVE)
    for rule in res.get("life_saving_rules", []):
        quote = rule.get("evidence_quote", "")
        assert is_exact_substring(quote, SAMPLE_NARRATIVE), f"Quote not verbatim substring: {quote}"

def test_extractor_modes():
    """Verify extractor mode retrieval."""
    mode = get_extractor_mode()
    assert mode in ("auto", "finetuned", "external")

def test_pipeline_integration_model_info():
    """Verify that SafetyIntelligencePipeline passes model provenance to output record."""
    record = pipeline.process_report(
        narrative_text=SAMPLE_NARRATIVE,
        site="Field Site 4 - Duliajan Central",
        activity="mechanical_electrical_maintenance"
    )
    assert "model_info" in record
    assert "RiskRadar-Extractor" in record["model_info"] or "Hybrid" in record["model_info"]
    assert hasattr(record["assessment"], "sif_potential_label")
