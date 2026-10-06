from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

CURRENT_LIVE_MODEL = "gemini-3.8-live"
LEGACY_LIVE_MODELS = {
    "gemini-live-2.5-flash-preview",
    "gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini-3.1-flash-live-preview",
}

@dataclass(frozen=True)
class Settings:
    api_key: str
    live_model: str
    name: str
    system_prompt: str

def get_settings():
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Copy .env.example to .env and add your key.")

    configured=os.getenv("GEMINI_LIVE_MODEL","").strip()
    live_model=CURRENT_LIVE_MODEL if not configured or configured in LEGACY_LIVE_MODELS else configured

    if configured in LEGACY_LIVE_MODELS:
        print(
            f"[Dharshini] Legacy Live model '{configured}' detected; "
            f"using '{CURRENT_LIVE_MODEL}' instead.",
            flush=True,
        )

    return Settings(
        api_key=key,
        live_model=live_model,
        name=os.getenv("DHARSHINI_NAME","Dharshini").strip() or "Dharshini",
        system_prompt=os.getenv(
            "DHARSHINI_SYSTEM_PROMPT",
            "You are Dharshini, a capable Windows desktop AI assistant.",
        ).strip(),
    )
