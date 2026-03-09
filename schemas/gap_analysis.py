from dataclasses import asdict, dataclass, field


@dataclass
class GapAnalysisResult:
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    priority_to_improve: list[str] = field(default_factory=list)
    match_score: int = 0
    advice: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def empty_gap_analysis() -> dict:
    return GapAnalysisResult(
        advice="暂时无法判断能力匹配度，请先查看 JD 智能解析结果。"
    ).to_dict()
