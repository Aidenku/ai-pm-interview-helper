import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

import app as legacy_app

app = Flask(__name__, static_folder=None)

_BOOTSTRAPPED = False
_BOOTSTRAP_LOCK = threading.Lock()
_SCHEDULER_STARTED = False


def bootstrap() -> None:
    global _BOOTSTRAPPED, _SCHEDULER_STARTED
    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAPPED:
            return

        legacy_app.init_db()
        legacy_app.cleanup_legacy_rows()
        legacy_app.ensure_bootstrap_data()

        with legacy_app.STATE_LOCK:
            if legacy_app.STATE["last_run"] is None:
                legacy_app.STATE["last_run"] = legacy_app.now_str()
                legacy_app.STATE["next_run"] = (
                    datetime.now(legacy_app.TZ) + timedelta(seconds=legacy_app.REFRESH_INTERVAL_SECONDS)
                ).strftime("%Y-%m-%d %H:%M:%S")

        if not _SCHEDULER_STARTED:
            scheduler = threading.Thread(target=legacy_app.scheduler_loop, daemon=True)
            scheduler.start()
            _SCHEDULER_STARTED = True

        _BOOTSTRAPPED = True


def _json(payload, status=200):
    return jsonify(payload), status


def _serve_static(file_name: str, content_type: str | None = None):
    response = send_from_directory(str(legacy_app.STATIC_DIR), file_name)
    if content_type:
        response.headers["Content-Type"] = content_type
    response.headers["Cache-Control"] = "no-store"
    return response


def _get_json_body():
    payload = request.get_json(silent=True)
    if payload is None:
        return None, (jsonify({"error": "invalid json body"}), 400)
    return payload, None


@app.before_request
def _ensure_ready():
    bootstrap()


@app.get("/")
@app.get("/index.html")
def index():
    return _serve_static("index.html", "text/html; charset=utf-8")


@app.get("/job.html")
def job_page():
    return _serve_static("job.html", "text/html; charset=utf-8")


@app.get("/mock-interview")
def mock_interview_page():
    return _serve_static("mock-interview.html", "text/html; charset=utf-8")


@app.get("/styles.css")
def styles():
    return _serve_static("styles.css", "text/css; charset=utf-8")


@app.get("/app.js")
def app_js():
    return _serve_static("app.js", "application/javascript; charset=utf-8")


@app.get("/job.js")
def job_js():
    return _serve_static("job.js", "application/javascript; charset=utf-8")


@app.get("/mock-interview.js")
def mock_interview_js():
    return _serve_static("mock-interview.js", "application/javascript; charset=utf-8")


@app.get("/api/jobs")
def api_jobs():
    filters = {
        "keyword": (request.args.get("keyword") or "").strip(),
        "company": (request.args.get("company") or "").strip(),
        "city": (request.args.get("city") or "").strip(),
    }
    rows = legacy_app.list_jobs(filters)
    return _json({"items": rows, "count": len(rows)})


@app.get("/api/jobs/<job_id>")
def api_job_detail(job_id):
    if not str(job_id).isdigit():
        return _json({"error": "invalid id"}, 400)
    detail = legacy_app.get_job_detail(int(job_id))
    if not detail:
        return _json({"error": "not found"}, 404)
    return _json(detail)


@app.get("/api/status")
def api_status():
    with legacy_app.STATE_LOCK:
        state = {
            "is_running": legacy_app.STATE["is_running"],
            "last_run": legacy_app.STATE["last_run"],
            "last_error": legacy_app.STATE["last_error"],
            "next_run": legacy_app.STATE["next_run"],
            "event_id": legacy_app.STATE["event_id"],
        }
    return _json(state)


@app.get("/api/companies")
def api_companies():
    return _json({"items": legacy_app.list_companies()})


@app.get("/api/progress")
def api_progress():
    with legacy_app.STATE_LOCK:
        events = list(legacy_app.STATE["events"][-80:])
    return _json({"items": events})


@app.get("/api/progress/stream")
def api_progress_stream():
    def generate():
        last_id = 0
        while True:
            with legacy_app.STATE_LOCK:
                events = [e for e in legacy_app.STATE["events"] if e["id"] > last_id]
            for event in events:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                last_id = event["id"]
            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


