from dataclasses import asdict, dataclass, field


@dataclass
class JobDomainAnalysisResult:
    primary_domain: str = "通用AI产品"
    secondary_domain: str = ""
    domain_confidence: int = 0
    business_context: list[str] = field(default_factory=list)
    required_domain_experience: list[str] = field(default_factory=list)
    core_metrics: list[str] = field(default_factory=list)
    decision_focus: list[str] = field(default_factory=list)
    domain_keywords: list[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def empty_job_domain_analysis() -> dict:
    return JobDomainAnalysisResult(
        reasoning="当前 JD 信号不足，先按通用AI产品处理。",
    ).to_dict()
