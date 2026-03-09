from schemas.gap_analysis import GapAnalysisResult, empty_gap_analysis


PROFILE_STRENGTH_SKILL_MAP = {
    "产品需求分析": {"需求分析", "PRD"},
    "基础数据分析": {"数据分析"},
    "用户场景拆解": {"用户研究", "需求分析"},
    "基础 Prompt 理解": {"Prompt设计"},
}

PROFILE_WEAK_SKILL_MAP = {
    "SQL实战": {"SQL"},
    "A/B测试设计": {"A/B测试"},
    "模型评测体系": {"模型评测体系"},
    "Agent / RAG 系统理解": {"Agent系统理解", "RAG系统理解"},
    "指标体系与漏斗分析": {"指标体系与漏斗分析"},
}

TECH_TOPIC_TO_SKILL = {
    "大模型": "模型理解",
    "RAG": "RAG系统理解",
    "Agent": "Agent系统理解",
    "推荐": "推荐系统理解",
    "搜索": "搜索系统理解",
    "评测": "模型评测体系",
}

SCENARIO_TO_SKILL = {
    "增长策略": "指标体系与漏斗分析",
    "AI搜索": "搜索系统理解",
    "平台工具": "项目推进",
}


class GapAnalysisService:
    def analyze(self, jd_analysis: dict, user_profile) -> dict:
        if not jd_analysis:
            return empty_gap_analysis()

        required_skills = self._collect_required_skills(jd_analysis)
        if not required_skills:
            return empty_gap_analysis()

        user_strengths = self._expand_profile_skills(user_profile.strengths, PROFILE_STRENGTH_SKILL_MAP)
        weak_priorities = self._expand_profile_skills(user_profile.weak_areas, PROFILE_WEAK_SKILL_MAP)
        weak_rank = self._build_rank_map(user_profile.weak_areas, PROFILE_WEAK_SKILL_MAP)

        matched = []
        missing = []
        matched_weight = 0
        total_weight = 0

        for skill, weight in required_skills.items():
            total_weight += weight
            if skill in user_strengths:
                matched.append(skill)
                matched_weight += weight
            else:
                missing.append(skill)

        match_score = round((matched_weight / total_weight) * 100) if total_weight else 0
        missing_sorted = sorted(
            missing,
            key=lambda item: (
                -(1 if item in weak_rank else 0),
                -required_skills.get(item, 0),
                weak_rank.get(item, 999),
                item,
            ),
        )
        priority = missing_sorted[:3]
        advice = self._build_advice(
            match_score=match_score,
            matched=matched,
            missing=missing_sorted,
            priority=priority,
            weak_priorities=weak_priorities,
        )

        return GapAnalysisResult(
            matched_skills=matched,
            missing_skills=missing_sorted,
            priority_to_improve=priority,
            match_score=match_score,
            advice=advice,
        ).to_dict()

    def _collect_required_skills(self, jd_analysis: dict) -> dict[str, int]:
        required = {}

        for tag in jd_analysis.get("skill_tags") or []:
            self._add_skill(required, tag, 2)

        for item in jd_analysis.get("technical_requirements") or []:
            topic = item.get("topic") or ""
            depth = item.get("depth") or ""
            mapped = TECH_TOPIC_TO_SKILL.get(topic)
            if not mapped:
                continue
            weight = 2
            if depth == "中等":
                weight = 3
            elif depth == "较深":
                weight = 4
            self._add_skill(required, mapped, weight)

        for scenario in jd_analysis.get("scenario_tags") or []:
            mapped = SCENARIO_TO_SKILL.get(scenario)
            if mapped:
                self._add_skill(required, mapped, 1)

        return required

    def _add_skill(self, required: dict[str, int], skill: str, weight: int):
        current = required.get(skill, 0)
        required[skill] = max(current, weight)

    def _expand_profile_skills(self, profile_items: list[str], mapping: dict[str, set[str]]) -> set[str]:
        expanded = set()
        for item in profile_items or []:
            expanded.update(mapping.get(item, set()))
        return expanded

    def _build_rank_map(self, profile_items: list[str], mapping: dict[str, set[str]]) -> dict[str, int]:
        rank = {}
        for index, item in enumerate(profile_items or []):
            for skill in mapping.get(item, set()):
                rank[skill] = min(rank.get(skill, index), index)
        return rank

    def _build_advice(
        self,
        match_score: int,
        matched: list[str],
        missing: list[str],
        priority: list[str],
        weak_priorities: set[str],
    ) -> str:
        matched_text = "、".join(matched[:3]) or "基础产品能力"
        priority_text = "、".join(priority[:3]) or "核心能力补齐"
        weak_overlap = [item for item in priority if item in weak_priorities]

        if match_score >= 80 and not missing:
            return f"该岗位与你当前能力较为匹配，现阶段可以重点把{matched_text}转化成更具体的项目表达。"

        if weak_overlap:
            weak_text = "、".join(weak_overlap[:2])
            return (
                f"该岗位与你的{matched_text}基础较匹配，但在{weak_text}上仍有明显 gap，"
                f"建议优先补齐{priority_text}。"
            )

        return (
            f"该岗位与你的{matched_text}有一定匹配度，但距离岗位要求仍有差距，"
            f"建议优先补齐{priority_text}。"
        )


def get_gap_analysis_service() -> GapAnalysisService:
    return GapAnalysisService()
