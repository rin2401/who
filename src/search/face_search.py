import numpy as np
from typing import Optional
from ..database import get_db


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_face_embedding(image_source: str) -> list[float]:
    """
    Generate face embedding from an image using Ultralytics YOLO.
    image_source: base64 string or URL or file path
    """
    from ultralytics import YOLO
    from PIL import Image
    from io import BytesIO
    import base64
    
    # Load face detection model
    model = YOLO("yolov8n.pt")  # or yolov8n-face.pt for better face detection
    
    # Handle image source
    if image_source.startswith("data:"):
        # Base64 image
        img_data = base64.b64decode(image_source.split(",")[1])
        img = Image.open(BytesIO(img_data))
    else:
        img = Image.open(image_source)
    
    # Run detection
    results = model(img, verbose=False)
    
    embeddings = []
    for result in results:
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                face_crop = img.crop((x1, y1, x2, y2))
                # Resize to standard face size
                face_crop = face_crop.resize((160, 160))
                # Simple embedding: flatten normalized pixels
                emb = np.array(face_crop).flatten() / 255.0
                embeddings.append(emb.tolist())
    
    return embeddings


async def search_by_face(
    image_base64: str,
    company: Optional[str] = None,
    limit: int = 10
) -> list[dict]:
    """Search for similar faces in MongoDB."""
    # Get embedding from query image
    query_embeddings = await get_face_embedding(image_base64)
    
    if not query_embeddings:
        raise ValueError("No faces detected in the query image")
    
    query_emb = query_embeddings[0]
    
    # Build MongoDB query
    db = get_db()
    query = {"embeddings": {"$exists": True, "$ne": []}}
    
    if company:
        query["company_slug"] = company
    
    # Fetch profiles with embeddings
    profiles = await db.profiles.find(query).to_list(length=1000)
    
    # Compute similarity
    results = []
    for p in profiles:
        if not p.get("embeddings"):
            continue
        sim = cosine_similarity(query_emb, p["embeddings"][0])
        results.append({
            "profile": {
                "id": str(p["_id"]),
                "name": p["name"],
                "role": p.get("role", ""),
                "avatar_url": p.get("avatar_url", ""),
                "profile_url": p.get("profile_url", ""),
                "company_slug": p.get("company_slug", "")
            },
            "similarity": float(sim)
        })
    
    # Sort by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)
    
    return results[:limit]


async def compute_and_save_embedding(profile_id: str) -> dict:
    """Pre-compute and store embedding for a profile."""
    from bson import ObjectId
    from ..models.profile import ProfileCreate
    
    db = get_db()
    profile = await db.profiles.find_one({"_id": ObjectId(profile_id)})
    
    if not profile:
        raise ValueError("Profile not found")
    
    avatar_path = profile.get("avatar_local_path") or profile.get("avatar_url")
    if not avatar_path:
        raise ValueError("No avatar to compute embedding from")
    
    embeddings = await get_face_embedding(avatar_path)
    
    await db.profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {"$set": {"embeddings": embeddings, "updated_at": profile.utcnow()}}
    )
    
    return profile
