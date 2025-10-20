from __future__ import annotations
from typing import Any, Dict, Tuple, List

TOOL_SPEC: Dict[str, Dict[str, Any]] = {
    "list_contacts": {
        "params": {
            "top":   {"type": "integer", "optional": True,  "default": 100, "min": 1, "max": 999},
            "domain":{"type": "string",  "optional": True},
            "query": {"type": "string",  "optional": True}
        }
    },
    "get_contact": {
        "params": {
            "contact_id": {"type": "string", "optional": False}
        }
    },
    "create_contact": {
        "params": {
            "givenName":      {"type": "string",       "optional": False},
            "surname":        {"type": "string",       "optional": True},
            "email":          {"type": "string",       "optional": True},
            "businessPhones": {"type": "array_string", "optional": True},
            "extra":          {"type": "object",       "optional": True}
        }
    },
    "list_inbox": {
        "params": {
            "top": {"type": "integer", "optional": True, "default": 25, "min": 1, "max": 100}
        }
    },
    "list_sent": {
        "params": {
            "top": {"type": "integer", "optional": True, "default": 25, "min": 1, "max": 100}
        }
    },
    "send_mail": {
        "params": {
            "subject":   {"type": "string",       "optional": False},
            "body_html": {"type": "string",       "optional": False},
            "to":        {"type": "array_string", "optional": False}
        }
    }
}

OFFENSIVE_TERMS = {
    "porra","caralho","merda","buceta","punheta","puta","puto","foder","foda-se","fdp",
    "desgraçado","imbecil","otário","vagabunda","vagabundo","seu lixo",
    "sexo","pornô","pornografia","nude","nudes","boquete","gozar","gozo",
    "estupro","estuprar","pedofilia","zoofilia"
}

def _contains_offensive(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(term in t for term in OFFENSIVE_TERMS)

def _type_check(name: str, spec: Dict[str, Any], value: Any) -> Tuple[bool, str, Any]:
    t = spec.get("type")
    if t == "string":
        if not isinstance(value, str):
            return False, f"param '{name}' deve ser string", None
        return True, "", value.strip()
    if t == "integer":
        if isinstance(value, bool):
            return False, f"param '{name}' deve ser inteiro (não boolean)", None
        if isinstance(value, int):
            v = value
        elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
            v = int(value.strip())
        else:
            return False, f"param '{name}' deve ser inteiro", None
        min_v = spec.get("min")
        max_v = spec.get("max")
        if min_v is not None and v < min_v:
            return False, f"param '{name}' mínimo é {min_v}", None
        if max_v is not None and v > max_v:
            return False, f"param '{name}' máximo é {max_v}", None
        return True, "", v
    if t == "array_string":
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            return False, f"param '{name}' deve ser array de strings", None
        return True, "", [x.strip() for x in value]
    if t == "object":
        if not isinstance(value, dict):
            return False, f"param '{name}' deve ser objeto", None
        return True, "", value
    return False, f"tipo '{t}' inválido na spec do param '{name}'", None

def validate_ai_action(plan: Dict[str, Any], raw_model_text: str) -> Dict[str, Any]:
    if not isinstance(plan, dict):
        return {"valid": False, "message": "Plano não é um objeto JSON.", "clean": None}

    action = plan.get("action")
    if action not in TOOL_SPEC:
        return {"valid": False, "message": f"Ação inválida: {action}", "clean": None}

    params = plan.get("params")
    if not isinstance(params, dict):
        return {"valid": False, "message": "Campo 'params' deve ser um objeto.", "clean": None}

    spec = TOOL_SPEC[action]["params"]

    clean: Dict[str, Any] = {}
    for name, p_spec in spec.items():
        if name in params:
            ok, msg, coerced = _type_check(name, p_spec, params[name])
            if not ok:
                return {"valid": False, "message": msg, "clean": None}
            clean[name] = coerced
        else:
            if not p_spec.get("optional", False):
                return {"valid": False, "message": f"Parâmetro obrigatório ausente: '{name}'", "clean": None}
            if "default" in p_spec:
                clean[name] = p_spec["default"]

    if action == "send_mail":
        if not clean.get("to") or len(clean["to"]) == 0:
            return {"valid": False, "message": "send_mail requer ao menos um destinatário em 'to'.", "clean": None}
        if not clean.get("subject"):
            return {"valid": False, "message": "send_mail requer 'subject' não vazio.", "clean": None}
        if not clean.get("body_html"):
            return {"valid": False, "message": "send_mail requer 'body_html' não vazio.", "clean": None}
        if _contains_offensive(clean.get("subject", "")) or _contains_offensive(clean.get("body_html", "")):
            return {"valid": False, "message": "Conteúdo ofensivo/explicitamente inadequado detectado no e-mail.", "clean": None}

    forbidden_markers = ["create table", "drop table", "curl ", " wget ", " rm -rf "]
    raw_lower = (raw_model_text or "").lower()
    if any(m in raw_lower for m in forbidden_markers):
        return {"valid": False, "message": "Conteúdo potencialmente fora do escopo permitido.", "clean": None}
    if _contains_offensive(raw_lower):
        return {"valid": False, "message": "Conteúdo ofensivo/inadequado não é permitido.", "clean": None}

    reason = plan.get("reason")
    confidence = plan.get("confidence")
    if reason is not None and not isinstance(reason, str):
        return {"valid": False, "message": "Campo 'reason' deve ser string.", "clean": None}
    if confidence is not None and not isinstance(confidence, (int, float)):
        return {"valid": False, "message": "Campo 'confidence' deve ser número.", "clean": None}

    cleaned_plan = {
        "action": action,
        "params": clean,
        "reason": reason.strip() if isinstance(reason, str) else "",
        "confidence": float(confidence) if isinstance(confidence, (int, float)) else 0.0
    }
    return {"valid": True, "message": "ok", "clean": cleaned_plan}