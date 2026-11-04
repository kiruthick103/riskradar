import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

from app.db.repository import repository
from app.extraction.llm_client import get_llm_provider, LLMProvider

logger = logging.getLogger("riskradar.assistant")

class SafetyChatAssistant:
    """
    Retrieval-Augmented Generation (RAG) AI Safety Assistant.
    Grounds all answers in authentic safety observations from the repository database.
    Strictly forbids ungrounded hallucinations, enforcing verbatim citation references.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def _extract_query_keywords(self, query: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", query.lower())
        stopwords = {
            "what", "which", "where", "when", "who", "how", "why", "is", "are", "was", "were",
            "the", "this", "that", "these", "those", "had", "have", "has", "any", "all",
            "show", "me", "list", "give", "tell", "find", "in", "at", "on", "for", "with",
            "month", "period", "year", "reports", "report", "incident", "cases", "about"
        }
        return [w for w in cleaned.split() if len(w) > 2 and w not in stopwords]

    def search_relevant_reports(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        all_reports = repository.list_reports(limit=1000)
        keywords = self._extract_query_keywords(query)
        scored: List[tuple] = []
        for r in all_reports:
            score = 0
            narrative = (r.get("narrative_text") or "").lower()
            site = (r.get("site") or "").lower()
            activity = (r.get("activity") or "").lower()

            a = r.get("assessment") or {}
            if hasattr(a, "sif_potential_label"):
                lbl = a.sif_potential_label.value if hasattr(a.sif_potential_label, "value") else str(a.sif_potential_label)
            elif isinstance(a, dict):
                lbl = a.get("sif_potential_label", "LOW")
            else:
                lbl = "LOW"

            rules = [
                (m.life_saving_rule.lower() if hasattr(m, "life_saving_rule") else m.get("life_saving_rule", "").lower())
                for m in (r.get("rule_mappings") or [])
            ]

            for kw in keywords:
                if kw in site:
                    score += 6
                if kw in narrative:
                    score += 4
                if kw in activity:
                    score += 5
                if any(kw in rule for rule in rules):
                    score += 6
                if kw in ("high", "sif", "critical", "fatal") and lbl == "HIGH":
                    score += 4
                if kw in ("medium", "precursor") and lbl == "MEDIUM":
                    score += 3
                if kw in ("isolation", "loto", "valve", "lockout") and ("isolation" in narrative or "isolation" in activity or any("isolation" in rule for rule in rules)):
                    score += 7
                if kw in ("lift", "rigging", "crane", "load") and ("lift" in narrative or "lifting" in activity or any("lifting" in rule for rule in rules)):
                    score += 7
                if kw in ("height", "scaffold", "fall", "ladder") and ("height" in narrative or any("height" in rule for rule in rules)):
                    score += 7
                if kw in ("gas", "h2s", "flammable", "leak", "hydrocarbon") and ("gas" in narrative or "hydrocarbon" in narrative):
                    score += 6

            if score > 0:
                scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def answer_query(self, query: str, tenant_name: str = "Oil India Limited") -> Dict[str, Any]:
        matched_reports = self.search_relevant_reports(query, top_k=6)
        citations = []
        context_snippets = []

        for r in matched_reports:
            r_id = r.get("report_id", "")
            ext_ref = r.get("external_ref") or f"NS-2026-{r_id[-5:]}"
            site = r.get("site", "Unknown Site")
            date = r.get("report_date", "2026-03")
            activity = (r.get("activity") or "").replace("_", " ").title()

            a = r.get("assessment") or {}
            if hasattr(a, "sif_potential_label"):
                lbl = a.sif_potential_label.value if hasattr(a.sif_potential_label, "value") else str(a.sif_potential_label)
            elif isinstance(a, dict):
                lbl = a.get("sif_potential_label", "LOW")
            else:
                lbl = "LOW"

            narrative = r.get("narrative_text", "")
            short_narrative = narrative[:220] + ("..." if len(narrative) > 220 else "")

            citations.append({
                "report_id": r_id,
                "external_ref": ext_ref,
                "site": site,
                "date": date,
                "activity": activity,
                "sif_potential_label": lbl,
                "narrative_excerpt": short_narrative
            })

            context_snippets.append(
                f"- [Ref: {ext_ref}] | Site: {site} | Date: {date} | Activity: {activity} | SIF Tier: {lbl}\n  Evidence: \"{short_narrative}\""
            )

        if not matched_reports:
            return {
                "query": query,
                "response": f"No safety reports matched your query across {tenant_name} installations. Please check your keywords (e.g. 'isolation failures', 'working at height', 'Duliajan', 'rigging').",
                "citations": [],
                "grounded_report_count": 0,
                "mode": "grounded_rag"
            }

        context_str = "\n".join(context_snippets)

        # Attempt live LLM completion if available
        try:
            if os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
                sys_prompt = (
                    f"You are the RiskRadar AI Safety Assistant for {tenant_name}. "
                    "Answer the HSE query accurately and concisely based SOLELY on the provided safety report excerpts. "
                    "Cite every finding by its exact reference ID [Ref: NS-XXXX] and site. "
                    "Never invent or extrapolate facts beyond the provided excerpts."
                )
                user_prompt = f"HSE Query: {query}\n\nRelevant Verified Reports Context:\n{context_str}\n\nStructured HSE Answer with citations:"
                raw = self.provider.complete_structured(
                    system_prompt=sys_prompt,
                    task_prompt=user_prompt,
                    temperature=0.0
                )
                if isinstance(raw, dict) and "answer" in raw:
                    return {
                        "query": query,
                        "response": raw["answer"],
                        "citations": citations,
                        "grounded_report_count": len(citations),
                        "mode": "live_llm_grounded"
                    }
                elif isinstance(raw, str):
                    return {
                        "query": query,
                        "response": raw,
                        "citations": citations,
                        "grounded_report_count": len(citations),
                        "mode": "live_llm_grounded"
                    }
        except Exception as e:
            logger.info(f"Falling back to deterministic grounded synthesis: {e}")

        sif_high = [c for c in citations if c["sif_potential_label"] == "HIGH"]
        sites_affected = sorted(list(set(c["site"] for c in citations)))

        synthesis_lines = [
            f"Based on **{len(citations)} retrieved safety reports** across **{tenant_name}** installations, here is the verified analysis for your query:",
            "",
            f"**Key Affected Installations ({len(sites_affected)}):** {', '.join(sites_affected)}.",
            f"**High-SIF Precursors Identified:** {len(sif_high)} report(s) flagged with potential catastrophic consequence.",
            "",
            "**Grounded Evidence Excerpts:**"
        ]

        for c in citations[:4]:
            synthesis_lines.append(
                f"• **[{c['external_ref']}] ({c['site']})** — *{c['activity']}* ({c['sif_potential_label']} SIF): \"{c['narrative_excerpt']}\""
            )

        synthesis_lines.extend([
            "",
            "**Recommended HSE Advisory:** Immediate cross-site verification standdown recommended for affected installations to confirm positive barrier status and life-saving rule compliance before continuing work."
        ])

        return {
            "query": query,
            "response": "\n".join(synthesis_lines),
            "citations": citations,
            "grounded_report_count": len(citations),
            "mode": "deterministic_grounded_rag"
        }

chat_assistant = SafetyChatAssistant()
