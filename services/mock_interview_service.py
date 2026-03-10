from services.llm_service import LLMServiceError, get_llm_service
from services.mock_interview_bank import (
    get_business_question_template,
    get_category_sequence,
    get_mode_config,
    get_question_bank,
)
from services.prompt_templates import (
    MOCK_INTERVIEW_FEEDBACK_SYSTEM_PROMPT,
    MOCK_INTERVIEW_NEXT_QUESTION_SYSTEM_PROMPT,
)


QUESTION_STRATEGY_PLANS = {
    "quick": ["universal", "job_specific", "resume_deep_dive", "job_specific", "universal"],
    "standard": ["universal", "job_specific", "resume_deep_dive", "universal", "job_specific", "universal", "resume_deep_dive", "job_specific", "universal", "job_specific"],
    "pressure": ["resume_deep_dive", "job_specific", "universal", "resume_deep_dive", "job_specific", "universal", "job_specific", "resume_deep_dive"],
}


class MockInterviewService:
    def __init__(self):
        self.llm = get_llm_service()
        self.question_bank = get_question_bank()

    def get_mode_options(self) -> list[dict]:
        return [get_mode_config(key).to_dict() for key in ("quick", "standard", "pressure")]

    def start_session(self, mode_key: str, profile_analysis: dict | None = None, job_context: dict | None = None) -> dict:
        mode = get_mode_config(mode_key)
        result = self._generate_question(
            mode_key=mode.key,
            question_number=1,
            asked_questions=[],
            history=None,
            profile_analysis=profile_analysis,
            job_context=job_context,
        )
        return {
            "data": {
                "session": self._build_session_payload(mode, 1),
                "question": result["question"],
                "finished": False,
                "mode_options": self.get_mode_options(),
            },
            "meta": result["meta"],
        }

    def next_question(
        self,
        mode_key: str,
        question_index: int,
        asked_questions: list[str] | None = None,
        history: list[dict] | None = None,
        profile_analysis: dict | None = None,
        job_context: dict | None = None,
    ) -> dict:
        mode = get_mode_config(mode_key)
        next_index = max(0, int(question_index)) + 1
        if next_index > mode.total_questions:
            return {
                "data": {
                    "session": self._build_session_payload(mode, mode.total_questions),
                    "question": None,
                    "finished": True,
                },
                "meta": {"source": "fallback", "used_fallback": True, "reason": "session_complete"},
            }

        result = self._generate_question(
            mode_key=mode.key,
            question_number=next_index,
            asked_questions=asked_questions or [],
            history=history,
            profile_analysis=profile_analysis,
            job_context=job_context,
        )
        return {
            "data": {
                "session": self._build_session_payload(mode, next_index),
                "question": result["question"],
                "finished": False,
            },
            "meta": result["meta"],
        }

    def evaluate_answer(
        self,
        mode_key: str,
        question: dict,
        answer: str,
        history: list[dict] | None = None,
        profile_analysis: dict | None = None,
        job_context: dict | None = None,
    ) -> dict:
        sanitized_question = self._normalize_question(question) or self._ensure_question_shape(self._get_fallback_question(mode_key, 0, [], profile_analysis, job_context))
        fallback = self._build_fallback_feedback(mode_key, sanitized_question, answer, profile_analysis, job_context)
        if not self.llm.is_configured():
            return {"data": fallback, "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"}}

        payload = {
            "mode": get_mode_config(mode_key).to_dict(),
            "question": sanitized_question,
            "answer": answer,
            "history": history or [],
            "allow_follow_up": sanitized_question.get("question_kind") != "follow_up",
            "profile_analysis": self._compact_profile(profile_analysis),
            "job_context": self._compact_job_context(job_context),
        }
        try:
            raw = self.llm.generate_json(MOCK_INTERVIEW_FEEDBACK_SYSTEM_PROMPT, payload)
            feedback = self._normalize_feedback(raw, sanitized_question)
            if not feedback:
                raise LLMServiceError("invalid interview feedback")
            return {"data": feedback, "meta": {"source": "llm", "used_fallback": False}}
        except Exception as exc:
            return {
                "data": fallback,
                "meta": {"source": "fallback", "used_fallback": True, "reason": str(exc)},
            }

    def _generate_question(self, mode_key: str, question_number: int, asked_questions: list[str], history: list[dict] | None, profile_analysis: dict | None, job_context: dict | None) -> dict:
        mode = get_mode_config(mode_key)
        offset = max(0, question_number - 1)
        asked = [str(item).strip() for item in (asked_questions or []) if str(item).strip()]
        fallback = self._ensure_question_shape(self._get_fallback_question(mode.key, offset, asked, profile_analysis, job_context))
        if not self.llm.is_configured():
            return {
                "question": fallback,
                "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"},
            }

        payload = {
            "mode": mode.to_dict(),
            "next_question_number": question_number,
            "already_asked_questions": asked,
            "history": history or [],
            "target_category": self._get_target_category(mode.key, offset),
            "question_strategy": self._get_question_strategy(mode.key, offset, profile_analysis, job_context),
            "profile_analysis": self._compact_profile(profile_analysis),
            "job_context": self._compact_job_context(job_context),
            "fallback_question": fallback,
        }
        try:
            raw = self.llm.generate_json(MOCK_INTERVIEW_NEXT_QUESTION_SYSTEM_PROMPT, payload)
            question = self._normalize_question(raw)
            if not question:
                raise LLMServiceError("invalid next question")
            return {"question": question, "meta": {"source": "llm", "used_fallback": False}}
        except Exception as exc:
            return {
                "question": fallback,
                "meta": {"source": "fallback", "used_fallback": True, "reason": str(exc)},
            }

    def _build_session_payload(self, mode, current_index: int) -> dict:
        return {
            "mode": mode.to_dict(),
            "current_index": current_index,
            "total_questions": mode.total_questions,
            "progress_text": f"第 {current_index} 题 / 共 {mode.total_questions} 题",
        }

    def _get_target_category(self, mode_key: str, question_offset: int) -> str:
        sequence = get_category_sequence(mode_key)
        if not sequence:
            return "产品基础题"
        return sequence[min(question_offset, len(sequence) - 1)]

    def _get_question_strategy(self, mode_key: str, question_offset: int, profile_analysis: dict | None, job_context: dict | None) -> str:
        plan = QUESTION_STRATEGY_PLANS.get(mode_key, QUESTION_STRATEGY_PLANS["quick"])
        strategy = plan[min(question_offset, len(plan) - 1)]
        if strategy == "job_specific" and not self._has_job_context(job_context):
            return "universal"
        if strategy == "resume_deep_dive" and not self._has_profile_context(profile_analysis):
            return "universal"
        return strategy

    def _get_fallback_question(self, mode_key: str, question_offset: int, asked_questions: list[str], profile_analysis: dict | None, job_context: dict | None) -> dict:
        strategy = self._get_question_strategy(mode_key, question_offset, profile_analysis, job_context)
        target_category = self._get_target_category(mode_key, question_offset)
        if strategy == "job_specific":
            question = self._build_job_specific_question(target_category, job_context, asked_questions)
            if question:
                return question
        if strategy == "resume_deep_dive":
            question = self._build_resume_deep_dive_question(target_category, profile_analysis, job_context, asked_questions)
            if question:
                return question
        ordered_categories = [target_category, "产品基础题", "AI专项题", "项目深挖题"]
        for category in ordered_categories:
            seen = set(asked_questions)
            for item in self.question_bank.get(category, []):
                if item.question_id not in seen:
                    question = item.to_dict()
                    question["question_source"] = "universal"
                    question["context_label"] = "通用题"
                    return question
        first_category = ordered_categories[0]
        question = self.question_bank[first_category][question_offset % len(self.question_bank[first_category])].to_dict()
        question["question_source"] = "universal"
        question["context_label"] = "通用题"
        return question

    def _build_job_specific_question(self, target_category: str, job_context: dict | None, asked_questions: list[str]) -> dict | None:
        domain = self._extract_job_domain(job_context)
        if not domain:
            return None
        template = get_business_question_template(domain, target_category)
        if not template:
            return None
        company = str((job_context or {}).get("company") or "目标公司").strip()
        title = str((job_context or {}).get("title") or "目标岗位").strip()
        question_id = f"job-{domain}-{target_category}"
        if question_id in set(asked_questions):
            question_id = f"job-{domain}-{target_category}-{len(asked_questions)}"
        return {
            "question_id": question_id,
            "question": template["question"].format(company=company, title=title),
            "category": target_category,
            "focus_points": list(template["focus_points"]),
            "answer_framework": template["framework"],
            "why_this_matters": template["why"],
            "question_kind": "main",
            "parent_question_id": "",
            "question_source": "job_specific",
            "context_label": f"岗位业务面 · {domain}",
        }

    def _build_resume_deep_dive_question(self, target_category: str, profile_analysis: dict | None, job_context: dict | None, asked_questions: list[str]) -> dict | None:
        profile = profile_analysis or {}
        anchor = self._extract_resume_anchor(profile)
        if not anchor:
            return None
        strong_domain = (profile.get("strong_domains") or [""])[0]
        target_domain = self._extract_job_domain(job_context)
        question_id = f"resume-{abs(hash(anchor)) % 100000}"
        if question_id in set(asked_questions):
            question_id = f"resume-{abs(hash(anchor + str(len(asked_questions)))) % 100000}"

        if target_domain and strong_domain and target_domain != strong_domain:
            question = f"你的经历更偏 {strong_domain}。如果现在投 {target_domain} 方向岗位，你会迁移哪些方法论？请结合“{anchor}”具体讲。"
            focus_points = ["真实项目细节", "方法迁移", "业务约束", "指标验证"]
            why = "这道题用来判断你能否把已有经历迁移到目标岗位，而不是只讲通用能力。"
        else:
            question = f"你提到做过“{anchor}”。请具体讲你负责的目标、关键决策、结果指标，以及你本人起到的作用。"
            focus_points = ["本人职责", "关键决策", "结果指标", "复盘反思"]
            why = "简历深挖题重点看你是否真的做过，而不是只会复述项目名称。"

        return {
            "question_id": question_id,
            "question": question,
            "category": target_category if target_category in {"项目深挖题", "产品基础题", "AI专项题"} else "项目深挖题",
            "focus_points": focus_points,
            "answer_framework": "先讲背景，再讲你负责什么、怎么做、结果如何",
            "why_this_matters": why,
            "question_kind": "main",
            "parent_question_id": "",
            "question_source": "resume_deep_dive",
            "context_label": "简历深挖题",
        }

    def _build_fallback_feedback(self, mode_key: str, question: dict, answer: str, profile_analysis: dict | None, job_context: dict | None) -> dict:
        text = (answer or "").strip()
        length = len(text)
        lowered = text.lower()
        structure_hits = sum(keyword in text for keyword in ["首先", "其次", "最后", "第一", "第二", "第三"]) + sum(
            keyword in lowered for keyword in ["first", "second", "finally"]
        )
        metric_hits = sum(keyword in text for keyword in ["指标", "转化", "留存", "点击", "实验", "评测", "召回", "排序", "roi", "ctr"])
        ai_hits = sum(keyword in lowered for keyword in ["prompt", "rag", "agent", "workflow", "模型", "评测", "检索", "召回", "排序"])

        relevance = "较强" if length >= 90 else "一般" if length >= 45 else "较弱"
        structure = "较强" if structure_hits >= 2 else "一般" if structure_hits >= 1 else "较弱"
        depth_score = metric_hits + ai_hits + (1 if mode_key == "pressure" and length >= 120 else 0)
        depth = "较强" if depth_score >= 3 else "一般" if depth_score >= 1 else "较弱"

        tips = []
        if structure == "较弱":
            tips.append("先给结论，再按 2 到 3 个要点展开，避免想到哪说到哪。")
        if relevance == "较弱":
            tips.append("回答时先回到题目本身，明确你在解决什么问题、服务谁、目标是什么。")
        if depth == "较弱":
            tips.append("多补充指标、实验方法、系统链路或取舍逻辑，体现 AI PM 的分析深度。")
        if question.get("question_source") == "resume_deep_dive":
            tips.append("简历深挖题必须讲清你本人负责部分、结果指标和失败复盘，不能只讲团队做了什么。")
        if question.get("question_source") == "job_specific":
            tips.append("岗位业务题要回到该岗位场景的核心指标和业务取舍，不要只讲通用产品框架。")
        if question.get("category") == "AI专项题":
            tips.append("AI 题需要同时讲概念、适用边界和落地场景，不能只给定义。")
        tips = self._unique(tips)[:4] or ["保持结论先行，并尽量给出指标、场景和取舍逻辑。"]

        feedback = "你的回答已经覆盖了题目方向，但表达还有提升空间。"
        if question.get("question_source") == "resume_deep_dive" and depth == "较弱":
            feedback = "这道题本质上在验证你是否真的做过这段经历。当前回答更像概述，缺少你本人决策、结果指标和复盘细节。"
        elif question.get("question_source") == "job_specific" and depth == "较弱":
            feedback = "你有一定产品思路，但还没真正进入该岗位业务场景。需要把回答落到具体链路、指标和权衡。"
        elif relevance == "较强" and structure == "较强" and depth == "较强":
            feedback = "这段回答整体完整，既有结论，也有拆解逻辑和一定深度，已经接近正式面试可用水平。"
        elif depth == "较弱":
            feedback = "回答方向基本对，但深度还不够，建议补充产品判断依据、指标设计和系统层面的理解。"
        elif structure == "较弱":
            feedback = "内容有点散，建议先给结论，再分点展开，这样面试官更容易快速抓住你的思路。"

        follow_up = None
        if question.get("question_kind") != "follow_up":
            follow_up = self._build_follow_up_payload(mode_key, question, relevance, structure, depth, profile_analysis, job_context)

        return {
            "question": question.get("question", ""),
            "category": question.get("category", "产品基础题"),
            "evaluation": {
                "relevance": relevance,
                "structure": structure,
                "depth": depth,
            },
            "feedback": feedback,
            "improvement_tips": tips,
            "follow_up": follow_up,
            "follow_up_question": (follow_up or {}).get("question", ""),
        }

    def _build_follow_up_payload(self, mode_key: str, question: dict, relevance: str, structure: str, depth: str, profile_analysis: dict | None, job_context: dict | None) -> dict | None:
        should_follow_up = get_mode_config(mode_key).pressure_mode or structure == "较弱" or depth == "较弱"
        if not should_follow_up:
            return None

        focus_points = []
        if structure == "较弱":
            focus_points.extend(["结论先行", "结构化表达"])
        if depth == "较弱":
            focus_points.extend(["指标设计", "取舍逻辑", "系统链路"])
        if relevance == "较弱":
            focus_points.append("回到题目本身")
        if not focus_points:
            focus_points = ["关键判断依据", "案例拆解"]

        category = question.get("category", "产品基础题")
        source = question.get("question_source") or "universal"
        if source == "resume_deep_dive":
            question_text = "刚才这段经历里，真正由你拍板的决策是什么？如果结果没有达到预期，你会怎么复盘？"
            context_label = "简历追问"
        elif source == "job_specific":
            domain = self._extract_job_domain(job_context)
            question_text = self._build_job_specific_follow_up(domain, category)
            context_label = f"岗位追问 · {domain or '业务面'}"
        elif category == "产品基础题":
            question_text = "如果业务目标和用户价值发生冲突，你会怎么做取舍？请给出判断顺序。"
            context_label = "通用追问"
        elif category == "AI专项题":
            question_text = "如果线上效果没有提升，你会先排查模型、检索、提示词还是产品交互？为什么？"
            context_label = "通用追问"
        else:
            question_text = "如果让你重做一次这个项目，你会优先重做哪个节点？你会用什么指标验证优化是否有效？"
            context_label = "通用追问"

        return {
            "question_id": f"followup-{question.get('question_id', 'unknown')}",
            "question": question_text,
            "category": category,
            "focus_points": self._unique(focus_points)[:4],
            "answer_framework": "先结论，再讲依据和取舍",
            "why_this_matters": "这道追问用于进一步验证你的结构化表达和分析深度。",
            "question_kind": "follow_up",
            "parent_question_id": str(question.get("question_id") or ""),
            "question_source": source,
            "context_label": context_label,
        }

    def _build_job_specific_follow_up(self, domain: str | None, category: str) -> str:
        if domain == "广告商业化产品":
            return "如果 CTR 提升但 ROI 继续下滑，你会优先动流量策略、创意策略还是转化链路？为什么？"
        if domain == "AI搜索产品":
            return "如果用户说答案不准，你会怎么区分是 query 理解问题、召回问题还是生成问题？"
        if domain == "AI陪伴/社交产品":
            return "如果短期活跃不错但长期留存不行，你会优先调整记忆机制、人设设计还是互动节奏？"
        if domain == "推荐策略产品":
            return "如果点击率和停留时长方向相反，你会用什么原则决定下一轮策略优化？"
        if domain == "企业服务产品":
            return "如果客户很想要定制能力，但平台化成本很高，你会怎么判断要不要做？"
        if category == "AI专项题":
            return "如果线上效果没有提升，你会先排查模型、检索、提示词还是产品交互？为什么？"
        if category == "项目深挖题":
            return "如果让你重做一次这个项目，你会优先重做哪个节点？你会用什么指标验证优化是否有效？"
        return "如果业务目标和用户价值发生冲突，你会怎么做取舍？请给出判断顺序。"

    def _ensure_question_shape(self, question: dict) -> dict:
        normalized = dict(question)
        normalized.setdefault("question_kind", "main")
        normalized.setdefault("parent_question_id", "")
        normalized.setdefault("focus_points", [])
        normalized.setdefault("answer_framework", "结论先行 + 分点回答")
        normalized.setdefault("why_this_matters", "这道题用来考察 AI PM 的通用能力。")
        normalized.setdefault("question_source", "universal")
        normalized.setdefault("context_label", "通用题")
        return normalized

    def _normalize_question(self, raw: dict | None) -> dict | None:
        if not isinstance(raw, dict):
            return None
        category = str(raw.get("category") or "").strip()
        if category not in {"产品基础题", "AI专项题", "项目深挖题"}:
            return None
        question = str(raw.get("question") or "").strip()
        if not question:
            return None
        question_kind = str(raw.get("question_kind") or "main").strip()
        if question_kind not in {"main", "follow_up"}:
            question_kind = "main"
        question_source = str(raw.get("question_source") or "universal").strip()
        if question_source not in {"universal", "job_specific", "resume_deep_dive"}:
            question_source = "universal"
        focus_points = self._normalize_string_list(raw.get("focus_points"), 4)
        return {
            "question_id": str(raw.get("question_id") or f"generated-{abs(hash(question)) % 100000}"),
            "question": question,
            "category": category,
            "focus_points": focus_points,
            "answer_framework": str(raw.get("answer_framework") or "结论先行 + 分点回答").strip(),
            "why_this_matters": str(raw.get("why_this_matters") or "这道题用来考察 AI PM 的通用能力。").strip(),
            "question_kind": question_kind,
            "parent_question_id": str(raw.get("parent_question_id") or "").strip(),
            "question_source": question_source,
            "context_label": str(raw.get("context_label") or self._default_context_label(question_source)).strip(),
        }

    def _normalize_feedback(self, raw: dict | None, question: dict) -> dict | None:
        if not isinstance(raw, dict):
            return None
        evaluation = raw.get("evaluation") if isinstance(raw.get("evaluation"), dict) else {}
        follow_up = self._normalize_question(raw.get("follow_up")) if isinstance(raw.get("follow_up"), dict) else None
        if follow_up:
            follow_up["question_kind"] = "follow_up"
            follow_up["parent_question_id"] = str(question.get("question_id") or follow_up.get("parent_question_id") or "")
        if question.get("question_kind") == "follow_up":
            follow_up = None
        result = {
            "question": question.get("question", ""),
            "category": question.get("category", "产品基础题"),
            "evaluation": {
                "relevance": self._normalize_level(evaluation.get("relevance")),
                "structure": self._normalize_level(evaluation.get("structure")),
                "depth": self._normalize_level(evaluation.get("depth")),
            },
            "feedback": str(raw.get("feedback") or "").strip(),
            "improvement_tips": self._normalize_string_list(raw.get("improvement_tips"), 4),
            "follow_up": follow_up,
            "follow_up_question": (follow_up or {}).get("question", ""),
        }
        if not result["feedback"]:
            return None
        if len(result["improvement_tips"]) < 2:
            fallback_tips = self._build_fallback_feedback("quick", question, "", None, None).get("improvement_tips", [])
            result["improvement_tips"] = fallback_tips
        return result

    def _normalize_level(self, value) -> str:
        text = str(value or "").strip()
        return text if text in {"较弱", "一般", "较强"} else "一般"

    def _normalize_string_list(self, value, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        items = []
        for item in value:
            text = str(item).strip()
            if text and text not in items:
                items.append(text)
        return items[:limit]

    def _has_job_context(self, job_context: dict | None) -> bool:
        job = job_context or {}
        return bool(job.get("title") or job.get("jd_text") or self._extract_job_domain(job_context))

    def _has_profile_context(self, profile_analysis: dict | None) -> bool:
        profile = profile_analysis or {}
        return bool(profile.get("project_experiences") or profile.get("ai_experiences") or profile.get("product_experiences") or profile.get("summary"))

    def _compact_profile(self, profile_analysis: dict | None) -> dict:
        profile = profile_analysis or {}
        return {
            "summary": str(profile.get("summary") or "").strip(),
            "project_experiences": (profile.get("project_experiences") or [])[:3],
            "ai_experiences": (profile.get("ai_experiences") or [])[:2],
            "product_experiences": (profile.get("product_experiences") or [])[:2],
            "strong_domains": (profile.get("strong_domains") or [])[:3],
            "transferable_domains": (profile.get("transferable_domains") or [])[:3],
        }

    def _compact_job_context(self, job_context: dict | None) -> dict:
        job = job_context or {}
        domain = self._extract_job_domain(job)
        jd_analysis = job.get("jd_analysis") if isinstance(job.get("jd_analysis"), dict) else {}
        return {
            "job_id": job.get("id"),
            "company": str(job.get("company") or "").strip(),
            "title": str(job.get("title") or "").strip(),
            "primary_domain": domain,
            "scenario_tags": (jd_analysis.get("scenario_tags") or [])[:3],
            "skill_tags": (jd_analysis.get("skill_tags") or [])[:4],
            "jd_summary": str(jd_analysis.get("summary") or "").strip(),
        }

    def _extract_job_domain(self, job_context: dict | None) -> str:
        job = job_context or {}
        for key in [
            (job.get("job_domain_analysis") or {}).get("primary_domain") if isinstance(job.get("job_domain_analysis"), dict) else "",
            ((job.get("gap_analysis") or {}).get("job_domain_analysis") or {}).get("primary_domain") if isinstance(job.get("gap_analysis"), dict) else "",
        ]:
            if key:
                return str(key).strip()
        jd_analysis = job.get("jd_analysis") if isinstance(job.get("jd_analysis"), dict) else {}
        scenarios = jd_analysis.get("scenario_tags") or []
        if scenarios:
            scenario = str(scenarios[0]).strip()
            mapping = {
                "AI搜索": "AI搜索产品",
                "广告商业化": "广告商业化产品",
                "AI陪伴": "AI陪伴/社交产品",
                "内容社区": "AI陪伴/社交产品",
                "平台工具": "平台工具产品",
                "增长策略": "增长产品",
            }
            return mapping.get(scenario, "通用AI产品")
        return ""

    def _extract_resume_anchor(self, profile_analysis: dict) -> str:
        for bucket in ["project_experiences", "ai_experiences", "product_experiences"]:
            items = profile_analysis.get(bucket) or []
            if items:
                text = str(items[0]).strip()
                return text[:40]
        summary = str(profile_analysis.get("summary") or "").strip()
        return summary[:40] if summary else ""

    def _default_context_label(self, source: str) -> str:
        mapping = {
            "universal": "通用题",
            "job_specific": "岗位业务面",
            "resume_deep_dive": "简历深挖题",
        }
        return mapping.get(source, "通用题")

    def _unique(self, items: list[str]) -> list[str]:
        result = []
        for item in items:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result


def get_mock_interview_service() -> MockInterviewService:
    return MockInterviewService()
