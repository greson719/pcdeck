#!/usr/bin/env python3
"""
Hydrogen Frontier AI Client - Strict Gemini 4 Architecture.
Allowed Models: gemini-4-hydrogen, gemini-4-argon, gemini-4-carbon.
No Gemini 2.5 or legacy fallbacks permitted.
"""
import sys
import os
import json
import argparse
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry
except ImportError:
    requests = None

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_MODELS = [
    ("gemini-4-hydrogen", True, 45),
    ("gemini-4-argon", True, 45),
    ("gemini-4-carbon", True, 45),
]

def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        break
    return key or ""

def get_resilient_session() -> "requests.Session":
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def query_model(session: "requests.Session", model: str, prompt: str, api_key: str, system_prompt: str = "", timeout: int = 45) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload_dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.0
        }
    }
    
    if system_prompt:
        payload_dict["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PCDeck-Hydrogen/3.0"
    }

    resp = session.post(url, json=payload_dict, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
        
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidate response returned from model {model}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()

def run_prompt(prompt: str, system_prompt: str = "", preferred_model: str = "") -> str:
    api_key = get_api_key()
    if not api_key:
        return "ERROR: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment or .env file."

    if not requests:
        return "ERROR: Python 'requests' package not installed."

    session = get_resilient_session()

    models = list(ALLOWED_MODELS)
    if preferred_model:
        if preferred_model not in [m[0] for m in ALLOWED_MODELS]:
            return f"ERROR: Model '{preferred_model}' is forbidden. Only hydrogen, argon, or carbon are permitted."
        models = [m for m in models if m[0] == preferred_model] + [m for m in models if m[0] != preferred_model]

    last_error = ""

    for model_name, is_high, timeout_sec in models:
        try:
            print(f"[Hydrogen Router] Querying {model_name} (Timeout: {timeout_sec}s)...", file=sys.stderr)
            result = query_model(session, model_name, prompt, api_key, system_prompt=system_prompt, timeout=timeout_sec)
            if result:
                print(f"[Hydrogen Router] Success with {model_name}.", file=sys.stderr)
                return result
        except Exception as e:
            last_error = str(e)
            print(f"[Hydrogen Router] {model_name} failed: {e}. Failing over...", file=sys.stderr)
            continue

    return f"ERROR: All Gemini 4 models (hydrogen/argon/carbon) failed. Last error: {last_error}"

def self_improve() -> str:
    script_path = Path(__file__).resolve()
    current_code = script_path.read_text(encoding="utf-8")
    meta_prompt = f"""You are an elite autonomous AI systems architect and Python performance specialist.
Review the following code of `tools/hydrogen.py`:

```python
{current_code}
```

Audit and improve this client strictly within the Gemini 4 family (hydrogen, argon, carbon).
"""
    return run_prompt(meta_prompt, system_prompt="You are an expert autonomous software engineer and AI systems architect.")

def main():
    parser = argparse.ArgumentParser(description="Hydrogen Frontier AI Client (Strict Gemini 4)")
    parser.add_argument("prompt", nargs="*", help="Prompt to evaluate")
    parser.add_argument("--system", default="", help="System instruction prompt")
    parser.add_argument("--model", default="", choices=["gemini-4-hydrogen", "gemini-4-argon", "gemini-4-carbon"], help="Select model override")
    parser.add_argument("--self-improve", action="store_true", help="Run self-audit on hydrogen")

    args = parser.parse_args()

    if args.self_improve:
        print("[Hydrogen] Executing self-improvement analysis...", file=sys.stderr)
        print(self_improve())
        return

    if args.prompt:
        prompt_text = " ".join(args.prompt)
    elif not sys.stdin.isatty():
        prompt_text = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(0)

    result = run_prompt(prompt_text, system_prompt=args.system, preferred_model=args.model)
    print(result)

if __name__ == "__main__":
    main()
