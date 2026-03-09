const query = new URLSearchParams(window.location.search);
const id = query.get("id");

const el = {
  loading: document.getElementById("loading"),
  content: document.getElementById("content"),
  title: document.getElementById("title"),
  meta: document.getElementById("meta"),
  applyLink: document.getElementById("applyLink"),
  jd: document.getElementById("jd"),
  focus: document.getElementById("focus"),
  plan: document.getElementById("plan"),
  questions: document.getElementById("questions"),
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
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function render(detail) {
  el.title.textContent = detail.title;
  el.meta.textContent = `${detail.company} · ${detail.city} · 开放日期 ${detail.open_date || "-"}`;
  el.applyLink.href = detail.apply_url;
  el.jd.textContent = detail.jd_text || "暂无JD内容";

  el.focus.innerHTML = detail.prep_plan.focus_areas.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
  el.plan.innerHTML = detail.prep_plan.plan.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
  el.questions.innerHTML = detail.prep_plan.mock_questions
    .map((x) => `<li>${escapeHtml(x)}</li>`)
    .join("");

  el.loading.classList.add("hidden");
  el.content.classList.remove("hidden");
}

async function bootstrap() {
  if (!id || !/^\d+$/.test(id)) {
    el.loading.textContent = "参数错误：缺少岗位ID";
    return;
  }

  try {
    const detail = await fetchJSON(`/api/jobs/${id}`);
    render(detail);
  } catch (err) {
    el.loading.textContent = `加载失败：${err.message}`;
  }
}

bootstrap();
