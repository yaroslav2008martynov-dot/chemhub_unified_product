from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://chemhub:chemhub@postgres:5432/chemhub"
    ADMIN_PASSWORD: str = "Ch3mHub!Admin#2026"
    MAX_UPLOAD_MB: int = 100
    PUBLIC_BASE_URL: str = "http://localhost:3000"
    OPENAI_API_KEY: str = ""

settings = Settings()
