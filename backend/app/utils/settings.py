from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


for dotenv_path in (Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"):
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)


@dataclass(slots=True)
class AppSettings:
    ai_provider: str = "fake"
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None


def get_settings() -> AppSettings:
    return AppSettings(
        ai_provider=os.getenv("EWA_AI_PROVIDER", "fake"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    )
