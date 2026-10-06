from __future__ import annotations
import importlib, os, platform

def main()->int:
    print("Dharshini system check")
    print("OS:", platform.platform())
    if os.name!="nt":
        print("FAIL: Windows is required for local PC control.")
        return 1
    failed=False
    for name in ("google.genai","sounddevice","numpy","psutil","PIL"):
        try: importlib.import_module(name); print("OK  "+name)
        except Exception as exc: print("FAIL "+name+": "+str(exc)); failed=True
    print("OK  GEMINI_API_KEY is set" if os.getenv("GEMINI_API_KEY","").strip() else "WARN GEMINI_API_KEY is not set")
    return 1 if failed else 0

if __name__=="__main__": raise SystemExit(main())
