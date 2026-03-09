from schemas.interview_prep import InterviewPrepResult, InterviewQuestion, empty_interview_prep
from services.interview_question_bank import (
    AI_SPECIAL_TEMPLATES,
    BASE_AI_SPECIAL_TEMPLATES,
    GENERAL_PRODUCT_TEMPLATES,
    SCENARIO_TEMPLATES,
)


GENERAL_CATEGORY = "通用产品题"
AI_CATEGORY = "AI产品专项题"
ROLE_CATEGORY = "岗位定向题"


class BaseQuestionGeneratorService:
    def generate(self, company: str, title: str, jd_analysis: dict, seed_questions: list[dict] | None = None) -> dict:
        raise NotImplementedError


class RuleBasedQuestionGeneratorService(BaseQuestionGeneratorService):
    def generate(self, company: str, title: str, jd_analysis: dict, seed_questions: list[dict] | None = None) -> dict:
        if not jd_analysis:
            return empty_interview_prep()

        questions = []
        seen = set()

        def add_question(category: str, item: dict):
            question_text = (item.get("question") or "").strip()
            if not question_text or question_text in seen:
                return
            seen.add(question_text)
            questions.append(
                InterviewQuestion(
                    question=question_text,
                    category=category,
                    why_this_may_be_asked=(item.get("why") or item.get("why_this_may_be_asked") or "").strip(),
                    suggested_points=[point.strip() for point in (item.get("points") or item.get("suggested_points") or []) if point.strip()],
                )
            )

        for item in GENERAL_PRODUCT_TEMPLATES[:4]:
            add_question(GENERAL_CATEGORY, item)

        for item in BASE_AI_SPECIAL_TEMPLATES[:3]:
            add_question(AI_CATEGORY, item)

        skill_tags = jd_analysis.get("skill_tags") or []
        for skill in skill_tags:
            for item in AI_SPECIAL_TEMPLATES.get(skill, [])[:2]:
                add_question(AI_CATEGORY, item)

        for tech in jd_analysis.get("technical_requirements") or []:
            topic = tech.get("topic") or ""
            mapped_skill = {
                "大模型": "模型理解",
                "Agent": "Agent系统理解",
                "RAG": "RAG系统理解",
                "评测": "评测体系",
            }.get(topic)
            if not mapped_skill:
                continue
            for item in AI_SPECIAL_TEMPLATES.get(mapped_skill, [])[:1]:
                add_question(AI_CATEGORY, item)

        for scenario in jd_analysis.get("scenario_tags") or []:
            for item in SCENARIO_TEMPLATES.get(scenario, [])[:2]:
                add_question(ROLE_CATEGORY, item)

        for seed in seed_questions or []:
            seed_question = (seed.get("question") or "").strip()
            if not seed_question or seed_question in seen:
                continue
            add_question(
                ROLE_CATEGORY,
                {
                    "question": seed_question,
                    "why": f"{company} 或相近产品岗的真实面经里出现过类似问题，值得优先准备。",
                    "points": self._build_seed_points(seed_question, title, jd_analysis),
                },
            )

        grouped = self._limit_by_category(questions)
        ordered = grouped[GENERAL_CATEGORY] + grouped[AI_CATEGORY] + grouped[ROLE_CATEGORY]
        return InterviewPrepResult(questions=ordered).to_dict()

    def _limit_by_category(self, questions: list[InterviewQuestion]) -> dict[str, list[InterviewQuestion]]:
        grouped = {
            GENERAL_CATEGORY: [],
            AI_CATEGORY: [],
            ROLE_CATEGORY: [],
        }
        for question in questions:
            bucket = grouped.get(question.category)
            if bucket is None:
                continue
            if len(bucket) >= 4:
                continue
            bucket.append(question)
        return grouped

    def _build_seed_points(self, question: str, title: str, jd_analysis: dict) -> list[str]:
        scenario_text = "、".join((jd_analysis.get("scenario_tags") or [])[:2]) or "当前岗位场景"
        keyword_text = "、".join((jd_analysis.get("keywords") or [])[:3]) or "岗位核心关键词"
        return [
            f"先结合 {title} 的业务目标解释题目背景",
            f"把问题拆回到 {scenario_text} 的真实用户场景",
            f"回答时尽量围绕 {keyword_text} 展开，不要只讲抽象方法论",
            "最好补一个可量化的指标或验证方式",
        ]


def get_question_generator_service() -> BaseQuestionGeneratorService:
    return RuleBasedQuestionGeneratorService()
