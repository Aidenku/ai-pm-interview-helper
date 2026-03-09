const state = {
  jobs: [],
  activeJobId: null,
  activePane: "jd",
};

const ALL_COMPANIES = [
  "腾讯",
  "京东",
  "美团",
  "阿里巴巴",
  "百度",
  "快手",
  "小红书",
  "拼多多",
  "携程",
  "网易",
  "小米",
  "字节跳动",
];

const el = {
  keyword: document.getElementById("keyword"),
  company: document.getElementById("company"),
  city: document.getElementById("city"),
  searchBtn: document.getElementById("searchBtn"),
  refreshBtn: document.getElementById("refreshBtn"),
  jobList: document.getElementById("jobList"),
  jobCount: document.getElementById("jobCount"),
  statusText: document.getElementById("statusText"),
  lastRunText: document.getElementById("lastRunText"),
  nextRunText: document.getElementById("nextRunText"),
  detailEmpty: document.getElementById("detailEmpty"),
  detailContent: document.getElementById("detailContent"),
  detailTitle: document.getElementById("detailTitle"),
  detailMeta: document.getElementById("detailMeta"),
  detailApply: document.getElementById("detailApply"),
  showJD: document.getElementById("showJD"),
  showGap: document.getElementById("showGap"),
  showPrep: document.getElementById("showPrep"),
  jdPane: document.getElementById("jdPane"),
  gapPane: document.getElementById("gapPane"),
  prepPane: document.getElementById("prepPane"),
  detailJD: document.getElementById("detailJD"),
  analysisDifficulty: document.getElementById("analysisDifficulty"),
  analysisKeywords: document.getElementById("analysisKeywords"),
  analysisSkills: document.getElementById("analysisSkills"),
  analysisTech: document.getElementById("analysisTech"),
  analysisScenarios: document.getElementById("analysisScenarios"),
  analysisSummary: document.getElementById("analysisSummary"),
  gapProfileText: document.getElementById("gapProfileText"),
  gapScore: document.getElementById("gapScore"),
  gapMatched: document.getElementById("gapMatched"),
  gapMissing: document.getElementById("gapMissing"),
  gapPriority: document.getElementById("gapPriority"),
  gapAdvice: document.getElementById("gapAdvice"),
  interviewPrepGroups: document.getElementById("interviewPrepGroups"),
};

function escapeHtml(input) {
  return String(input || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function setPane(name) {
  state.activePane = name;
  const jdActive = name === "jd";
  const gapActive = name === "gap";
  const prepActive = name === "prep";
  el.jdPane.classList.toggle("hidden", !jdActive);
  el.gapPane.classList.toggle("hidden", !gapActive);
  el.prepPane.classList.toggle("hidden", !prepActive);
  el.showJD.classList.toggle("active-btn", jdActive);
  el.showGap.classList.toggle("active-btn", gapActive);
  el.showPrep.classList.toggle("active-btn", prepActive);
}

function renderChipList(target, items, emptyText = "暂无") {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    target.innerHTML = `<span class="chip muted-chip">${escapeHtml(emptyText)}</span>`;
    return;
  }
  target.innerHTML = values.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
}

function renderTechRequirements(items) {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    el.analysisTech.innerHTML = '<div class="tech-item"><span class="tech-topic">暂无明确技术方向要求</span></div>';
    return;
  }

  el.analysisTech.innerHTML = values
    .map((item) => {
      const evidence = Array.isArray(item.evidence) && item.evidence.length
        ? `<span class="tech-evidence">${escapeHtml(item.evidence.join(" / "))}</span>`
        : "";
      return `
        <div class="tech-item">
          <div>
            <div class="tech-topic">${escapeHtml(item.topic || "未命名方向")}</div>
            ${evidence}
          </div>
          <span class="tech-depth">${escapeHtml(item.depth || "待定")}</span>
        </div>
      `;
    })
    .join("");
}

function buildProfileSummary(profile) {
  if (!profile) return "默认 AI PM 实习画像";
  const strengths = Array.isArray(profile.strengths) ? profile.strengths.slice(0, 2).join(" / ") : "";
  return `${profile.target_role || "AI产品经理实习"} · 已有 ${strengths || "基础产品能力"}`;
}

