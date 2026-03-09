# AI PM 实习雷达（MVP）

一个可本地运行的网站，支持：
- 聚合字节 / 腾讯 / 美团 / 京东岗位（实时抓取 + 回退数据）
- 岗位列表与详情
- JD 智能解析（关键词 / 能力标签 / 技术理解 / 场景方向 / 难度 / 总结）
- 能力 gap 分析（已匹配能力 / 待补能力 / 优先补齐建议 / 匹配度）
- 高频面试题自动生成（通用产品题 / AI产品专项题 / 岗位定向题）
- AI PM 模拟面试（独立页面 / 文本训练 / LLM 反馈 / 本地兜底）
- LLM 安全接入（后端调用 + 环境变量 + mock fallback）
- 每日自动刷新（24小时）

## 启动

在项目根目录执行：

```bash
python /Users/aiden/Documents/userA/AIPMdropsite/app.py
```

默认地址：
- `http://127.0.0.1:8080`

如果端口被占用：

```bash
PORT=8090 python /Users/aiden/Documents/userA/AIPMdropsite/app.py
```

## 环境变量

1. 复制 `/Users/aiden/Documents/userA/AIPMdropsite/.env.example` 为 `.env.local`
2. 在 `.env.local` 中填写：

```env
LLM_API_KEY=你的真实key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=20
```

说明：
- `LLM_API_KEY`：你的真实模型 key
- `LLM_BASE_URL`：兼容 OpenAI Chat Completions 的服务地址
- `LLM_MODEL`：模型名
- `LLM_TIMEOUT_SECONDS`：后端调用超时秒数

如果 `.env.local` 不填写，项目仍可运行，后端会自动回退到现有 mock / rule-based 逻辑。

## API

- `GET /api/jobs` 岗位列表（支持 `keyword/company/city`）
- `GET /api/jobs/{id}` 岗位详情 + JD 智能解析 + 能力 gap 分析 + 面试准备
- `POST /api/refresh` 手动触发抓取
- `GET /api/status` 任务状态
- `GET /api/progress` 近期日志
- `GET /api/progress/stream` 实时进度流（SSE）

新增 AI 接口：
- `POST /api/jd-parse`
- `POST /api/gap-analysis`
- `POST /api/interview-questions`
- `POST /api/mock-interview/start`
- `POST /api/mock-interview/respond`
- `POST /api/mock-interview/next`

这些接口都会：
- 只在后端读取环境变量里的 API key
- 优先走 LLM
- 失败时自动 fallback 到 mock 结果
- 返回结构化 JSON

## 页面

- 首页：`/`
- 模拟面试页：`/mock-interview`

## 说明

- 不要在前端代码里填写 key。
- LLM 配置读取位置在 `/Users/aiden/Documents/userA/AIPMdropsite/services/llm_service.py`。
- `.env.local` 已加入 `.gitignore`，不会被默认提交。
- 数据库存储在 `/Users/aiden/Documents/userA/AIPMdropsite/data/jobs.db`。
