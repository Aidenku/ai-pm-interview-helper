from dataclasses import dataclass, field


@dataclass
class MockInterviewQuestion:
    question_id: str
    question: str
    category: str
    focus_points: list[str] = field(default_factory=list)
    answer_framework: str = "结论先行"
    why_this_matters: str = ""
    question_source: str = "universal"
    context_label: str = "通用题"

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "category": self.category,
            "focus_points": list(self.focus_points),
            "answer_framework": self.answer_framework,
            "why_this_matters": self.why_this_matters,
            "question_source": self.question_source,
            "context_label": self.context_label,
        }


@dataclass
class MockInterviewMode:
    key: str
    label: str
    total_questions: int
    pressure_mode: bool
    description: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "total_questions": self.total_questions,
            "pressure_mode": self.pressure_mode,
            "description": self.description,
        }


@dataclass
class MockInterviewFeedback:
    question: str
    category: str
    evaluation: dict
    feedback: str
    improvement_tips: list[str] = field(default_factory=list)
    follow_up_question: str = ""

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "category": self.category,
            "evaluation": dict(self.evaluation),
            "feedback": self.feedback,
            "improvement_tips": list(self.improvement_tips),
            "follow_up_question": self.follow_up_question,
        }
