# Dharshini AI Agent

Dharshini is a Windows-first voice AI agent designed to act like a personal computer assistant.

## Current architecture
- Voice/AI: Google Gemini Live API
- Runtime: Python 3.11+
- Windows control: controlled local tools
- Safety: destructive/system-changing tools require confirmation
- Configuration: .env

## V1 capabilities
- Gemini connection foundation
- Controlled Windows application launching
- Folder and URL opening
- Basic system information
- Desktop screenshot tool
- Explicit tool allow-list and risk classification

## Setup
1. Install Python 3.11+.
2. Clone this repository.
3. Run:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
4. Add your Gemini API key to .env.
5. Run:
   ```powershell
   python -m dharshini.main
   ```

## Safety
Dharshini does not expose arbitrary PowerShell/CMD execution to the model. Tools are allow-listed and classified SAFE, CONFIRM, or BLOCKED.

## Planned milestones
1. Gemini Live voice transport
2. Wake word: Dharshini
3. Browser automation with Playwright
4. Screen vision and mouse/keyboard control
5. Printing automation
6. Git/GitHub developer tools
7. Windows tray app and startup
8. Long-term memory
