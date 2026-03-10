from schemas.gap_analysis import (
    EvidenceCompareResult,
    GapAnalysisEvidence,
    GapAnalysisResult,
    MatchScoreBreakdown,
    empty_gap_analysis,
)
from services.job_domain_analysis import get_job_domain_analysis_service
from services.match_scoring import calculate_match_score, compare_evidence
from services.user_profile import get_user_profile_service


PROFILE_STRENGTH_SKILL_MAP = {
    "产品需求分析": {"需求分析", "PRD", "项目推进"},
    "基础数据分析": {"数据分析"},
    "用户场景拆解": {"用户研究", "需求分析"},
    "基础 Prompt 理解": {"Prompt设计", "模型理解"},
    "SQL实战": {"SQL", "数据分析"},
    "A/B测试设计": {"A/B测试", "指标体系与漏斗分析"},
    "模型评测体系": {"模型评测体系"},
    "Agent / RAG 系统理解": {"Agent系统理解", "RAG系统理解", "模型理解"},
    "指标体系与漏斗分析": {"指标体系与漏斗分析"},
    "AI产品实践": {"模型理解", "Prompt设计", "项目推进"},
    "项目推进": {"项目推进"},
}

PROFILE_WEAK_SKILL_MAP = {
    "SQL实战": {"SQL"},
    "A/B测试设计": {"A/B测试"},
    "模型评测体系": {"模型评测体系"},
    "Agent / RAG 系统理解": {"Agent系统理解", "RAG系统理解"},
    "指标体系与漏斗分析": {"指标体系与漏斗分析"},
    "项目推进": {"项目推进"},
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
    "AI办公": "项目推进",
    "内容社区": "用户研究",
    "AI陪伴": "用户研究",
    "广告商业化": "策略设计",
}

PROFILE_TEXT_SKILL_MAP = {
    "sql": "SQL",
    "埋点": "数据分析",
    "指标": "指标体系与漏斗分析",
    "漏斗": "指标体系与漏斗分析",
    "prompt": "Prompt设计",
    "提示词": "Prompt设计",
    "模型": "模型理解",
    "评测": "模型评测体系",
    "agent": "Agent系统理解",
    "智能体": "Agent系统理解",
    "rag": "RAG系统理解",
    "需求": "需求分析",
    "prd": "PRD",
    "用户": "用户研究",
    "访谈": "用户研究",
    "a/b": "A/B测试",
    "ab测试": "A/B测试",
    "实验": "A/B测试",
    "项目": "项目推进",
    "上线": "项目推进",
    "搜索": "搜索系统理解",
    "检索": "搜索系统理解",
    "推荐": "推荐系统理解",
    "广告": "策略设计",
}

DOMAIN_GAP_TEMPLATES = {
    "广告商业化产品": [
        ("缺少广告投放经验", ["广告投放", "投放策略", "预算分配", "广告策略"]),
        ("缺少商业化指标理解", ["CTR", "ROI", "eCPM", "转化率"]),
        ("缺少变现链路经验", ["商业化产品", "变现", "广告主", "收入"]),
    ],
    "AI搜索产品": [
        ("缺少搜索质量优化经验", ["搜索", "召回", "排序", "query"]),
        ("缺少检索或RAG系统理解", ["RAG", "检索增强", "知识库"]),
        ("缺少搜索效果评估经验", ["NDCG", "召回率", "点击率"]),
    ],
    "AI陪伴/社交产品": [
        ("缺少陪伴或社交场景经验", ["陪伴", "社交", "人设"]),
        ("缺少长期留存机制理解", ["留存", "长期记忆", "活跃"]),
        ("缺少内容安全与体验平衡经验", ["安全", "审核", "体验"]),
    ],
    "推荐策略产品": [
        ("缺少推荐策略经验", ["推荐", "召回", "排序"]),
        ("缺少分发指标理解", ["点击率", "转化率", "留存"]),
        ("缺少实验迭代经验", ["A/B测试", "实验平台", "策略优化"]),
    ],
    "平台工具产品": [
        ("缺少平台化工具经验", ["平台工具", "工作台", "配置平台"]),
        ("缺少跨团队流程设计经验", ["流程", "协同", "平台规则"]),
        ("缺少稳定性和效率指标经验", ["效率", "成功率", "稳定性"]),
    ],
    "企业服务产品": [
        ("缺少ToB业务经验", ["企业服务", "SaaS", "B端"]),
        ("缺少复杂流程或权限体系经验", ["权限", "审批", "工作流"]),
        ("缺少交付与落地经验", ["交付", "实施", "客户成功"]),
    ],
    "增长产品": [
        ("缺少增长实验经验", ["增长", "拉新", "转化", "留存"]),
        ("缺少漏斗与指标体系理解", ["漏斗", "北极星", "转化率"]),
        ("缺少增长策略落地经验", ["活动", "策略", "投放"]),
    ],
    "通用AI产品": [
        ("缺少AI产品落地经验", ["AI产品", "大模型应用", "Agent", "RAG"]),
        ("缺少模型能力评估经验", ["评测", "badcase", "回答质量"]),
        ("缺少AI场景指标理解", ["准确率", "帮助度", "稳定性"]),
    ],
}

