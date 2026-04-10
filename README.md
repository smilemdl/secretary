# secretary

A personal scheduler web MVP built with FastAPI, SQLite, APScheduler, and a configurable OpenAI-compatible LLM backend.

## MVP Scope

- Serve a simple text-based web UI at `/`
- Parse common scheduling commands
- Store tasks in SQLite
- Surface current reminders back to the page
- Keep open tasks in a reminder loop until they are completed or cancelled

## Local Run

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and fill in runtime configuration.
4. Start the server:

```bash
uvicorn app.main:app --reload
```

## Supported Commands

- `明天下午3点提醒我交水电费`
- `今天还有什么`
- `未完成`
- `完成`
- `取消`
- `15分钟后提醒`
- `今晚8点提醒`
- `改到明天9点`

## LLM Backend

The app uses rule parsing first, then falls back to a configurable OpenAI-compatible backend.

Example DashScope-compatible configuration:

```env
LLM_API_KEY=your-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-flash-2026-02-23
LLM_ENABLE_THINKING=false
```

## Deployment Notes

- The app service listens on `127.0.0.1:8001`
- The web UI is served at `/`
- Suggested deployment files are under `deploy/systemd` and `deploy/nginx`