@app.post("/api/refresh")
def api_refresh():
    with legacy_app.STATE_LOCK:
        is_running = legacy_app.STATE["is_running"]
    if is_running:
        return _json({"ok": False, "message": "refresh already running"}, 409)
    thread = threading.Thread(target=legacy_app.run_refresh, kwargs={"trigger": "manual"}, daemon=True)
    thread.start()
    return _json({"ok": True, "message": "refresh started"})


@app.post("/api/jd-parse")
def api_jd_parse():
    payload, error = _get_json_body()
    if error:
        return error
    company = str(payload.get("company") or "").strip()
    title = str(payload.get("title") or "").strip()
    jd_text = str(payload.get("jd_text") or "").strip()
    if not jd_text:
        return _json({"error": "jd_text is required"}, 400)
    return _json(legacy_app.AI_FEATURES.parse_jd(company=company, title=title, jd_text=jd_text))


@app.post("/api/gap-analysis")
def api_gap_analysis():
    payload, error = _get_json_body()
    if error:
        return error
    company = str(payload.get("company") or "").strip()
    title = str(payload.get("title") or "").strip()
    jd_text = str(payload.get("jd_text") or "").strip()
    if not jd_text:
        return _json({"error": "jd_text is required"}, 400)
    jd_analysis = payload.get("jd_analysis") if isinstance(payload.get("jd_analysis"), dict) else None
    user_profile = payload.get("user_profile") if isinstance(payload.get("user_profile"), dict) else None
    result = legacy_app.AI_FEATURES.analyze_gap(
        company=company,
        title=title,
        jd_text=jd_text,
        jd_analysis=jd_analysis,
        user_profile=user_profile,
    )
    return _json(result)


@app.post("/api/interview-questions")
def api_interview_questions():
    payload, error = _get_json_body()
    if error:
        return error
    company = str(payload.get("company") or "").strip()
    title = str(payload.get("title") or "").strip()
    jd_text = str(payload.get("jd_text") or "").strip()
    if not jd_text:
        return _json({"error": "jd_text is required"}, 400)
    jd_analysis = payload.get("jd_analysis") if isinstance(payload.get("jd_analysis"), dict) else None
    seed_questions = payload.get("seed_questions") if isinstance(payload.get("seed_questions"), list) else None
    result = legacy_app.AI_FEATURES.generate_interview_questions(
        company=company,
        title=title,
        jd_text=jd_text,
        jd_analysis=jd_analysis,
        seed_questions=seed_questions,
    )
    return _json(result)


@app.post("/api/mock-interview/start")
def api_mock_start():
    payload, error = _get_json_body()
    if error:
        return error
    mode = str(payload.get("mode") or "quick").strip() or "quick"
    return _json(legacy_app.MOCK_INTERVIEW.start_session(mode))


@app.post("/api/mock-interview/respond")
def api_mock_respond():
    payload, error = _get_json_body()
    if error:
        return error
    mode = str(payload.get("mode") or "quick").strip() or "quick"
    question = payload.get("question")
    answer = str(payload.get("answer") or "").strip()
    history = payload.get("history") if isinstance(payload.get("history"), list) else None
    if not isinstance(question, dict):
        return _json({"error": "question is required"}, 400)
    if not answer:
        return _json({"error": "answer is required"}, 400)
    result = legacy_app.MOCK_INTERVIEW.evaluate_answer(
        mode_key=mode,
        question=question,
        answer=answer,
        history=history,
    )
    return _json(result)


@app.post("/api/mock-interview/next")
def api_mock_next():
    payload, error = _get_json_body()
    if error:
        return error
    mode = str(payload.get("mode") or "quick").strip() or "quick"
    asked_questions = payload.get("asked_questions") if isinstance(payload.get("asked_questions"), list) else None
    history = payload.get("history") if isinstance(payload.get("history"), list) else None
    try:
        question_index = int(payload.get("question_index") or 0)
    except (TypeError, ValueError):
        question_index = 0
    result = legacy_app.MOCK_INTERVIEW.next_question(
        mode_key=mode,
        question_index=question_index,
        asked_questions=asked_questions,
        history=history,
    )
    return _json(result)


if __name__ == "__main__":
    bootstrap()
    port = int(legacy_app.os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
