from schemas.mock_interview import MockInterviewMode, MockInterviewQuestion


MODE_CONFIGS = {
    "quick": MockInterviewMode(
        key="quick",
        label="快速模式",
        total_questions=5,
        pressure_mode=False,
        description="5题快速热身，覆盖产品基础、AI专项和项目深挖。",
    ),
    "standard": MockInterviewMode(
        key="standard",
        label="标准模式",
        total_questions=10,
        pressure_mode=False,
        description="10题完整训练，适合系统练习表达结构和AI理解。",
    ),
    "pressure": MockInterviewMode(
        key="pressure",
        label="压力模式",
        total_questions=8,
        pressure_mode=True,
        description="8题高压训练，会更强调追问、深挖和反问式反馈。",
    ),
}


CATEGORY_ROTATIONS = {
    "quick": ["产品基础题", "AI专项题", "项目深挖题", "AI专项题", "产品基础题"],
    "standard": [
        "产品基础题",
        "AI专项题",
        "项目深挖题",
        "产品基础题",
        "AI专项题",
        "项目深挖题",
        "产品基础题",
        "AI专项题",
        "项目深挖题",
        "产品基础题",
    ],
    "pressure": ["项目深挖题", "AI专项题", "产品基础题", "项目深挖题", "AI专项题", "产品基础题", "项目深挖题", "AI专项题"],
}


