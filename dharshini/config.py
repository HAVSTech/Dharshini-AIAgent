from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    api_key: str
    live_model: str
    name: str
    system_prompt: str

def get_settings() -> Settings:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Copy .env.example to .env and add your API key.")
    return Settings(
        api_key=api_key,
        live_model=os.getenv("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-preview").strip(),
        name=os.getenv("DHARSHINI_NAME", "Dharshini").strip() or "Dharshini",
        system_prompt=os.getenv("DHARSHINI_SYSTEM_PROMPT", "You are Dharshini, a helpful Windows desktop AI assistant.").strip(),
    )
