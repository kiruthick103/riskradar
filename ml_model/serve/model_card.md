# Model Card: RiskRadar-Extractor-v1

## Model Overview
- **Model Name:** RiskRadar-Extractor-v1
- **Base Architecture:** Qwen2.5-1.5B-Instruct (Parameter-efficient LoRA adapter)
- **Adapter Configuration:** LoRA rank $r=16$, $\alpha=32$, dropout $0.05$, target modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- **Task:** End-to-end extraction of structured safety observation entities (activity, hazard, energy type, energy level, exposure, barrier, barrier status, potential consequence, and IOGP Life-Saving Rules with verbatim evidence quotes)
- **Deployment Interface:** `ml_model/serve/inference.py` via `extract(report_text, activity_hint)`

---

## Training Dataset
- **Sources:**
  1. **Authentic Ground Truth:** All 60 case study PDFs from `Dataset_reports/` (real oilfield, drilling, refinery, and pipeline incidents with fatalities and serious injuries).
  2. **Synthetic Operational Reports:** 250 reports covering low-risk routine patrols, false-alarm finger pinches, training sessions, and unverified barrier observations.
  3. **Data Augmentations:** 930 variations (linguistic paraphrasing, sentence permuting, short radio-log phrasing, dialect variations, negation and contradiction checks).
- **Total Corpus Size:** 1,240 labeled examples.
- **Data Splits (Stratified by root incident to prevent leakage):**
  - **Train:** 848 examples (68.4%)
  - **Validation:** 184 examples (14.8%)
  - **Held-Out Blind Test:** 208 examples (16.8%) — including all 3 showcase demo cases.

---

## 3-Way Comparative Benchmark (Held-out Test Set, N=208)

| Metric | Keyword Baseline | External LLM | **RiskRadar-Extractor-v1 (Ours)** |
| :--- | :---: | :---: | :---: |
| **JSON Schema Validity** | 0.0% | 98.5% | **99.5%** |
| **SIF Detection Precision** | 52.8% | 94.1% | **96.9%** |
| **SIF Detection Recall** | 61.5% | 98.5% | **98.5%** |
| **F1 Score** | 56.8% | 96.2% | **97.7%** |
| **F2 Score (Safety Weighted)** | 59.5% | 97.6% | **98.2%** |
| **Verbatim Substring Grounding** | N/A | 91.2% | **100.0%** |
| **Average Latency** | 12 ms | 2,850 ms | **145 ms** |

---

## Key Capabilities & Guardrails
1. **Verbatim Evidence Grounding:** Every asserted rule violation must be an exact verbatim substring within the input safety report. Extracted quotes with zero offset alignment are dropped or flagged.
2. **Deterministic Confidence & Calibration:** Outputs feed into the CS23533 Bayesian Network and Knowledge Base for exact probabilistic marginalization and Horn clause resolution.
3. **Graceful Fallback:** Controlled by configuration flag `EXTRACTOR=auto|finetuned|external`. In `auto` mode, the fine-tuned model is executed first, seamlessly falling back to external hybrid extraction if confidence drops below threshold.

---

## Intended Use & Governance
- **Primary Domain:** Oil & Gas upstream drilling, hydrocarbon processing, pipeline maintenance, and refinery operations.
- **Role:** Decision-support intelligence agent. Provides structured entity recommendations and causal risk precursor trees for HSE safety officers.
- **Safety Directive:** Decision-support only. Not an autonomous safety shut-in authority. All predictions remain fully reviewable and editable by human safety engineers.
