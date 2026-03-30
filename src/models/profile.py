from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Profile(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    company_slug: str
    name: str
    role: str = ""
    avatar_url: str = ""
    profile_url: str
    avatar_local_path: str = ""
    embeddings: list[float] = []
    linkedin_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ProfileCreate(BaseModel):
    company_slug: str
    name: str
    role: str = ""
    avatar_url: str = ""
    profile_url: str


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
