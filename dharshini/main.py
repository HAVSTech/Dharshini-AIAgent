from __future__ import annotations
import asyncio
from dharshini.agent.live import DharshiniLiveAgent
from dharshini.config import get_settings

def main() -> None:
    settings = get_settings()
    agent = DharshiniLiveAgent(settings)
    print(f"Starting {settings.name}...")
    print("Testing the Gemini connection.")
    async def run() -> None:
        result = await agent.run_text_test("Reply with exactly: Dharshini is online.")
        print(result.strip())
        print("Dharshini foundation is ready. Gemini Live audio transport is the next runtime layer.")
    asyncio.run(run())

if __name__ == "__main__":
    main()
