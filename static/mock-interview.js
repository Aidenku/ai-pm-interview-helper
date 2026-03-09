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
    },
    {
      question_id: "local-product-eval",
      question: "如果要上线一个新功能，你会如何设计效果评估方案？",
      category: "产品基础题",
      focus_points: ["目标", "指标", "实验设计", "复盘"],
      answer_framework: "目标 -> 指标 -> 数据 -> 结论",
      why_this_matters: "考察产品闭环与指标设计能力。",
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
    },
    {
      question_id: "local-ai-eval",
      question: "你会如何评估一个 AI 产品回答质量？",
      category: "AI专项题",
      focus_points: ["离线评测", "线上指标", "人工评审", "badcase"],
      answer_framework: "评测维度 + 评测流程",
      why_this_matters: "考察评测体系与AI产品方法论。",
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
    },
    {
      question_id: "local-project-llm",
      question: "为什么选择在这些节点使用 LLM，而不是全部用规则？",
      category: "项目深挖题",
      focus_points: ["边界判断", "成本", "稳定性", "兜底策略"],
      answer_framework: "对比式回答",
      why_this_matters: "考察你对 AI 工程边界的理解。",
    },
  ],
};

const CATEGORY_ROTATIONS = {
  quick: ["产品基础题", "AI专项题", "项目深挖题", "AI专项题", "产品基础题"],
  standard: ["产品基础题", "AI专项题", "项目深挖题", "产品基础题", "AI专项题", "项目深挖题", "产品基础题", "AI专项题", "项目深挖题", "产品基础题"],
  pressure: ["项目深挖题", "AI专项题", "产品基础题", "项目深挖题", "AI专项题", "产品基础题", "项目深挖题", "AI专项题"],
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
};

const el = {
  startInterviewBtn: document.getElementById("startInterviewBtn"),
  modeCards: Array.from(document.querySelectorAll(".mode-card")),
  mockEmpty: document.getElementById("mockEmpty"),
  mockChatList: document.getElementById("mockChatList"),
  answerInput: document.getElementById("answerInput"),
  submitAnswerBtn: document.getElementById("submitAnswerBtn"),
  nextQuestionBtn: document.getElementById("nextQuestionBtn"),
  endInterviewBtn: document.getElementById("endInterviewBtn"),
  mockStatusText: document.getElementById("mockStatusText"),
  currentCategory: document.getElementById("currentCategory"),
  currentFocusPoints: document.getElementById("currentFocusPoints"),
  currentFramework: document.getElementById("currentFramework"),
  currentProgress: document.getElementById("currentProgress"),
  currentModeDesc: document.getElementById("currentModeDesc"),
  engineBadge: document.getElementById("engineBadge"),
};

