import asyncio
import re
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from ..config import settings
from ..database import get_db
from ..models.profile import ProfileCreate


async def login_and_scroll(page, company_slug: str) -> list[dict[str, Any]]:
    """Login to LinkedIn and scroll through the people page."""
    print("🔐 Logging into LinkedIn...")
    
    await page.goto("https://www.linkedin.com/login", wait_until="networkidle")
    await page.fill("#username", settings.linkedin_email)
    await page.fill("#password", settings.linkedin_password)
    await page.click('.btn__primary--large[type="submit"]')
    
    try:
        await page.wait_for_url("**/feed/**", timeout=30000)
        print("✅ Logged in successfully")
    except Exception:
        print("⚠️ Login may have failed, continuing anyway...")
    
    # Navigate to company people page
    url = f"https://www.linkedin.com/company/{company_slug}/people/"
    print(f"📜 Crawling: {url}")
    await page.goto(url, wait_until="networkidle")
    
    # Wait for people list
    try:
        await page.wait_for_selector(".org-people-profile-card", timeout=10000)
    except Exception:
        print("⚠️ People list not found, trying alternate selectors...")
    
    profiles = []
    last_height = 0
    page_count = 0
    
    while page_count < settings.max_scroll_pages:
        # Extract profiles from current view
        page_profiles = await page.evaluate("""() => {
            const items = document.querySelectorAll('.org-people-profile-card');
            return Array.from(items).map(item => {
                const nameEl = item.querySelector('.org-people-profile-card__profile-title');
                const roleEl = item.querySelector('.artdeco-entity-lockup__subtitle');
                const avatarEl = item.querySelector('.presence-entity__image') || item.querySelector('img');
                const linkEl = item.querySelector('a.app-aware-link');
                
                return {
                    name: nameEl?.textContent?.trim() || '',
                    role: roleEl?.textContent?.trim() || '',
                    avatarUrl: avatarEl?.src || '',
                    profileUrl: linkEl?.href || ''
                };
            }).filter(p => p.name);
        }""")
        
        for p in page_profiles:
            if not any(existing["profileUrl"] == p["profileUrl"] for existing in profiles):
                profiles.append(p)
        
        print(f"  Page {page_count + 1}: {len(page_profiles)} profiles (total: {len(profiles)})")
        
        # Scroll down
        last_height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(settings.scroll_delay_ms / 1000)
        
        # Check if we've reached the bottom
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            # Try to click "Show more" button
            try:
                show_more = page.locator('button[aria-label="See more profiles"]')
                if await show_more.is_visible():
                    await show_more.click()
                    await asyncio.sleep(settings.scroll_delay_ms / 1000)
                else:
                    break
            except Exception:
                break
        
        page_count += 1
    
    return profiles


async def save_profiles(profiles: list[dict[str, Any]], company_slug: str) -> int:
    """Save profiles to MongoDB."""
    db = get_db()
    collection = db.profiles
    
    count = 0
    for p in profiles:
        profile_data = ProfileCreate(
            company_slug=company_slug,
            name=p["name"],
            role=p.get("role", ""),
            avatar_url=p.get("avatarUrl", ""),
            profile_url=p["profileUrl"]
        )
        
        # Upsert
        result = await collection.update_one(
            {"profile_url": profile_data.profile_url},
            {"$set": profile_data.model_dump()}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            count += 1
    
    return count


async def crawl_company(company_slug: str) -> list[dict[str, Any]]:
    """Main crawler function."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            profiles = await login_and_scroll(page, company_slug)
            count = await save_profiles(profiles, company_slug)
            print(f"\n🎉 Done! Saved {count} profiles from {company_slug}")
            return profiles
        finally:
            await browser.close()
