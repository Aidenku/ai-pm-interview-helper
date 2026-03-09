#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import sys
import threading
import time
import html
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.ai_feature_service import get_ai_feature_service
from services.env_loader import load_env_file
from services.gap_analysis import get_gap_analysis_service
from services.jd_parser import get_jd_parser_service
from services.mock_interview_service import get_mock_interview_service
from services.question_generator import get_question_generator_service
from services.user_profile import get_user_profile_service

load_env_file(BASE_DIR / '.env.local')

STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jobs.db"
SEED_INTERVIEW_PATH = DATA_DIR / "interview_questions_seed.json"

TZ = datetime.now().astimezone().tzinfo or timezone.utc

STATE = {
    "is_running": False,
    "last_run": None,
    "last_error": None,
    "next_run": None,
    "events": [],
    "event_id": 0,
}
STATE_LOCK = threading.Lock()
REFRESH_LOCK = threading.Lock()
REFRESH_INTERVAL_SECONDS = 24 * 60 * 60
JD_PARSER = get_jd_parser_service()
GAP_ANALYZER = get_gap_analysis_service()
QUESTION_GENERATOR = get_question_generator_service()
USER_PROFILE_SERVICE = get_user_profile_service()
AI_FEATURES = get_ai_feature_service()
MOCK_INTERVIEW = get_mock_interview_service()

COMPANY_SOURCES = [
    {
        "company": "阿里巴巴",
        "url": "https://careers.alibaba.com/",
        "fallback": [],
        "strategy": "hold",
    },
    {
        "company": "字节跳动",
        "url": "https://jobs.bytedance.com/campus/position?keywords=&category=6704215864629004552%2C6704215864591255820%2C6704216224387041544%2C6704215924712409352&location=&project=7194661644654577981&type=&job_hot_flag=&current=1&limit=10&functionCategory=&tag=",
        "fallback": [],
        "strategy": "bytedance",
    },
    {
        "company": "腾讯",
        "url": "https://careers.tencent.com/",
        "fallback": [],
        "strategy": "tencent",
    },
    {
        "company": "美团",
        "url": "https://zhaopin.meituan.com/",
        "fallback": [
            {
                "title": "【转正实习】AI产品经理",
                "city": "北京/上海",
                "apply_url": "https://zhaopin.meituan.com/web/position/detail?jobUnionId=4220518746&highlightType=campus",
                "jd_text": "岗位职责：参与AI核心团队产品方向，推动AI能力落地并结合业务场景快速迭代。任职要求：对AI产品有理解与实践，学习能力强，具备分析和动手能力。",
                "opened_at": "2026-03-07",
            }
        ],
        "strategy": "meituan",
    },
    {
        "company": "京东",
        "url": "https://zhaopin.jd.com/",
        "fallback": [],
        "strategy": "jd",
    },
    {
        "company": "百度",
        "url": "https://talent.baidu.com/jobs/intern-list?keyword=%E4%BA%A7%E5%93%81%E7%BB%8F%E7%90%86",
        "fallback": [],
        "strategy": "baidu",
    },
    {
        "company": "快手",
        "url": "https://campus.kuaishou.cn",
        "fallback": [],
        "strategy": "kuaishou",
    },
    {
        "company": "小红书",
        "url": "https://job.xiaohongshu.com/campus",
        "fallback": [],
        "strategy": "hold",
    },
    {
        "company": "拼多多",
        "url": "https://careers.pinduoduo.com/campus/",
        "fallback": [],
        "strategy": "hold",
    },
    {
        "company": "携程",
        "url": "https://jobs.careers.trip.com/zh_CN/careers/SearchJobs/?keyword=product+manager",
        "fallback": [],
        "strategy": "trip",
    },
    {
        "company": "网易",
        "url": "https://campus.163.com/",
        "fallback": [],
        "strategy": "hold",
    },
    {
        "company": "小米",
        "url": "https://hr.xiaomi.com/",
        "fallback": [],
        "strategy": "hold",
    },
]


def now_str():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def parse_dt(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)


