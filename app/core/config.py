from pydantic_settings import BaseSettings,SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    GCP_PROJECT_ID:str
    BQ_DATASET:str
    
    #llm models
    SQL_MODEL:str
    ROUTER_MODEL:str
    FORECAST_MODEL:str
    SYNTHESIS_MODEL:str

    #safety and limits
    MAX_SQL_RETRIES:int
    MAX_ROWS_RETURNED:int

    #apikey
    # OPENAI_API_KEY:str
    OPENROUTER_API_KEY:str

    #obeservability
    PHOENIX_ENABLED:bool
    PHOENIX_COLLECTOR_ENDPOINT:str

    MONGO_URI:str
    MONGO_DB_NAME:str
    TOOLBOX_URL:str = "http://127.0.0.1:5000"



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

@lru_cache
def get_settings()->Settings:
    """Cached singleton accessor — import this, never instantiate Settings()."""
    return Settings()