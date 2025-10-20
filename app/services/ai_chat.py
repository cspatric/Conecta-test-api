from __future__ import annotations
import os, re, requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

API_VERSIONS = ["v1", "v1beta"]

def _url(version: str, path: str) -> str:
    return f"https://generativelanguage.googleapis.com/{version}/{path}?key={GEMINI_API_KEY}"

def _payload(prompt: str) -> dict:
    return {"contents": [{"parts": [{"text": prompt}]}]}

def _list_models(version: str) -> list[str]:
    r = requests.get(_url(version, "models"), timeout=20)
    r.raise_for_status()
    return [m.get("name","") for m in r.json().get("models",[])]

def _normalize(name: str) -> str:
    return name.split("/", 1)[-1]

def _pick_model(version: str, desired: str) -> str | None:
    """Escolhe o melhor modelo disponível nesse 'version' a partir do desejado."""
    names = _list_models(version)
    if not names:
        return None
    clean = [_normalize(n) for n in names]

    # 1) match exato
    if desired in clean:
        return f"models/{desired}"

    # 2) sem -latest (ex.: gemini-2.5-flash-latest -> gemini-2.5-flash)
    base = re.sub(r"-latest$", "", desired)
    if base in clean:
        return f"models/{base}"

    # 3) mesma família (flash/pro) dentro da linha 2.5
    fam = "flash" if "flash" in base else ("pro" if "pro" in base else "")
    if fam:
        for n in clean:
            if n.startswith("gemini-2.5-") and fam in n:
                return f"models/{n}"

    # 4) qualquer 2.5
    for n in clean:
        if n.startswith("gemini-2.5-") or n == "gemini-2.5":
            return f"models/{n}"

    # 5) fallback: 1.5 flash
    for n in clean:
        if n.startswith("gemini-1.5-") and "flash" in n:
            return f"models/{n}"

    return names[0]

def ai_chat(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY ausente no .env.")

    last_err = None
    tried = []
    for ver in API_VERSIONS:
        try:
            model_path = _pick_model(ver, GEMINI_MODEL)
        except requests.HTTPError as e:
            tried.append(f"{ver}:LIST->{getattr(e.response,'status_code',None)}")
            last_err = e
            continue
        except Exception as e:
            tried.append(f"{ver}:LIST->EXC")
            last_err = e
            continue

        if not model_path:
            tried.append(f"{ver}:no-models")
            continue

        url = _url(ver, f"{model_path}:generateContent")
        tried.append(f"{ver}:{_normalize(model_path)}")
        try:
            r = requests.post(url, json=_payload(prompt), timeout=60)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            body = e.response.text if e.response is not None else ""
            if status == 404:
                last_err = e
                continue
            raise RuntimeError(f"Gemini {status} - {body}") from e
        except Exception as e:
            last_err = e
            continue

    hint = (
        "Habilite a 'Generative Language API' no projeto da sua API key, "
        "ligue o billing e evite restrições de key incompatíveis (teste sem restrições)."
    )
    raise RuntimeError(f"Falhou: {', '.join(tried)}. {hint} Erro final: {last_err}")