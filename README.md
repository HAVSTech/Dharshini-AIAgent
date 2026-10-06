# Dharshini AI Agent

Dharshini is a Windows-first personal AI assistant: microphone audio goes to Gemini Live, Gemini can request explicitly registered local tools, the local app executes approved actions, and Gemini speaks the result.

## End-to-end flow

Microphone -> Gemini Live -> Function call -> Local tool -> Function response -> Gemini -> Speaker

Gemini Live is a WebSocket-based, bidirectional API. The current implementation follows Google's documented 16-bit PCM/16 kHz input and native audio output flow, with manual client-side handling of function calls.

## Included now

- Gemini 3.8 Live voice session
- Continuous multi-turn voice session
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
- Brother HL-L2400D-oriented intelligent print workflow
- PDF, Word, and Excel print support
- Per-file page-count and orientation analysis
- 1-page simplex printing
- 2+ page portrait duplex with long-edge binding
- 2+ page landscape duplex with short-edge binding
- Sequential folder printing with queue completion checks
- Printer discovery, default-printer reporting, and status checks

## Printer workflow

Dharshini treats printing as a controlled local action. For a command such as:

```
Print everything in H:\Projects\Local-agent\TestPrint
```

the flow is:

1. Find supported PDF, Word, and Excel files.
2. Sort them by path/name.
3. Analyze the current file independently.
4. Determine page count and dominant orientation.
5. Select printing mode:
   - 1 page -> simplex
   - 2+ portrait pages -> duplex long-edge
   - 2+ landscape pages -> duplex short-edge
6. Configure the Windows printer settings through its DEVMODE.
7. Print only that file.
8. Wait for its print job to leave the queue.
9. Move to the next file.
10. Report the per-file result.

The default printer is used unless a printer name is explicitly supplied.

### Windows printer prerequisites

Install the Python dependencies:

```cmd
pip install -r requirements.txt
```

For PDF printing, install **SumatraPDF manually** (the earlier automatic downloader was intentionally not retained because antivirus blocked it) and set:

```env
DHARSHINI_SUMATRA_PATH=C:\Path\To\SumatraPDF.exe
```

For Word/Excel printing, Microsoft Word and/or Excel must be installed on the Windows machine.

Dharshini does not download printer executables automatically.

## Safety boundary

Dharshini does not expose arbitrary shell execution. Windows application launching is allow-listed, URLs are restricted to HTTP/HTTPS, and screenshot capture requires confirmation by default.

Actual printing is also a confirmation-required action. Dharshini can safely report printer status and inspect the intended print workflow, but a print operation must be explicitly approved before files are sent to the printer.

The model does not directly control Windows. It asks the local application to execute a registered function; the application returns the result to Gemini.

## Setup on Windows

```cmd
git clone https://github.com/HAVSTech/Dharshini-AIAgent.git
cd Dharshini-AIAgent
py -3.11 -m venv .venv
.\\.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Put your Gemini API key in .env.

Run the local check:

```cmd
python -m dharshini.main --doctor
```

Test text mode:

```cmd
python -m dharshini.main --text "Introduce yourself"
```

Start voice mode:

```cmd
python -m dharshini.main --voice
```

Voice input is sent as raw 16-bit PCM at 16 kHz in 100 ms blocks, matching the Live API audio format.

## Current activation model

The current voice mode is always-listening while the process is running. A custom spoken "Dharshini" wake-word model and a Windows tray/hotkey shell are not claimed as complete because they require a local Windows audio/input test and, for a true custom wake phrase, a trained wake-word model.

## Verification

The repository contains tests/test_core.py for memory, safety, printer registration, and tool-registry checks. The final microphone, speaker, Windows application launch, printer driver, Office COM, SumatraPDF, and Gemini API paths still need to be exercised on the target Windows machine because this development environment cannot access the user's local hardware.

## Gemini availability handling

Text mode disables automatic function calling because text prompts do not need local tool execution. Transient Gemini HTTP failures such as 429/5xx are retried with exponential backoff before returning a friendly error. Voice mode keeps function calling enabled for the local tool router.
