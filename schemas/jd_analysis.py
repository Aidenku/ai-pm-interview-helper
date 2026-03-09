from dataclasses import asdict, dataclass, field


@dataclass
class TechnicalRequirement:
    topic: str
    depth: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class JDAnalysisResult:
    keywords: list[str] = field(default_factory=list)
    skill_tags: list[str] = field(default_factory=list)
    technical_requirements: list[TechnicalRequirement] = field(default_factory=list)
    scenario_tags: list[str] = field(default_factory=list)
    difficulty: str = "入门"
    summary: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["technical_requirements"] = [asdict(item) for item in self.technical_requirements]
        return data


def empty_analysis() -> dict:
    return JDAnalysisResult(summary="暂未解析出稳定的结构化结论，请先阅读原始 JD。").to_dict()