GENERAL_GAP_LABELS = {
    "SQL": "SQL 实战证据不足",
    "A/B测试": "实验设计与结果判断能力不足",
    "模型评测体系": "缺少模型评测体系经验",
    "Agent系统理解": "缺少 Agent 系统拆解经验",
    "RAG系统理解": "缺少 RAG / 检索增强理解",
    "策略设计": "缺少策略设计与约束平衡经验",
    "搜索系统理解": "缺少搜索系统理解",
    "推荐系统理解": "缺少推荐系统理解",
    "项目推进": "缺少可展开的跨团队推进案例",
    "需求分析": "需求拆解案例不够具体",
    "PRD": "PRD 或方案沉淀证据不足",
    "用户研究": "用户洞察与验证证据不足",
    "指标体系与漏斗分析": "指标体系与漏斗分析证据不足",
    "数据分析": "数据分析闭环证据不足",
    "Prompt设计": "Prompt 设计方法论证据不足",
    "模型理解": "模型能力边界理解不足",
}


class GapAnalysisService:
    def __init__(self):
        self.user_profile_service = get_user_profile_service()
        self.job_domain_service = get_job_domain_analysis_service()

    def analyze(self, jd_analysis: dict, user_profile, company: str = "", title: str = "", jd_text: str = "") -> dict:
        if not jd_analysis:
            return empty_gap_analysis()

        profile = self.user_profile_service.normalize_profile(user_profile)
        required_skills = self._collect_required_skills(jd_analysis)
        if not required_skills:
            return empty_gap_analysis()

        job_domain = self.job_domain_service.analyze_job_domain(
            company=company,
            title=title,
            jd_text=jd_text or self._reconstruct_text(jd_analysis),
        )
        jd_signals = self._collect_jd_signals(jd_analysis, job_domain)
        user_capabilities = self._collect_user_capabilities(profile)
        weak_rank = self._build_rank_map(profile.weak_areas, PROFILE_WEAK_SKILL_MAP)

        matched = []
        missing = []
        for skill, _weight in required_skills.items():
            if skill in user_capabilities:
                matched.append(skill)
            else:
                missing.append(skill)

        missing_sorted = sorted(
            missing,
            key=lambda item: (
                -(1 if item in weak_rank else 0),
                -required_skills.get(item, 0),
                weak_rank.get(item, 999),
                item,
            ),
        )
        evidence_compare = compare_evidence(job_domain, jd_analysis, profile.to_dict())
        score_breakdown = calculate_match_score(job_domain, jd_analysis, profile.to_dict())

        domain_gap = self._build_domain_gap(job_domain, evidence_compare, profile)
        general_gap = self._build_general_gap(missing_sorted, domain_gap)
        priority_gap = self._build_priority_gap(domain_gap, general_gap)
        potential_strengths = self._collect_potential_strengths(profile, required_skills, matched, job_domain)
        realistic_advice = self._build_realistic_advice(score_breakdown, job_domain, domain_gap, general_gap, evidence_compare)
        not_recommended_reason = self._build_not_recommended_reason(score_breakdown, job_domain, domain_gap, evidence_compare)
        summary = self._build_summary(score_breakdown, job_domain, matched, domain_gap, general_gap, not_recommended_reason)
        resume_signals = self._collect_resume_signals(profile)

        return GapAnalysisResult(
            job_domain_analysis=job_domain,
            matched_skills=matched,
            missing_skills=missing_sorted,
            potential_strengths=potential_strengths,
            priority_to_improve=priority_gap[:3],
            domain_gap=domain_gap,
            general_gap=general_gap,
            priority_gap=priority_gap,
            realistic_advice=realistic_advice,
            not_recommended_reason=not_recommended_reason,
            summary=summary,
            match_score=score_breakdown["total_score"],
            advice=summary,
            evidence=GapAnalysisEvidence(jd_signals=jd_signals, resume_signals=resume_signals),
            score_breakdown=MatchScoreBreakdown(**score_breakdown),
            evidence_compare=EvidenceCompareResult(**evidence_compare),
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
                self._add_skill(required, mapped, 2)
        return required

    def _collect_user_capabilities(self, profile) -> set[str]:
        capabilities = set(profile.skills or [])
        for strength in profile.strengths or []:
            capabilities.update(PROFILE_STRENGTH_SKILL_MAP.get(strength, {strength}))
        for bucket in [profile.project_experiences, profile.ai_experiences, profile.product_experiences, profile.experience_highlights, profile.domain_evidence]:
            for item in bucket or []:
                lowered = item.lower()
                for signal, mapped in PROFILE_TEXT_SKILL_MAP.items():
                    if signal in lowered:
                        capabilities.add(mapped)
        return capabilities

    def _build_domain_gap(self, job_domain: dict, evidence_compare: dict, profile) -> list[str]:
        primary_domain = job_domain.get("primary_domain") or "通用AI产品"
        templates = DOMAIN_GAP_TEMPLATES.get(primary_domain, DOMAIN_GAP_TEMPLATES["通用AI产品"])
        missing_evidence = set(evidence_compare.get("missing_evidence") or [])
        strong_domains = set(profile.strong_domains or [])
        resume_domains = set(profile.resume_domains or [])

        gaps = []
        if primary_domain not in resume_domains:
            gaps.append(f"缺少 {primary_domain} 的直接业务经历")
        elif primary_domain not in strong_domains:
            gaps.append(f"{primary_domain} 只有弱相关经历，缺少足够深度")

        for label, signals in templates:
            if any(signal in missing_evidence for signal in signals) or primary_domain not in strong_domains:
                gaps.append(label)
            if len(gaps) >= 4:
                break
        return self._unique(gaps)[:4]

    def _build_general_gap(self, missing_skills: list[str], domain_gap: list[str]) -> list[str]:
        domain_related_words = " ".join(domain_gap)
        gaps = []
        for skill in missing_skills:
            label = GENERAL_GAP_LABELS.get(skill, f"缺少 {skill} 的直接证据")
            if skill in domain_related_words:
                continue
            gaps.append(label)
            if len(gaps) >= 4:
                break
        return self._unique(gaps)[:4]

    def _build_priority_gap(self, domain_gap: list[str], general_gap: list[str]) -> list[str]:
        ordered = []
        ordered.extend(domain_gap[:2])
        ordered.extend(general_gap[:3])
        return self._unique(ordered)[:4]

    def _collect_potential_strengths(self, profile, required_skills: dict[str, int], matched: list[str], job_domain: dict) -> list[str]:
        potential = []
        required_set = set(required_skills.keys())
        for strength in profile.strengths or []:
            expanded = PROFILE_STRENGTH_SKILL_MAP.get(strength, {strength})
            if expanded & required_set:
                potential.append(strength)
        for domain in profile.strong_domains or []:
            if domain == job_domain.get("primary_domain"):
                potential.append(f"已有 {domain} 直接经验")
        if profile.ai_experiences and any(skill in required_set for skill in {"模型理解", "Prompt设计", "Agent系统理解", "RAG系统理解", "模型评测体系"}):
            potential.append("已有 AI 相关项目经历")
        if profile.product_experiences and any(skill in required_set for skill in {"需求分析", "PRD", "项目推进", "用户研究"}):
            potential.append("已有产品项目经历")
        if profile.project_experiences and "项目推进" in matched:
            potential.append("有可用于面试展开的项目案例")
        return self._unique(potential)[:5]

    def _collect_jd_signals(self, jd_analysis: dict, job_domain: dict) -> list[str]:
        signals = [job_domain.get("primary_domain") or "通用AI产品"]
        signals.extend((job_domain.get("required_domain_experience") or [])[:2])
        signals.extend((jd_analysis.get("skill_tags") or [])[:2])
        for item in (jd_analysis.get("technical_requirements") or [])[:2]:
            topic = item.get("topic") or ""
            depth = item.get("depth") or ""
            if topic:
                signals.append(f"{topic}（{depth or '待定'}）")
        return self._unique(signals)[:6]

    def _collect_resume_signals(self, profile) -> list[str]:
        signals = []
        signals.extend((profile.strong_domains or [])[:2])
        signals.extend((profile.skills or [])[:2])
        signals.extend((profile.domain_evidence or [])[:2])
        if profile.project_experiences:
            signals.append(profile.project_experiences[0])
        return self._unique(signals)[:6]

    def _add_skill(self, required: dict[str, int], skill: str, weight: int):
        required[skill] = max(required.get(skill, 0), weight)

    def _build_rank_map(self, profile_items: list[str], mapping: dict[str, set[str]]) -> dict[str, int]:
        rank = {}
        for index, item in enumerate(profile_items or []):
            for skill in mapping.get(item, {item}):
                rank[skill] = min(rank.get(skill, index), index)
        return rank

    def _build_realistic_advice(self, score_breakdown: dict, job_domain: dict, domain_gap: list[str], general_gap: list[str], evidence_compare: dict) -> list[str]:
        primary_domain = job_domain.get("primary_domain") or "通用AI产品"
        advice = []
        if domain_gap:
            advice.append(f"先补一段与 {primary_domain} 直接相关的项目案例，否则场景分很难抬高。")
        if evidence_compare.get("missing_evidence"):
            missing_text = "、".join((evidence_compare.get("missing_evidence") or [])[:2])
            advice.append(f"把 {missing_text} 相关经历补成可验证的项目证据。")
        if general_gap:
            general_text = "、".join(general_gap[:2])
            advice.append(f"通用能力上优先补 {general_text}，不要同时铺太多方向。")
        if score_breakdown["total_score"] >= 75:
            advice.append("下一步重点不是再堆能力标签，而是把已有经历转成更硬的业务结果和指标表达。")
        return self._unique(advice)[:4]

    def _build_not_recommended_reason(self, score_breakdown: dict, job_domain: dict, domain_gap: list[str], evidence_compare: dict) -> str:
        primary_domain = job_domain.get("primary_domain") or "通用AI产品"
        if score_breakdown["total_score"] >= 60:
            return ""
        reasons = domain_gap[:2] or (evidence_compare.get("missing_evidence") or [])[:2]
        if reasons:
            reason_text = "、".join(reasons)
            return f"该岗位属于 {primary_domain} 方向，与当前经历差距较大，短期内不建议优先投递。主要问题在于{reason_text}。"
        return f"该岗位属于 {primary_domain} 方向，与当前经历差距较大，短期内不建议优先投递。"

    def _build_summary(self, score_breakdown: dict, job_domain: dict, matched: list[str], domain_gap: list[str], general_gap: list[str], not_recommended_reason: str) -> str:
        primary_domain = job_domain.get("primary_domain") or "通用AI产品"
        matched_text = "、".join(matched[:3]) or "基础产品能力"
        gap_text = "、".join((domain_gap or general_gap)[:2]) or "关键岗位证据"
        if not_recommended_reason:
            return f"当前岗位核心属于 {primary_domain}，你在 {matched_text} 上有一定基础，但决定性短板仍在 {gap_text}。这不是通用能力补一点就能解决的问题。"
        return f"当前岗位核心属于 {primary_domain}。你已命中 {matched_text}，但仍需优先补齐 {gap_text}，否则面试阶段会被场景和证据层拦下。"

    def _reconstruct_text(self, jd_analysis: dict) -> str:
        parts = []
        parts.extend(jd_analysis.get("keywords") or [])
        parts.extend(jd_analysis.get("skill_tags") or [])
        for item in jd_analysis.get("technical_requirements") or []:
            parts.append(str(item.get("topic") or ""))
            parts.extend(item.get("evidence") or [])
        parts.extend(jd_analysis.get("scenario_tags") or [])
        return "\n".join([part for part in parts if part])

    def _unique(self, items: list[str]) -> list[str]:
        result = []
        for item in items:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result



def get_gap_analysis_service() -> GapAnalysisService:
    return GapAnalysisService()
