const PROFILE_STORAGE_KEY = "ai_pm_radar_profile_text";
const PROFILE_DATA_KEY = "ai_pm_radar_profile_data";

const state = {
  jobs: [],
  activeJobId: null,
  activePane: "jd",
  activeDetail: null,
  userProfileText: "",
  userProfile: null,
};

const ALL_COMPANIES = ["腾讯", "京东", "美团", "阿里巴巴", "百度", "快手", "小红书", "拼多多", "携程", "网易", "小米", "字节跳动"];

const el = {
  keyword: document.getElementById("keyword"),
  company: document.getElementById("company"),
  city: document.getElementById("city"),
  searchBtn: document.getElementById("searchBtn"),
  refreshBtn: document.getElementById("refreshBtn"),
  profileInput: document.getElementById("profileInput"),
  profileFileInput: document.getElementById("profileFileInput"),
  applyProfileBtn: document.getElementById("applyProfileBtn"),
  resetProfileBtn: document.getElementById("resetProfileBtn"),
  profileStatusText: document.getElementById("profileStatusText"),
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
  detailMockInterview: document.getElementById("detailMockInterview"),
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
  gapLevel: document.getElementById("gapLevel"),
  gapPrimaryDomain: document.getElementById("gapPrimaryDomain"),
  gapSecondaryDomain: document.getElementById("gapSecondaryDomain"),
  gapDomainReasoning: document.getElementById("gapDomainReasoning"),
  gapRecommendation: document.getElementById("gapRecommendation"),
  gapRecommendationReason: document.getElementById("gapRecommendationReason"),
  gapDomainScore: document.getElementById("gapDomainScore"),
  gapGeneralScore: document.getElementById("gapGeneralScore"),
  gapEvidenceScore: document.getElementById("gapEvidenceScore"),
  gapDomainScoreHint: document.getElementById("gapDomainScoreHint"),
  gapGeneralScoreHint: document.getElementById("gapGeneralScoreHint"),
  gapEvidenceScoreHint: document.getElementById("gapEvidenceScoreHint"),
  gapDomainGap: document.getElementById("gapDomainGap"),
  gapGeneralGap: document.getElementById("gapGeneralGap"),
  gapPriorityGap: document.getElementById("gapPriorityGap"),
  gapSummary: document.getElementById("gapSummary"),
  gapRealisticAdvice: document.getElementById("gapRealisticAdvice"),
  gapMatched: document.getElementById("gapMatched"),
  gapPotential: document.getElementById("gapPotential"),
  gapJdSignals: document.getElementById("gapJdSignals"),
  gapResumeSignals: document.getElementById("gapResumeSignals"),
  gapMatchedEvidence: document.getElementById("gapMatchedEvidence"),
  gapMissingEvidence: document.getElementById("gapMissingEvidence"),
  gapWeakEvidence: document.getElementById("gapWeakEvidence"),
  gapRiskText: document.getElementById("gapRiskText"),
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

function renderBulletList(target, items, emptyText = "暂无") {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    target.innerHTML = `<li>${escapeHtml(emptyText)}</li>`;
    return;
  }
  target.innerHTML = values.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderTechRequirements(items) {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {
    el.analysisTech.innerHTML = '<div class="tech-item"><span class="tech-topic">暂无明确技术方向要求</span></div>';
    return;
  }
  el.analysisTech.innerHTML = values.map((item) => {
    const evidence = Array.isArray(item.evidence) && item.evidence.length ? `<span class="tech-evidence">${escapeHtml(item.evidence.join(" / "))}</span>` : "";
    return `<div class="tech-item"><div><div class="tech-topic">${escapeHtml(item.topic || "未命名方向")}</div>${evidence}</div><span class="tech-depth">${escapeHtml(item.depth || "待定")}</span></div>`;
  }).join("");
}

function buildProfileSummary(profile) {
  if (!profile) return "默认 AI PM 实习画像";
  const sourceMap = { default: "默认画像", resume_text: "文本画像", resume_pdf: "PDF简历画像" };
  const source = sourceMap[profile.source] || "个人画像";
  if (profile.summary) return `${source} · ${profile.summary}`;
  const domains = Array.isArray(profile.strong_domains) ? profile.strong_domains.slice(0, 2).join(" / ") : "";
  return `${source} · ${domains || profile.target_role || "AI产品经理实习"}`;
}

function groupInterviewQuestions(items) {
  const groups = { "通用产品题": [], "AI产品专项题": [], "岗位定向题": [] };
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
  const sections = order.map((category) => {
    const questions = groups[category] || [];
    if (!questions.length) return "";
    const cards = questions.map((item) => {
      const points = (item.suggested_points || []).map((point) => `<li>${escapeHtml(point)}</li>`).join("");
      return `<article class="question-card"><div class="question-card-head"><span class="question-category">${escapeHtml(item.category || category)}</span></div><h5>${escapeHtml(item.question || "未命名问题")}</h5><p class="question-why">${escapeHtml(item.why_this_may_be_asked || "该题与岗位要求直接相关。")}</p><ul class="question-points">${points}</ul></article>`;
    }).join("");
    return `<section class="question-group"><h5 class="question-group-title">${escapeHtml(category)}</h5><div class="question-group-list">${cards}</div></section>`;
  }).filter(Boolean);
  el.interviewPrepGroups.innerHTML = sections.length ? sections.join("") : '<div class="placeholder">暂未生成面试题</div>';
}

function difficultyClassName(value) {
  if (value === "较高") return "difficulty-high";
  if (value === "中等") return "difficulty-medium";
  return "difficulty-low";
}

function layerHint(score) {
  if (score >= 80) return "强";
  if (score >= 60) return "中";
  if (score >= 40) return "偏弱";
  return "弱";
}

function renderJobCard(job) {
  const sourceTag = `<span class="tag">${escapeHtml(job.source_type)}</span>`;
  const dateTag = `<span class="tag">开放: ${escapeHtml(job.open_date || "-")}</span>`;
  const typeTag = `<span class="tag">${escapeHtml(job.internship_label || "实习")}</span>`;
  let linkTag = '<span class="tag">官网入口</span>';
  if (job.link_quality === "direct") linkTag = '<span class="tag new">直达投递</span>';
  if (job.link_quality === "search") linkTag = '<span class="tag">岗位搜索</span>';
  const activeClass = state.activeJobId === job.id ? "active-card" : "";
  return `<article class="job-card ${activeClass}" data-id="${job.id}"><h3>${escapeHtml(job.display_title || job.title)}</h3><div class="meta">${escapeHtml(job.company)} · ${escapeHtml(job.city || "待确认")}</div><div class="meta">首次发现：${escapeHtml(job.first_seen || "-")}</div><div class="tag-row">${typeTag}${linkTag}${sourceTag}${dateTag}</div></article>`;
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
  el.jobList.innerHTML = items.length ? items.map(renderJobCard).join("") : '<div class="placeholder">当前没有匹配岗位</div>';
  bindJobClicks();
}

function renderGapSection(detail) {
  const gap = detail.gap_analysis || {};
  const profile = detail.user_profile || {};
  const evidence = gap.evidence || {};
  const jobDomain = gap.job_domain_analysis || {};
  const score = gap.score_breakdown || {};
  const evidenceCompare = gap.evidence_compare || {};
  const totalScore = Number(gap.match_score || score.total_score || 0);
  const recommend = totalScore >= 60 && !gap.not_recommended_reason;

  el.gapProfileText.textContent = buildProfileSummary(profile);
  el.gapScore.textContent = `${totalScore}`;
  el.gapLevel.textContent = score.level || "不建议投递";
  el.gapPrimaryDomain.textContent = jobDomain.primary_domain || "通用AI产品";
  el.gapSecondaryDomain.textContent = jobDomain.secondary_domain || "无明显副场景";
  el.gapDomainReasoning.textContent = jobDomain.reasoning || "暂无场景判断说明";
  el.gapRecommendation.textContent = recommend ? "可投递" : "不建议优先投递";
  el.gapRecommendation.className = `chip ${recommend ? "recommend-chip" : "reject-chip"}`;
  el.gapRecommendationReason.textContent = gap.not_recommended_reason || "当前可作为可迁移岗位投递，但仍需补强关键场景证据。";
  el.gapDomainScore.textContent = `${Number(score.domain_score || 0)}`;
  el.gapGeneralScore.textContent = `${Number(score.general_score || 0)}`;
  el.gapEvidenceScore.textContent = `${Number(score.evidence_score || 0)}`;
  el.gapDomainScoreHint.textContent = layerHint(Number(score.domain_score || 0));
  el.gapGeneralScoreHint.textContent = layerHint(Number(score.general_score || 0));
  el.gapEvidenceScoreHint.textContent = layerHint(Number(score.evidence_score || 0));

  renderChipList(el.gapDomainGap, gap.domain_gap || [], "暂无明显场景差距");
  renderChipList(el.gapGeneralGap, gap.general_gap || [], "暂无明显通用能力缺口");
  renderChipList(el.gapPriorityGap, gap.priority_gap || gap.priority_to_improve || [], "暂无优先补齐项");
  renderBulletList(el.gapRealisticAdvice, gap.realistic_advice || [], "暂无现实建议");
  el.gapSummary.textContent = gap.summary || gap.advice || "暂无总结";

  renderChipList(el.gapMatched, gap.matched_skills || [], "暂无明确已匹配能力");
  renderChipList(el.gapPotential, gap.potential_strengths || [], "暂未识别出可放大的优势");
  renderChipList(el.gapJdSignals, evidence.jd_signals || [], "暂无JD信号");
  renderChipList(el.gapResumeSignals, evidence.resume_signals || [], "暂无简历命中信号");
  renderChipList(el.gapMatchedEvidence, evidenceCompare.matched_evidence || [], "暂无已命中证据");
  renderChipList(el.gapMissingEvidence, evidenceCompare.missing_evidence || [], "暂无关键缺失证据");
  renderChipList(el.gapWeakEvidence, evidenceCompare.weak_evidence || [], "暂无明显弱证据");
  el.gapRiskText.textContent = evidenceCompare.hallucination_risk
    ? "当前存在较高幻觉风险：通用能力看起来匹配，但缺少足够的项目或业务证据支撑高分。"
    : `当前判断置信度 ${Number(score.confidence || 0)}。`;
}

function renderDetail(detail) {
  state.activeDetail = detail;
  el.detailEmpty.classList.add("hidden");
  el.detailContent.classList.remove("hidden");
  el.detailTitle.textContent = detail.display_title || detail.title;
  let linkLabel = "官网入口链接";
  if (detail.link_quality === "direct") linkLabel = "直达投递链接";
  if (detail.link_quality === "search") linkLabel = "岗位搜索链接";
  el.detailMeta.textContent = `${detail.company} · ${detail.city} · ${detail.internship_label || "实习"} · 开放日期 ${detail.open_date || "-"} · ${linkLabel}`;
  el.detailApply.href = detail.apply_url;
  el.detailMockInterview.href = `/mock-interview?job_id=${encodeURIComponent(detail.id)}`;

  const analysis = detail.jd_analysis || {};
  el.analysisDifficulty.textContent = analysis.difficulty || "待解析";
  el.analysisDifficulty.className = `difficulty-badge ${difficultyClassName(analysis.difficulty || "")}`;
  renderChipList(el.analysisKeywords, analysis.keywords || [], "暂无关键词");
  renderChipList(el.analysisSkills, analysis.skill_tags || [], "暂无技能标签");
  renderChipList(el.analysisScenarios, analysis.scenario_tags || [], "暂无场景标签");
  renderTechRequirements(analysis.technical_requirements || []);
  el.analysisSummary.textContent = analysis.summary || "暂无结构化总结";

  renderGapSection(detail);
  el.detailJD.textContent = detail.jd_text || "暂无完整JD内容";
  renderInterviewPrep((detail.interview_prep || {}).questions || []);
}

function renderCompanyOptions(items) {
  const current = el.company.value;
  const merged = Array.from(new Set([...(items || []), ...ALL_COMPANIES]));
  const options = ['<option value="">全部</option>'].concat(merged.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`));
  el.company.innerHTML = options.join("");
  if (merged.includes(current)) el.company.value = current;
}

function saveProfileState() {
  localStorage.setItem(PROFILE_STORAGE_KEY, state.userProfileText || "");
  if (state.userProfile) localStorage.setItem(PROFILE_DATA_KEY, JSON.stringify(state.userProfile));
  else localStorage.removeItem(PROFILE_DATA_KEY);
}

function hydrateProfileState() {
  state.userProfileText = localStorage.getItem(PROFILE_STORAGE_KEY) || "";
  el.profileInput.value = state.userProfileText;
  try {
    state.userProfile = JSON.parse(localStorage.getItem(PROFILE_DATA_KEY) || "null");
  } catch (_) {
    state.userProfile = null;
  }
  updateProfileStatus();
}

function clearProfileState() {
  state.userProfileText = "";
  state.userProfile = null;
  el.profileInput.value = "";
  if (el.profileFileInput) el.profileFileInput.value = "";
  saveProfileState();
  updateProfileStatus();
}

function updateProfileStatus(message) {
  if (message) {
    el.profileStatusText.textContent = message;
    return;
  }
  if (state.userProfile && state.userProfile.source !== "default") {
    const summary = state.userProfile.summary || buildProfileSummary(state.userProfile);
    el.profileStatusText.textContent = `当前使用个人画像：${summary}`;
    return;
  }
  el.profileStatusText.textContent = "当前使用默认画像。";
}

async function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("file_read_failed"));
    reader.readAsDataURL(file);
  });
}

async function applyProfileToDetail(detail) {
  if (!detail || !state.userProfile || state.userProfile.source === "default") return;
  try {
    const result = await fetchJSON("/api/gap-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: detail.company,
        title: detail.title,
        jd_text: detail.jd_text,
        jd_analysis: detail.jd_analysis,
        user_profile: state.userProfile,
      }),
    });
    detail.user_profile = state.userProfile;
    detail.gap_analysis = result.data || detail.gap_analysis;
    detail.gap_analysis_meta = result.meta || detail.gap_analysis_meta;
    if (state.activeDetail && state.activeDetail.id === detail.id) renderGapSection(detail);
  } catch (_) {
    // keep default gap analysis
  }
}

async function applyUserProfile() {
  const profileText = el.profileInput.value.trim();
  const selectedFile = el.profileFileInput && el.profileFileInput.files ? el.profileFileInput.files[0] : null;
  if (!profileText && !selectedFile) {
    clearProfileState();
    if (state.activeJobId) await loadJobDetail(state.activeJobId, state.activePane);
    return;
  }

  updateProfileStatus(selectedFile ? "正在解析你的 PDF 简历..." : "正在解析你的个人画像...");
  try {
    const payload = {};
    if (selectedFile) {
      payload.file_name = selectedFile.name;
      payload.file_data_base64 = await readFileAsDataUrl(selectedFile);
      payload.profile_text = profileText;
    } else {
      payload.profile_text = profileText;
    }
    const result = await fetchJSON("/api/profile-parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.userProfileText = profileText;
    state.userProfile = result.data || null;
    saveProfileState();
    updateProfileStatus();
    if (state.activeDetail) await applyProfileToDetail(state.activeDetail);
  } catch (_) {
    updateProfileStatus("画像解析失败，仍然使用默认画像。请稍后重试。");
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
  state.activeDetail = null;
  el.detailContent.classList.add("hidden");
  el.detailEmpty.classList.remove("hidden");
}

async function loadJobDetail(jobId, pane = "jd") {
  const detail = await fetchJSON(`/api/jobs/${jobId}`);
  renderDetail(detail);
  await applyProfileToDetail(detail);
  setPane(pane);
}

async function loadStatus() {
  const data = await fetchJSON("/api/status");
  el.statusText.textContent = data.is_running ? "抓取中..." : "空闲";
  el.lastRunText.textContent = `最近执行：${data.last_run || "-"}`;
  el.nextRunText.textContent = `下次自动抓取：${data.next_run || "-"}`;
}

function bindEvents() {
  el.searchBtn.addEventListener("click", () => loadJobs().catch(() => {}));
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
  el.applyProfileBtn.addEventListener("click", () => applyUserProfile().catch(() => {}));
  el.resetProfileBtn.addEventListener("click", () => {
    clearProfileState();
    if (state.activeJobId) loadJobDetail(state.activeJobId, state.activePane).catch(() => {});
  });
  el.showJD.addEventListener("click", () => setPane("jd"));
  el.showGap.addEventListener("click", () => { if (state.activeJobId) setPane("gap"); });
  el.showPrep.addEventListener("click", () => { if (state.activeJobId) setPane("prep"); });
}

async function bootstrap() {
  hydrateProfileState();
  bindEvents();
  await loadStatus();
  await loadCompanies();
  await loadJobs();
  setInterval(() => loadStatus().catch(() => {}), 20000);
}

bootstrap().catch(() => {});
