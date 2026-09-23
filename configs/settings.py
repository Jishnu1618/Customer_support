import os
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

CONFIG_DIR = Path(__file__).parent
BRAND_CONFIG_FILE = CONFIG_DIR / "brand_config.json"


class BrandConfig(BaseModel):
    """
    Configuration model for the Brand identity and voice guidelines.
    """
    brand_name: str = Field(default="TechFlow Solutions", description="Name of the brand")
    industry: str = Field(default="SaaS & Cloud Services", description="Industry domain")
    tone: str = Field(default="Professional, empathetic, and solution-oriented", description="Tone of response")
    support_email: str = Field(default="support@techflow.com", description="Official support email")
    primary_language: str = Field(default="en", description="Default primary language")
    guidelines: list[str] = Field(
        default_factory=lambda: [
            "Be polite, empathetic, and clear.",
            "Acknowledge the customer's problem before presenting a solution.",
            "Never promise features or discounts not officially approved.",
            "Provide actionable step-by-step resolution steps when applicable."
        ],
        description="Key communication rules for replies"
    )

    @classmethod
    def load_from_file(cls, filepath: Path = BRAND_CONFIG_FILE) -> "BrandConfig":
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        return cls()


class Settings(BaseModel):
    """
    Application-wide settings including API keys and LLM parameters.
    """
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # LLM Provider Configuration
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq"))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "groq/compound"))
    llm_judge_model: str = Field(default_factory=lambda: os.getenv("LLM_JUDGE_MODEL", "groq/compound"))
    
    # API Keys (Loaded from environment variables, kept outside version control)
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_api_keys: list[str] = Field(
        default_factory=lambda: [
            k.strip() for k in os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", "")).split(",") if k.strip()
        ]
    )
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    
    # Brand Configuration
    brand: BrandConfig = Field(default_factory=BrandConfig.load_from_file)


settings = Settings()
