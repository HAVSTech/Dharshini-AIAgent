# Dharshini AI Agent

Dharshini is a Windows-first personal AI agent: voice in, Gemini reasoning and tool use, actions on the local PC, voice out.

## Current system
- Gemini Live bidirectional audio
- 16 kHz microphone input / 24 kHz speaker output
- Input and output transcription
- Local SQLite memory and action audit log
- Controlled Windows tool architecture
- Safety classifications and confirmation gates
- Local wake-word adapter with push-to-talk fallback

## Setup

```powershell
git clone https://github.com/HAVSTech/Dharshini-AIAgent.git
cd Dharshini-AIAgent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
notepad .env
```

Add your Gemini API key, then:

```powershell
python -m dharshini.main --text "say hello"
python -m dharshini.main --voice
```

## Voice design

The agent uses Gemini Live for real-time audio and function calling. Google documents raw 16-bit PCM at 16 kHz for input and 24 kHz audio output. Live tool calls must be executed by the client and returned with function responses.

The default activation mode is push-to-talk. A custom local “Dharshini” wake-word model can be plugged into the wake layer later; the included openWakeWord package is local and does not require an API key, but its stock models do not contain a custom Dharshini phrase.

## Safety

Dharshini does not expose unrestricted shell execution. Tools are explicitly registered and marked SAFE, CONFIRM, or BLOCKED. File writes, printing, screenshots, clipboard writes, and screen interaction require confirmation by default.

## Planned hardening

- Custom Dharshini wake model
- Windows tray/startup application
- Screen vision loop
- Better printer-specific orientation/paper detection
- Optional local/offline LLM backend
- Plugin/MCP bridge
