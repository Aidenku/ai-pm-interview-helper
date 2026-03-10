import re

from services.domain_rules import DOMAIN_ENUMS, DOMAIN_RULES
from services.llm_service import LLMServiceError, get_llm_service
from services.prompt_templates import PROFILE_PARSE_SYSTEM_PROMPT
from services.user_profile import get_user_profile_service


SKILL_SIGNAL_MAP = {
    "需求分析": ["需求分析", "需求拆解", "产品方案", "prd", "原型", "流程设计"],
    "数据分析": ["数据分析", "埋点", "数据看板", "指标", "转化", "留存", "漏斗"],
    "SQL": ["sql", "mysql", "hive", "postgresql", "clickhouse"],
    "A/B测试": ["a/b", "ab测试", "实验设计", "实验平台"],
    "Prompt设计": ["prompt", "提示词", "提示工程"],
    "模型理解": ["大模型", "llm", "模型能力", "模型原理", "模型效果"],
    "模型评测体系": ["评测", "badcase", "人工标注", "评估体系", "回答质量"],
    "Agent系统理解": ["agent", "智能体", "工具调用", "规划执行"],
    "RAG系统理解": ["rag", "检索增强", "向量检索", "召回", "知识库"],
    "指标体系与漏斗分析": ["指标体系", "北极星", "漏斗分析", "增长指标"],
    "项目推进": ["项目推进", "跨团队", "跨部门", "协同", "推动上线", "项目管理"],
    "用户研究": ["用户研究", "用户访谈", "用户洞察", "场景拆解", "用户旅程"],
    "PRD": ["prd", "需求文档", "产品文档"],
}

STRENGTH_SIGNAL_MAP = {
    "产品需求分析": ["需求分析", "产品方案", "prd", "产品设计", "原型"],
    "基础数据分析": ["数据分析", "埋点", "指标", "留存", "漏斗", "sql"],
    "用户场景拆解": ["用户研究", "用户访谈", "场景拆解", "用户旅程"],
    "基础 Prompt 理解": ["prompt", "提示词", "大模型应用"],
    "SQL实战": ["sql", "mysql", "hive", "postgresql"],
    "A/B测试设计": ["a/b", "ab测试", "实验设计"],
    "模型评测体系": ["评测", "badcase", "人工标注", "回答质量"],
    "Agent / RAG 系统理解": ["agent", "rag", "检索增强", "workflow", "工具调用"],
    "指标体系与漏斗分析": ["指标体系", "漏斗", "北极星"],
    "项目推进": ["项目推进", "跨团队", "协同", "推动上线"],
    "AI产品实践": ["ai产品", "大模型产品", "智能体", "生成式ai", "rag", "agent"],
}

DEFAULT_STRENGTHS = ["产品需求分析", "基础数据分析", "用户场景拆解", "基础 Prompt 理解"]
DEFAULT_WEAKNESSES = ["SQL实战", "A/B测试设计", "模型评测体系", "Agent / RAG 系统理解", "指标体系与漏斗分析"]
AI_EXPERIENCE_SIGNALS = ["ai", "大模型", "llm", "prompt", "智能体", "agent", "rag", "评测", "coze"]
PRODUCT_EXPERIENCE_SIGNALS = ["产品", "需求", "prd", "用户", "原型", "上线", "功能", "策略"]
DOMAIN_PRIORITY = ["广告商业化产品", "AI搜索产品", "推荐策略产品", "AI陪伴/社交产品", "企业服务产品"]


