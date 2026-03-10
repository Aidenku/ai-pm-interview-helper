const PROFILE_DATA_KEY = "ai_pm_radar_profile_data";

const MODES = {
  quick: {
    key: "quick",
    label: "快速模式",
    total_questions: 5,
    pressure_mode: false,
    description: "5题快速热身，覆盖产品基础、AI专项和项目深挖。",
  },
  standard: {
    key: "standard",
    label: "标准模式",
    total_questions: 10,
    pressure_mode: false,
    description: "10题完整训练，适合系统练习表达结构和AI理解。",
  },
  pressure: {
    key: "pressure",
    label: "压力模式",
    total_questions: 8,
    pressure_mode: true,
    description: "8题高压训练，会更强调追问、深挖和反问式反馈。",
  },
};

const LOCAL_QUESTION_BANK = {
  "产品基础题": [
    {
      question_id: "local-product-priority",
      question: "你会如何判断一个需求的优先级？",
      category: "产品基础题",
      focus_points: ["目标澄清", "用户价值", "业务价值", "资源约束"],
      answer_framework: "结论先行 + 分点回答",
      why_this_matters: "考察基础产品判断和取舍能力。",
      question_kind: "main",
      parent_question_id: "",
      question_source: "universal",
      context_label: "通用题",
    },
    {
      question_id: "local-product-eval",
      question: "如果要上线一个新功能，你会如何设计效果评估方案？",
      category: "产品基础题",
      focus_points: ["目标", "指标", "实验设计", "复盘"],
      answer_framework: "目标 -> 指标 -> 数据 -> 结论",
      why_this_matters: "考察产品闭环与指标设计能力。",
      question_kind: "main",
      parent_question_id: "",
      question_source: "universal",
      context_label: "通用题",
    },
  ],
  "AI专项题": [
    {
      question_id: "local-ai-rag",
      question: "RAG 是什么？适合解决什么问题？",
      category: "AI专项题",
      focus_points: ["概念", "适用场景", "边界", "价值"],
      answer_framework: "定义 -> 场景 -> 局限",
      why_this_matters: "考察 AI 产品系统理解。",
      question_kind: "main",
      parent_question_id: "",
      question_source: "universal",
      context_label: "通用题",
    },
    {
      question_id: "local-ai-eval",
      question: "你会如何评估一个 AI 产品回答质量？",
      category: "AI专项题",
      focus_points: ["离线评测", "线上指标", "人工评审", "badcase"],
      answer_framework: "评测维度 + 评测流程",
      why_this_matters: "考察评测体系与AI产品方法论。",
      question_kind: "main",
      parent_question_id: "",
      question_source: "universal",
      context_label: "通用题",
    },
  ],
  "项目深挖题": [
    {
      question_id: "local-project-why",
      question: "你为什么做这个 AI PM 岗位分析工具？最初想解决什么问题？",
      category: "项目深挖题",
      focus_points: ["背景", "痛点", "目标用户", "价值"],
      answer_framework: "背景 -> 问题 -> 方案 -> 价值",
      why_this_matters: "考察你是否真正理解自己做的项目。",
      question_kind: "main",
      parent_question_id: "",
      question_source: "universal",
      context_label: "通用题",
    },
    {
      question_id: "local-project-llm",
      question: "为什么选择在这些节点使用 LLM，而不是全部用规则？",
      category: "项目深挖题",
      focus_points: ["边界判断", "成本", "稳定性", "兜底策略"],
      answer_framework: "对比式回答",
      why_this_matters: "考察你对 AI 工程边界的理解。",
      question_kind: "main",
      parent_question_id: "",
      question_source: "universal",
      context_label: "通用题",
    },
  ],
};

const CATEGORY_ROTATIONS = {
  quick: ["产品基础题", "AI专项题", "项目深挖题", "AI专项题", "产品基础题"],
  standard: ["产品基础题", "AI专项题", "项目深挖题", "产品基础题", "AI专项题", "项目深挖题", "产品基础题", "AI专项题", "项目深挖题", "产品基础题"],
  pressure: ["项目深挖题", "AI专项题", "产品基础题", "项目深挖题", "AI专项题", "产品基础题", "项目深挖题", "AI专项题"],
};

