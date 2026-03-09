from services.llm_service import LLMServiceError, get_llm_service
from services.mock_interview_bank import get_category_sequence, get_mode_config, get_question_bank
from services.prompt_templates import (
    MOCK_INTERVIEW_FEEDBACK_SYSTEM_PROMPT,
    MOCK_INTERVIEW_NEXT_QUESTION_SYSTEM_PROMPT,
)


class MockInterviewService:
    def __init__(self):
        self.llm = get_llm_service()
        self.question_bank = get_question_bank()

    def get_mode_options(self) -> list[dict]:
        return [get_mode_config(key).to_dict() for key in ("quick", "standard", "pressure")]

    def start_session(self, mode_key: str) -> dict:
        mode = get_mode_config(mode_key)
        question = self._get_fallback_question(mode.key, 0, [])
        return {
            "data": {
                "session": self._build_session_payload(mode, 1),
                "question": question,
                "finished": False,
                "mode_options": self.get_mode_options(),
            },
            "meta": {"source": "fallback", "used_fallback": True, "reason": "question_bank"},
        }

    def next_question(self, mode_key: str, question_index: int, asked_questions: list[str] | None = None, history: list[dict] | None = None) -> dict:
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

        asked = [str(item).strip() for item in (asked_questions or []) if str(item).strip()]
        fallback = self._get_fallback_question(mode.key, next_index - 1, asked)
        if not self.llm.is_configured():
            return {
                "data": {
                    "session": self._build_session_payload(mode, next_index),
                    "question": fallback,
                    "finished": False,
                },
                "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"},
            }

        payload = {
            "mode": mode.to_dict(),
            "next_question_number": next_index,
            "already_asked_questions": asked,
            "history": history or [],
            "target_category": self._get_target_category(mode.key, next_index - 1),
            "fallback_question": fallback,
        }
        try:
            raw = self.llm.generate_json(MOCK_INTERVIEW_NEXT_QUESTION_SYSTEM_PROMPT, payload)
            question = self._normalize_question(raw)
            if not question:
                raise LLMServiceError("invalid next question")
            return {
                "data": {
                    "session": self._build_session_payload(mode, next_index),
                    "question": question,
                    "finished": False,
                },
                "meta": {"source": "llm", "used_fallback": False},
            }
        except Exception as exc:
            return {
                "data": {
                    "session": self._build_session_payload(mode, next_index),
                    "question": fallback,
                    "finished": False,
                },
                "meta": {"source": "fallback", "used_fallback": True, "reason": str(exc)},
            }

    def evaluate_answer(self, mode_key: str, question: dict, answer: str, history: list[dict] | None = None) -> dict:
        sanitized_question = self._normalize_question(question) or self._get_fallback_question(mode_key, 0, [])
        fallback = self._build_fallback_feedback(mode_key, sanitized_question, answer)
        if not self.llm.is_configured():
            return {"data": fallback, "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"}}

        payload = {
            "mode": get_mode_config(mode_key).to_dict(),
            "question": sanitized_question,
            "answer": answer,
            "history": history or [],
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

    def _get_fallback_question(self, mode_key: str, question_offset: int, asked_questions: list[str]) -> dict:
        target_category = self._get_target_category(mode_key, question_offset)
        ordered_categories = [target_category, "产品基础题", "AI专项题", "项目深挖题"]
        for category in ordered_categories:
            seen = set(asked_questions)
            for item in self.question_bank.get(category, []):
                if item.question_id not in seen:
                    return item.to_dict()
        first_category = ordered_categories[0]
        return self.question_bank[first_category][question_offset % len(self.question_bank[first_category])].to_dict()

    def _build_fallback_feedback(self, mode_key: str, question: dict, answer: str) -> dict:
        text = (answer or "").strip()
        length = len(text)
        lowered = text.lower()
        structure_hits = sum(keyword in text for keyword in ["首先", "其次", "最后", "第一", "第二", "第三"]) + sum(
            keyword in lowered for keyword in ["first", "second", "finally"]
        )
        metric_hits = sum(keyword in text for keyword in ["指标", "转化", "留存", "点击", "实验", "评测", "召回", "排序"])
        ai_hits = sum(keyword in lowered for keyword in ["prompt", "rag", "agent", "workflow", "模型", "评测", "检索"])

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
        if question.get("category") == "项目深挖题":
            tips.append("项目题尽量按背景、问题、方案、结果四段说，避免只描述功能。")
        if question.get("category") == "AI专项题":
            tips.append("AI 题需要同时讲概念、适用边界和落地场景，不能只给定义。")
        tips = tips[:3] or ["保持结论先行，并尽量给出指标、场景和取舍逻辑。"]

        feedback = "你的回答已经覆盖了题目方向，但表达还有提升空间。"
        if relevance == "较强" and structure == "较强" and depth == "较强":
            feedback = "这段回答整体完整，既有结论，也有拆解逻辑和一定深度，已经接近正式面试可用水平。"
        elif depth == "较弱":
            feedback = "回答方向基本对，但深度还不够，建议补充产品判断依据、指标设计和AI系统层面的理解。"
        elif structure == "较弱":
            feedback = "内容有点散，建议先给结论，再分点展开，这样面试官更容易快速抓住你的思路。"

        follow_up = ""
        if get_mode_config(mode_key).pressure_mode:
            follow_up = self._build_follow_up_question(question)

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
            "follow_up_question": follow_up,
        }

    def _build_follow_up_question(self, question: dict) -> str:
        category = question.get("category", "")
        if category == "产品基础题":
            return "如果资源再砍掉一半，你的优先级判断会怎么变？"
        if category == "AI专项题":
            return "如果线上效果没有提升，你会优先怀疑模型、检索、提示词还是产品交互？为什么？"
        return "如果让你重做一次这个项目，你会先改哪一个关键节点？为什么？"

    def _normalize_question(self, raw: dict | None) -> dict | None:
        if not isinstance(raw, dict):
            return None
        category = str(raw.get("category") or "").strip()
        if category not in {"产品基础题", "AI专项题", "项目深挖题"}:
            return None
        question = str(raw.get("question") or "").strip()
        if not question:
            return None
        focus_points = self._normalize_string_list(raw.get("focus_points"), 4)
        return {
            "question_id": str(raw.get("question_id") or f"generated-{abs(hash(question)) % 100000}"),
            "question": question,
            "category": category,
            "focus_points": focus_points,
            "answer_framework": str(raw.get("answer_framework") or "结论先行 + 分点回答").strip(),
            "why_this_matters": str(raw.get("why_this_matters") or "这道题用来考察 AI PM 的通用能力。\n").strip(),
        }

    def _normalize_feedback(self, raw: dict | None, question: dict) -> dict | None:
        if not isinstance(raw, dict):
            return None
        evaluation = raw.get("evaluation") if isinstance(raw.get("evaluation"), dict) else {}
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
            "follow_up_question": str(raw.get("follow_up_question") or "").strip(),
        }
        if not result["feedback"]:
            return None
        if len(result["improvement_tips"]) < 2:
            fallback_tips = self._build_fallback_feedback("quick", question, "").get("improvement_tips", [])
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


def get_mock_interview_service() -> MockInterviewService:
    return MockInterviewService()
