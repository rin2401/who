from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import math

from ..database import connect_db, close_db, get_db
from ..search.face_search import search_by_face
from ..config import settings


app = FastAPI(title="Who - Team Directory")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await connect_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


# Mount static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "../../public")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class FaceSearchRequest(BaseModel):
    image_base64: str
    company: Optional[str] = None
    limit: int = 10


class ProfileResponse(BaseModel):
    id: str
    company_slug: str
    name: str
    role: str
    avatar_url: str
    profile_url: str


class FaceSearchResult(BaseModel):
    profile: ProfileResponse
    similarity: float


@app.get("/")
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "../../public/index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Who API - See /docs for API documentation"}


@app.get("/api/profiles")
async def get_profiles(
    q: Optional[str] = Query(None, description="Search query"),
    company: Optional[str] = Query(None, description="Company slug"),
    limit: int = Query(50, ge=1, le=500)
):
    """Search profiles by name or role."""
    db = get_db()
    
    query = {}
    if company:
        query["company_slug"] = company
    
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"role": {"$regex": q, "$options": "i"}}
        ]
    
    cursor = db.profiles.find(query).limit(limit)
    profiles = await cursor.to_list(length=limit)
    
    return {
        "profiles": [
            {
                "id": str(p["_id"]),
                "company_slug": p.get("company_slug", ""),
                "name": p["name"],
                "role": p.get("role", ""),
                "avatar_url": p.get("avatar_url", ""),
                "profile_url": p.get("profile_url", "")
            }
            for p in profiles
        ],
        "count": len(profiles)
    }


@app.post("/api/search/face", response_model=dict)
async def face_search(req: FaceSearchRequest):
    """Find similar faces."""
    try:
        results = await search_by_face(
            image_base64=req.image_base64,
            company=req.company,
            limit=req.limit
        )
        return {"results": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies")
async def get_companies():
    """List all companies in the database."""
    db = get_db()
    companies = await db.profiles.distinct("company_slug")
    return {"companies": companies}


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok"}


def run():
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
