from dataclasses import asdict, dataclass, field


@dataclass
class GapAnalysisEvidence:
    jd_signals: list[str] = field(default_factory=list)
    resume_signals: list[str] = field(default_factory=list)


@dataclass
class MatchScoreBreakdown:
    total_score: int = 0
    domain_score: int = 0
    general_score: int = 0
    evidence_score: int = 0
    level: str = "不建议投递"
    confidence: int = 0


@dataclass
class EvidenceCompareResult:
    matched_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    weak_evidence: list[str] = field(default_factory=list)
    hallucination_risk: bool = False


@dataclass
class GapAnalysisResult:
    job_domain_analysis: dict = field(default_factory=dict)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    potential_strengths: list[str] = field(default_factory=list)
    priority_to_improve: list[str] = field(default_factory=list)
    domain_gap: list[str] = field(default_factory=list)
    general_gap: list[str] = field(default_factory=list)
    priority_gap: list[str] = field(default_factory=list)
    realistic_advice: list[str] = field(default_factory=list)
    not_recommended_reason: str = ""
    summary: str = ""
    match_score: int = 0
    advice: str = ""
    evidence: GapAnalysisEvidence = field(default_factory=GapAnalysisEvidence)
    score_breakdown: MatchScoreBreakdown = field(default_factory=MatchScoreBreakdown)
    evidence_compare: EvidenceCompareResult = field(default_factory=EvidenceCompareResult)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["evidence"] = asdict(self.evidence)
        data["score_breakdown"] = asdict(self.score_breakdown)
        data["evidence_compare"] = asdict(self.evidence_compare)
        return data


def empty_gap_analysis() -> dict:
    return GapAnalysisResult(
        realistic_advice=["先补充个人背景或简历，再重新生成岗位匹配分析。"],
        advice="暂时无法判断能力匹配度，请先查看 JD 智能解析结果。",
        summary="暂时无法判断能力匹配度，请先查看 JD 智能解析结果。",
        not_recommended_reason="缺少足够信息，当前不建议直接依据该结果投递。",
    ).to_dict()
