from dataclasses import asdict, dataclass, field


@dataclass
class UserProfile:
    profile_id: str
    target_role: str
    strengths: list[str] = field(default_factory=list)
    weak_areas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_USER_PROFILE = UserProfile(
    profile_id="default_ai_pm_intern",
    target_role="AI产品经理实习",
    strengths=[
        "产品需求分析",
        "基础数据分析",
        "用户场景拆解",
        "基础 Prompt 理解",
    ],
    weak_areas=[
        "SQL实战",
        "A/B测试设计",
        "模型评测体系",
        "Agent / RAG 系统理解",
        "指标体系与漏斗分析",
    ],
)


class UserProfileService:
    def get_default_profile(self) -> UserProfile:
        return DEFAULT_USER_PROFILE


def get_user_profile_service() -> UserProfileService:
    return UserProfileService()