class ProfileParserService:
    def __init__(self):
        self.llm = get_llm_service()
        self.user_profile_service = get_user_profile_service()

    def parse_profile(self, profile_text: str, source: str = "resume_text") -> dict:
        text = (profile_text or "").strip()
        fallback = self._fallback_parse(text, source=source)
        if not self.llm.is_configured():
            return {"data": fallback, "meta": {"source": "fallback", "used_fallback": True, "reason": "llm_not_configured"}}

        try:
            raw = self.llm.generate_json(PROFILE_PARSE_SYSTEM_PROMPT, {"profile_text": text})
            normalized = self._normalize_profile(raw, text, source=source)
            if not normalized:
                raise LLMServiceError("invalid parsed profile")
            return {"data": normalized, "meta": {"source": "llm", "used_fallback": False}}
        except Exception as exc:
            return {"data": fallback, "meta": {"source": "fallback", "used_fallback": True, "reason": str(exc)}}

    def _fallback_parse(self, profile_text: str, source: str) -> dict:
        lowered = profile_text.lower()
        skills = self._collect_skills(lowered)
        strengths = self._collect_strengths(lowered)
        weaknesses = self._collect_weaknesses(profile_text)
        project_experiences = self._extract_experience_items(profile_text)
        ai_experiences = self._filter_experiences(project_experiences, AI_EXPERIENCE_SIGNALS, 3)
        product_experiences = self._filter_experiences(project_experiences, PRODUCT_EXPERIENCE_SIGNALS, 3)
        domain_analysis = self._analyze_resume_domains(profile_text, project_experiences)

        if not strengths:
            strengths = list(DEFAULT_STRENGTHS)
        else:
            strengths = self._merge_unique(DEFAULT_STRENGTHS, strengths)[:6]

        if not weaknesses:
            weaknesses = [item for item in DEFAULT_WEAKNESSES if item not in strengths][:5]
        else:
            weaknesses = [item for item in weaknesses if item not in strengths] or [item for item in DEFAULT_WEAKNESSES if item not in strengths][:5]

        profile = {
            "profile_id": f"profile_{abs(hash(profile_text)) % 1000000}",
            "target_role": "AI产品经理实习",
            "summary": self._build_summary(skills, strengths, weaknesses, domain_analysis),
            "skills": skills,
            "project_experiences": project_experiences,
            "ai_experiences": ai_experiences,
            "product_experiences": product_experiences,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "experience_highlights": project_experiences[:4],
            "resume_domains": domain_analysis["resume_domains"],
            "strong_domains": domain_analysis["strong_domains"],
            "weak_domains": domain_analysis["weak_domains"],
            "domain_evidence": domain_analysis["domain_evidence"],
            "transferable_domains": domain_analysis["transferable_domains"],
            "source": source,
            "raw_text": profile_text,
        }
        return self.user_profile_service.normalize_profile(profile).to_dict()

    def _normalize_profile(self, raw: dict, profile_text: str, source: str) -> dict | None:
        if not isinstance(raw, dict):
            return None
        project_experiences = self._normalize_string_list(raw.get("project_experiences"), 4)
        domain_analysis = self._analyze_resume_domains(profile_text, project_experiences or self._extract_experience_items(profile_text))
        profile = {
            "profile_id": f"profile_{abs(hash(profile_text)) % 1000000}",
            "target_role": "AI产品经理实习",
            "summary": str(raw.get("summary") or "").strip(),
            "skills": self._normalize_string_list(raw.get("skills"), 10) or self._collect_skills(profile_text.lower()),
            "project_experiences": project_experiences or self._extract_experience_items(profile_text),
            "ai_experiences": self._normalize_string_list(raw.get("ai_experiences"), 3),
            "product_experiences": self._normalize_string_list(raw.get("product_experiences"), 3),
            "strengths": self._normalize_string_list(raw.get("strengths"), 6) or self._collect_strengths(profile_text.lower()) or list(DEFAULT_STRENGTHS),
            "weaknesses": self._normalize_string_list(raw.get("weaknesses") or raw.get("weak_areas"), 5) or self._collect_weaknesses(profile_text),
            "experience_highlights": (project_experiences or self._extract_experience_items(profile_text))[:4],
            "resume_domains": self._normalize_string_list(raw.get("resume_domains"), 5) or domain_analysis["resume_domains"],
            "strong_domains": self._normalize_string_list(raw.get("strong_domains"), 3) or domain_analysis["strong_domains"],
            "weak_domains": self._normalize_string_list(raw.get("weak_domains"), 4) or domain_analysis["weak_domains"],
            "domain_evidence": self._normalize_string_list(raw.get("domain_evidence"), 5) or domain_analysis["domain_evidence"],
            "transferable_domains": self._normalize_string_list(raw.get("transferable_domains"), 4) or domain_analysis["transferable_domains"],
            "source": source,
            "raw_text": profile_text,
        }
        normalized = self.user_profile_service.normalize_profile(profile).to_dict()
        if not normalized.get("summary"):
            normalized["summary"] = self._build_summary(
                normalized.get("skills") or [],
                normalized.get("strengths") or [],
                normalized.get("weak_areas") or [],
                {
                    "strong_domains": normalized.get("strong_domains") or [],
                    "transferable_domains": normalized.get("transferable_domains") or [],
                },
            )
        return normalized

    def _analyze_resume_domains(self, profile_text: str, project_experiences: list[str]) -> dict:
        sentences = [part.strip().lower() for part in re.split(r"[\n；;。，,]", profile_text) if part.strip()]
        project_lowered = [item.lower() for item in project_experiences]
        scored = []
        negative_domains = []
        for domain in DOMAIN_ENUMS:
            rule = DOMAIN_RULES[domain]
            direct_hits = 0
            evidence = []
            for item in project_lowered:
                if self._is_negative_context(item):
                    if self._match_domain_rule(rule, item):
                        negative_domains.append(domain)
                    continue
                hits = self._match_domain_rule(rule, item)
                if hits:
                    direct_hits += len(hits)
                    evidence.extend(hits[:2])
            global_hits = []
            for sentence in sentences:
                hits = self._match_domain_rule(rule, sentence)
                if not hits:
                    continue
                if self._is_negative_context(sentence):
                    negative_domains.append(domain)
                    continue
                global_hits.extend(hits)
            score = direct_hits * 4 + len(self._merge_unique(global_hits, []))
            scored.append((domain, score, self._merge_unique(evidence, global_hits)[:3]))

        scored.sort(key=lambda item: item[1], reverse=True)
        resume_domains = [domain for domain, score, _ in scored if score > 0][:5]
        strong_domains = [domain for domain, score, _ in scored if score >= 5][:3]
        domain_evidence = []
        for domain, score, evidence in scored:
            if score <= 0:
                continue
            if evidence:
                domain_evidence.append(f"{domain}：{' / '.join(evidence[:2])}")
            if len(domain_evidence) >= 4:
                break

        transferable = []
        for domain in strong_domains:
            for adjacent in DOMAIN_RULES[domain]["adjacent_domains"]:
                if adjacent not in strong_domains and adjacent not in transferable:
                    transferable.append(adjacent)

        weak_domains = []
        for domain in self._merge_unique(negative_domains, []):
            if domain not in strong_domains and domain not in weak_domains:
                weak_domains.append(domain)
        scored_map = {domain: score for domain, score, _ in scored}
        for domain in DOMAIN_PRIORITY:
            if domain in strong_domains or domain in transferable or domain in weak_domains:
                continue
            if scored_map.get(domain, 0) == 0:
                weak_domains.append(domain)
            if len(weak_domains) >= 3:
                break

        return {
            "resume_domains": resume_domains,
            "strong_domains": strong_domains,
            "weak_domains": weak_domains[:4],
            "domain_evidence": domain_evidence,
            "transferable_domains": transferable[:4],
        }

    def _is_negative_context(self, lowered: str) -> bool:
        negative_tokens = ["没有", "无", "缺少", "没做过", "未做过", "未接触", "不熟悉", "缺乏"]
        return any(token in lowered for token in negative_tokens)

    def _match_domain_rule(self, rule: dict, lowered: str) -> list[str]:
        hits = []
        for bucket in ["business_context", "required_domain_experience", "core_metrics", "decision_focus", "domain_keywords"]:
            for phrase in rule[bucket]:
                if phrase.lower() in lowered and phrase not in hits:
                    hits.append(phrase)
        return hits

    def _collect_skills(self, lowered: str) -> list[str]:
        skills = []
        for label, signals in SKILL_SIGNAL_MAP.items():
            if any(signal in lowered for signal in signals):
                skills.append(label)
        return skills[:10]

    def _collect_strengths(self, lowered: str) -> list[str]:
        strengths = []
        for label, signals in STRENGTH_SIGNAL_MAP.items():
            if any(signal in lowered for signal in signals):
                strengths.append(label)
        return strengths[:6]

    def _collect_weaknesses(self, profile_text: str) -> list[str]:
        weaknesses = []
        weak_patterns = [r"不熟悉(.{0,18})", r"薄弱(.{0,18})", r"欠缺(.{0,18})", r"还不会(.{0,18})", r"希望提升(.{0,18})"]
        snippets = []
        for pattern in weak_patterns:
            snippets.extend(match.group(0) for match in re.finditer(pattern, profile_text, flags=re.IGNORECASE))
        joined = " ".join(snippets).lower()
        for label, signals in STRENGTH_SIGNAL_MAP.items():
            if any(signal in joined for signal in signals):
                weaknesses.append(label)
        return weaknesses[:5]

    def _extract_experience_items(self, profile_text: str) -> list[str]:
        parts = re.split(r"[\n；;。，,]", profile_text)
        items = []
        for part in parts:
            text = part.strip().lstrip("-•0123456789. ")
            if len(text) < 10:
                continue
            if text not in items:
                items.append(text)
            if len(items) >= 4:
                break
        return items

    def _filter_experiences(self, items: list[str], signals: list[str], limit: int) -> list[str]:
        result = []
        for item in items:
            lowered = item.lower()
            if any(signal in lowered for signal in signals) and item not in result:
                result.append(item)
            if len(result) >= limit:
                break
        return result

    def _build_summary(self, skills, strengths, weaknesses, domain_analysis) -> str:
        skill_text = "、".join((skills or strengths)[:3]) or "基础产品能力"
        weak_text = "、".join(weaknesses[:2]) or "SQL与AI系统理解"
        strong_domains = domain_analysis.get("strong_domains") or []
        if strong_domains:
            return f"当前背景更偏向{'、'.join(strong_domains[:2])}场景，已具备{skill_text}等能力，但在{weak_text}上仍有明显补齐空间。"
        return f"从当前背景来看，你已具备{skill_text}等基础能力，但在{weak_text}上仍有较明显 gap。"

    def _merge_unique(self, first: list[str], second: list[str]) -> list[str]:
        merged = []
        for item in list(first) + list(second):
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
        return merged

    def _normalize_string_list(self, value, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        items = []
        for item in value:
            text = str(item).strip()
            if text and text not in items:
                items.append(text)
        return items[:limit]



def get_profile_parser_service() -> ProfileParserService:
    return ProfileParserService()
