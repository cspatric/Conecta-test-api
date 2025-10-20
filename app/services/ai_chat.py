from __future__ import annotations
import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest").strip()
API_VERSIONS = ["v1beta2", "v1beta"]

def _build_url(api_version: str, model: str) -> str:
    return f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={GEMINI_API_KEY}"

def _payload_for(prompt: str) -> dict:
    return {"contents": [{"parts": [{"text": prompt}]}]}

def _try_request(url: str, payload: dict) -> str:
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

def ai_chat(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY ausente. Defina no .env sem aspas.")

    payload = _payload_for(prompt)
    last_err = None
    tried = []
    models_to_try = [GEMINI_MODEL]
    if GEMINI_MODEL.endswith("-latest"):
        models_to_try.append(GEMINI_MODEL.replace("-latest", ""))

    for version in API_VERSIONS:
        for model in models_to_try:
            url = _build_url(version, model)
            tried.append(f"{version}:{model}")
            try:
                return _try_request(url, payload)
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status and status != 404:
                    body = e.response.text if e.response is not None else ""
                    raise RuntimeError(f"Gemini {status} - {body}") from e
                last_err = e
            except Exception as e:
                last_err = e

    hint = "Verifique se a 'Generative Language API' está habilitada no seu projeto GCP e se a chave pertence ao mesmo projeto."
    tried_str = ", ".join(tried)
    raise RuntimeError(f"Não foi possível acessar a Gemini (tentativas: {tried_str}). {hint}. Erro: {last_err}")