function escapeHtml(input) {
  return String(input || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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

function setMode(modeKey) {
  state.mode = MODES[modeKey] ? modeKey : "quick";
  state.totalQuestions = MODES[state.mode].total_questions;
  el.modeCards.forEach((card) => card.classList.toggle("active-mode", card.dataset.mode === state.mode));
  el.currentModeDesc.textContent = MODES[state.mode].description;
  if (!state.started) {
    el.currentProgress.textContent = `共 ${state.totalQuestions} 题`;
  }
}

function renderMessages() {
  if (!state.messages.length) {
    el.mockEmpty.classList.remove("hidden");
    el.mockChatList.classList.add("hidden");
    el.mockChatList.innerHTML = "";
    return;
  }

  el.mockEmpty.classList.add("hidden");
  el.mockChatList.classList.remove("hidden");
  el.mockChatList.innerHTML = state.messages
    .map((message) => {
      if (message.type === "feedback") {
        const tips = (message.payload.improvement_tips || []).map((tip) => `<li>${escapeHtml(tip)}</li>`).join("");
        const followUp = message.payload.follow_up_question
          ? `<p class="feedback-followup"><strong>追问：</strong>${escapeHtml(message.payload.follow_up_question)}</p>`
          : "";
        return `
          <article class="mock-message feedback-message">
            <div class="message-badge">面试反馈</div>
            <div class="feedback-grid">
              <span>相关性：${escapeHtml(message.payload.evaluation.relevance || "一般")}</span>
              <span>结构性：${escapeHtml(message.payload.evaluation.structure || "一般")}</span>
              <span>深度：${escapeHtml(message.payload.evaluation.depth || "一般")}</span>
            </div>
            <p>${escapeHtml(message.payload.feedback || "")}</p>
            <ul class="feedback-tips">${tips}</ul>
            ${followUp}
          </article>
        `;
      }

      const roleLabel = message.type === "interviewer" ? "面试官提问" : message.type === "system" ? "训练状态" : "你的回答";
      return `
        <article class="mock-message ${escapeHtml(message.type)}-message">
          <div class="message-badge">${escapeHtml(roleLabel)}</div>
          <p>${escapeHtml(message.text || "")}</p>
        </article>
      `;
    })
    .join("");

  el.mockChatList.scrollTop = el.mockChatList.scrollHeight;
}

function updateSidebar(question) {
  const activeQuestion = question || state.currentQuestion;
  el.currentCategory.textContent = activeQuestion?.category || "-";
  renderChipList(el.currentFocusPoints, activeQuestion?.focus_points || [], "等待题目");
  el.currentFramework.textContent = activeQuestion?.answer_framework || "-";
  el.currentProgress.textContent = state.started
    ? `第 ${state.currentIndex} 题 / 共 ${state.totalQuestions} 题`
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
  el.submitAnswerBtn.disabled = !canSubmit;
  el.nextQuestionBtn.disabled = !canNext;
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

function buildLocalQuestion(modeKey, index, askedIds) {
  const targetCategory = getCategoryForIndex(modeKey, index);
  const categories = [targetCategory, "产品基础题", "AI专项题", "项目深挖题"];
  for (const category of categories) {
    const list = LOCAL_QUESTION_BANK[category] || [];
    const candidate = list.find((item) => !askedIds.includes(item.question_id));
    if (candidate) return candidate;
  }
  return LOCAL_QUESTION_BANK[targetCategory][0];
}

function buildLocalFeedback(question, answer, modeKey) {
  const text = String(answer || "").trim();
  const length = text.length;
  const lower = text.toLowerCase();
  const structureHits = ["首先", "其次", "最后", "第一", "第二", "第三", "first", "second", "finally"].filter((keyword) => text.includes(keyword) || lower.includes(keyword)).length;
  const depthHits = ["指标", "实验", "评测", "取舍", "prompt", "rag", "agent", "召回", "排序"].filter((keyword) => text.includes(keyword) || lower.includes(keyword)).length;
  const relevance = length >= 90 ? "较强" : length >= 45 ? "一般" : "较弱";
  const structure = structureHits >= 2 ? "较强" : structureHits >= 1 ? "一般" : "较弱";
  const depth = depthHits >= 3 ? "较强" : depthHits >= 1 ? "一般" : "较弱";
  const tips = [];
  if (relevance === "较弱") tips.push("先明确题目在问什么，再回答目标、对象和判断逻辑。 ");
  if (structure !== "较强") tips.push("建议采用结论先行，再按 2 到 3 点展开的结构。 ");
  if (depth !== "较强") tips.push("适当补充指标、实验方案或系统链路，会更像 AI PM 面试回答。 ");
  if (question.category === "项目深挖题") tips.push("项目题要讲清背景、问题、方案、结果，不要只介绍功能。 ");
  const followUp = MODES[modeKey].pressure_mode
    ? question.category === "AI专项题"
      ? "如果线上效果没有提升，你会先排查模型、提示词还是产品交互？为什么？"
      : question.category === "项目深挖题"
        ? "如果要你删掉一个模块，你会先删哪一个？为什么？"
        : "如果资源减半，你的方案会怎么调整？"
    : "";
  return {
    question: question.question,
    category: question.category,
    evaluation: { relevance, structure, depth },
    feedback: relevance === "较强" && structure === "较强"
      ? "你的回答已经有比较完整的结构，下一步要继续加强分析深度和取舍逻辑。"
      : "你的回答方向基本正确，但还可以进一步压缩表达、补充逻辑和数据视角。",
    improvement_tips: tips.slice(0, 3).map((tip) => tip.trim()),
    follow_up_question: followUp,
  };
}

async function startInterview() {
  resetSession();
  setStatus("正在生成第一道题...");
  try {
    const result = await postJSON("/api/mock-interview/start", { mode: state.mode });
    const question = result?.data?.question;
    if (!question) throw new Error("empty question");
    state.started = true;
    state.currentQuestion = question;
    state.currentIndex = 1;
    state.totalQuestions = result?.data?.session?.total_questions || MODES[state.mode].total_questions;
    state.askedQuestionIds = [question.question_id];
    state.answeredCurrent = false;
    addMessage("interviewer", question.question);
    updateSidebar(question);
    setEngineBadge(result?.meta?.source || "fallback");
    setStatus("第一题已生成，开始作答。 ");
    updateControls();
  } catch (_) {
    const question = buildLocalQuestion(state.mode, 0, []);
    state.started = true;
    state.currentQuestion = question;
    state.currentIndex = 1;
    state.totalQuestions = MODES[state.mode].total_questions;
    state.askedQuestionIds = [question.question_id];
    state.answeredCurrent = false;
    addMessage("interviewer", question.question);
    updateSidebar(question);
    setEngineBadge("fallback");
    setStatus("接口暂不可用，已切换到本地练习模式。 ");
    updateControls();
  }
}

async function submitAnswer() {
  const answer = el.answerInput.value.trim();
  if (!answer || !state.currentQuestion || state.answeredCurrent) return;

  addMessage("user", answer);
  el.answerInput.value = "";
  setStatus("正在生成反馈...");
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
    });
    const feedback = result?.data;
    if (!feedback) throw new Error("empty feedback");
    addMessage("feedback", "", feedback);
    state.answeredCurrent = true;
    setEngineBadge(result?.meta?.source || state.lastEngineSource);
    setStatus("已生成反馈，可以进入下一题。 ");
    updateControls();
  } catch (_) {
    const feedback = buildLocalFeedback(state.currentQuestion, answer, state.mode);
    addMessage("feedback", "", feedback);
    state.answeredCurrent = true;
    setEngineBadge("fallback");
    setStatus("接口暂不可用，已使用本地反馈兜底。 ");
    updateControls();
  }
}

