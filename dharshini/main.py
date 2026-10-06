from __future__ import annotations
import argparse,asyncio,os
from dharshini.agent.live import DharshiniAgent
from dharshini.config import get_settings
from dharshini.memory import MemoryStore
from dharshini.safety import SafetyManager

def main():
    p=argparse.ArgumentParser(description="Dharshini AI Agent")
    p.add_argument("--voice",action="store_true")
    p.add_argument("--text")
    args=p.parse_args()
    settings=get_settings()
    memory=MemoryStore(os.getenv("DHARSHINI_MEMORY_DB","data/dharshini.db"))
    safety=SafetyManager(os.getenv("DHARSHINI_CONFIRM_RISKY","true").lower()!="false")
    agent=DharshiniAgent(settings,memory,safety)
    try:
        if args.text:print(asyncio.run(agent.text(args.text)))
        elif args.voice:asyncio.run(agent.voice())
        else:
            print(f"{settings.name} is installed.")
            print("Use --text for a test or --voice for live voice mode.")
    finally:memory.close()

if __name__=="__main__":main()