const QUESTION_STRATEGY_PLANS = {
  quick: ["universal", "job_specific", "resume_deep_dive", "job_specific", "universal"],
  standard: ["universal", "job_specific", "resume_deep_dive", "universal", "job_specific", "universal", "resume_deep_dive", "job_specific", "universal", "job_specific"],
  pressure: ["resume_deep_dive", "job_specific", "universal", "resume_deep_dive", "job_specific", "universal", "job_specific", "resume_deep_dive"],
};

const state = {
  mode: "quick",
  started: false,
  finished: false,
  currentQuestion: null,
  currentIndex: 0,
  totalQuestions: MODES.quick.total_questions,
  messages: [],
  askedQuestionIds: [],
  answeredCurrent: false,
  lastEngineSource: "fallback",
  pendingFollowUpQuestion: null,
  isFollowUpRound: false,
  userProfile: null,
  jobContext: null,
};

const el = {
  startInterviewBtn: document.getElementById("startInterviewBtn"),
  modeCards: Array.from(document.querySelectorAll(".mode-card")),
  mockEmpty: document.getElementById("mockEmpty"),
  mockChatList: document.getElementById("mockChatList"),
  answerInput: document.getElementById("answerInput"),
  submitAnswerBtn: document.getElementById("submitAnswerBtn"),
  answerFollowUpBtn: document.getElementById("answerFollowUpBtn"),
  nextQuestionBtn: document.getElementById("nextQuestionBtn"),
  endInterviewBtn: document.getElementById("endInterviewBtn"),
  mockStatusText: document.getElementById("mockStatusText"),
  currentCategory: document.getElementById("currentCategory"),
  currentStrategy: document.getElementById("currentStrategy"),
  currentFocusPoints: document.getElementById("currentFocusPoints"),
  currentFramework: document.getElementById("currentFramework"),
  currentProgress: document.getElementById("currentProgress"),
  currentModeDesc: document.getElementById("currentModeDesc"),
  engineBadge: document.getElementById("engineBadge"),
  jobContextText: document.getElementById("jobContextText"),
  profileContextText: document.getElementById("profileContextText"),
};

