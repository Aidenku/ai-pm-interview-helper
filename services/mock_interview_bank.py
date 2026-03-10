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


DOMAIN_BUSINESS_TEMPLATES = {
    "广告商业化产品": {
        "产品基础题": {
            "question": "如果你负责{company}{title}，发现 CTR 提升但 ROI 下滑，你会怎么拆解问题并决定下一步？",
            "focus_points": ["目标冲突", "流量质量", "出价与定向", "收入与体验平衡"],
            "framework": "先判断问题归因，再讲策略取舍",
            "why": "这是典型广告商业化业务面问题，核心看你是否理解变现链路和指标权衡。",
        },
        "AI专项题": {
            "question": "在广告商业化 AI 产品里，你会如何平衡点击率、转化率、ROI 和用户体验？",
            "focus_points": ["多目标优化", "策略分层", "实验验证", "约束条件"],
            "framework": "先目标排序，再讲策略与验证",
            "why": "商业化岗位会重点看你是否能处理多目标冲突，而不是只会讲模型能力。",
        },
        "项目深挖题": {
            "question": "如果让你从 0 到 1 设计一个 AI 广告优化能力，你会先打哪条链路：定向、创意、出价还是评估？为什么？",
            "focus_points": ["链路选择", "优先级", "验证指标", "落地难点"],
            "framework": "结论先行 + 链路拆解",
            "why": "这类问题用来判断你是否真的理解广告商业化产品的业务优先级。",
        },
    },
    "AI搜索产品": {
        "产品基础题": {
            "question": "如果 AI 搜索回答满意度下降，你会先排查 query 理解、召回、排序还是回答生成？为什么？",
            "focus_points": ["问题定位", "链路拆解", "用户意图", "验证方式"],
            "framework": "先定界问题，再按链路排查",
            "why": "AI 搜索岗位会重点看你是否能把搜索问题拆到可执行链路。",
        },
        "AI专项题": {
            "question": "在 AI 搜索产品里，RAG 质量不好时你会重点优化哪一层？",
            "focus_points": ["检索质量", "召回排序", "知识库质量", "评测体系"],
            "framework": "先定义问题，再讲优化优先级",
            "why": "这是 AI 搜索业务面高频题，核心看你是否理解检索增强链路。",
        },
        "项目深挖题": {
            "question": "如果让你为一个 AI 搜索功能设计核心指标，你会怎么定义满意度、成功率和留存之间的关系？",
            "focus_points": ["指标体系", "用户价值", "链路指标", "长期留存"],
            "framework": "目标 -> 指标树 -> 验证",
            "why": "搜索场景不仅要看答案质量，还要看用户是否真的完成任务。",
        },
    },
    "AI陪伴/社交产品": {
        "产品基础题": {
            "question": "如果一个 AI 陪伴产品短期活跃不错，但 7 日留存很低，你会优先从哪几层找原因？",
            "focus_points": ["人设稳定性", "长期记忆", "互动机制", "留存设计"],
            "framework": "先拆留存链路，再讲优化动作",
            "why": "陪伴场景更看长期关系和持续使用，而不是一次回答是否正确。",
        },
        "AI专项题": {
            "question": "你会如何评估一个 AI 陪伴角色的人设稳定性和情绪反馈质量？",
            "focus_points": ["角色一致性", "长期记忆", "用户主观体验", "安全边界"],
            "framework": "评测维度 + 线上验证",
            "why": "这类岗位会重点看你是否理解情感类 AI 产品的评测难点。",
        },
        "项目深挖题": {
            "question": "如果用户觉得 AI 角色越来越无聊，你会从产品机制和模型能力两侧怎么优化？",
            "focus_points": ["互动机制", "内容新鲜度", "记忆机制", "增长与留存"],
            "framework": "问题拆解 -> 优化假设 -> 验证",
            "why": "AI 陪伴产品最怕短期新鲜感过去后留存断崖式下滑。",
        },
    },
    "推荐策略产品": {
        "产品基础题": {
            "question": "如果推荐点击率上升但用户停留时长下降，你会怎么判断问题出在召回、排序还是分发策略？",
            "focus_points": ["指标冲突", "召回排序", "内容质量", "用户价值"],
            "framework": "先看目标，再拆策略链路",
            "why": "推荐策略岗位最常见的就是多指标冲突下的策略判断。",
        },
        "AI专项题": {
            "question": "推荐系统里为什么不能只盯 CTR？你会补哪些指标来避免策略跑偏？",
            "focus_points": ["短期点击", "长期价值", "留存", "满意度"],
            "framework": "指出风险 -> 给补充指标",
            "why": "推荐产品岗位更看重你是否理解指标设计和策略副作用。",
        },
        "项目深挖题": {
            "question": "如果你接手一个推荐策略项目，第一周会优先拿哪些数据判断当前策略有没有明显问题？",
            "focus_points": ["核心指标", "分层分析", "问题定位", "优化优先级"],
            "framework": "目标 -> 数据 -> 问题定位",
            "why": "这类问题用来判断你是否真的具备策略产品的工作方式。",
        },
    },
    "平台工具产品": {
        "产品基础题": {
            "question": "如果一个平台工具类产品使用率低，你会先判断是能力缺失、流程过长还是接入成本太高？",
            "focus_points": ["用户路径", "接入门槛", "平台价值", "流程效率"],
            "framework": "先拆 adoption 链路，再讲优化优先级",
            "why": "平台工具岗位经常考察你是否能从流程和效率角度看问题。",
        },
        "AI专项题": {
            "question": "如果你做一个 AI 工作台工具，怎么平衡灵活性、可控性和使用门槛？",
            "focus_points": ["配置能力", "默认体验", "权限治理", "错误成本"],
            "framework": "先讲约束，再讲产品方案",
            "why": "工具平台岗位更看重你是否理解平台化产品的治理和约束。",
        },
        "项目深挖题": {
            "question": "如果平台方、业务方和研发方的诉求不一致，你会怎么定义平台工具的优先级？",
            "focus_points": ["多方协同", "公共能力", "优先级框架", "治理规则"],
            "framework": "先明确目标，再讲排序依据",
            "why": "平台工具岗位天然是多方博弈场景。",
        },
    },
    "企业服务产品": {
        "产品基础题": {
            "question": "如果一个企业服务产品的流程很长、用户抱怨复杂，但业务方又坚持保留，你会怎么处理？",
            "focus_points": ["流程复杂度", "权限与合规", "业务约束", "产品简化"],
            "framework": "先识别不可动约束，再讲可优化部分",
            "why": "ToB 产品往往不是纯体验最优，而是体验、流程和组织约束的平衡。",
        },
        "AI专项题": {
            "question": "如果你做一个 ToB AI 助手，怎么证明它对企业客户是真的有价值，而不是 Demo 效果好看？",
            "focus_points": ["交付价值", "效率指标", "真实使用率", "业务结果"],
            "framework": "价值假设 -> 指标 -> 验证",
            "why": "企业服务岗位很看重你是否会用业务结果定义 AI 价值。",
        },
        "项目深挖题": {
            "question": "如果客户提出的需求都很定制化，你怎么判断要做成平台能力还是项目化交付？",
            "focus_points": ["共性抽象", "交付成本", "产品化边界", "优先级"],
            "framework": "先分共性与个性，再讲决策标准",
            "why": "ToB 产品最核心的难点之一就是产品化和项目化的边界判断。",
        },
    },
    "增长产品": {
        "产品基础题": {
            "question": "如果一个新用户转化漏斗掉得很厉害，你会先从哪几层拆问题？",
            "focus_points": ["漏斗拆解", "用户分层", "触达策略", "实验设计"],
            "framework": "先看漏斗，再做归因",
            "why": "增长岗位更看重你是否能快速定位漏斗问题，而不是只讲概念。",
        },
        "AI专项题": {
            "question": "如果用 AI 做增长策略，你会先把它用在创意生成、用户分群还是触达时机判断？为什么？",
            "focus_points": ["增长链路", "AI切入点", "ROI", "验证方式"],
            "framework": "场景选择 -> 预期收益 -> 验证",
            "why": "增长 + AI 的岗位会看你是否能把 AI 放到真正影响漏斗的节点。",
        },
        "项目深挖题": {
            "question": "如果你来设计一个增长实验体系，如何避免只优化短期转化而伤害长期留存？",
            "focus_points": ["短期与长期", "实验指标", "用户价值", "迭代机制"],
            "framework": "风险 -> 机制 -> 指标",
            "why": "增长岗位里，短期收益和长期价值冲突是经典难题。",
        },
    },
    "通用AI产品": {
        "产品基础题": {
            "question": "如果一个 AI 功能用户觉得有用，但日常使用率不高，你会怎么判断问题是在价值、入口还是交互？",
            "focus_points": ["用户价值", "入口设计", "使用频率", "留存"],
            "framework": "价值判断 -> 使用链路 -> 优化动作",
            "why": "通用 AI 产品岗位更看重你是否理解从能力到使用闭环的转化。",
        },
        "AI专项题": {
            "question": "如果一个 AI 产品回答看起来不错，但用户并不信任它，你会从哪几层改善？",
            "focus_points": ["可解释性", "准确性", "容错机制", "反馈闭环"],
            "framework": "信任问题拆解 -> 优化路径",
            "why": "AI 产品不只是效果问题，还包括用户是否愿意持续依赖它。",
        },
        "项目深挖题": {
            "question": "如果你要给一个通用 AI 产品设计上线前评估，你会如何定义通过门槛？",
            "focus_points": ["离线评测", "线上验证", "风险控制", "放量条件"],
            "framework": "评估维度 -> 门槛 -> 放量策略",
            "why": "这道题用来判断你是否具备把 AI 能力产品化的判断标准。",
        },
    },
}


def get_mode_config(mode_key: str) -> MockInterviewMode:
    return MODE_CONFIGS.get(mode_key, MODE_CONFIGS["quick"])


def get_category_sequence(mode_key: str) -> list[str]:
    return list(CATEGORY_ROTATIONS.get(mode_key, CATEGORY_ROTATIONS["quick"]))


def get_question_bank() -> dict[str, list[MockInterviewQuestion]]:
    return QUESTION_BANK


def get_business_question_template(domain: str, category: str) -> dict | None:
    return (DOMAIN_BUSINESS_TEMPLATES.get(domain) or DOMAIN_BUSINESS_TEMPLATES["通用AI产品"]).get(category)
