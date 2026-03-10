from services.domain_rules import DOMAIN_RULES, SPECIALIZED_DOMAINS


SKILL_SIGNAL_MAP = {
    "SQL": ["sql", "mysql", "hive"],
    "数据分析": ["数据分析", "埋点", "指标", "分析"],
    "Prompt设计": ["prompt", "提示词"],
    "A/B测试": ["a/b", "ab测试", "实验"],
    "需求分析": ["需求分析", "需求拆解", "产品方案"],
    "模型理解": ["模型", "大模型", "llm"],
    "模型评测体系": ["评测", "badcase", "评估"],
    "Agent系统理解": ["agent", "智能体"],
    "RAG系统理解": ["rag", "检索增强", "知识库"],
    "指标体系与漏斗分析": ["指标体系", "漏斗", "北极星"],
    "项目推进": ["项目推进", "协同", "上线"],
    "用户研究": ["用户研究", "访谈", "洞察"],
    "PRD": ["prd", "需求文档"],
    "搜索系统理解": ["搜索", "检索", "query", "召回", "排序"],
    "推荐系统理解": ["推荐", "召回", "排序", "分发"],
    "策略设计": ["策略", "定向", "投放", "商业化"],
}


def compare_evidence(job_domain_analysis: dict, jd_analysis: dict, profile_analysis: dict) -> dict:
    primary_domain = job_domain_analysis.get("primary_domain") or "通用AI产品"
    resume_text = _profile_text(profile_analysis)
    matched_evidence = []
    missing_evidence = []
    weak_evidence = []

    expected = []
    expected.extend((job_domain_analysis.get("required_domain_experience") or [])[:3])
    expected.extend((job_domain_analysis.get("core_metrics") or [])[:2])
    expected.extend((jd_analysis.get("skill_tags") or [])[:3])

    for item in _unique(expected):
        if _has_semantic_match(item, resume_text):
            matched_evidence.append(item)
        else:
            missing_evidence.append(item)

    project_experiences = profile_analysis.get("project_experiences") or []
    if not project_experiences:
        weak_evidence.append("简历缺少可展开的项目经历")
    elif len(project_experiences) == 1:
        weak_evidence.append("项目证据较少，面试中容易被追问深度")

    if primary_domain not in (profile_analysis.get("strong_domains") or []):
        weak_evidence.append(f"缺少 {primary_domain} 的直接场景证据")

    hallucination_risk = len(matched_evidence) == 0 or (len(missing_evidence) >= 3 and primary_domain in SPECIALIZED_DOMAINS)

    return {
        "matched_evidence": _unique(matched_evidence)[:6],
        "missing_evidence": _unique(missing_evidence)[:6],
        "weak_evidence": _unique(weak_evidence)[:4],
        "hallucination_risk": hallucination_risk,
    }


