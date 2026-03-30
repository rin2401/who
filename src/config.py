from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "who"
    
    # LinkedIn auth - either cookies OR email/password
    linkedin_cookies_file: str = "linkedin_cookies.json"
    linkedin_email: str = ""
    linkedin_password: str = ""
    
    max_scroll_pages: int = 50
    scroll_delay_ms: int = 2000
    
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
