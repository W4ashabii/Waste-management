from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MOCK_MODE: bool = True
    
    class Config:
        env_file = ".env"


settings = Settings()