def calculate_match_score(job_domain_analysis: dict, jd_analysis: dict, profile_analysis: dict) -> dict:
    primary_domain = job_domain_analysis.get("primary_domain") or "通用AI产品"
    strong_domains = set(profile_analysis.get("strong_domains") or [])
    resume_domains = set(profile_analysis.get("resume_domains") or [])
    transferable_domains = set(profile_analysis.get("transferable_domains") or [])

    confidence = int(job_domain_analysis.get("domain_confidence") or 50)
    if primary_domain in strong_domains:
        domain_score = min(96, 84 + confidence // 9)
    elif primary_domain in resume_domains:
        domain_score = min(60, 50 + confidence // 20)
    elif primary_domain in transferable_domains:
        domain_score = min(60, 42 + confidence // 25)
    else:
        domain_score = min(45, 25 + confidence // 25)

    if primary_domain not in strong_domains:
        domain_score = min(domain_score, 60)
    if primary_domain not in resume_domains:
        domain_score = min(domain_score, 45)
    if primary_domain in transferable_domains and primary_domain not in strong_domains:
        domain_score = min(domain_score, 60)

    general_score = _calculate_general_score(jd_analysis, profile_analysis)
    evidence = compare_evidence(job_domain_analysis, jd_analysis, profile_analysis)
    evidence_score = _calculate_evidence_score(evidence)

    total_score = round(domain_score * 0.4 + general_score * 0.35 + evidence_score * 0.25)
    if primary_domain in SPECIALIZED_DOMAINS and primary_domain not in strong_domains:
        total_score = min(total_score, 72)
    if primary_domain not in resume_domains:
        total_score = min(total_score, 65)
    if evidence.get("hallucination_risk"):
        total_score = min(total_score, 58)

    return {
        "total_score": max(0, min(100, total_score)),
        "domain_score": max(0, min(100, domain_score)),
        "general_score": max(0, min(100, general_score)),
        "evidence_score": max(0, min(100, evidence_score)),
        "level": _score_level(total_score),
        "confidence": max(0, min(100, round(confidence * 0.6 + evidence_score * 0.4))),
    }


def _calculate_general_score(jd_analysis: dict, profile_analysis: dict) -> int:
    required = []
    required.extend(jd_analysis.get("skill_tags") or [])
    for item in jd_analysis.get("technical_requirements") or []:
        topic = item.get("topic")
        if topic == "搜索":
            required.append("搜索系统理解")
        elif topic == "推荐":
            required.append("推荐系统理解")
        elif topic == "RAG":
            required.append("RAG系统理解")
        elif topic == "Agent":
            required.append("Agent系统理解")
        elif topic == "评测":
            required.append("模型评测体系")
        elif topic == "大模型":
            required.append("模型理解")
    required = _unique(required)
    if not required:
        return 45

    profile_skills = set(profile_analysis.get("skills") or [])
    profile_text = _profile_text(profile_analysis)
    matched = 0
    for skill in required:
        if skill in profile_skills or _has_semantic_match(skill, profile_text):
            matched += 1
    ratio = matched / len(required)
    return round(25 + ratio * 65)


def _calculate_evidence_score(evidence: dict) -> int:
    matched = len(evidence.get("matched_evidence") or [])
    missing = len(evidence.get("missing_evidence") or [])
    weak = len(evidence.get("weak_evidence") or [])
    score = 25 + matched * 15 - missing * 9 - weak * 6
    if evidence.get("hallucination_risk"):
        score -= 15
    return max(10, min(95, score))


def _score_level(total_score: int) -> str:
    if total_score >= 90:
        return "高度匹配"
    if total_score >= 75:
        return "较匹配"
    if total_score >= 60:
        return "中等匹配"
    return "不建议投递"


def _profile_text(profile_analysis: dict) -> str:
    parts = []
    for key in ["summary", "raw_text"]:
        if profile_analysis.get(key):
            parts.append(str(profile_analysis.get(key)))
    for key in ["skills", "project_experiences", "ai_experiences", "product_experiences", "strengths", "domain_evidence"]:
        for item in profile_analysis.get(key) or []:
            parts.append(str(item))
    return "\n".join(parts).lower()


def _has_semantic_match(label: str, profile_text: str) -> bool:
    lowered = str(label or "").lower()
    for sentence in [part.strip() for part in profile_text.split("\n") if part.strip()]:
        if lowered in sentence and not _is_negative_context(sentence):
            return True
    for signal, patterns in SKILL_SIGNAL_MAP.items():
        if signal == label:
            for sentence in [part.strip() for part in profile_text.split("\n") if part.strip()]:
                if _is_negative_context(sentence):
                    continue
                if any(pattern in sentence for pattern in patterns):
                    return True
    return False



def _is_negative_context(lowered: str) -> bool:
    negative_tokens = ["没有", "无", "缺少", "没做过", "未做过", "未接触", "不熟悉", "缺乏"]
    return any(token in lowered for token in negative_tokens)


def _unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result