function escapeHtml(input) {
  return String(input || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function renderChipList(target, items, emptyText = "暂无") {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    target.innerHTML = `<span class="chip muted-chip">${escapeHtml(emptyText)}</span>`;
    return;
  }
  target.innerHTML = values.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
}

function normalizeQuestion(question) {
  if (!question) return null;
  const source = ["universal", "job_specific", "resume_deep_dive"].includes(question.question_source)
    ? question.question_source
    : "universal";
  return {
    question_id: question.question_id || `local-${Date.now()}`,
    question: question.question || "未命名问题",
    category: question.category || "产品基础题",
    focus_points: Array.isArray(question.focus_points) ? question.focus_points : [],
    answer_framework: question.answer_framework || "结论先行 + 分点回答",
    why_this_matters: question.why_this_matters || "这道题用来考察 AI PM 的通用能力。",
    question_kind: question.question_kind || "main",
    parent_question_id: question.parent_question_id || "",
    question_source: source,
    context_label: question.context_label || strategyLabel(source),
  };
}

function strategyLabel(source) {
  if (source === "job_specific") return "岗位业务面";
  if (source === "resume_deep_dive") return "简历深挖题";
  return "通用题";
}

function setMode(modeKey) {
  state.mode = MODES[modeKey] ? modeKey : "quick";
  state.totalQuestions = MODES[state.mode].total_questions;
  el.modeCards.forEach((card) => {
    card.classList.toggle("active-mode", card.dataset.mode === state.mode);
  });
  el.currentModeDesc.textContent = MODES[state.mode].description;
  updateSidebar(null);
}

function renderMessages() {
  const hasMessages = state.messages.length > 0;
  el.mockEmpty.classList.toggle("hidden", hasMessages);
  el.mockChatList.classList.toggle("hidden", !hasMessages);
  if (!hasMessages) {
    el.mockChatList.innerHTML = "";
    return;
  }
  el.mockChatList.innerHTML = state.messages.map((message) => {
    if (message.type === "feedback") {
      const payload = message.payload || {};
      const evaluation = payload.evaluation || {};
      const tips = (payload.improvement_tips || []).map((tip) => `<li>${escapeHtml(tip)}</li>`).join("");
      const followUp = payload.follow_up_question
        ? `<div class="feedback-followup"><span class="message-badge">已准备追问</span><p>${escapeHtml(payload.follow_up_question)}</p></div>`
        : "";
      return `
        <article class="mock-message feedback-message">
          <div class="message-badge">反馈</div>
          <div class="feedback-grid">
            <span>相关性：${escapeHtml(evaluation.relevance || "-")}</span>
            <span>结构：${escapeHtml(evaluation.structure || "-")}</span>
            <span>深度：${escapeHtml(evaluation.depth || "-")}</span>
          </div>
          <p>${escapeHtml(payload.feedback || "")}</p>
          <ul class="feedback-tips">${tips}</ul>
          ${followUp}
        </article>
      `;
    }
    const roleLabel = message.type === "interviewer" ? "面试官提问" : message.type === "system" ? "训练状态" : "你的回答";
    const sourceLabel = message.payload?.context_label ? `<span class="message-badge secondary-badge">${escapeHtml(message.payload.context_label)}</span>` : "";
    return `
      <article class="mock-message ${escapeHtml(message.type)}-message">
        <div class="message-badge-row">
          <span class="message-badge">${escapeHtml(roleLabel)}</span>
          ${sourceLabel}
        </div>
        <p>${escapeHtml(message.text || "")}</p>
      </article>
    `;
  }).join("");
  el.mockChatList.scrollTop = el.mockChatList.scrollHeight;
}

function updateSidebar(question) {
  const activeQuestion = question || state.currentQuestion;
  el.currentCategory.textContent = activeQuestion?.category || "-";
  el.currentStrategy.textContent = activeQuestion?.context_label || "通用题";
  renderChipList(el.currentFocusPoints, activeQuestion?.focus_points || [], "等待题目");
  el.currentFramework.textContent = activeQuestion?.answer_framework || "-";
  const suffix = state.isFollowUpRound ? " · 当前为追问" : "";
  el.currentProgress.textContent = state.started
    ? `第 ${state.currentIndex} 题 / 共 ${state.totalQuestions} 题${suffix}`
    : `共 ${state.totalQuestions} 题`;
}

function setEngineBadge(source) {
  state.lastEngineSource = source || "fallback";
  el.engineBadge.textContent = state.lastEngineSource === "llm" ? "训练引擎：LLM" : "训练引擎：本地兜底";
}

function setStatus(text) {
  el.mockStatusText.textContent = text;
}

function updateControls() {
  const canSubmit = state.started && !state.finished && !state.answeredCurrent && !!state.currentQuestion;
  const canNext = state.started && !state.finished && state.answeredCurrent;
  const canFollowUp = state.started && !state.finished && state.answeredCurrent && !!state.pendingFollowUpQuestion;
  el.submitAnswerBtn.disabled = !canSubmit;
  el.answerFollowUpBtn.disabled = !canFollowUp;
  el.nextQuestionBtn.disabled = !canNext;
  el.nextQuestionBtn.textContent = state.pendingFollowUpQuestion ? "跳过追问，下一题" : "下一题";
  el.answerInput.disabled = !canSubmit;
}

function resetSession() {
  state.started = false;
  state.finished = false;
  state.currentQuestion = null;
  state.currentIndex = 0;
  state.messages = [];
  state.askedQuestionIds = [];
  state.answeredCurrent = false;
  state.pendingFollowUpQuestion = null;
  state.isFollowUpRound = false;
  el.answerInput.value = "";
  renderMessages();
  updateSidebar(null);
  setStatus("当前未开始训练。");
  updateControls();
}

function addMessage(type, text, payload = null) {
  state.messages.push({ type, text, payload });
  renderMessages();
}

function getCategoryForIndex(modeKey, index) {
  const sequence = CATEGORY_ROTATIONS[modeKey] || CATEGORY_ROTATIONS.quick;
  return sequence[Math.min(index, sequence.length - 1)] || "产品基础题";
}

function getQuestionStrategy(modeKey, index) {
  const plan = QUESTION_STRATEGY_PLANS[modeKey] || QUESTION_STRATEGY_PLANS.quick;
  const source = plan[Math.min(index, plan.length - 1)] || "universal";
  if (source === "job_specific" && !state.jobContext) return "universal";
  if (source === "resume_deep_dive" && !state.userProfile) return "universal";
  return source;
}

function extractJobDomain() {
  return state.jobContext?.job_domain_analysis?.primary_domain || state.jobContext?.gap_analysis?.job_domain_analysis?.primary_domain || "";
}

function buildLocalJobQuestion(category) {
  const domain = extractJobDomain();
  const company = state.jobContext?.company || "目标公司";
  const title = state.jobContext?.title || "目标岗位";
  const templates = {
    "广告商业化产品": {
      "产品基础题": `如果你负责${company}${title}，发现 CTR 提升但 ROI 下滑，你会怎么拆解问题并决定下一步？`,
      "AI专项题": "在广告商业化 AI 产品里，你会如何平衡点击率、转化率、ROI 和用户体验？",
      "项目深挖题": "如果让你从 0 到 1 设计一个 AI 广告优化能力，你会先打哪条链路：定向、创意、出价还是评估？为什么？",
    },
    "AI搜索产品": {
      "产品基础题": "如果 AI 搜索回答满意度下降，你会先排查 query 理解、召回、排序还是回答生成？为什么？",
      "AI专项题": "在 AI 搜索产品里，RAG 质量不好时你会重点优化哪一层？",
      "项目深挖题": "如果让你为一个 AI 搜索功能设计核心指标，你会怎么定义满意度、成功率和留存之间的关系？",
    },
  };
  const text = templates[domain]?.[category];
  if (!text) return null;
  return normalizeQuestion({
    question_id: `local-job-${domain}-${category}`,
    question: text,
    category,
    focus_points: ["业务链路", "核心指标", "取舍逻辑", "验证方式"],
    answer_framework: "先结论，再拆业务链路和指标",
    why_this_matters: "这是一道岗位业务面问题，重点考察你是否真正进入目标岗位场景。",
    question_kind: "main",
    parent_question_id: "",
    question_source: "job_specific",
    context_label: `岗位业务面 · ${domain || "目标岗位"}`,
  });
}

function buildLocalResumeQuestion(category) {
  const project = state.userProfile?.project_experiences?.[0] || state.userProfile?.ai_experiences?.[0] || state.userProfile?.product_experiences?.[0] || state.userProfile?.summary;
  if (!project) return null;
  return normalizeQuestion({
    question_id: `local-resume-${Date.now()}`,
    question: `你提到做过“${project.slice(0, 36)}”。请具体讲你负责的目标、关键决策、结果指标，以及你本人起到的作用。`,
    category,
    focus_points: ["本人职责", "关键决策", "结果指标", "复盘反思"],
    answer_framework: "背景 -> 目标 -> 你的动作 -> 结果",
    why_this_matters: "这道题会验证你是否真的做过这段经历。",
    question_kind: "main",
    parent_question_id: "",
    question_source: "resume_deep_dive",
    context_label: "简历深挖题",
  });
}

function buildLocalQuestion(modeKey, index, askedIds) {
  const category = getCategoryForIndex(modeKey, index);
  const strategy = getQuestionStrategy(modeKey, index);
  if (strategy === "job_specific") {
    const question = buildLocalJobQuestion(category);
    if (question && !askedIds.includes(question.question_id)) return question;
  }
  if (strategy === "resume_deep_dive") {
    const question = buildLocalResumeQuestion(category);
    if (question && !askedIds.includes(question.question_id)) return question;
  }
  const categories = [category, "产品基础题", "AI专项题", "项目深挖题"];
  for (const name of categories) {
    const list = LOCAL_QUESTION_BANK[name] || [];
    const candidate = list.find((item) => !askedIds.includes(item.question_id));
    if (candidate) return normalizeQuestion(candidate);
  }
  return normalizeQuestion(LOCAL_QUESTION_BANK[category][0]);
}

function buildLocalFollowUp(question, modeKey, evaluation) {
  if (question.question_kind === "follow_up") return null;
  const shouldFollowUp = MODES[modeKey].pressure_mode || evaluation.structure === "较弱" || evaluation.depth === "较弱";
  if (!shouldFollowUp) return null;
  let text = "请你再把刚才的回答更结构化一点，先给结论，再讲依据。";
  if (question.question_source === "resume_deep_dive") {
    text = "刚才这段经历里，真正由你拍板的决策是什么？如果结果没有达到预期，你会怎么复盘？";
  } else if (question.question_source === "job_specific") {
    text = extractJobDomain() === "广告商业化产品"
      ? "如果 CTR 提升但 ROI 继续下滑，你会优先动流量策略、创意策略还是转化链路？为什么？"
      : "如果业务结果没有提升，你会先排查哪条业务链路？为什么？";
  } else if (question.category === "AI专项题") {
    text = "如果线上效果没有提升，你会优先排查模型、提示词、检索还是产品交互？为什么？";
  } else if (question.category === "项目深挖题") {
    text = "如果这个项目结果不准，你会优先优化哪个节点？你会怎么验证优化是否有效？";
  }
  return normalizeQuestion({
    question_id: `followup-${question.question_id}`,
    question: text,
    category: question.category,
    focus_points: ["结构化表达", "关键判断依据", "指标或取舍逻辑"],
    answer_framework: "先结论，再讲依据和取舍",
    why_this_matters: "这道追问用于进一步验证你的分析深度和表达结构。",
    question_kind: "follow_up",
    parent_question_id: question.question_id,
    question_source: question.question_source,
    context_label: question.question_source === "job_specific" ? "岗位追问" : question.question_source === "resume_deep_dive" ? "简历追问" : "通用追问",
  });
}

function buildLocalFeedback(question, answer, modeKey) {
  const text = String(answer || "").trim();
  const length = text.length;
  const lower = text.toLowerCase();
  const structureHits = ["首先", "其次", "最后", "第一", "第二", "第三", "first", "second", "finally"].filter((keyword) => text.includes(keyword) || lower.includes(keyword)).length;
  const depthHits = ["指标", "实验", "评测", "取舍", "prompt", "rag", "agent", "召回", "排序", "roi", "ctr"].filter((keyword) => text.includes(keyword) || lower.includes(keyword)).length;
  const relevance = length >= 90 ? "较强" : length >= 45 ? "一般" : "较弱";
  const structure = structureHits >= 2 ? "较强" : structureHits >= 1 ? "一般" : "较弱";
  const depth = depthHits >= 3 ? "较强" : depthHits >= 1 ? "一般" : "较弱";
  const tips = [];
  if (relevance === "较弱") tips.push("先明确题目在问什么，再回答目标、对象和判断逻辑。");
  if (structure !== "较强") tips.push("建议采用结论先行，再按 2 到 3 点展开的结构。");
  if (depth !== "较强") tips.push("适当补充指标、实验方案或系统链路，会更像 AI PM 面试回答。");
  if (question.question_source === "resume_deep_dive") tips.push("简历深挖题要讲清你本人负责部分、结果指标和复盘，而不是泛泛描述项目。");
  if (question.question_source === "job_specific") tips.push("岗位业务题要回到具体业务场景、核心指标和取舍，不要只讲通用框架。");
  const evaluation = { relevance, structure, depth };
  const followUp = buildLocalFollowUp(question, modeKey, evaluation);
  const feedback = question.question_source === "resume_deep_dive" && depth === "较弱"
    ? "这道题本质上在验证你是否真的做过这段经历。当前回答更像概述，缺少你本人决策、结果指标和复盘细节。"
    : question.question_source === "job_specific" && depth === "较弱"
      ? "你有一定产品思路，但还没真正进入该岗位业务场景。需要把回答落到具体链路、指标和权衡。"
      : relevance === "较强" && structure === "较强"
        ? "你的回答已经有比较完整的结构，下一步要继续加强分析深度和业务取舍逻辑。"
        : "你的回答方向基本正确，但还可以进一步压缩表达、补充逻辑和数据视角。";
  return {
    question: question.question,
    category: question.category,
    evaluation,
    feedback,
    improvement_tips: tips.slice(0, 4).map((tip) => tip.trim()),
    follow_up: followUp,
    follow_up_question: followUp?.question || "",
  };
}

function buildInterviewContextPayload() {
  const job = state.jobContext
    ? {
        id: state.jobContext.id,
        company: state.jobContext.company,
        title: state.jobContext.title,
        jd_text: state.jobContext.jd_text,
        jd_analysis: state.jobContext.jd_analysis,
        gap_analysis: state.jobContext.gap_analysis,
        job_domain_analysis: state.jobContext.gap_analysis?.job_domain_analysis || state.jobContext.job_domain_analysis,
      }
    : null;
  return {
    profile_analysis: state.userProfile || null,
    job_context: job,
  };
}

async function hydrateInterviewContext() {
  try {
    state.userProfile = JSON.parse(localStorage.getItem(PROFILE_DATA_KEY) || "null");
  } catch (_) {
    state.userProfile = null;
  }
  const jobId = new URLSearchParams(window.location.search).get("job_id");
  if (jobId && /^\d+$/.test(jobId)) {
    try {
      state.jobContext = await fetchJSON(`/api/jobs/${jobId}`);
    } catch (_) {
      state.jobContext = null;
    }
  }
  updateContextPanel();
}

function updateContextPanel() {
  if (state.jobContext) {
    const domain = state.jobContext?.gap_analysis?.job_domain_analysis?.primary_domain || state.jobContext?.job_domain_analysis?.primary_domain || "未识别岗位场景";
    el.jobContextText.textContent = `${state.jobContext.company} · ${state.jobContext.title} · ${domain}`;
  } else {
    el.jobContextText.textContent = "当前未绑定具体岗位，将进行通用训练。";
  }

  if (state.userProfile && state.userProfile.source !== "default") {
    const domains = (state.userProfile.strong_domains || []).slice(0, 2).join(" / ");
    const summary = state.userProfile.summary || domains || "已加载个人画像";
    el.profileContextText.textContent = summary;
  } else {
    el.profileContextText.textContent = "当前未读取个人画像，将不会生成简历深挖题。";
  }
}

async function startInterview() {
  resetSession();
  setStatus("正在生成第一道题...");
  try {
    const result = await postJSON("/api/mock-interview/start", {
      mode: state.mode,
      ...buildInterviewContextPayload(),
    });
    const question = normalizeQuestion(result?.data?.question);
    if (!question) throw new Error("empty question");
    state.started = true;
    state.currentQuestion = question;
    state.currentIndex = 1;
    state.totalQuestions = result?.data?.session?.total_questions || MODES[state.mode].total_questions;
    state.askedQuestionIds = [question.question_id];
    state.answeredCurrent = false;
    state.pendingFollowUpQuestion = null;
    state.isFollowUpRound = false;
    addMessage("interviewer", question.question, question);
    updateSidebar(question);
    setEngineBadge(result?.meta?.source || "fallback");
    setStatus("第一题已生成，开始作答。");
    updateControls();
  } catch (_) {
    const question = buildLocalQuestion(state.mode, 0, []);
    state.started = true;
    state.currentQuestion = question;
    state.currentIndex = 1;
    state.totalQuestions = MODES[state.mode].total_questions;
    state.askedQuestionIds = [question.question_id];
    state.answeredCurrent = false;
    state.pendingFollowUpQuestion = null;
    state.isFollowUpRound = false;
    addMessage("interviewer", question.question, question);
    updateSidebar(question);
    setEngineBadge("fallback");
    setStatus("接口暂不可用，已切换到本地练习模式。");
    updateControls();
  }
}

async function submitAnswer() {
  const answer = el.answerInput.value.trim();
  if (!answer || !state.currentQuestion || state.answeredCurrent) return;

  addMessage("user", answer);
  el.answerInput.value = "";
  setStatus(state.isFollowUpRound ? "正在生成追问反馈..." : "正在生成反馈...");
  updateControls();

  const history = state.messages.map((item) => {
    if (item.type === "user") return { role: "candidate", content: item.text };
    if (item.type === "interviewer") return { role: "interviewer", content: item.text };
    if (item.type === "feedback") return { role: "feedback", content: item.payload.feedback };
    return { role: item.type, content: item.text };
  });

  try {
    const result = await postJSON("/api/mock-interview/respond", {
      mode: state.mode,
      question: state.currentQuestion,
      answer,
      history,
      ...buildInterviewContextPayload(),
    });
    const feedback = result?.data;
    if (!feedback) throw new Error("empty feedback");
    feedback.follow_up = normalizeQuestion(feedback.follow_up);
    addMessage("feedback", "", feedback);
    state.answeredCurrent = true;
    state.pendingFollowUpQuestion = state.isFollowUpRound ? null : normalizeQuestion(feedback.follow_up);
    state.isFollowUpRound = false;
    setEngineBadge(result?.meta?.source || state.lastEngineSource);
    setStatus(state.pendingFollowUpQuestion ? "已生成反馈，并准备了一道追问。" : "已生成反馈，可以进入下一题。");
    updateControls();
  } catch (_) {
    const feedback = buildLocalFeedback(state.currentQuestion, answer, state.mode);
    addMessage("feedback", "", feedback);
    state.answeredCurrent = true;
    state.pendingFollowUpQuestion = state.isFollowUpRound ? null : normalizeQuestion(feedback.follow_up);
    state.isFollowUpRound = false;
    setEngineBadge("fallback");
    setStatus(state.pendingFollowUpQuestion ? "接口暂不可用，已使用本地反馈并生成追问。" : "接口暂不可用，已使用本地反馈兜底。");
    updateControls();
  }
}

async function nextQuestion() {
  if (!state.started || !state.answeredCurrent) return;
  if (state.currentIndex >= state.totalQuestions) {
    finishInterview();
    return;
  }

  state.pendingFollowUpQuestion = null;
  state.isFollowUpRound = false;
  setStatus("正在准备下一题...");
  try {
    const result = await postJSON("/api/mock-interview/next", {
      mode: state.mode,
      question_index: state.currentIndex,
      asked_questions: state.askedQuestionIds,
      history: state.messages,
      ...buildInterviewContextPayload(),
    });
    if (result?.data?.finished) {
      finishInterview();
      return;
    }
    const question = normalizeQuestion(result?.data?.question);
    if (!question) throw new Error("empty next question");
    state.currentQuestion = question;
    state.currentIndex += 1;
    state.askedQuestionIds.push(question.question_id);
    state.answeredCurrent = false;
    addMessage("interviewer", question.question, question);
    updateSidebar(question);
    setEngineBadge(result?.meta?.source || state.lastEngineSource);
    setStatus("下一题已生成。");
    updateControls();
  } catch (_) {
    const question = buildLocalQuestion(state.mode, state.currentIndex, state.askedQuestionIds);
    state.currentQuestion = question;
    state.currentIndex += 1;
    state.askedQuestionIds.push(question.question_id);
    state.answeredCurrent = false;
    addMessage("interviewer", question.question, question);
    updateSidebar(question);
    setEngineBadge("fallback");
    setStatus("接口暂不可用，已切换到本地题库继续训练。");
    updateControls();
  }
}

function answerFollowUp() {
  if (!state.pendingFollowUpQuestion) return;
  state.currentQuestion = normalizeQuestion(state.pendingFollowUpQuestion);
  state.pendingFollowUpQuestion = null;
  state.answeredCurrent = false;
  state.isFollowUpRound = true;
  addMessage("interviewer", state.currentQuestion.question, state.currentQuestion);
  updateSidebar(state.currentQuestion);
  setStatus("请回答这道追问，它不会占用新的题号。");
  updateControls();
}

function finishInterview() {
  state.finished = true;
  state.answeredCurrent = false;
  state.currentQuestion = null;
  state.pendingFollowUpQuestion = null;
  state.isFollowUpRound = false;
  addMessage("system", `本轮结束。你已完成 ${state.currentIndex} / ${state.totalQuestions} 题训练。`);
  setStatus("本轮模拟已结束，可以重新开始下一轮。");
  updateSidebar(null);
  updateControls();
}

function bindEvents() {
  el.modeCards.forEach((card) => {
    card.addEventListener("click", () => setMode(card.dataset.mode));
  });
  el.startInterviewBtn.addEventListener("click", () => {
    startInterview().catch(() => {});
  });
  el.submitAnswerBtn.addEventListener("click", () => {
    submitAnswer().catch(() => {});
  });
  el.answerFollowUpBtn.addEventListener("click", () => {
    answerFollowUp();
  });
  el.nextQuestionBtn.addEventListener("click", () => {
    nextQuestion().catch(() => {});
  });
  el.endInterviewBtn.addEventListener("click", () => {
    resetSession();
  });
}

async function bootstrap() {
  setMode("quick");
  updateSidebar(null);
  updateControls();
  renderMessages();
  bindEvents();
  await hydrateInterviewContext();
}

bootstrap().catch(() => {
  setStatus("初始化上下文失败，已回退到通用训练模式。");
});
