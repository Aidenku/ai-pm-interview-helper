from schemas.jd_analysis import JDAnalysisResult, TechnicalRequirement, empty_analysis
from services.jd_tag_rules import (
    DIFFICULTY_RULES,
    KEYWORD_RULES,
    SCENARIO_RULES,
    SKILL_RULES,
    TECHNICAL_RULES,
)


class BaseJDParserService:
    def parse_job(self, company: str, title: str, jd_text: str) -> dict:
        raise NotImplementedError


class MockJDParserService(BaseJDParserService):
    def parse_job(self, company: str, title: str, jd_text: str) -> dict:
        text = f"{company or ''}\n{title or ''}\n{jd_text or ''}"
        normalized = text.lower()
        if not normalized.strip():
            return empty_analysis()

        keywords = self._match_rule_labels(normalized, KEYWORD_RULES, 8)
        skill_tags = self._match_rule_labels(normalized, SKILL_RULES, 10)
        scenario_tags = self._match_rule_labels(normalized, SCENARIO_RULES, 6)
        technical_requirements = self._build_technical_requirements(normalized)
        difficulty = self._judge_difficulty(normalized, skill_tags, technical_requirements)
        summary = self._build_summary(title, keywords, skill_tags, technical_requirements, scenario_tags, difficulty)

        return JDAnalysisResult(
            keywords=keywords,
            skill_tags=skill_tags,
            technical_requirements=technical_requirements,
            scenario_tags=scenario_tags,
            difficulty=difficulty,
            summary=summary,
        ).to_dict()

    def _match_rule_labels(self, text: str, rule_map: dict[str, list[str]], limit: int) -> list[str]:
        matches = []
        for label, patterns in rule_map.items():
            if any(pattern.lower() in text for pattern in patterns):
                matches.append(label)
        return matches[:limit]

    def _build_technical_requirements(self, text: str) -> list[TechnicalRequirement]:
        requirements = []
        for topic, rules in TECHNICAL_RULES.items():
            evidence = []
            score = 0

            for pattern in rules["base"]:
                if pattern.lower() in text:
                    score = max(score, 1)
                    if pattern not in evidence:
                        evidence.append(pattern)

            for pattern in rules["deep"]:
                if pattern.lower() in text:
                    score = max(score, 2)
                    if pattern not in evidence:
                        evidence.append(pattern)

            if topic in ("搜索", "推荐", "评测") and any(pattern.lower() in text for pattern in rules["base"] + rules["deep"]):
                score = max(score, 2)

            if score == 0:
                continue
            if score == 1:
                depth = "了解"
            elif score == 2:
                depth = "中等"
            else:
                depth = "较深"
            requirements.append(TechnicalRequirement(topic=topic, depth=depth, evidence=evidence[:3]))
        return requirements

    def _judge_difficulty(self, text: str, skill_tags: list[str], technical_requirements: list[TechnicalRequirement]) -> str:
        score = 0
        if len(skill_tags) >= 6:
            score += 2
        elif len(skill_tags) >= 4:
            score += 1

        for item in technical_requirements:
            if item.depth == "较深":
                score += 2
            elif item.depth == "中等":
                score += 1

        if any(pattern in text for pattern in DIFFICULTY_RULES["较高"]):
            score += 2
        elif any(pattern in text for pattern in DIFFICULTY_RULES["中等"]):
            score += 1

        if "英语" in text or "英文" in text or "global" in text:
            score += 1

        if score >= 5:
            return "较高"
        if score >= 2:
            return "中等"
        return "入门"

    def _build_summary(
        self,
        title: str,
        keywords: list[str],
        skill_tags: list[str],
        technical_requirements: list[TechnicalRequirement],
        scenario_tags: list[str],
        difficulty: str,
    ) -> str:
        title_text = title or "该岗位"
        keyword_text = "、".join(keywords[:3]) or "产品需求分析与方案推进"
        skill_text = "、".join(skill_tags[:4]) or "需求分析、项目推进"
        scenario_text = "、".join(scenario_tags[:2]) or "通用产品场景"

        if technical_requirements:
            tech_text = "；".join([f"{item.topic}{item.depth}" for item in technical_requirements[:3]])
        else:
            tech_text = "更强调通用产品能力，技术深度要求相对有限"

        sentences = [
            f"{title_text}主要聚焦{scenario_text}相关的产品问题，关键词集中在{keyword_text}。",
            f"岗位最看重{skill_text}等基础能力，候选人需要能把问题拆解、方案设计和推动落地串起来。",
            f"技术理解方面，当前判断为{tech_text}。",
            f"整体难度判断为{difficulty}，更适合具备产品基础、并能快速补齐业务与技术理解的候选人。",
        ]
        return " ".join(sentences)


def get_jd_parser_service() -> BaseJDParserService:
    return MockJDParserService()
