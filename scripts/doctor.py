from __future__ import annotations

import importlib
import os
import platform


def main() -> int:
    print("Dharshini system check")
    print("OS:", platform.platform())

    if os.name != "nt":
        print("FAIL: Windows is required for local PC control.")
        return 1

    failed = False
    for name in (
        "google.genai",
        "sounddevice",
        "numpy",
        "psutil",
        "PIL",
        "pypdf",
        "win32print",
        "win32com.client",
        "pystray",
        "openwakeword",
    ):
        try:
            importlib.import_module(name)
            print("OK  " + name)
        except Exception as exc:
            print("FAIL " + name + ": " + str(exc))
            failed = True

    wake_path = os.getenv(
        "DHARSHINI_WAKE_MODEL_PATH", "models/dharshini.tflite"
    ).strip()
    if os.path.isfile(wake_path):
        print("OK  Wake-word model:", wake_path)
    else:
        print(
            "WARN Wake-word model not found:",
            wake_path,
            "-> voice mode will fall back to always-listening.",
        )

    sumatra = os.getenv("DHARSHINI_SUMATRA_PATH", "").strip()
    if sumatra and os.path.isfile(sumatra):
        print("OK  SumatraPDF:", sumatra)
    elif sumatra:
        print("WARN SumatraPDF path does not exist:", sumatra)
    else:
        candidates = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
            r"C:\Tools\SumatraPDF\SumatraPDF.exe",
        ]
        found = next((p for p in candidates if os.path.isfile(p)), None)
        if found:
            print("OK  SumatraPDF:", found)
        else:
            print("WARN SumatraPDF not found; PDF printing needs a manual installation.")

    try:
        import win32print

        printer = win32print.GetDefaultPrinter()
        print("OK  Default printer:", printer)
        if not printer:
            print("WARN No default printer is configured.")
    except Exception as exc:
        print("FAIL Printer access:", str(exc))
        failed = True

    print(
        "OK  GEMINI_API_KEY is set"
        if os.getenv("GEMINI_API_KEY", "").strip()
        else "WARN GEMINI_API_KEY is not set"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
