# Dharshini AI Agent

Dharshini is a Windows-first personal AI assistant: microphone audio goes to Gemini Live, Gemini can request explicitly registered local tools, the local app executes approved actions, and Gemini speaks the result.

## End-to-end flow

Microphone -> Gemini Live -> Function call -> Local tool -> Function response -> Gemini -> Speaker

Gemini Live is a WebSocket-based, bidirectional API. The current implementation follows Google's documented 16-bit PCM/16 kHz input and native audio output flow, with manual client-side handling of function calls.

## Included now

- Gemini 3.8 Live voice session
- 16 kHz mono microphone streaming and 24 kHz speaker playback
- Input and output transcription
- Function calling into a local, allow-listed Windows tool registry
- Open Notepad, Calculator, Paint, Explorer or VS Code
- Open HTTP/HTTPS URLs
- Open an existing folder
- Read CPU/RAM status
- Desktop screenshot with confirmation
- SQLite memory and action audit log
- Risk confirmation for non-SAFE tools
- Text-mode Gemini test
- Local doctor command and automated core tests

## Safety boundary

Dharshini does not expose arbitrary shell execution. Windows application launching is allow-listed, URLs are restricted to HTTP/HTTPS, and screenshot capture requires confirmation by default.

The model does not directly control Windows. It asks the local application to execute a registered function; the application returns the result to Gemini.

## Setup on Windows

```powershell
git clone https://github.com/HAVSTech/Dharshini-AIAgent.git
cd Dharshini-AIAgent
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Put your Gemini API key in .env.

Run the local check:

```powershell
python -m dharshini.main --doctor
```

Test text mode:

```powershell
python -m dharshini.main --text "Introduce yourself"
```

Start voice mode:

```powershell
python -m dharshini.main --voice
```

Voice input is sent as raw 16-bit PCM at 16 kHz in 100 ms blocks, matching the Live API audio format.

## Current activation model

The current voice mode is always-listening while the process is running. A custom spoken "Dharshini" wake-word model and a Windows tray/hotkey shell are not claimed as complete because they require a local Windows audio/input test and, for a true custom wake phrase, a trained wake-word model.

## Verification

The repository contains tests/test_core.py for memory, safety, and tool-registry checks. GitHub Actions can run those checks automatically. The final microphone, speaker, Windows application launch, and Gemini API path still need to be exercised on the target Windows machine because this development environment cannot access the user's audio devices.

## Roadmap after first successful run

- True "Dharshini" custom wake word
- Windows tray application and startup
- Screen vision on demand
- Printer-specific workflow for the Brother HL-L2400D
- More narrowly scoped Windows controls
- Session reconnect/extension handling for long-running assistant sessions


## Gemini availability handling

Text mode disables automatic function calling because text prompts do not need local tool execution. Transient Gemini HTTP failures such as 429/5xx are retried with exponential backoff before returning a friendly error. Voice mode keeps function calling enabled for the local tool router.
