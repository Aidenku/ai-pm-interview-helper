from services.gap_analysis import get_gap_analysis_service
from services.jd_parser import get_jd_parser_service
from services.job_domain_analysis import get_job_domain_analysis_service
from services.llm_service import LLMServiceError, get_llm_service
from services.prompt_templates import (
    GAP_ANALYSIS_SYSTEM_PROMPT,
    INTERVIEW_QUESTIONS_SYSTEM_PROMPT,
    JD_PARSE_SYSTEM_PROMPT,
)
from services.question_generator import get_question_generator_service
from services.user_profile import get_user_profile_service


class AIFeatureService:
    def __init__(self):
        self.llm = get_llm_service()
        self.jd_parser = get_jd_parser_service()
        self.job_domain_analyzer = get_job_domain_analysis_service()
        self.gap_analyzer = get_gap_analysis_service()
        self.question_generator = get_question_generator_service()
        self.user_profile_service = get_user_profile_service()

    def parse_jd(self, company: str, title: str, jd_text: str) -> dict:
        fallback = self.jd_parser.parse_job(company=company, title=title, jd_text=jd_text)
        payload = {"company": company, "title": title, "jd_text": jd_text}
        return self._run_with_fallback(
            system_prompt=JD_PARSE_SYSTEM_PROMPT,
            payload=payload,
            fallback=fallback,
            normalizer=self._normalize_jd_parse,
        )

    def analyze_job_domain(self, company: str, title: str, jd_text: str) -> dict:
        data = self.job_domain_analyzer.analyze_job_domain(company=company, title=title, jd_text=jd_text)
        return {"data": data, "meta": {"source": "rule_engine", "used_fallback": False}}

    def analyze_gap(self, company: str, title: str, jd_text: str, jd_analysis: dict | None = None, user_profile: dict | None = None) -> dict:
        profile = self.user_profile_service.normalize_profile(user_profile or self.user_profile_service.get_default_profile())
        analysis = jd_analysis or self.jd_parser.parse_job(company=company, title=title, jd_text=jd_text)
        fallback = self.gap_analyzer.analyze(analysis, profile, company=company, title=title, jd_text=jd_text)
        payload = {
            "company": company,
            "title": title,
            "jd_text": jd_text,
            "jd_analysis": analysis,
            "user_profile": profile.to_dict(),
            "rule_based_gap": fallback,
        }
        if not self.llm.is_configured():
            return {"data": fallback, "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"}}

        try:
            raw = self.llm.generate_json(GAP_ANALYSIS_SYSTEM_PROMPT, payload)
            normalized = self._normalize_gap_analysis(raw)
            if not normalized:
                raise LLMServiceError("Empty normalized result")
            merged = self._merge_gap_analysis(fallback, normalized)
            return {"data": merged, "meta": {"source": "llm", "used_fallback": False}}
        except Exception as exc:
            return {
                "data": fallback,
                "meta": {"source": "fallback", "used_fallback": True, "reason": str(exc)},
            }

    def generate_interview_questions(self, company: str, title: str, jd_text: str, jd_analysis: dict | None = None, seed_questions: list[dict] | None = None) -> dict:
        analysis = jd_analysis or self.jd_parser.parse_job(company=company, title=title, jd_text=jd_text)
        fallback = self.question_generator.generate(company=company, title=title, jd_analysis=analysis, seed_questions=seed_questions or [])
        payload = {
            "company": company,
            "title": title,
            "jd_text": jd_text,
            "jd_analysis": analysis,
            "seed_questions": seed_questions or [],
        }
        return self._run_with_fallback(
            system_prompt=INTERVIEW_QUESTIONS_SYSTEM_PROMPT,
            payload=payload,
            fallback=fallback,
            normalizer=self._normalize_interview_questions,
        )

    def _run_with_fallback(self, system_prompt: str, payload: dict, fallback: dict, normalizer):
        if not self.llm.is_configured():
            return {"data": fallback, "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"}}
        try:
            raw = self.llm.generate_json(system_prompt, payload)
            normalized = normalizer(raw)
            if not normalized:
                raise LLMServiceError("Empty normalized result")
            return {"data": normalized, "meta": {"source": "llm", "used_fallback": False}}
        except Exception as exc:
            return {
                "data": fallback,
                "meta": {"source": "fallback", "used_fallback": True, "reason": str(exc)},
            }

    def _normalize_jd_parse(self, raw: dict) -> dict:
        technical = []
        for item in raw.get("technical_requirements") or []:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic") or "").strip()
            depth = str(item.get("depth") or "").strip()
            evidence = [str(x).strip() for x in (item.get("evidence") or []) if str(x).strip()]
            if not topic or depth not in {"了解", "中等", "较深"}:
                continue
            technical.append({"topic": topic, "depth": depth, "evidence": evidence[:3]})
        return {
            "keywords": self._normalize_string_list(raw.get("keywords"), 8),
            "skill_tags": self._normalize_string_list(raw.get("skill_tags"), 10),
            "technical_requirements": technical,
            "scenario_tags": self._normalize_string_list(raw.get("scenario_tags"), 6),
            "difficulty": self._normalize_enum(raw.get("difficulty"), {"入门", "中等", "较高"}, "中等"),
            "summary": str(raw.get("summary") or "").strip(),
        }

    def _normalize_gap_analysis(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            return {}
        evidence_raw = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
        return {
            "domain_gap": self._normalize_string_list(raw.get("domain_gap"), 4),
            "general_gap": self._normalize_string_list(raw.get("general_gap"), 4),
            "priority_gap": self._normalize_string_list(raw.get("priority_gap"), 4),
            "potential_strengths": self._normalize_string_list(raw.get("potential_strengths"), 5),
            "realistic_advice": self._normalize_string_list(raw.get("realistic_advice"), 4),
            "not_recommended_reason": str(raw.get("not_recommended_reason") or "").strip(),
            "summary": str(raw.get("summary") or "").strip(),
            "evidence": {
                "jd_signals": self._normalize_string_list(evidence_raw.get("jd_signals"), 6),
                "resume_signals": self._normalize_string_list(evidence_raw.get("resume_signals"), 6),
            },
        }

    def _merge_gap_analysis(self, fallback: dict, llm_data: dict) -> dict:
        merged = dict(fallback)
        merged["domain_gap"] = self._merge_lists(
            fallback.get("domain_gap") or [],
            llm_data.get("domain_gap") or [],
            4,
        )
        merged["general_gap"] = self._merge_lists(
            fallback.get("general_gap") or [],
            llm_data.get("general_gap") or [],
            4,
        )
        merged["priority_gap"] = self._merge_lists(
            fallback.get("priority_gap") or [],
            llm_data.get("priority_gap") or [],
            4,
        )
        merged["potential_strengths"] = self._merge_lists(
            fallback.get("potential_strengths") or [],
            llm_data.get("potential_strengths") or [],
            5,
        )
        merged["realistic_advice"] = self._merge_lists(
            fallback.get("realistic_advice") or [],
            llm_data.get("realistic_advice") or [],
            4,
        )
        merged["not_recommended_reason"] = fallback.get("not_recommended_reason") or llm_data.get("not_recommended_reason") or ""
        merged["summary"] = llm_data.get("summary") or fallback.get("summary") or fallback.get("advice") or ""
        merged["advice"] = merged["summary"]
        merged["evidence"] = {
            "jd_signals": self._merge_lists(
                (fallback.get("evidence") or {}).get("jd_signals") or [],
                (llm_data.get("evidence") or {}).get("jd_signals") or [],
                6,
            ),
            "resume_signals": self._merge_lists(
                (fallback.get("evidence") or {}).get("resume_signals") or [],
                (llm_data.get("evidence") or {}).get("resume_signals") or [],
                6,
            ),
        }
        return merged

    def _normalize_interview_questions(self, raw: dict) -> dict:
        questions = []
        for item in raw.get("questions") or []:
            if not isinstance(item, dict):
                continue
            category = self._normalize_enum(
                item.get("category"),
                {"通用产品题", "AI产品专项题", "岗位定向题"},
                "岗位定向题",
            )
            question = str(item.get("question") or "").strip()
            why = str(item.get("why_this_may_be_asked") or "").strip()
            points = self._normalize_string_list(item.get("suggested_points"), 5)
            if not question or not why or len(points) < 3:
                continue
            questions.append(
                {
                    "question": question,
                    "category": category,
                    "why_this_may_be_asked": why,
                    "suggested_points": points,
                }
            )
        return {"questions": questions[:12]}

    def _normalize_string_list(self, value, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result[:limit]

    def _merge_lists(self, first: list[str], second: list[str], limit: int) -> list[str]:
        result = []
        for item in list(first) + list(second):
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result[:limit]

    def _normalize_enum(self, value, allowed: set[str], default: str) -> str:
        text = str(value or "").strip()
        return text if text in allowed else default



def get_ai_feature_service() -> AIFeatureService:
    return AIFeatureService()
