# Who - Team Directory

Crawl LinkedIn employee profiles, search by name/role, and find people by face.

## Setup

```bash
# Install dependencies
uv sync

# Copy and edit env
cp .env.example .env
```

## Getting LinkedIn Cookies (Recommended)

1. Open Chrome/Edge on your computer
2. Go to linkedin.com and login
3. Press F12 → Application tab → Cookies → linkedin.com
4. Copy the `li_at` cookie value and `JSESSIONID` cookie value
5. Create `linkedin_cookies.json`:

```json
[
  {"name": "li_at", "value": "YOUR_LI_AT_VALUE", "domain": ".linkedin.com", "path": "/"},
  {"name": "JSESSIONID", "value": "YOUR_JSESSIONID_VALUE", "domain": ".linkedin.com", "path": "/"}
]
```

## Run

```bash
# Crawl profiles (uses cookies automatically)
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
