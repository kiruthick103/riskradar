import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.database import engine, Base, SessionLocal
from app.db.models import ReportModel, AuditLogModel
from app.schemas.domain import ExtractionResult, SIFAssessment, RuleMapping, PrecursorChain, ReviewDecision

logger = logging.getLogger("riskradar.repository")

# Create tables on startup — wrapped so app never crashes if DB is unavailable
try:
    Base.metadata.create_all(bind=engine)
except Exception as _db_init_err:
    logger.warning(f"DB table creation skipped (will use memory cache): {_db_init_err}")

class ReportRepository:
    """
    Unified Data Access Repository.
    Synchronizes persistence across SQLAlchemy database and fast in-memory query caches.
    """

    def __init__(self):
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._audit_cache: List[Dict[str, Any]] = []
        self.load_from_db()

    def _model_to_dict(self, model: ReportModel) -> Dict[str, Any]:
        """Converts an ORM ReportModel into a complete API-compatible report dictionary."""
        return {
            "report_id": model.report_id,
            "external_ref": model.external_ref or f"NS-2026-{model.report_id[-5:]}",
            "title": model.title or f"{model.site} — HSE Safety Precursor Assessment",
            "report_type": model.report_type or "NEAR_MISS",
            "report_date": model.report_date or datetime.now().strftime("%Y-%m-%d"),
            "site": model.site or "Field Site 4 - Duliajan Central",
            "activity": model.activity or "mechanical_electrical_maintenance",
            "narrative_text": model.narrative_text or "",
            "actual_severity": model.actual_severity or "NONE",
            "contractor_involved": model.contractor_involved if model.contractor_involved is not None else True,
            "difficulty_category": model.difficulty_category or "dataset_report",
            "extraction": model.extraction_json or {},
            "assessment": model.assessment_json or {"sif_potential_label": "LOW", "raw_score": 0.0},
            "rule_mappings": model.rule_mappings_json or [],
            "precursor_chain": model.precursor_chain_json or {},
            "embedding": model.embedding_vector or [],
            "extracted_images": model.extracted_images or [],
            "version_tags": model.version_tags or {},
            "review_status": model.review_status or "PENDING",
            "reviewed_by": model.reviewed_by,
            "review_decision": model.review_decision,
            "review_comment": model.review_comment
        }

    def load_from_db(self):
        """Loads all reports from the database into the fast in-memory query cache."""
        try:
            db = SessionLocal()
            try:
                models = db.query(ReportModel).all()
                for m in models:
                    self._memory_cache[m.report_id] = self._model_to_dict(m)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error loading reports from DB: {e}")

    def ingest_dataset_reports_if_empty(self):
        """Ingests all 60 PDF case studies from Dataset_reports if DB is empty."""
        self.load_from_db()
        if len(self._memory_cache) > 0:
            return

        import os
        from concurrent.futures import ThreadPoolExecutor
        from app.extraction.document_agent import document_agent

        # Resolve project root and candidate Dataset_reports directories
        current_file = os.path.abspath(__file__)
        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        # Priority 1: Seed from pre-extracted authentic live reports (67 OIL reports)
        if self._seed_from_live_reports(backend_root):
            return

        # Priority 2: Ingest from authentic Dataset_reports PDFs if directory present
        candidate_dirs = [
            "Dataset_reports",
            os.path.join(os.path.dirname(backend_root), "Dataset_reports"),
            os.path.join(backend_root, "Dataset_reports"),
            r"s:\projects\RISKRADAR DEMO\RISK DEMO\Dataset_reports"
        ]

        ds_dir = None
        for cand in candidate_dirs:
            if os.path.exists(cand) and os.path.isdir(cand):
                ds_dir = cand
                break

        if ds_dir and os.path.exists(ds_dir):
            pdf_files = [f for f in sorted(os.listdir(ds_dir)) if f.endswith(".pdf")]
            def process_one(fn):
                path = os.path.join(ds_dir, fn)
                with open(path, "rb") as f:
                    data = f.read()
                return document_agent.process_document(file_bytes=data, filename=fn)

            with ThreadPoolExecutor(max_workers=8) as executor:
                for recs in executor.map(process_one, pdf_files):
                    if recs:
                        for r in recs:
                            self.save_report(r)
        else:
            # Priority 3: Fallback to demo_cases.json
            self._seed_from_demo_json(backend_root)

    def _seed_from_live_reports(self, backend_root: str) -> bool:
        """Seeds full authentic dataset reports from data/live_local_reports.json."""
        import os, json
        live_path = os.path.join(backend_root, "data", "live_local_reports.json")
        if not os.path.exists(live_path):
            return False
        try:
            with open(live_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            if not records:
                return False
            for r in records:
                self.save_report(r)
            logger.info(f"Seeded {len(records)} authentic reports from live_local_reports.json")
            return True
        except Exception as e:
            logger.warning(f"Error seeding from live_local_reports.json: {e}")
            return False

    def _seed_from_demo_json(self, backend_root: str):
        """Seeds the repository from data/demo_cases.json when PDFs are not available."""
        import os, json, uuid
        demo_path = os.path.join(backend_root, "data", "demo_cases.json")
        if not os.path.exists(demo_path):
            logger.warning("demo_cases.json not found, starting with empty dataset")
            return

        try:
            with open(demo_path, "r", encoding="utf-8") as f:
                cases = json.load(f)

            for case in cases:
                # Handle potential list or string values
                h_val = case.get("hazard", "")
                hazard = h_val[0] if isinstance(h_val, list) and h_val else str(h_val)

                b_val = case.get("barrier", "")
                barrier = b_val[0] if isinstance(b_val, list) and b_val else str(b_val)

                lsr_val = case.get("life_saving_rule")
                if isinstance(lsr_val, list):
                    lsr_list = [str(x) for x in lsr_val]
                elif lsr_val:
                    lsr_list = [str(lsr_val)]
                else:
                    lsr_list = []

                rule_mappings = [
                    {
                        "life_saving_rule": r,
                        "rule_display_name": r.replace("_", " ").title(),
                        "is_process_safety_fundamental": bool(case.get("process_safety_relevant", False)),
                        "confidence": float(case.get("confidence", 0.85))
                    }
                    for r in lsr_list if r
                ]

                record = {
                    "report_id": case.get("report_id") or f"OIL-{uuid.uuid4().hex[:8].upper()}",
                    "external_ref": case.get("external_ref", ""),
                    "title": case.get("title", f"{case.get('site', 'Site')} — HSE Safety Precursor Assessment"),
                    "report_type": case.get("report_type", "NEAR_MISS"),
                    "report_date": case.get("report_date", "2026-01-01"),
                    "site": case.get("site", ""),
                    "activity": case.get("activity", ""),
                    "narrative_text": case.get("narrative_text", ""),
                    "actual_severity": case.get("actual_severity", "NONE"),
                    "contractor_involved": bool(case.get("contractor_involved", False)),
                    "difficulty_category": case.get("difficulty_category", "demo"),
                    "extraction": {
                        "hazard": hazard,
                        "energy_type": case.get("energy_type", ""),
                        "energy_level": case.get("energy_level", ""),
                        "exposure_present": case.get("exposure_present", False),
                        "exposure_description": case.get("exposure_description", ""),
                        "proximity": case.get("proximity", ""),
                        "activity_criticality": case.get("activity_criticality", ""),
                        "barrier": barrier,
                        "barrier_failure_type": case.get("barrier_failure_type", ""),
                        "potential_consequence": case.get("potential_consequence", ""),
                        "evidence_sentence": case.get("evidence_sentence", ""),
                        "process_safety_relevant": case.get("process_safety_relevant", False),
                    },
                    "assessment": {
                        "sif_potential_label": case.get("sif_potential_label", "LOW"),
                        "raw_score": float(case.get("raw_score", 0.0)),
                        "confidence": float(case.get("confidence", 0.85)),
                        "routing_decision": "AUTOMATED_CLOSE" if case.get("sif_potential_label") == "LOW" else "HUMAN_TRIAGE_REQUIRED",
                        "component_scores": {"hazard": 1, "energy": 1, "barrier": 1, "proximity": 1, "activity": 1},
                        "process_safety_relevant": bool(case.get("process_safety_relevant", False)),
                        "reasons": [case.get("evidence_sentence", "")] if case.get("evidence_sentence") else []
                    },
                    "rule_mappings": rule_mappings,
                    "precursor_chain": {},
                    "embedding": [],
                    "extracted_images": [],
                    "version_tags": {},
                    "review_status": "PENDING",
                    "reviewed_by": None,
                    "review_decision": None,
                    "review_comment": None,
                }
                self.save_report(record)

            logger.info(f"Seeded {len(cases)} reports from demo_cases.json")
        except Exception as e:
            logger.warning(f"Failed to seed from demo_cases.json: {e}")

    def save_report(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Saves or updates a processed report record in database and memory cache."""
        r_id = record["report_id"]
        self._memory_cache[r_id] = record

        try:
            db = SessionLocal()
            try:
                model = db.query(ReportModel).filter(ReportModel.report_id == r_id).first()
                if not model:
                    model = ReportModel(report_id=r_id)
                    db.add(model)

                model.external_ref = record.get("external_ref", "")
                model.title = record.get("title", "")
                model.report_type = str(record.get("report_type", "NEAR_MISS"))
                model.report_date = str(record.get("report_date", datetime.now().strftime("%Y-%m-%d")))
                model.site = record.get("site", "")
                model.activity = record.get("activity", "")
                model.narrative_text = record.get("narrative_text", "")
                model.actual_severity = str(record.get("actual_severity", "NONE"))
                model.contractor_involved = bool(record.get("contractor_involved", False))
                model.difficulty_category = str(record.get("difficulty_category", "standard"))

                # Serialize Pydantic objects to dict for JSON columns
                ext = record.get("extraction")
                model.extraction_json = ext.model_dump() if hasattr(ext, "model_dump") else ext

                assessment = record.get("assessment")
                model.assessment_json = assessment.model_dump() if hasattr(assessment, "model_dump") else assessment

                rules = record.get("rule_mappings", [])
                model.rule_mappings_json = [r.model_dump() if hasattr(r, "model_dump") else r for r in rules]

                chain = record.get("precursor_chain")
                model.precursor_chain_json = chain.model_dump() if hasattr(chain, "model_dump") else chain

                model.embedding_vector = record.get("embedding", [])
                model.extracted_images = record.get("extracted_images", [])
                model.version_tags = record.get("version_tags", {})

                model.review_status = str(record.get("review_status", "PENDING"))
                model.reviewed_by = record.get("reviewed_by")
                model.review_decision = str(record.get("review_decision")) if record.get("review_decision") else None
                model.review_comment = record.get("review_comment")

                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not persist report to relational DB (using memory cache): {e}")

        return record

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single report by ID."""
        return self._memory_cache.get(report_id)

    def list_reports(
        self,
        site: Optional[str] = None,
        activity: Optional[str] = None,
        sif_label: Optional[str] = None,
        rule: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 250
    ) -> List[Dict[str, Any]]:
        """Lists and filters reports."""
        results = list(self._memory_cache.values())

        if site:
            results = [r for r in results if r.get("site") == site]
        if activity:
            results = [r for r in results if r.get("activity") == activity]
        if sif_label:
            results = [r for r in results if self._get_sif_label(r) == sif_label]
        if rule:
            results = [r for r in results if any(self._rule_matches(m, rule) for m in r.get("rule_mappings", []))]
        if search:
            s_lower = search.lower()
            results = [
                r for r in results
                if s_lower in r.get("narrative_text", "").lower()
                or s_lower in r.get("title", "").lower()
                or s_lower in r.get("external_ref", "").lower()
            ]

        return results[:limit]

    def _get_sif_label(self, record: Dict[str, Any]) -> str:
        assessment = record.get("assessment")
        if hasattr(assessment, "sif_potential_label"):
            return assessment.sif_potential_label.value if hasattr(assessment.sif_potential_label, "value") else str(assessment.sif_potential_label)
        if isinstance(assessment, dict):
            return assessment.get("sif_potential_label", "LOW")
        return "LOW"

    def _rule_matches(self, mapping: Any, rule_id: str) -> bool:
        if hasattr(mapping, "life_saving_rule"):
            return mapping.life_saving_rule == rule_id
        if isinstance(mapping, dict):
            return mapping.get("life_saving_rule") == rule_id
        return False

    def log_audit_event(self, report_id: str, actor: str, event_type: str, payload: Dict[str, Any]):
        """Appends an immutable event to the audit trail."""
        log_entry = {
            "audit_id": str(datetime.now().timestamp()),
            "report_id": report_id,
            "actor": actor,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        self._audit_cache.append(log_entry)

        try:
            db = SessionLocal()
            try:
                audit_model = AuditLogModel(
                    report_id=report_id,
                    actor=actor,
                    event_type=event_type,
                    payload=payload
                )
                db.add(audit_model)
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

    def get_audit_trail(self, report_id: str) -> List[Dict[str, Any]]:
        """Returns the audit trail for a report."""
        return [log for log in self._audit_cache if log.get("report_id") == report_id]

    def clear_all(self):
        """Clears all reports and audit logs from database and cache."""
        self._memory_cache.clear()
        self._audit_cache.clear()
        try:
            db = SessionLocal()
            try:
                db.query(AuditLogModel).delete()
                db.query(ReportModel).delete()
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error clearing db: {e}")

repository = ReportRepository()
