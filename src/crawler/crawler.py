import asyncio
from typing import Any

from playwright.async_api import async_playwright

from ..config import settings
from ..database import get_db
from ..models.profile import ProfileCreate


async def login_and_scroll(page, company_slug: str) -> list[dict[str, Any]]:
    """Login to LinkedIn and scroll through the people page."""
    if not settings.linkedin_email or not settings.linkedin_password:
        raise ValueError(
            "Missing LinkedIn credentials! Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env\n"
            "Example: cp .env.example .env && nano .env"
        )
    
    print("🔐 Logging into LinkedIn...")
    
    # Use mobile LinkedIn which has simpler anti-bot
    await page.goto(
        "https://www.linkedin.com/login",
        wait_until="commit",
        timeout=30000
    )
    await page.wait_for_timeout(3000)
    
    # Try alternative selectors for login form
    email_filled = False
    for email_sel in ["input[name='session_key']", "#username", "input[type='email']"]:
        try:
            await page.fill(email_sel, settings.linkedin_email, timeout=3000)
            email_filled = True
            print(f"✅ Filled email with selector: {email_sel}")
            break
        except Exception:
            continue
    
    if not email_filled:
        raise ValueError("Could not find email input field")
    
    for pass_sel in ["input[name='session_password']", "#password"]:
        try:
            await page.fill(pass_sel, settings.linkedin_password, timeout=3000)
            print(f"✅ Filled password with selector: {pass_sel}")
            break
        except Exception:
            continue
    
    await page.click("button[type='submit']", timeout=5000)
    await page.wait_for_timeout(5000)
    
    # Navigate to company people page
    url = f"https://www.linkedin.com/company/{company_slug}/people/"
    print(f"📜 Crawling: {url}")
    await page.goto(url, wait_until="commit", timeout=30000)
    await page.wait_for_timeout(3000)
    
    profiles = []
    page_count = 0
    
    while page_count < settings.max_scroll_pages:
        # Extract profiles - try multiple selectors for different LinkedIn UIs
        page_profiles = await page.evaluate("""() => {
            // Try multiple selectors for people cards
            let items = document.querySelectorAll('.org-people-profile-card');
            if (items.length === 0) {
                items = document.querySelectorAll('.mn-person-card');
            }
            if (items.length === 0) {
                items = document.querySelectorAll('[data-anonymize="people"]');
            }
            if (items.length === 0) {
                items = document.querySelectorAll('.scaffold-finite-scroll .entity-result');
            }
            
            return Array.from(items).map(item => {
                // Try multiple name selectors
                let name = '';
                for (const sel of [
                    '.org-people-profile-card__profile-title',
                    '.mn-person-card__name',
                    '.entity-result__title-text a',
                    '[data-anonymize="people-name"]',
                    '.actor-name'
                ]) {
                    const el = item.querySelector(sel);
                    if (el) { name = el.textContent?.trim() || ''; break; }
                }
                
                // Try multiple role selectors  
                let role = '';
                for (const sel of [
                    '.artdeco-entity-lockup__subtitle',
                    '.mn-person-card__occupation',
                    '.entity-result__primary-subtitle',
                    '[data-anonymize="people-title"]'
                ]) {
                    const el = item.querySelector(sel);
                    if (el) { role = el.textContent?.trim() || ''; break; }
                }
                
                // Avatar
                let avatarUrl = '';
                for (const sel of [
                    '.presence-entity__image',
                    '.mn-person-card__avatar img',
                    '.entity-result__avatar img',
                    'img[src*="linkedin"]'
                ]) {
                    const el = item.querySelector(sel);
                    if (el) { avatarUrl = el.src || ''; break; }
                }
                
                // Link
                let profileUrl = '';
                for (const sel of [
                    'a.app-aware-link',
                    '.mn-person-card__link a',
                    '.entity-result__title a',
                    'a[href*="/in/"]'
                ]) {
                    const el = item.querySelector(sel);
                    if (el) { profileUrl = el.href || ''; break; }
                }
                
                return { name, role, avatarUrl, profileUrl };
            }).filter(p => p.name);
        }""")
        
        if len(page_profiles) > 0:
            print(f"✅ Found {len(page_profiles)} profiles on this page")
        
        for p in page_profiles:
            if not any(existing["profileUrl"] == p["profileUrl"] for existing in profiles):
                profiles.append(p)
        
        print(f"  Page {page_count + 1}: {len(page_profiles)} profiles (total: {len(profiles)})")
        
        # Scroll down
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(settings.scroll_delay_ms / 1000)
        
        # Check if we've reached the bottom
        new_height = await page.evaluate("document.body.scrollHeight")
        old_height = await page.evaluate("document.body.scrollHeight")
        if new_height == old_height:
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
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
            locale="en-US",
        )
        page = await context.new_page()
        
        try:
            profiles = await login_and_scroll(page, company_slug)
            count = await save_profiles(profiles, company_slug)
            print(f"\n🎉 Done! Saved {count} profiles from {company_slug}")
            return profiles
        finally:
            await browser.close()
