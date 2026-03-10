from dataclasses import asdict, dataclass, field


@dataclass
class ProfileAnalysisResult:
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    project_experiences: list[str] = field(default_factory=list)
    ai_experiences: list[str] = field(default_factory=list)
    product_experiences: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def empty_profile_analysis() -> dict:
    return ProfileAnalysisResult(summary="暂未解析出稳定的个人画像，请补充更多简历或项目描述。",).to_dict()