function groupInterviewQuestions(items) {
  const groups = {
    "通用产品题": [],
    "AI产品专项题": [],
    "岗位定向题": [],
  };
  (items || []).forEach((item) => {
    const category = item.category || "岗位定向题";
    if (!groups[category]) groups[category] = [];
    groups[category].push(item);
  });
  return groups;
}

function renderInterviewPrep(items) {
  const groups = groupInterviewQuestions(items);
  const order = ["通用产品题", "AI产品专项题", "岗位定向题"];
  const sections = order
    .map((category) => {
      const questions = groups[category] || [];
      if (!questions.length) return "";
      const cards = questions
        .map((item) => {
          const points = (item.suggested_points || [])
            .map((point) => `<li>${escapeHtml(point)}</li>`)
            .join("");
          return `
            <article class="question-card">
              <div class="question-card-head">
                <span class="question-category">${escapeHtml(item.category || category)}</span>
              </div>
              <h5>${escapeHtml(item.question || "未命名问题")}</h5>
              <p class="question-why">${escapeHtml(item.why_this_may_be_asked || "该题与岗位要求直接相关。")}</p>
              <ul class="question-points">${points}</ul>
            </article>
          `;
        })
        .join("");
      return `
        <section class="question-group">
          <h5 class="question-group-title">${escapeHtml(category)}</h5>
          <div class="question-group-list">${cards}</div>
        </section>
      `;
    })
    .filter(Boolean);

  el.interviewPrepGroups.innerHTML = sections.length
    ? sections.join("")
    : '<div class="placeholder">暂未生成面试题</div>';
}

function difficultyClassName(value) {
  if (value === "较高") return "difficulty-high";
  if (value === "中等") return "difficulty-medium";
  return "difficulty-low";
}

function renderJobCard(job) {
  const sourceTag = `<span class="tag">${escapeHtml(job.source_type)}</span>`;
  const dateTag = `<span class="tag">开放: ${escapeHtml(job.open_date || "-")}</span>`;
  const typeTag = `<span class="tag">${escapeHtml(job.internship_label || "实习")}</span>`;
  let linkTag = '<span class="tag">官网入口</span>';
  if (job.link_quality === "direct") linkTag = '<span class="tag new">直达投递</span>';
  if (job.link_quality === "search") linkTag = '<span class="tag">岗位搜索</span>';
  const activeClass = state.activeJobId === job.id ? "active-card" : "";

  return `
    <article class="job-card ${activeClass}" data-id="${job.id}">
      <h3>${escapeHtml(job.display_title || job.title)}</h3>
      <div class="meta">${escapeHtml(job.company)} · ${escapeHtml(job.city || "待确认")}</div>
      <div class="meta">首次发现：${escapeHtml(job.first_seen || "-")}</div>
      <div class="tag-row">${typeTag}${linkTag}${sourceTag}${dateTag}</div>
    </article>
  `;
}

function bindJobClicks() {
  el.jobList.querySelectorAll(".job-card").forEach((card) => {
    card.addEventListener("click", () => {
      const id = Number(card.dataset.id);
      state.activeJobId = id;
      renderJobs(state.jobs);
      loadJobDetail(id, "jd").catch(() => {});
    });
  });
}

function renderJobs(items) {
  state.jobs = items;
  el.jobCount.textContent = `${items.length} 条`;
  el.jobList.innerHTML = items.length
    ? items.map(renderJobCard).join("")
    : '<div class="placeholder">当前没有匹配岗位</div>';
  bindJobClicks();
}

