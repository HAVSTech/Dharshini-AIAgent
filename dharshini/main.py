from __future__ import annotations

import argparse
import asyncio
import os

from dharshini.agent.live import DharshiniAgent
from dharshini.config import get_settings
from dharshini.memory import MemoryStore
from dharshini.safety import SafetyManager


def main():
    p = argparse.ArgumentParser(description="Dharshini AI Agent")
    p.add_argument("--voice", action="store_true", help="Start Gemini Live voice mode.")
    p.add_argument("--text", help="Send one text prompt to Gemini.")
    p.add_argument("--tray", action="store_true", help="Start the Windows system tray.")
    p.add_argument(
        "--install-startup",
        action="store_true",
        help="Start Dharshini automatically with Windows.",
    )
    p.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="Remove Dharshini from Windows startup.",
    )
    p.add_argument("--doctor", action="store_true", help="Run local dependency checks.")
    args = p.parse_args()

    if args.doctor:
        from scripts.doctor import main as doctor
        raise SystemExit(doctor())

    if args.install_startup or args.uninstall_startup:
        from dharshini.startup import install_startup, uninstall_startup

        print(
            install_startup()
            if args.install_startup
            else uninstall_startup()
        )
        return

    settings = get_settings()
    memory = MemoryStore(os.getenv("DHARSHINI_MEMORY_DB", "data/dharshini.db"))
    safety = SafetyManager(
        os.getenv("DHARSHINI_CONFIRM_RISKY", "true").lower() != "false"
    )
    agent = DharshiniAgent(settings, memory, safety)

    try:
        if args.text:
            print(asyncio.run(agent.text(args.text)))
        elif args.voice:
            asyncio.run(agent.voice())
        elif args.tray:
            from dharshini.tray import run_tray

            run_tray(agent)
        else:
            print(f"{settings.name} is installed.")
            print(
                'Use --doctor, --text "hello", --voice, or --tray.'
            )
    finally:
        memory.close()


if __name__ == "__main__":
    main()
