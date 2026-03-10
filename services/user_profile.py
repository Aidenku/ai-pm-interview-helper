from dataclasses import asdict, dataclass, field


@dataclass
class UserProfile:
    profile_id: str
    target_role: str
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    project_experiences: list[str] = field(default_factory=list)
    ai_experiences: list[str] = field(default_factory=list)
    product_experiences: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weak_areas: list[str] = field(default_factory=list)
    experience_highlights: list[str] = field(default_factory=list)
    resume_domains: list[str] = field(default_factory=list)
    strong_domains: list[str] = field(default_factory=list)
    weak_domains: list[str] = field(default_factory=list)
    domain_evidence: list[str] = field(default_factory=list)
    transferable_domains: list[str] = field(default_factory=list)
    source: str = "default"
    raw_text: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["weaknesses"] = list(self.weak_areas)
        return data


DEFAULT_USER_PROFILE = UserProfile(
    profile_id="default_ai_pm_intern",
    target_role="AI产品经理实习",
    summary="默认 AI PM 实习画像，具备基础产品分析和 Prompt 理解能力，但在 SQL、实验设计和 AI 系统深度上仍有提升空间。",
    skills=["需求分析", "数据分析", "Prompt设计", "用户场景拆解"],
    project_experiences=["具备基础产品需求分析能力", "具备基础数据分析和用户场景拆解能力"],
    ai_experiences=["理解 Prompt 的基本使用方式"],
    product_experiences=["参与过基础产品分析与需求拆解"],
    strengths=["产品需求分析", "基础数据分析", "用户场景拆解", "基础 Prompt 理解"],
    weak_areas=["SQL实战", "A/B测试设计", "模型评测体系", "Agent / RAG 系统理解", "指标体系与漏斗分析"],
    experience_highlights=["具备基础产品需求分析能力", "具备基础数据分析和用户场景拆解能力", "理解 Prompt 的基本使用方式"],
    resume_domains=["通用AI产品", "平台工具产品"],
    strong_domains=["通用AI产品"],
    weak_domains=["广告商业化产品"],
    domain_evidence=["只有通用 AI 产品与基础产品分析经历"],
    transferable_domains=["AI搜索产品", "增长产品"],
    source="default",
)


class UserProfileService:
    def get_default_profile(self) -> UserProfile:
        return DEFAULT_USER_PROFILE

    def normalize_profile(self, profile_input) -> UserProfile:
        if isinstance(profile_input, UserProfile):
            return profile_input

        if isinstance(profile_input, dict):
            weak_areas = self._normalize_list(
                profile_input.get("weak_areas") or profile_input.get("weaknesses"),
                DEFAULT_USER_PROFILE.weak_areas,
            )
            strengths = self._normalize_list(profile_input.get("strengths"), DEFAULT_USER_PROFILE.strengths)
            skills = self._normalize_list(profile_input.get("skills"), self._derive_skills(strengths))
            return UserProfile(
                profile_id=str(profile_input.get("profile_id") or "custom_profile").strip() or "custom_profile",
                target_role=str(profile_input.get("target_role") or DEFAULT_USER_PROFILE.target_role).strip() or DEFAULT_USER_PROFILE.target_role,
                summary=str(profile_input.get("summary") or "").strip(),
                skills=skills,
                project_experiences=self._normalize_list(profile_input.get("project_experiences"), []),
                ai_experiences=self._normalize_list(profile_input.get("ai_experiences"), []),
                product_experiences=self._normalize_list(profile_input.get("product_experiences"), []),
                strengths=strengths,
                weak_areas=[item for item in weak_areas if item not in strengths] or list(DEFAULT_USER_PROFILE.weak_areas),
                experience_highlights=self._normalize_list(profile_input.get("experience_highlights") or profile_input.get("project_experiences"), []),
                resume_domains=self._normalize_list(profile_input.get("resume_domains"), []),
                strong_domains=self._normalize_list(profile_input.get("strong_domains"), []),
                weak_domains=self._normalize_list(profile_input.get("weak_domains"), []),
                domain_evidence=self._normalize_list(profile_input.get("domain_evidence"), []),
                transferable_domains=self._normalize_list(profile_input.get("transferable_domains"), []),
                source=str(profile_input.get("source") or "custom").strip() or "custom",
                raw_text=str(profile_input.get("raw_text") or "").strip(),
            )

        return DEFAULT_USER_PROFILE

    def _normalize_list(self, value, default):
        if not isinstance(value, list):
            return list(default)
        items = []
        for item in value:
            text = str(item).strip()
            if text and text not in items:
                items.append(text)
        return items or list(default)

    def _derive_skills(self, strengths: list[str]) -> list[str]:
        skill_map = {
            "产品需求分析": "需求分析",
            "基础数据分析": "数据分析",
            "用户场景拆解": "用户研究",
            "基础 Prompt 理解": "Prompt设计",
            "SQL实战": "SQL",
            "A/B测试设计": "A/B测试",
            "模型评测体系": "模型评测体系",
            "Agent / RAG 系统理解": "Agent系统理解",
        }
        skills = []
        for strength in strengths:
            mapped = skill_map.get(strength, strength)
            if mapped not in skills:
                skills.append(mapped)
        return skills



def get_user_profile_service() -> UserProfileService:
    return UserProfileService()
