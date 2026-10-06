from __future__ import annotations
import asyncio
from typing import Any
from google import genai
from google.genai import types
from dharshini.config import Settings
from dharshini.tools.registry import TOOLS, as_gemini_tools

class DharshiniLiveAgent:
    """Gemini Live agent with controlled local tool execution."""
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = genai.Client(api_key=settings.api_key)

    async def run_text_test(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.settings.live_model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=self.settings.system_prompt),
        )
        return response.text or ""

    async def run_session(self) -> None:
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.settings.system_prompt,
            tools=[types.Tool(function_declarations=as_gemini_tools())],
        )
        async with self.client.aio.live.connect(model=self.settings.live_model, config=config) as session:
            print(f"{self.settings.name} Live session started.")
            while True:
                await asyncio.sleep(1)
                # Audio transport is intentionally isolated as the next milestone.
                _ = session

    async def handle_tool_call(self, name: str, args: dict[str, Any]) -> str:
        spec = TOOLS.get(name)
        if spec is None:
            raise ValueError(f"Unknown tool: {name}")
        if spec.risk == "CONFIRM":
            raise PermissionError(f"Confirmation required for {name}.")
        if name == "open_app":
            return spec.handler(app=str(args.get("app", "")))
        if name == "open_url":
            return spec.handler(url=str(args.get("url", "")))
        if name == "open_folder":
            return spec.handler(path=str(args.get("path", "")))
        if name == "take_screenshot":
            return spec.handler(path=str(args.get("path", "dharshini_screenshot.png")))
        return spec.handler()