function renderDetail(detail) {
  el.detailEmpty.classList.add("hidden");
  el.detailContent.classList.remove("hidden");

  el.detailTitle.textContent = detail.display_title || detail.title;
  let linkLabel = "官网入口链接";
  if (detail.link_quality === "direct") linkLabel = "直达投递链接";
  if (detail.link_quality === "search") linkLabel = "岗位搜索链接";
  el.detailMeta.textContent = `${detail.company} · ${detail.city} · ${detail.internship_label || "实习"} · 开放日期 ${detail.open_date || "-"} · ${linkLabel}`;
  el.detailApply.href = detail.apply_url;

  const analysis = detail.jd_analysis || {};
  el.analysisDifficulty.textContent = analysis.difficulty || "待解析";
  el.analysisDifficulty.className = `difficulty-badge ${difficultyClassName(analysis.difficulty || "")}`;
  renderChipList(el.analysisKeywords, analysis.keywords || [], "暂无关键词");
  renderChipList(el.analysisSkills, analysis.skill_tags || [], "暂无技能标签");
  renderChipList(el.analysisScenarios, analysis.scenario_tags || [], "暂无场景标签");
  renderTechRequirements(analysis.technical_requirements || []);
  el.analysisSummary.textContent = analysis.summary || "暂无结构化总结";

  const gap = detail.gap_analysis || {};
  el.gapProfileText.textContent = buildProfileSummary(detail.user_profile || {});
  el.gapScore.textContent = `${Number(gap.match_score || 0)}`;
  renderChipList(el.gapMatched, gap.matched_skills || [], "暂无明确已匹配能力");
  renderChipList(el.gapMissing, gap.missing_skills || [], "暂无明显能力缺口");
  renderChipList(el.gapPriority, gap.priority_to_improve || [], "暂无优先补齐项");
  el.gapAdvice.textContent = gap.advice || "暂无建议";

  el.detailJD.textContent = detail.jd_text || "暂无完整JD内容";
  renderInterviewPrep((detail.interview_prep || {}).questions || []);
}

function renderCompanyOptions(items) {
  const current = el.company.value;
  const merged = Array.from(new Set([...(items || []), ...ALL_COMPANIES]));
  const options = ['<option value="">全部</option>']
    .concat(merged.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`));
  el.company.innerHTML = options.join("");
  if (merged.includes(current)) {
    el.company.value = current;
  }
}

async function loadCompanies() {
  const data = await fetchJSON("/api/companies");
  renderCompanyOptions(data.items || []);
}

async function loadJobs() {
  const params = new URLSearchParams({
    keyword: el.keyword.value.trim(),
    company: el.company.value.trim(),
    city: el.city.value.trim(),
  });
  const data = await fetchJSON(`/api/jobs?${params.toString()}`);
  renderJobs(data.items || []);

  if (data.items && data.items.length) {
    const exists = data.items.some((x) => x.id === state.activeJobId);
    if (!exists) state.activeJobId = data.items[0].id;
    renderJobs(data.items);
    await loadJobDetail(state.activeJobId, state.activePane);
    return;
  }

  state.activeJobId = null;
  el.detailContent.classList.add("hidden");
  el.detailEmpty.classList.remove("hidden");
}

async function loadJobDetail(jobId, pane = "jd") {
  const detail = await fetchJSON(`/api/jobs/${jobId}`);
  renderDetail(detail);
  setPane(pane);
}

async function loadStatus() {
  const data = await fetchJSON("/api/status");
  el.statusText.textContent = data.is_running ? "抓取中..." : "空闲";
  el.lastRunText.textContent = `最近执行：${data.last_run || "-"}`;
  el.nextRunText.textContent = `下次自动抓取：${data.next_run || "-"}`;
}

function bindEvents() {
  el.searchBtn.addEventListener("click", () => {
    loadJobs().catch(() => {});
  });

  el.refreshBtn.addEventListener("click", async () => {
    try {
      await fetchJSON("/api/refresh", { method: "POST" });
      setTimeout(() => {
        loadStatus().catch(() => {});
        loadCompanies().catch(() => {});
        loadJobs().catch(() => {});
      }, 1000);
    } catch (_) {
      // no-op
    }
  });

  el.showJD.addEventListener("click", () => setPane("jd"));
  el.showGap.addEventListener("click", () => {
    if (!state.activeJobId) return;
    setPane("gap");
  });
  el.showPrep.addEventListener("click", () => {
    if (!state.activeJobId) return;
    setPane("prep");
  });
}

async function bootstrap() {
  bindEvents();
  await loadStatus();
  await loadCompanies();
  await loadJobs();
  setInterval(() => loadStatus().catch(() => {}), 20000);
}

bootstrap().catch(() => {});
