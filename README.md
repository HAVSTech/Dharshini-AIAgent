# Dharshini AI Agent

Dharshini is a Windows-first personal AI assistant: microphone audio goes to Gemini Live, Gemini can request explicitly registered local tools, the local app executes approved actions, and Gemini speaks the result.

## End-to-end flow

Microphone -> local wake word -> Gemini Live -> Function call -> Local tool -> Function response -> Gemini -> Speaker

When the custom wake-word model is not installed, voice mode safely falls back to the previous always-listening behavior.

## Included now

- Gemini 3.8 Live voice session
- Continuous multi-turn voice session
- Local custom "Dharshini" wake-word runtime using openWakeWord
- Windows system-tray application
- Start-with-Windows registration
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
- Per-file page-count, orientation, and paper-size analysis
- Printer paper capability discovery through the Windows driver
- Automatic paper-size selection against supported printer forms
- 1-page simplex printing
- 2+ page portrait duplex with long-edge binding
- 2+ page landscape duplex with short-edge binding
- Sequential folder printing with queue/error checks
- Limited retry handling for transient printer failures
- Printer discovery, default-printer reporting, capability and status checks

## Custom wake word

Wake-word detection runs locally and does not send audio to Gemini while waiting.

Place a custom openWakeWord-compatible model at:

```
models/dharshini.tflite
```

Configuration:

```env
DHARSHINI_WAKE_WORD_ENABLED=true
DHARSHINI_WAKE_MODEL_PATH=models/dharshini.tflite
DHARSHINI_WAKE_THRESHOLD=0.5
```

If the model is missing, Dharshini prints a warning and falls back to always-listening mode instead of failing.

openWakeWord supports custom target phrases and local 16 kHz PCM inference. Its official project documents both deployment and custom-model training: https://github.com/dscripka/openWakeWord

## System tray

Start the tray:

```cmd
python -m dharshini.main --tray
```

The tray provides:

- Start Voice
- Stop request
- Start with Windows
- Exit

You can also install or remove Windows startup from CMD:

```cmd
python -m dharshini.main --install-startup
python -m dharshini.main --uninstall-startup
```

Startup is registered only for the current Windows user through the normal Windows Run key.

## Printer workflow

Dharshini treats printing as a controlled local action.

For:

```
Print everything in H:\Projects\Local-agent\TestPrint
```

the flow is:

1. Find supported PDF, Word, and Excel files.
2. Sort them by path/name.
3. Analyze the current file independently.
4. Determine rendered page count and dominant orientation.
5. Detect the document's physical page size from the rendered page.
6. Ask the Windows printer driver which paper forms it supports.
7. Select the closest supported paper form.
8. Select printing mode:
   - 1 page -> simplex
   - 2+ portrait pages -> duplex long-edge
   - 2+ landscape pages -> duplex short-edge
9. Configure the printer's DEVMODE.
10. Print only that file.
11. Monitor the printer queue and driver status.
12. Retry transient failures up to three attempts.
13. Move to the next file.
14. Report successes and failures.

Windows exposes printer paper IDs, names, and dimensions through DeviceCapabilities, while DEVMODE exposes paper size, orientation, and duplex settings. The implementation uses those local Windows APIs rather than hard-coding a single paper size. https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-devicecapabilitiesw

### Printer prerequisites

Install dependencies:

```cmd
pip install -r requirements.txt
```

For PDF printing, install **SumatraPDF manually** and set:

```env
DHARSHINI_SUMATRA_PATH=C:\Path\To\SumatraPDF.exe
```

For Word/Excel printing, Microsoft Word and/or Excel must be installed.

Dharshini does not download printer executables automatically.

## Safety boundary

Dharshini does not expose arbitrary shell execution. Windows application launching is allow-listed, URLs are restricted to HTTP/HTTPS, and screenshot capture requires confirmation.

Actual printing is also a confirmation-required action.

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

Run:

```cmd
python -m dharshini.main --doctor
```

Voice mode:

```cmd
python -m dharshini.main --voice
```

Tray mode:

```cmd
python -m dharshini.main --tray
```

Text mode:

```cmd
python -m dharshini.main --text "Introduce yourself"
```

## Verification

The repository contains tests/test_core.py for memory, safety, printer registration, and tool-registry checks. The final microphone, speaker, wake-word model, Windows application launch, printer driver, Office COM, SumatraPDF, and Gemini API paths still need to be exercised on the target Windows machine because this development environment cannot access the user's local hardware.

## Gemini availability handling

Text mode disables automatic function calling because text prompts do not need local tool execution. Transient Gemini HTTP failures such as 429/5xx are retried with exponential backoff before returning a friendly error. Voice mode keeps function calling enabled for the local tool router.