QUESTION_BANK = {
    "产品基础题": [
        MockInterviewQuestion(
            question_id="product-priority",
            question="你会如何判断一个需求的优先级？",
            category="产品基础题",
            focus_points=["目标澄清", "用户价值", "业务价值", "资源约束"],
            answer_framework="结论先行 + 分点回答",
            why_this_matters="这是 AI PM 面试里最常见的产品基础题，用来判断你是否具备清晰的产品判断框架。",
        ),
        MockInterviewQuestion(
            question_id="product-evaluation",
            question="如果要上线一个新功能，你会如何设计效果评估方案？",
            category="产品基础题",
            focus_points=["核心目标", "指标设计", "实验设计", "复盘机制"],
            answer_framework="目标 -> 指标 -> 数据 -> 结论",
            why_this_matters="面试官会通过这类问题判断你是否真正理解产品闭环，而不仅仅是会提需求。",
        ),
        MockInterviewQuestion(
            question_id="product-tradeoff",
            question="做产品时你怎么平衡用户价值和技术成本？",
            category="产品基础题",
            focus_points=["价值判断", "实现成本", "阶段性取舍", "跨团队协同"],
            answer_framework="结论先行 + 取舍逻辑",
            why_this_matters="AI 产品岗位经常要在体验、成本和上线节奏之间做取舍。",
        ),
        MockInterviewQuestion(
            question_id="product-abtest",
            question="如果一个功能上线后效果一般，你会如何判断是继续优化还是停止投入？",
            category="产品基础题",
            focus_points=["目标回看", "数据拆解", "问题归因", "决策阈值"],
            answer_framework="现象 -> 归因 -> 决策",
            why_this_matters="这道题主要考察你是否有迭代意识和结果思维。",
        ),
        MockInterviewQuestion(
            question_id="product-collaboration",
            question="如果研发认为你的需求实现成本过高，你会怎么推进？",
            category="产品基础题",
            focus_points=["目标对齐", "拆解方案", "阶段性方案", "协作推进"],
            answer_framework="先对齐目标，再提出方案",
            why_this_matters="AI PM 的实际工作中，跨团队协同和资源博弈是高频场景。",
        ),
    ],
    "AI专项题": [
        MockInterviewQuestion(
            question_id="ai-prompt-vs-ft",
            question="Prompt 和微调的区别是什么？各自适合什么场景？",
            category="AI专项题",
            focus_points=["成本差异", "上线速度", "适用边界", "维护方式"],
            answer_framework="定义差异 + 场景对比",
            why_this_matters="这是 AI PM 面试中最常见的基础题之一，用来判断你是否理解大模型产品的优化手段。",
        ),
        MockInterviewQuestion(
            question_id="ai-rag",
            question="RAG 是什么？它适合解决什么问题，不适合解决什么问题？",
            category="AI专项题",
            focus_points=["知识更新", "检索增强", "准确性提升", "边界条件"],
            answer_framework="概念 -> 适用场景 -> 局限",
            why_this_matters="这题通常用来判断你是否理解 AI 产品系统层面的设计，而不仅仅停留在模型表层。",
        ),
        MockInterviewQuestion(
            question_id="ai-agent",
            question="Agent 和普通 workflow 的区别是什么？",
            category="AI专项题",
            focus_points=["决策能力", "工具调用", "可控性", "场景适配"],
            answer_framework="先定义，再比较，再讲适用场景",
            why_this_matters="很多 AI PM 岗位会考察你是否知道什么时候该用 Agent，什么时候不该硬上。",
        ),
        MockInterviewQuestion(
            question_id="ai-evaluation",
            question="你会如何评估一个 AI 产品回答质量？",
            category="AI专项题",
            focus_points=["离线评测", "线上指标", "人工评审", "badcase管理"],
            answer_framework="评测维度 + 评测流程",
            why_this_matters="AI 产品的关键能力之一，就是把模型效果转译成可度量、可优化的产品指标。",
        ),
        MockInterviewQuestion(
            question_id="ai-hallucination",
            question="如果 AI 产品经常出现幻觉，你会怎么定位和优化？",
            category="AI专项题",
            focus_points=["问题分类", "链路排查", "提示词/检索/模型优化", "效果验证"],
            answer_framework="问题分类 -> 定位链路 -> 给出优化方案",
            why_this_matters="这道题主要考察你是否能把 AI 问题拆解成可执行的产品优化动作。",
        ),
    ],
    "项目深挖题": [
        MockInterviewQuestion(
            question_id="project-why-build",
            question="你为什么做这个 AI PM 岗位分析工具？你最初想解决什么问题？",
            category="项目深挖题",
            focus_points=["问题发现", "目标用户", "场景痛点", "方案选择"],
            answer_framework="背景 -> 痛点 -> 方案 -> 价值",
            why_this_matters="项目深挖最看重你是否真的理解你做的事情，而不是只会描述表层功能。",
        ),
        MockInterviewQuestion(
            question_id="project-workflow",
            question="你的工作流有哪些关键节点？为什么要这么设计？",
            category="项目深挖题",
            focus_points=["流程拆解", "模块职责", "设计取舍", "闭环逻辑"],
            answer_framework="先总后分",
            why_this_matters="这题用来判断你是否具备系统思维和清晰的产品结构表达能力。",
        ),
        MockInterviewQuestion(
            question_id="project-llm-usage",
            question="为什么选择在这些节点使用 LLM，而不是全部用规则？",
            category="项目深挖题",
            focus_points=["规则与模型边界", "成本", "稳定性", "可解释性"],
            answer_framework="对比式回答",
            why_this_matters="AI PM 面试官很关注你是否理解 LLM 在产品中的真实边界，而不是为了用 AI 而用 AI。",
        ),
        MockInterviewQuestion(
            question_id="project-accuracy",
            question="如果这个工具给出的岗位分析结果不准，你会怎么优化？",
            category="项目深挖题",
            focus_points=["问题定位", "数据回流", "prompt优化", "规则兜底"],
            answer_framework="问题定位 -> 方案 -> 验证",
            why_this_matters="这道题主要考察你是否具备产品迭代意识和结果导向。",
        ),
        MockInterviewQuestion(
            question_id="project-metrics",
            question="如果你来定义这个工具的核心指标，你会怎么设计？",
            category="项目深挖题",
            focus_points=["用户价值指标", "使用行为指标", "结果指标", "长期留存"],
            answer_framework="目标 -> 指标树",
            why_this_matters="这是项目深挖里最容易拉开差距的一题，考察你的抽象和指标设计能力。",
        ),
    ],
}


def get_mode_config(mode_key: str) -> MockInterviewMode:
    return MODE_CONFIGS.get(mode_key, MODE_CONFIGS["quick"])


def get_category_sequence(mode_key: str) -> list[str]:
    return list(CATEGORY_ROTATIONS.get(mode_key, CATEGORY_ROTATIONS["quick"]))


def get_question_bank() -> dict[str, list[MockInterviewQuestion]]:
    return QUESTION_BANK
