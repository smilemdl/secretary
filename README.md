# secretary

A Feishu group chat scheduler bot MVP built with FastAPI, SQLite, APScheduler, and optional OpenAI parsing.

## MVP Scope

- Receive Feishu group chat text events
- Parse common scheduling commands
- Store tasks in SQLite
- Send reminders back to the Feishu chat
- Keep open tasks in a reminder loop until they are completed or cancelled

## Local Run

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and fill in Feishu credentials.
4. Start the server:

```bash
uvicorn app.main:app --reload
```

## Supported Commands

- `@助手 明天下午3点提醒我交水电费`
- `@助手 今天还有什么`
- `@助手 未完成`
- `完成`
- `取消`
- `15分钟后提醒`
- `今晚8点提醒`
- `改到明天9点`