async function nextQuestion() {
  if (!state.started || !state.answeredCurrent) return;
  if (state.currentIndex >= state.totalQuestions) {
    finishInterview();
    return;
  }

  setStatus("正在准备下一题...");
  try {
    const result = await postJSON("/api/mock-interview/next", {
      mode: state.mode,
      question_index: state.currentIndex,
      asked_questions: state.askedQuestionIds,
      history: state.messages,
    });
    if (result?.data?.finished) {
      finishInterview();
      return;
    }
    const question = result?.data?.question;
    if (!question) throw new Error("empty next question");
    state.currentQuestion = question;
    state.currentIndex += 1;
    state.askedQuestionIds.push(question.question_id);
    state.answeredCurrent = false;
    addMessage("interviewer", question.question);
    updateSidebar(question);
    setEngineBadge(result?.meta?.source || state.lastEngineSource);
    setStatus("下一题已生成。 ");
    updateControls();
  } catch (_) {
    const question = buildLocalQuestion(state.mode, state.currentIndex, state.askedQuestionIds);
    state.currentQuestion = question;
    state.currentIndex += 1;
    state.askedQuestionIds.push(question.question_id);
    state.answeredCurrent = false;
    addMessage("interviewer", question.question);
    updateSidebar(question);
    setEngineBadge("fallback");
    setStatus("接口暂不可用，已切换到本地题库继续训练。 ");
    updateControls();
  }
}

function finishInterview() {
  state.finished = true;
  state.answeredCurrent = false;
  state.currentQuestion = null;
  addMessage("system", `本轮结束。你已完成 ${state.currentIndex} / ${state.totalQuestions} 题训练。`);
  setStatus("本轮模拟已结束，可以重新开始下一轮。 ");
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
  el.nextQuestionBtn.addEventListener("click", () => {
    nextQuestion().catch(() => {});
  });
  el.endInterviewBtn.addEventListener("click", () => {
    resetSession();
  });
}

function bootstrap() {
  setMode("quick");
  updateSidebar(null);
  updateControls();
  renderMessages();
  bindEvents();
}

bootstrap();
