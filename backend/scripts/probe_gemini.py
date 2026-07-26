"""Probe which Gemini models work with the configured API key."""
from __future__ import annotations

from app.config import get_settings
import google.generativeai as genai


def main() -> None:
    s = get_settings()
    genai.configure(api_key=s.google_api_key)
    print("key_len", len(s.google_api_key or ""))
    print("configured_model", s.gemini_model)

    print("\n--- list_models (generateContent) ---")
    try:
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                print(m.name)
    except Exception as e:
        print("list fail:", e)

    models = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-1.5-pro",
        "gemini-pro",
    ]
    print("\n--- probe generate_content ---")
    for model in models:
        try:
            m = genai.GenerativeModel(model)
            r = m.generate_content("Reply with exactly: OK")
            text = (r.text or "").strip()[:40]
            print("WORKS", model, "->", text)
        except Exception as e:
            msg = str(e).replace("\n", " ")[:160]
            print("FAIL ", model, "->", msg)


if __name__ == "__main__":
    main()
