from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str = "hope-mvp/0.1 by Horror-Subject-4980"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 1000
    
    class Config:
        env_file = ".env"

settings = Settings()
