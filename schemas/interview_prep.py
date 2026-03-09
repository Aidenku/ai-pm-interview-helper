from dataclasses import asdict, dataclass, field


@dataclass
class InterviewQuestion:
    question: str
    category: str
    why_this_may_be_asked: str
    suggested_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InterviewPrepResult:
    questions: list[InterviewQuestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"questions": [question.to_dict() for question in self.questions]}


def empty_interview_prep() -> dict:
    return InterviewPrepResult().to_dict()
