import os
import json
import pytest

def test_all_dataset_reports_ingested():
    """
    Coverage test: Ensures 100% of PDF case studies in Dataset_reports/
    are ingested into authentic_reports.json and ground_truth.json.
    Fails if any single PDF is missing.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ds_dir = os.path.join(base_dir, "Dataset_reports")
    auth_path = os.path.join(base_dir, "backend", "data", "authentic_reports.json")
    gt_path = os.path.join(base_dir, "backend", "data", "ground_truth.json")

    assert os.path.exists(ds_dir), f"Dataset directory missing: {ds_dir}"
    assert os.path.exists(auth_path), f"authentic_reports.json missing: {auth_path}"
    assert os.path.exists(gt_path), f"ground_truth.json missing: {gt_path}"

    pdf_files = sorted([f for f in os.listdir(ds_dir) if f.lower().endswith(".pdf")])
    total_pdfs = len(pdf_files)
    assert total_pdfs > 0, "No PDF files found in Dataset_reports"

    with open(auth_path, "r", encoding="utf-8") as f:
        auth_records = json.load(f)

    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    ingested_files = {r["source_file"] for r in auth_records}
    gt_files = {v["source_file"] for v in gt_data.values()}

    missing_in_auth = [f for f in pdf_files if f not in ingested_files]
    missing_in_gt = [f for f in pdf_files if f not in gt_files]

    print(f"\n{len(auth_records)}/{total_pdfs} case studies used")

    assert not missing_in_auth, f"Missing {len(missing_in_auth)} case studies in authentic_reports.json: {missing_in_auth}"
    assert not missing_in_gt, f"Missing {len(missing_in_gt)} case studies in ground_truth.json: {missing_in_gt}"
    assert len(auth_records) == total_pdfs, f"Coverage mismatch: {len(auth_records)} records vs {total_pdfs} PDFs"
