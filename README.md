# Who - Team Directory

Crawl LinkedIn employee profiles, search by name/role, and find people by face.

## Setup

```bash
# Install dependencies
uv sync

# Copy and edit env
cp .env.example .env
# Edit .env with your LinkedIn credentials and MongoDB URI

# Run crawler
uv run python src/crawler/main.py --company zalo

# Start server
uv run uvicorn src.server.main:app --reload
# → http://localhost:8000
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profiles?q=keyword&company=zalo` | Search by name/role |
| POST | `/api/search/face` | Find similar faces |
| GET | `/api/companies` | List all companies |

## Tech Stack

- **Crawler**: Playwright (Python)
- **Database**: MongoDB + Motor (async)
- **Server**: FastAPI
- **Face Search**: Ultralytics YOLO + cosine similarity
- **Frontend**: Vanilla HTML/JS