def emit_event(stage, message, extra=None):
    payload = {
        "ts": now_str(),
        "stage": stage,
        "message": message,
        "extra": extra or {},
    }
    with STATE_LOCK:
        STATE["event_id"] += 1
        payload["id"] = STATE["event_id"]
        STATE["events"].append(payload)
        if len(STATE["events"]) > 500:
            STATE["events"] = STATE["events"][-300:]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            city TEXT,
            jd_text TEXT,
            apply_url TEXT NOT NULL,
            source_url TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            is_new INTEGER NOT NULL DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'fallback',
            UNIQUE(company, title, city, apply_url)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role_keyword TEXT,
            question TEXT NOT NULL,
            source TEXT,
            difficulty TEXT
        )
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(1) AS c FROM interview_questions")
    if cur.fetchone()["c"] == 0 and SEED_INTERVIEW_PATH.exists():
        items = json.loads(SEED_INTERVIEW_PATH.read_text(encoding="utf-8"))
        for item in items:
            cur.execute(
                """
                INSERT INTO interview_questions(company, role_keyword, question, source, difficulty)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item.get("company", ""),
                    item.get("role_keyword", ""),
                    item.get("question", ""),
                    item.get("source", ""),
                    item.get("difficulty", "中"),
                ),
            )
        conn.commit()
    conn.close()


def fetch_html(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        },
    )
    with urlopen(req, timeout=12) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="ignore")


def fetch_json(url, params=None, referer=""):
    if params:
        query = urlencode(params, doseq=True)
        url = f"{url}?{query}"
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": referer or f"{urlparse(url).scheme}://{urlparse(url).netloc}/",
        },
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def post_json(url, payload, referer=""):
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Origin": f"{urlparse(url).scheme}://{urlparse(url).netloc}",
            "Referer": referer or f"{urlparse(url).scheme}://{urlparse(url).netloc}/",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def cleanup_text(raw):
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def extract_embedded_json_array(html, field_name):
    needle = f'{field_name}":['
    idx = html.find(needle)
    if idx == -1:
        return []
    start = idx + len(f'{field_name}":')
    depth = 0
    end = None
    for pos, ch in enumerate(html[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = pos + 1
                break
    if end is None:
        return []
    try:
        return json.loads(html[start:end])
    except Exception:
        return []


def guess_city(text):
    for city in ["北京", "上海", "杭州", "深圳", "广州", "成都", "南京", "武汉"]:
        if city in text:
            return city
    return "待确认"

def is_detail_url(url):
    u = (url or "").lower()
    patterns = [
        "position/detail",
        "jobunionid=",
        "jobid=",
        "positionid=",
        "#/details",
        "jobdesc.html?postid=",
        "post_detail.html?postid=",
        "/campus/position/",
        "/apply",
        "/posting",
        "/api/wx/position/index",
    ]
    return any(x in u for x in patterns)


def get_link_quality(url):
    if is_detail_url(url):
        return "direct"
    u = (url or "").lower()
    if "keyword=" in u or "keywords=" in u:
        return "search"
    return "homepage"


def get_internship_label(title, jd_text):
    t = f"{title or ''} {jd_text or ''}"
    if "转正" in t or "留用" in t or "byteintern" in t.lower():
        return "转正实习"
    if "暑期" in t:
        return "暑期实习"
    if "日常实习" in t:
        return "日常实习"
    if "应届实习" in t:
        return "应届实习"
    if "项目实习" in t:
        return "项目实习"
    if "Pre留学生实习" in t or "pre留学生实习" in t.lower():
        return "Pre留学生实习"
    if re.search(r"\b(intern|internship)\b", t, flags=re.IGNORECASE):
        return "实习"
    if "校园" in t or "实习" in t:
        return "实习"
    return "待确认"


def build_display_title(title, internship_label):
    title = (title or "").strip()
    internship_label = (internship_label or "").strip()
    if not title or not internship_label or internship_label == "待确认":
        return title

    explicit_labels = ["转正实习", "暑期实习", "日常实习", "应届实习", "项目实习", "Pre留学生实习"]
    if any(label in title for label in explicit_labels):
        return title
    if internship_label == "实习" and "实习" in title:
        return title
    return f"{title}（{internship_label}）"


def extract_job_union_id(apply_url):
    try:
        q = parse_qs(urlparse(apply_url).query)
        return (q.get("jobUnionId", [""])[0] or "").strip()
    except Exception:
        return ""


def fetch_meituan_job_detail(job_union_id, highlight_type="campus"):
    url = "https://zhaopin.meituan.com/api/official/job/getJobDetail"
    referer = f"https://zhaopin.meituan.com/web/position/detail?jobUnionId={job_union_id}&highlightType={highlight_type}"
    payload = {"jobUnionId": str(job_union_id), "highlightType": highlight_type}
    resp = post_json(url, payload, referer=referer)
    data = resp.get("data") or {}
    if not data:
        return None

    title = data.get("name") or ""
    city_list = [c.get("name", "") for c in (data.get("cityList") or []) if c.get("name")]
    city = "、".join(city_list) if city_list else "待确认"
    duty = (data.get("jobDuty") or "").strip()
    reqs = (data.get("jobRequirement") or "").strip()
    full_jd = []
    if duty:
        full_jd.append("岗位职责")
        full_jd.append(duty)
    if reqs:
        full_jd.append("任职要求")
        full_jd.append(reqs)

    return {
        "title": title,
        "city": city,
        "jd_text": "\n\n".join(full_jd).strip(),
        "apply_url": referer,
    }


def fetch_meituan_pm_jobs():
    url = "https://zhaopin.meituan.com/api/official/job/getJobList"
    referer = "https://zhaopin.meituan.com/web/position"
    queries = [
        "产品经理 转正实习",
        "实习 产品经理",
        "AI产品经理",
    ]

    seen = set()
    jobs = []

    for keyword in queries:
        payload = {
            "page": {"pageNo": 1, "pageSize": 50},
            "keywords": keyword,
            "hiringType": "12",
        }
        resp = post_json(url, payload, referer=referer)
        items = ((resp.get("data") or {}).get("list") or [])
        for it in items:
            job_union_id = (it.get("jobUnionId") or "").strip()
            title = (it.get("name") or "").strip()
            if not job_union_id or not title:
                continue
            if job_union_id in seen:
                continue
            if not re.search(r"(产品经理|产品实习|产品岗|AI ?产品经理)", title):
                continue

            job_type = str(it.get("jobType") or "")
            special_code = str(it.get("jobSpecialCode") or "")
            source = str(it.get("jobSource") or "")
            text = " ".join(
                [
                    title,
                    it.get("jobDuty") or "",
                    it.get("jobRequirement") or "",
                    it.get("highLight") or "",
                ]
            )

            # 只收产品相关的转正实习/日常实习/项目实习等岗位，不混入普通社招/校招全职岗。
            is_internship_like = (
                job_type == "2"
                or (source == "2" and special_code == "1")
                or re.search(r"(实习|转正|项目实习|留用)", text)
            )
            if not is_internship_like:
                continue

            seen.add(job_union_id)

            try:
                detail = fetch_meituan_job_detail(job_union_id, "campus") or {}
            except Exception:
                detail = {}

            city_list = [c.get("name", "") for c in (it.get("cityList") or []) if c.get("name")]
            city = detail.get("city") or ("、".join(city_list) if city_list else "待确认")
            jd_text = detail.get("jd_text") or ""
            if not jd_text:
                duty = (it.get("jobDuty") or "").strip()
                reqs = (it.get("jobRequirement") or "").strip()
                hi = (it.get("highLight") or "").strip()
                jd_parts = []
                if duty:
                    jd_parts.extend(["岗位职责", duty])
                if reqs:
                    jd_parts.extend(["任职要求", reqs])
                if hi:
                    jd_parts.extend(["岗位亮点", hi])
                jd_text = "\n\n".join(jd_parts).strip()

            opened_at = ""
            ts = it.get("firstPostTime") or it.get("refreshTime")
            if isinstance(ts, int) and ts > 0:
                opened_at = datetime.fromtimestamp(ts / 1000, TZ).strftime("%Y-%m-%d")

            jobs.append(
                {
                    "title": detail.get("title") or title,
                    "city": city,
                    "apply_url": detail.get("apply_url")
                    or f"https://zhaopin.meituan.com/web/position/detail?jobUnionId={job_union_id}&highlightType=campus",
                    "jd_text": jd_text or "美团岗位暂未返回完整JD文本。",
                    "opened_at": opened_at,
                }
            )

    return jobs


def fetch_jd_internship_jobs():
    url = "https://campus.jd.com/api/wx/position/page?type=internship"
    referer = "https://campus.jd.com/#/jobs?selProjects=45"
    # pageIndex=0 是该接口的第一页
    base_payload = {
        "pageSize": 50,
        "pageIndex": 0,
        "parameter": {
            "positionName": "",
            "planIdList": [45, 51],
            "jobDirectionCodeList": [],
            "workCityCodeList": [],
            "positionDeptList": [],
        },
    }
    resp = post_json(url, base_payload, referer=referer)
    items = ((resp.get("body") or {}).get("items") or [])
    jobs = []
    seen = set()
    for it in items:
        name = (it.get("positionName") or "").strip()
        if "产品" not in name:
            continue

        publish_id = it.get("publishId")
        if not publish_id:
            continue
        if publish_id in seen:
            continue
        seen.add(publish_id)

        work_content = (it.get("workContent") or "").strip()
        qualification = (it.get("qualification") or "").strip()
        req_list = it.get("requirementVoList") or []
        cities = []
        for r in req_list:
            wc = (r.get("workCity") or "").strip()
            if not wc:
                continue
            city_name = wc.split("-")[-1] if "-" in wc else wc
            if city_name and city_name not in cities:
                cities.append(city_name)
        city = "、".join(cities[:5]) if cities else "待确认"

        jd_parts = []
        if work_content:
            jd_parts.append("岗位职责")
            jd_parts.append(work_content)
        if qualification:
            jd_parts.append("任职要求")
            jd_parts.append(qualification)
        full_jd = "\n\n".join(jd_parts).strip()

        publish_time = it.get("publishTime")
        opened_at = ""
        if isinstance(publish_time, int) and publish_time > 0:
            opened_at = datetime.fromtimestamp(publish_time / 1000, TZ).strftime("%Y-%m-%d")

        detail_url = f"https://campus.jd.com/api/wx/position/index?type=internship#/details?type=internship&id={publish_id}"
        jobs.append(
            {
                "title": f"{name}（京东实习）",
                "city": city,
                "apply_url": detail_url,
                "jd_text": full_jd or "来自京东校招接口，暂未返回完整JD文本。",
                "opened_at": opened_at,
            }
        )
    return jobs


def fetch_tencent_pm_jobs():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://join.qq.com",
        "Referer": "https://join.qq.com/post.html",
    }

    search_url = "https://join.qq.com/api/v1/position/searchPosition"
    detail_base = "https://join.qq.com/api/v1/jobDetails/getJobDetailsByPostId?postId="
    payload = {
        "projectIdList": [2, 4],  # 应届实习 + 日常实习
        "positionFidList": [94],  # 通用产品类
        "pageIndex": 1,
        "pageSize": 100,
    }

    req = Request(search_url, data=json.dumps(payload).encode("utf-8"), method="POST", headers=headers)
    resp = json.loads(urlopen(req, timeout=20).read().decode("utf-8", errors="ignore"))
    items = ((resp.get("data") or {}).get("positionList") or [])

    jobs = []
    seen = set()
    for it in items:
        post_id = (it.get("postId") or "").strip()
        title = (it.get("positionTitle") or "").strip()
        project_name = (it.get("projectName") or it.get("recruitLabelName") or "").strip()
        if not post_id or post_id.startswith("-"):
            continue
        if post_id in seen:
            continue
        if not title:
            continue
        if project_name not in ("应届实习", "日常实习"):
            continue
        if not re.search(r"(产品|策划|运营|项目管理)", title):
            continue

        detail_req = Request(f"{detail_base}{post_id}", headers={k: v for k, v in headers.items() if k != "Content-Type"})
        try:
            detail_resp = json.loads(urlopen(detail_req, timeout=20).read().decode("utf-8", errors="ignore"))
            d = detail_resp.get("data") or {}
        except Exception:
            d = {}

        detail_title = (d.get("title") or title).strip()
        desc = (d.get("desc") or "").strip()
        requirement = (d.get("request") or "").strip()
        bonus = (d.get("internBonus") or d.get("graduateBonus") or "").strip()
        city_list = d.get("workCityList") or []
        city = "、".join([c for c in city_list if c]) if city_list else cleanup_text(it.get("workCities") or "") or "待确认"

        jd_parts = []
        if desc:
            jd_parts.extend(["岗位职责", desc])
        if requirement:
            jd_parts.extend(["任职要求", requirement])
        if bonus:
            jd_parts.extend(["加分项", bonus])
        if project_name:
            jd_parts.extend(["岗位类型", project_name])

        jobs.append(
            {
                "title": f"{detail_title}（腾讯实习）",
                "city": city,
                "apply_url": f"https://join.qq.com/post_detail.html?postId={post_id}",
                "jd_text": "\n\n".join(jd_parts).strip() or "腾讯校招岗位暂未返回完整JD文本。",
                "opened_at": "",
            }
        )
        seen.add(post_id)
    return jobs


def discover_bytedance_position_ids():
    seed_ids = [
        "7216534167425009979",
        "7381782399158208777",
        "7398373916379105573",
        "7447460068743104786",
        "7514520279256746248",
        "7591364983460628741",
        "7371730865183951114",
    ]
    queries = [
        "site:jobs.bytedance.com/campus/position/ 字节跳动 产品 实习",
        "site:jobs.bytedance.com/campus/position/ 字节跳动 产品经理 实习",
        "site:jobs.bytedance.com/campus/position/ 字节跳动 AI 产品 实习",
        "site:jobs.bytedance.com/campus/position/ 字节跳动 平台 产品 实习",
        "site:jobs.bytedance.com/campus/position/ 字节跳动 产品 战略 实习",
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    ids = list(seed_ids)
    seen = set(seed_ids)

    for query in queries:
        search_url = "https://duckduckgo.com/html/?" + urlencode({"q": query})
        req = Request(search_url, headers=headers)
        with urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="ignore")

        for m in re.finditer(r"uddg=([^&]+jobs\.bytedance\.com[^&]+)", text):
            link = html.unescape(unquote(m.group(1)))
            job_id_match = re.search(r"/position/(\d+)/detail", link)
            if not job_id_match:
                continue
            job_id = job_id_match.group(1)
            if job_id in seen:
                continue
            seen.add(job_id)
            ids.append(job_id)
    return ids


def fetch_bytedance_job_detail(job_id):
    url = f"https://jobs.bytedance.com/api/v1/job/posts/{job_id}"
    params = {"portal_type": 2, "source_job_post_id": ""}
    referer = f"https://jobs.bytedance.com/campus/position/{job_id}/detail"
    resp = fetch_json(url, params=params, referer=referer)
    return (resp.get("data") or {}).get("job_post_detail") or {}


def fetch_bytedance_pm_jobs():
    jobs = []
    for job_id in discover_bytedance_position_ids():
        try:
            detail = fetch_bytedance_job_detail(job_id)
        except Exception:
            continue

        title = (detail.get("title") or "").strip()
        if not title or "产品" not in title:
            continue
        if int(detail.get("channel_online_status") or 0) != 1:
            continue

        category = (detail.get("job_category") or {}).get("i18n_name") or ""
        category_parent = ((detail.get("job_category") or {}).get("parent") or {}).get("i18n_name") or ""
        desc = (detail.get("description") or "").strip()
        reqs = (detail.get("requirement") or "").strip()
        text = " ".join([title, category, category_parent, desc, reqs])
        if not re.search(r"(产品|产品经理|商业产品|体验产品|创意产品|平台产品|产品战略|AI)", text):
            continue
        if not re.search(r"(实习|byteintern|日常实习)", text, flags=re.IGNORECASE):
            continue

        cities = []
        for city_info in detail.get("city_list") or []:
            city_name = city_info.get("i18n_name") or city_info.get("name") or ""
            if city_name and city_name not in cities:
                cities.append(city_name)
        city = "、".join(cities[:5]) if cities else "待确认"

        jd_parts = []
        if desc:
            jd_parts.extend(["岗位职责", desc])
        if reqs:
            jd_parts.extend(["任职要求", reqs])

        publish_time = detail.get("publish_time")
        opened_at = ""
        if isinstance(publish_time, int) and publish_time > 0:
            opened_at = datetime.fromtimestamp(publish_time / 1000, TZ).strftime("%Y-%m-%d")

        jobs.append(
            {
                "title": title,
                "city": city,
                "apply_url": f"https://jobs.bytedance.com/campus/position/{job_id}/detail",
                "jd_text": "\n\n".join(jd_parts).strip() or "字节跳动岗位暂未返回完整JD文本。",
                "opened_at": opened_at,
            }
        )
    return jobs


def fetch_baidu_pm_jobs():
    html = fetch_html("https://talent.baidu.com/jobs/list?keyword=%E4%BA%A7%E5%93%81%E7%BB%8F%E7%90%86")
    rows = extract_embedded_json_array(html, "listDetailData")
    jobs = []
    for row in rows:
        title = (row.get("name") or "").replace("\\/", "/").strip()
        if "产品" not in title:
            continue

        summary_text = " ".join(
            [
                title,
                row.get("projectType") or "",
                row.get("workContent") or "",
                row.get("serviceCondition") or "",
            ]
        )
        if not re.search(r"(实习|暑期|留用|intern)", summary_text, flags=re.IGNORECASE):
            continue

        post_id = (row.get("postId") or "").strip()
        if not post_id:
            continue

        city = (row.get("workPlace") or "").strip() or guess_city(title)
        duty = (row.get("workContent") or "").strip()
        reqs = (row.get("serviceCondition") or "").strip()
        jd_parts = []
        if duty:
            jd_parts.append("岗位职责")
            jd_parts.append(duty)
        if reqs:
            jd_parts.append("任职要求")
            jd_parts.append(reqs)

        jobs.append(
            {
                "title": title,
                "city": city,
                "apply_url": f"https://talent.baidu.com/jobs/detail/SOCIAL/{post_id}",
                "jd_text": "\n\n".join(jd_parts).strip(),
                "opened_at": (row.get("publishDate") or "").strip(),
            }
        )
    return jobs


def fetch_kuaishou_pm_jobs():
    list_url = "https://campus.kuaishou.cn/recruit/campus/e/api/v1/open/positions/simple"
    detail_base = "https://campus.kuaishou.cn/recruit/campus/e/api/v1/open/positions/find?id="
    referer = "https://campus.kuaishou.cn/#/campus/jobs?positionNatureCode=intern&pageNum=1"
    payload = {
        "positionBO": {
            "recruitSubProjectCodes": ["20261707035672", "20261749721165"],
            "pageNum": 1,
            "pageSize": 50,
            "positionNatureCode": "intern",
        }
    }
    req = Request(
        list_url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json,text/plain,*/*",
            "Origin": "https://campus.kuaishou.cn",
            "Referer": referer,
        },
    )
    resp = json.loads(urlopen(req, timeout=20).read().decode("utf-8", errors="ignore"))
    items = ((resp.get("result") or {}).get("list") or [])

    jobs = []
    seen = set()
    for item in items:
        position_id = item.get("id")
        title = (item.get("name") or "").strip()
        text = " ".join(
            [
                title,
                item.get("description") or "",
                item.get("positionDemand") or "",
            ]
        )
        if not position_id or not title:
            continue
        if position_id in seen:
            continue
        if not re.search(r"(产品经理|产品|策划|运营|项目管理|AI)", title):
            continue
        if not re.search(r"(实习|留用|暑期|intern)", text, flags=re.IGNORECASE):
            continue

        try:
            detail_req = Request(
                f"{detail_base}{position_id}",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": referer,
                },
            )
            detail_resp = json.loads(urlopen(detail_req, timeout=20).read().decode("utf-8", errors="ignore"))
            detail = detail_resp.get("result") or {}
        except Exception:
            detail = {}

        if not detail:
            detail = item

        detail_title = (detail.get("name") or title).strip()
        detail_text = " ".join(
            [
                detail_title,
                detail.get("description") or "",
                detail.get("positionDemand") or "",
            ]
        )
        if not re.search(r"(产品经理|产品|策划|运营|项目管理|AI)", detail_title):
            continue
        if not re.search(r"(实习|留用|暑期|intern)", detail_text, flags=re.IGNORECASE):
            continue

        city_names = []
        for city in detail.get("workLocationDicts") or item.get("workLocationDicts") or []:
            name = (city.get("name") or "").strip()
            if name and name not in city_names:
                city_names.append(name)

        jd_parts = []
        desc = (detail.get("description") or item.get("description") or "").strip()
        demand = (detail.get("positionDemand") or item.get("positionDemand") or "").strip()
        if desc:
            jd_parts.extend(["岗位职责", desc])
        if demand:
            jd_parts.extend(["任职要求", demand])

        opened_at = ""
        release_time = (detail.get("releaseTime") or item.get("releaseTime") or "").strip()
        if release_time:
            opened_at = release_time[:10]

        jobs.append(
            {
                "title": detail_title,
                "city": "、".join(city_names) if city_names else "待确认",
                "apply_url": f"https://campus.kuaishou.cn/#/campus/job-info/{position_id}?positionNatureCode=intern",
                "jd_text": "\n\n".join(jd_parts).strip() or "快手校园岗位暂未返回完整JD文本。",
                "opened_at": opened_at,
            }
        )
        seen.add(position_id)
    return jobs


def fetch_trip_pm_jobs():
    html = fetch_html("https://jobs.careers.trip.com/en_US/careers/SearchJobs/?keyword=product+manager")
    jobs = []
    seen = set()
    pattern = re.compile(
        r'<article class="article article--result".*?<a href="([^"]+)">\s*(.*?)\s*</a>.*?<span class="list-item-posted">Posted (\d{2}-[A-Za-z]{3}-\d{4})</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    for href, raw_title, posted in pattern.findall(html):
        title = cleanup_text(raw_title)
        if not re.search(r"(product manager|product)", title, flags=re.IGNORECASE):
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        if not re.search(r"(intern|internship|实习)", title, flags=re.IGNORECASE):
            continue

        opened_at = ""
        try:
            opened_at = datetime.strptime(posted, "%d-%b-%Y").strftime("%Y-%m-%d")
        except Exception:
            pass

        jobs.append(
            {
                "title": title,
                "city": "待确认",
                "apply_url": href,
                "jd_text": "请点击岗位详情页查看完整JD。",
                "opened_at": opened_at,
            }
        )
    return jobs


def build_company_search_link(company, title, fallback_url):
    kw = quote((title or "AI 产品经理 实习").strip())
    if company == "京东":
        return f"https://campus.jd.com/#/jobs?keywords={kw}"
    if company == "美团":
        return f"https://zhaopin.meituan.com/web/position?keyword={kw}"
    if company == "阿里巴巴":
        return f"https://careers.alibaba.com/positionList.htm?keyWord={kw}"
    if company == "百度":
        return f"https://talent.baidu.com/jobs/intern-list?keyword={kw}"
    if company == "快手":
        return "https://campus.kuaishou.cn/#/campus/jobs?pageNum=1&positionNatureCode=intern"
    if company == "小红书":
        return "https://job.xiaohongshu.com/campus"
    if company == "拼多多":
        return "https://careers.pinduoduo.com/campus/"
    if company == "携程":
        return f"https://jobs.careers.trip.com/zh_CN/careers/SearchJobs/?keyword={kw}"
    if company == "网易":
        return "https://campus.163.com/"
    if company == "小米":
        return "https://hr.xiaomi.com/"
    return fallback_url


def extract_live_candidates(html, source_url, company):
    candidates = []
    seen = set()

    anchor_matches = re.findall(
        r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for href, raw_label in anchor_matches:
        label = cleanup_text(raw_label)
        if not label:
            continue
        if not re.search(r"(产品经理|AI|实习|Product Manager|Product Intern|AI Product)", label, flags=re.IGNORECASE):
            continue
        if href.startswith("javascript") or href.startswith("#"):
            continue

        title = label[:60]
        apply_url = urljoin(source_url, href)
        key = f"{title}|{apply_url}"
        if key in seen:
            continue
        seen.add(key)

        score = 0
        if re.search(r"(产品经理|AI|Product Manager|AI Product)", title, flags=re.IGNORECASE):
            score += 3
        if re.search(r"(实习|校园|转正|Intern|Internship)", title, flags=re.IGNORECASE):
            score += 2
        if is_detail_url(apply_url):
            score += 5
        if score < 4:
            continue

        candidates.append(
            {
                "title": title,
                "city": guess_city(label),
                "apply_url": apply_url,
                "jd_text": f"来自{company}招聘页实时抓取，建议点击投递链接查看完整JD。",
                "score": score,
            }
        )

    if candidates:
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        return candidates[:20]

    text = re.sub(r"\s+", " ", html)
    for m in re.finditer(
        r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{4,40}(?:产品经理|AI产品经理|产品实习生|产品经理实习生)[\u4e00-\u9fa5A-Za-z0-9（）()·\-]{0,20})",
        text,
    ):
        title = re.sub(r"\s+", "", m.group(1)[:60])
        if title in seen:
            continue
        seen.add(title)
        candidates.append(
            {
                "title": title,
                "city": guess_city(title),
                "apply_url": source_url,
                "jd_text": f"来自{company}公开招聘页面的实时抓取结果，建议进入投递入口查看完整JD。",
            }
        )
        if len(candidates) >= 10:
            break
    return candidates


def fetch_company_jobs(source):
    company = source["company"]
    source_url = source["url"]
    strategy = source.get("strategy", "generic")
    emit_event("crawl", f"开始抓取 {company} 招聘页", {"url": source_url})
    if strategy == "hold":
        emit_event("crawl", f"{company} 已接入公司列表，但当前未开放稳定抓取，不展示占位岗位")
        return [], "hold"

    if strategy == "bytedance":
        try:
            jobs = fetch_bytedance_pm_jobs()
            if jobs:
                emit_event("crawl", f"{company} 抓取到 {len(jobs)} 条产品实习岗位")
                return jobs, "bytedance_detail_api"
            emit_event("crawl", f"{company} 当前没有匹配的产品实习岗位")
            return [], "bytedance_empty"
        except Exception as exc:
            emit_event("crawl", f"{company} 抓取失败", {"error": str(exc)})
            return [], "bytedance_error"

    if strategy == "tencent":
        try:
            jobs = fetch_tencent_pm_jobs()
            if jobs:
                emit_event("crawl", f"{company} 接口抓取到 {len(jobs)} 条产品方向岗位")
                return jobs, "tencent_join_api"
            emit_event("crawl", f"{company} 暂无符合条件岗位")
            return [], "tencent_join_api_empty"
        except Exception as exc:
            emit_event("crawl", f"{company} 接口抓取失败", {"error": str(exc)})
            return [], "tencent_join_api_error"

    if strategy == "meituan":
        try:
            jobs = fetch_meituan_pm_jobs()
            if jobs:
                emit_event("crawl", f"{company} 接口抓取到 {len(jobs)} 条产品实习/转正实习岗位")
                return jobs, "meituan_api"
            emit_event("crawl", f"{company} 当前没有匹配的产品实习岗位")
            return [], "meituan_empty"
        except Exception as exc:
            emit_event("crawl", f"{company} 接口抓取失败", {"error": str(exc)})
            return source["fallback"], "meituan_error"

    if strategy == "baidu":
        try:
            jobs = fetch_baidu_pm_jobs()
            if jobs:
                emit_event("crawl", f"{company} 接口抓取到 {len(jobs)} 条产品实习岗位")
                return jobs, "baidu_embedded_json"
            emit_event("crawl", f"{company} 当前没有匹配的产品实习岗位")
            return [], "baidu_empty"
        except Exception as exc:
            emit_event("crawl", f"{company} 抓取失败", {"error": str(exc)})
            return [], "baidu_error"

    if strategy == "kuaishou":
        try:
            jobs = fetch_kuaishou_pm_jobs()
            if jobs:
                emit_event("crawl", f"{company} 接口抓取到 {len(jobs)} 条产品实习岗位")
                return jobs, "kuaishou_api"
            emit_event("crawl", f"{company} 当前没有匹配的产品实习岗位")
            return [], "kuaishou_empty"
        except Exception as exc:
            emit_event("crawl", f"{company} 接口抓取失败", {"error": str(exc)})
            return [], "kuaishou_error"

    if strategy == "jd":
        try:
            jd_jobs = fetch_jd_internship_jobs()
            if jd_jobs:
                merged = []
                merged_keys = set()
                for job in jd_jobs + source["fallback"]:
                    key = ((job.get("title") or "").strip(), (job.get("city") or "").strip())
                    if key in merged_keys:
                        continue
                    merged_keys.add(key)
                    merged.append(job)
                emit_event("crawl", f"{company} 接口抓取到 {len(jd_jobs)} 条产品实习岗位，合并后 {len(merged)} 条")
                return merged, "jd_api+fallback"
        except Exception as exc:
            emit_event("crawl", f"{company} 接口抓取失败，回退到常规抓取", {"error": str(exc)})

    if strategy == "trip":
        try:
            jobs = fetch_trip_pm_jobs()
            if jobs:
                emit_event("crawl", f"{company} 搜索页抓取到 {len(jobs)} 条产品实习岗位")
                return jobs, "trip_html"
            emit_event("crawl", f"{company} 当前没有匹配的产品实习岗位")
            return [], "trip_empty"
        except Exception as exc:
            emit_event("crawl", f"{company} 抓取失败", {"error": str(exc)})
            return [], "trip_error"

    try:
        html = fetch_html(source_url)
        live = extract_live_candidates(html, source_url, company)
        if company == "美团":
            enriched = []
            for job in live + source["fallback"]:
                job_union_id = extract_job_union_id(job.get("apply_url", ""))
                if not job_union_id:
                    enriched.append(job)
                    continue
                try:
                    detail = fetch_meituan_job_detail(job_union_id, "campus")
                    if detail:
                        job = {
                            **job,
                            "title": detail.get("title") or job.get("title"),
                            "city": detail.get("city") or job.get("city"),
                            "jd_text": detail.get("jd_text") or job.get("jd_text"),
                            "apply_url": detail.get("apply_url") or job.get("apply_url"),
                        }
                except Exception:
                    pass
                enriched.append(job)
            live = enriched
        if live:
            merged = []
            merged_keys = set()
            for job in live + source["fallback"]:
                key = (
                    (job.get("title") or "").strip(),
                    (job.get("city") or "").strip(),
                )
                if key in merged_keys:
                    continue
                merged_keys.add(key)
                merged.append(job)
            emit_event("crawl", f"{company} 实时抓取到 {len(live)} 条候选岗位，合并后 {len(merged)} 条")
            return merged, "live+fallback"
        emit_event("crawl", f"{company} 未提取到结构化岗位，使用回退数据")
        return source["fallback"], "fallback"
    except Exception as exc:
        emit_event("crawl", f"{company} 抓取失败，使用回退数据", {"error": str(exc)})
        return source["fallback"], "fallback"


def upsert_jobs(company, source_url, jobs, source_type):
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    updated = 0
    now = now_str()
    for job in jobs:
        title = job.get("title", "未命名岗位").strip()
        city = job.get("city", "待确认").strip()
        apply_url = job.get("apply_url", source_url).strip() or source_url
        if get_link_quality(apply_url) == "homepage":
            apply_url = build_company_search_link(company, title, apply_url)
        jd_text = job.get("jd_text", "").strip()

        raw_opened_at = (job.get("opened_at") or "").strip()
        normalized_opened_at = ""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_opened_at):
            normalized_opened_at = f"{raw_opened_at} 09:00:00"

        cur.execute(
            """
            SELECT id, first_seen, apply_url FROM jobs WHERE company=? AND title=? AND city=? AND apply_url=?
            """,
            (company, title, city, apply_url),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                SELECT id, first_seen, apply_url FROM jobs WHERE company=? AND title=? AND city=?
                ORDER BY id DESC LIMIT 1
                """,
                (company, title, city),
            )
            alt = cur.fetchone()
            if alt and get_link_quality(alt["apply_url"]) in ("homepage", "search") and get_link_quality(apply_url) == "direct":
                row = alt
        if row:
            first_seen = row["first_seen"]
            if normalized_opened_at and normalized_opened_at < first_seen:
                first_seen = normalized_opened_at
            cur.execute(
                """
                UPDATE jobs
                SET jd_text=?, source_url=?, apply_url=?, status='open', is_new=0, first_seen=?, last_seen=?, source_type=?
                WHERE id=?
                """,
                (jd_text, source_url, apply_url, first_seen, now, source_type, row["id"]),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO jobs(company, title, city, jd_text, apply_url, source_url, status, is_new, first_seen, last_seen, source_type)
                VALUES (?, ?, ?, ?, ?, ?, 'open', 1, ?, ?, ?)
                """,
                (
                    company,
                    title,
                    city,
                    jd_text,
                    apply_url,
                    source_url,
                    normalized_opened_at or now,
                    now,
                    source_type,
                ),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, updated


def generate_plan_for_job(job_row, questions):
    title = (job_row["title"] or "").strip()
    company = (job_row["company"] or "").strip()
    jd_text = (job_row["jd_text"] or "")
    text = f"{title}\n{jd_text}".lower()
    internship_label = get_internship_label(title, jd_text)

    knowledge = []
    generated_questions = []

    def add_unique(target, values):
        for value in values:
            value = (value or "").strip()
            if value and value not in target:
                target.append(value)

    add_unique(
        knowledge,
        [
            "用户需求拆解与场景分析",
            "产品方案设计与优先级判断",
            "核心指标定义与效果复盘",
        ],
    )
    add_unique(
        generated_questions,
        [
            f"如果让你定义这个{title or '岗位'}最核心的业务目标，你会怎么拆成可监控的指标？",
            "从需求发现、方案设计到上线验证，这个岗位最关键的推进动作分别是什么？",
        ],
    )

    if "ai" in text or "大模型" in text or "模型" in text or "agent" in text or "prompt" in text:
        add_unique(
            knowledge,
            [
                "大模型产品基础能力与边界",
                "Prompt设计、评测方法与效果迭代",
                "模型幻觉、稳定性与安全风险控制",
            ],
        )
        add_unique(
            generated_questions,
            [
                "如果这个AI功能回答不稳定，你会如何区分是模型问题、Prompt问题还是产品流程问题？",
                "你会如何设计一个AI产品的评测体系，覆盖效果、体验和安全性？",
                "如果要在现有业务里落一个Agent能力，你会优先选择什么场景，为什么？",
            ],
        )

    if "数据" in text or "sql" in text or "分析" in text or "实验" in text:
        add_unique(
            knowledge,
            [
                "SQL与数据分析基础",
                "漏斗、留存、转化率等指标分析",
                "A/B实验设计与结果解释",
            ],
        )
        add_unique(
            generated_questions,
            [
                "如果上线后核心转化率下降，你会先看哪些数据、如何逐层定位？",
                "这个岗位如果要做A/B实验，你会如何设实验指标、样本和止损条件？",
            ],
        )

    if "搜索" in text or "推荐" in text or "召回" in text or "排序" in text:
        add_unique(
            knowledge,
            [
                "搜索/推荐基础机制",
                "召回、排序、点击率与转化率指标",
            ],
        )
        add_unique(
            generated_questions,
            [
                "搜索或推荐效果变差时，你会如何区分是召回问题还是排序问题？",
                "如果用户点击率上升但转化率下降，你会如何判断问题出在哪个环节？",
            ],
        )

    if "增长" in text or "营销" in text or "投放" in text or "拉新" in text or "留存" in text:
        add_unique(
            knowledge,
            [
                "增长模型与用户分层方法",
                "拉新、激活、留存、转化链路拆解",
            ],
        )
        add_unique(
            generated_questions,
            [
                "如果目标是提升某一类用户的留存或转化，你会如何设计增长方案并验证效果？",
                "你会如何判断一个营销/增长动作带来的提升是真增长，还是短期透支？",
            ],
        )

    if "商家" in text or "供应商" in text or "saas" in text or "平台" in text or "to b" in text or "tob" in text:
        add_unique(
            knowledge,
            [
                "ToB产品设计方法",
                "权限、流程、配置化与平台化思维",
                "跨角色协同与交付流程设计",
            ],
        )
        add_unique(
            generated_questions,
            [
                "ToB产品需求和ToC产品需求在优先级判断上有哪些核心差异？",
                "如果商家/内部用户提出很多定制需求，你会如何抽象成通用能力？",
            ],
        )

    if "云" in text or "技术背景" in text or "基础设施" in text:
        add_unique(
            knowledge,
            [
                "云产品/技术平台基础认知",
                "技术能力抽象为产品能力的方法",
            ],
        )
        add_unique(
            generated_questions,
            [
                "如果你面对的是技术平台型产品，如何把复杂技术能力翻译成用户可理解的产品价值？",
            ],
        )

    if "项目" in text or "协同" in text or "推进" in text or "落地" in text:
        add_unique(
            knowledge,
            [
                "PRD撰写与项目管理基础",
                "跨部门协同、排期与风险管理",
            ],
        )
        add_unique(
            generated_questions,
            [
                "如果研发、设计、业务三方目标不一致，你会如何推动项目继续落地？",
            ],
        )

    if company == "美团":
        add_unique(
            generated_questions,
            [
                "美团业务通常同时涉及用户、商家、供给和履约，你会如何判断一个产品方案优先服务哪一侧？",
            ],
        )
    if company == "腾讯":
        add_unique(
            generated_questions,
            [
                f"腾讯这类{internship_label}岗位常会结合具体事业群追问，你会如何快速理解所在BG的业务目标并映射到产品方案？",
            ],
        )
    if company == "京东":
        add_unique(
            generated_questions,
            [
                "如果是电商/供应链场景的产品岗位，你会如何平衡效率、体验和业务收益？",
            ],
        )

    matched_seed_questions = []
    title_and_jd = f"{title}\n{jd_text}"
    for q in questions:
        role_keyword = (q.get("role_keyword") or "").strip()
        if q.get("company") == company:
            if not role_keyword or role_keyword in title_and_jd:
                matched_seed_questions.append(q.get("question") or "")

    merged_questions = []
    add_unique(merged_questions, matched_seed_questions)
    add_unique(merged_questions, generated_questions)

    return {
        "knowledge_points": knowledge[:8],
        "mock_questions": merged_questions[:8],
    }


def run_refresh(trigger="manual"):
    with REFRESH_LOCK:
        with STATE_LOCK:
            if STATE["is_running"]:
                emit_event("status", "已有抓取任务在运行，跳过本次触发")
                return
            STATE["is_running"] = True
            STATE["last_error"] = None

        emit_event("status", f"开始执行刷新任务（trigger={trigger}）")
        total_inserted = 0
        total_updated = 0
        try:
            for src in COMPANY_SOURCES:
                jobs, source_type = fetch_company_jobs(src)
                inserted, updated = upsert_jobs(src["company"], src["url"], jobs, source_type)
                total_inserted += inserted
                total_updated += updated
                emit_event(
                    "persist",
                    f"{src['company']} 入库完成：新增 {inserted}，更新 {updated}，来源 {source_type}",
                )

            upgrade_homepage_links()
            cleanup_legacy_rows()

            with STATE_LOCK:
                STATE["last_run"] = now_str()
                STATE["next_run"] = (datetime.now(TZ) + timedelta(seconds=REFRESH_INTERVAL_SECONDS)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            emit_event("done", f"刷新完成：总新增 {total_inserted}，总更新 {total_updated}")
        except Exception as exc:
            with STATE_LOCK:
                STATE["last_error"] = str(exc)
            emit_event("error", "刷新任务异常", {"error": str(exc)})
        finally:
            with STATE_LOCK:
                STATE["is_running"] = False


def scheduler_loop():
    while True:
        with STATE_LOCK:
            last_run = STATE["last_run"]
            running = STATE["is_running"]

        if not last_run:
            time.sleep(10)
            continue
        if running:
            time.sleep(5)
            continue

        last_dt = parse_dt(last_run)
        if datetime.now(TZ) - last_dt >= timedelta(seconds=REFRESH_INTERVAL_SECONDS):
            run_refresh(trigger="daily")
        time.sleep(20)


def upgrade_homepage_links():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, company, title, apply_url FROM jobs")
    rows = cur.fetchall()
    changed = 0
    for r in rows:
        old_url = r["apply_url"] or ""
        if get_link_quality(old_url) != "homepage":
            continue
        new_url = build_company_search_link(r["company"], r["title"], old_url)
        if new_url != old_url:
            cur.execute("UPDATE jobs SET apply_url=? WHERE id=?", (new_url, r["id"]))
            changed += 1
    conn.commit()
    conn.close()
    if changed:
        emit_event("persist", f"链接升级完成：{changed} 条官网入口改为岗位搜索链接")


def cleanup_legacy_rows():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='京东'
          AND source_type='fallback'
          AND apply_url LIKE 'https://zhaopin.jd.com%'
        """
    )
    deleted = cur.rowcount or 0
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='京东'
          AND title LIKE '%AI产品经理%'
          AND apply_url='https://campus.jd.com/#/jobs?selProjects=45'
        """
    )
    deleted += cur.rowcount or 0
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='京东'
          AND apply_url LIKE 'https://campus.jd.com/#/jobs?keywords=%'
        """
    )
    deleted += cur.rowcount or 0
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='京东'
          AND title='实习生招聘'
        """
    )
    deleted += cur.rowcount or 0
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='美团'
          AND (
            apply_url LIKE 'https://zhaopin.meituan.com/web/position?keyword=%'
            OR apply_url='https://zhaopin.meituan.com/'
          )
        """
    )
    deleted += cur.rowcount or 0
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='美团'
          AND title='【转正实习】AI产品经理'
          AND length(jd_text) < 200
        """
    )
    deleted += cur.rowcount or 0
    cur.execute(
        """
        DELETE FROM jobs
        WHERE company='腾讯'
          AND (
            apply_url LIKE 'https://careers.tencent.com/%'
            OR source_type='tencent_api'
          )
        """
    )
    deleted += cur.rowcount or 0
    cur.execute("DELETE FROM jobs WHERE company='阿里巴巴'")
    deleted += cur.rowcount or 0
    conn.commit()
    conn.close()
    if deleted:
        emit_event("persist", f"清理历史遗留记录：删除 {deleted} 条旧链接或占位岗位")


def list_companies():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT company FROM jobs WHERE status='open' ORDER BY company")
    rows = [r["company"] for r in cur.fetchall()]
    conn.close()
    return rows


def list_jobs(filters):
    conn = get_conn()
    cur = conn.cursor()
    clauses = []
    params = []
    if filters.get("keyword"):
        clauses.append("(title LIKE ? OR jd_text LIKE ?)")
        kw = f"%{filters['keyword']}%"
        params.extend([kw, kw])
    if filters.get("company"):
        clauses.append("company = ?")
        params.append(filters["company"])
    if filters.get("city"):
        clauses.append("city LIKE ?")
        params.append(f"%{filters['city']}%")

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    sql = f"""
        SELECT id, company, title, city, status, is_new, apply_url, source_type, first_seen, last_seen, jd_text
        FROM jobs
        {where_sql}
        ORDER BY first_seen DESC, last_seen DESC, id DESC
        LIMIT 300
    """
    cur.execute(sql, params)
    rows = []
    dedup = {}

    def score(item):
        quality = item.get("link_quality", "homepage")
        q = 0
        if quality == "direct":
            q = 3
        elif quality == "search":
            q = 2
        return (q, len(item.get("jd_text", "") or ""), item.get("last_seen", ""))

    for r in cur.fetchall():
        item = dict(r)
        item["open_date"] = (item.get("first_seen") or "")[:10]
        item["link_quality"] = get_link_quality(item.get("apply_url", ""))
        item["internship_label"] = get_internship_label(item.get("title", ""), item.get("jd_text", ""))
        item["display_title"] = build_display_title(item.get("title", ""), item["internship_label"])
        key = (item.get("company", ""), item.get("title", ""))
        if key not in dedup or score(item) > score(dedup[key]):
            dedup[key] = item
    rows = sorted(dedup.values(), key=lambda x: (x.get("first_seen", ""), x.get("last_seen", ""), x.get("id", 0)), reverse=True)
    for item in rows:
        item.pop("jd_text", None)
    conn.close()
    return rows


def get_job_detail(job_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    cur.execute(
        """
        SELECT company, role_keyword, question, source, difficulty
        FROM interview_questions
        WHERE company=? OR role_keyword LIKE '%产品经理%'
        ORDER BY id DESC
        LIMIT 8
        """,
        (row["company"],),
    )
    questions = [dict(r) for r in cur.fetchall()]
    company = row["company"]
    title = row["title"]
    jd_text = row["jd_text"] or ""
    user_profile = USER_PROFILE_SERVICE.get_default_profile().to_dict()

    jd_analysis_payload = AI_FEATURES.parse_jd(
        company=company,
        title=title,
        jd_text=jd_text,
    )
    jd_analysis = jd_analysis_payload["data"]

    gap_analysis_payload = AI_FEATURES.analyze_gap(
        company=company,
        title=title,
        jd_text=jd_text,
        jd_analysis=jd_analysis,
        user_profile=user_profile,
    )
    interview_prep_payload = AI_FEATURES.generate_interview_questions(
        company=company,
        title=title,
        jd_text=jd_text,
        jd_analysis=jd_analysis,
        seed_questions=questions,
    )
    conn.close()
    detail = dict(row)
    detail["open_date"] = (detail.get("first_seen") or "")[:10]
    detail["link_quality"] = get_link_quality(detail.get("apply_url", ""))
    detail["internship_label"] = get_internship_label(detail.get("title", ""), detail.get("jd_text", ""))
    detail["display_title"] = build_display_title(detail.get("title", ""), detail["internship_label"])
    detail["interview_questions"] = questions
    detail["jd_analysis"] = jd_analysis
    detail["jd_analysis_meta"] = jd_analysis_payload.get("meta", {})
    detail["user_profile"] = user_profile
    detail["gap_analysis"] = gap_analysis_payload["data"]
    detail["gap_analysis_meta"] = gap_analysis_payload.get("meta", {})
    detail["interview_prep"] = interview_prep_payload["data"]
    detail["interview_prep_meta"] = interview_prep_payload.get("meta", {})
    return detail


def serve_static(handler, file_name, content_type):
    file_path = STATIC_DIR / file_name
    if not file_path.exists():
        handler._set_headers(status=404, content_type="text/plain; charset=utf-8")
        handler.wfile.write(f"{file_name} not found".encode("utf-8"))
        return
    handler._set_headers(status=200, content_type=content_type)
    handler.wfile.write(file_path.read_bytes())


class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _write_json(self, payload, status=200):
        self._set_headers(status=status)
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            return None, "invalid content length"
        if length <= 0:
            return None, "empty request body"
        raw = self.rfile.read(length)
        if not raw:
            return None, "empty request body"
        try:
            return json.loads(raw.decode("utf-8")), None
        except Exception:
            return None, "invalid json body"

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            serve_static(self, "index.html", "text/html; charset=utf-8")
            return
        if path == "/job.html":
            serve_static(self, "job.html", "text/html; charset=utf-8")
            return
        if path == "/mock-interview":
            serve_static(self, "mock-interview.html", "text/html; charset=utf-8")
            return
        if path == "/styles.css":
            serve_static(self, "styles.css", "text/css; charset=utf-8")
            return
        if path == "/app.js":
            serve_static(self, "app.js", "application/javascript; charset=utf-8")
            return
        if path == "/job.js":
            serve_static(self, "job.js", "application/javascript; charset=utf-8")
            return
        if path == "/mock-interview.js":
            serve_static(self, "mock-interview.js", "application/javascript; charset=utf-8")
            return

        if path == "/api/jobs":
            qs = parse_qs(parsed.query)
            filters = {
                "keyword": (qs.get("keyword", [""])[0] or "").strip(),
                "company": (qs.get("company", [""])[0] or "").strip(),
                "city": (qs.get("city", [""])[0] or "").strip(),
            }
            rows = list_jobs(filters)
            self._write_json({"items": rows, "count": len(rows)})
            return

        if path.startswith("/api/jobs/"):
            raw_id = unquote(path.split("/api/jobs/")[-1]).strip()
            if not raw_id.isdigit():
                self._write_json({"error": "invalid id"}, status=400)
                return
            detail = get_job_detail(int(raw_id))
            if not detail:
                self._write_json({"error": "not found"}, status=404)
                return
            self._write_json(detail)
            return

        if path == "/api/status":
            with STATE_LOCK:
                state = {
                    "is_running": STATE["is_running"],
                    "last_run": STATE["last_run"],
                    "last_error": STATE["last_error"],
                    "next_run": STATE["next_run"],
                    "event_id": STATE["event_id"],
                }
            self._write_json(state)
            return

        if path == "/api/companies":
            self._write_json({"items": list_companies()})
            return

        if path == "/api/progress":
            with STATE_LOCK:
                events = list(STATE["events"][-80:])
            self._write_json({"items": events})
            return

        if path == "/api/progress/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            last_id = 0
            try:
                while True:
                    with STATE_LOCK:
                        events = [e for e in STATE["events"] if e["id"] > last_id]
                    for event in events:
                        self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        last_id = event["id"]
                    time.sleep(1)
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                return

        self._write_json({"error": "not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/refresh":
            with STATE_LOCK:
                is_running = STATE["is_running"]
            if is_running:
                self._write_json({"ok": False, "message": "refresh already running"}, status=409)
                return
            t = threading.Thread(target=run_refresh, kwargs={"trigger": "manual"}, daemon=True)
            t.start()
            self._write_json({"ok": True, "message": "refresh started"})
            return

        if parsed.path in {"/api/jd-parse", "/api/gap-analysis", "/api/interview-questions", "/api/mock-interview/start", "/api/mock-interview/respond", "/api/mock-interview/next"}:
            payload, error = self._read_json_body()
            if error:
                self._write_json({"error": error}, status=400)
                return

            if parsed.path.startswith("/api/mock-interview/"):
                mode = str((payload or {}).get("mode") or "quick").strip() or "quick"

                if parsed.path == "/api/mock-interview/start":
                    self._write_json(MOCK_INTERVIEW.start_session(mode))
                    return

                if parsed.path == "/api/mock-interview/respond":
                    question = (payload or {}).get("question")
                    answer = str((payload or {}).get("answer") or "").strip()
                    history = (payload or {}).get("history")
                    if not isinstance(question, dict):
                        self._write_json({"error": "question is required"}, status=400)
                        return
                    if not answer:
                        self._write_json({"error": "answer is required"}, status=400)
                        return
                    result = MOCK_INTERVIEW.evaluate_answer(
                        mode_key=mode,
                        question=question,
                        answer=answer,
                        history=history if isinstance(history, list) else None,
                    )
                    self._write_json(result)
                    return

                asked_questions = (payload or {}).get("asked_questions")
                history = (payload or {}).get("history")
                try:
                    question_index = int((payload or {}).get("question_index") or 0)
                except (TypeError, ValueError):
                    question_index = 0
                result = MOCK_INTERVIEW.next_question(
                    mode_key=mode,
                    question_index=question_index,
                    asked_questions=asked_questions if isinstance(asked_questions, list) else None,
                    history=history if isinstance(history, list) else None,
                )
                self._write_json(result)
                return

            company = str((payload or {}).get("company") or "").strip()
            title = str((payload or {}).get("title") or "").strip()
            jd_text = str((payload or {}).get("jd_text") or "").strip()
            if not jd_text:
                self._write_json({"error": "jd_text is required"}, status=400)
                return

            if parsed.path == "/api/jd-parse":
                result = AI_FEATURES.parse_jd(company=company, title=title, jd_text=jd_text)
                self._write_json(result)
                return

            if parsed.path == "/api/gap-analysis":
                jd_analysis = (payload or {}).get("jd_analysis")
                user_profile = (payload or {}).get("user_profile")
                result = AI_FEATURES.analyze_gap(
                    company=company,
                    title=title,
                    jd_text=jd_text,
                    jd_analysis=jd_analysis if isinstance(jd_analysis, dict) else None,
                    user_profile=user_profile if isinstance(user_profile, dict) else None,
                )
                self._write_json(result)
                return

            seed_questions = (payload or {}).get("seed_questions")
            result = AI_FEATURES.generate_interview_questions(
                company=company,
                title=title,
                jd_text=jd_text,
                jd_analysis=(payload or {}).get("jd_analysis") if isinstance((payload or {}).get("jd_analysis"), dict) else None,
                seed_questions=seed_questions if isinstance(seed_questions, list) else None,
            )
            self._write_json(result)
            return

        self._write_json({"error": "not found"}, status=404)

    def log_message(self, format, *args):
        return


def ensure_bootstrap_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) AS c FROM jobs")
    c = cur.fetchone()["c"]
    conn.close()
    if c == 0:
        emit_event("bootstrap", "初始化空库，导入首批岗位")
        run_refresh(trigger="bootstrap")


def main():
    init_db()
    cleanup_legacy_rows()
    ensure_bootstrap_data()

    with STATE_LOCK:
        if STATE["last_run"] is None:
            STATE["last_run"] = now_str()
            STATE["next_run"] = (datetime.now(TZ) + timedelta(seconds=REFRESH_INTERVAL_SECONDS)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    scheduler = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler.start()

    port = int(os.getenv("PORT", "8080"))
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as exc:
        raise RuntimeError(
            f"端口 {port} 已被占用。请先关闭旧的服务进程，再重新启动当前版本。"
        ) from exc

    print(f"Server running on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
