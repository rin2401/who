from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "who"
    
    linkedin_email: str = ""
    linkedin_password: str = ""
    
    max_scroll_pages: int = 50
    scroll_delay_ms: int = 2000
    
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
