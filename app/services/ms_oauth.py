from __future__ import annotations

import os
import requests
from typing import Any, Dict, List, Optional, Tuple
from requests_oauthlib import OAuth2Session

# =========================
# Config (env)
# =========================
TENANT = os.getenv("MS_TENANT_ID", "common")
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
REDIRECT_URI = os.getenv("MS_REDIRECT_URI", "http://localhost:8080/auth/callback")

SCOPES = os.getenv(
    "MS_SCOPES",
    "openid profile email offline_access User.Read Contacts.Read Contacts.ReadWrite Mail.Read Mail.Send",
).split()

AUTH_BASE = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"
AUTHORIZE_URL = f"{AUTH_BASE}/authorize"
TOKEN_URL = f"{AUTH_BASE}/token"

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


# =========================
# OAuth session factory
# =========================
def _oauth_session(state: Optional[str] = None, token: Optional[dict] = None) -> OAuth2Session:
    """
    Cria uma OAuth2Session configurada para Authorization Code + refresh automático (Microsoft).
    """
    if not CLIENT_ID:
        raise RuntimeError("MS_CLIENT_ID não configurado no ambiente.")
    if not CLIENT_SECRET:
        raise RuntimeError("MS_CLIENT_SECRET não configurado no ambiente.")
    if not REDIRECT_URI:
        raise RuntimeError("MS_REDIRECT_URI não configurado no ambiente.")

    return OAuth2Session(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,               # define o scope aqui
        state=state,
        token=token,                # pode incluir access/refresh token se já tiver
        auto_refresh_url=TOKEN_URL,
        auto_refresh_kwargs={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        token_updater=lambda t: None,  # se quiser, troque por callback que persiste o token
    )


# =========================
# OAuth: authorize + token
# =========================
def build_auth_url() -> Tuple[str, str]:
    """
    Retorna (auth_url, state) para iniciar o login Microsoft.
    """
    oauth = _oauth_session()
    # Use APENAS um prompt. "select_account" é o mais amigável.
    auth_url, state = oauth.authorization_url(
        AUTHORIZE_URL,
        prompt="select_account",
        response_mode="query",   # opcional, pode remover se preferir o default
        # response_type="code"   # default já é "code"
    )
    return auth_url, state


def fetch_token_by_code(code: str, state: Optional[str] = None) -> dict:
    """
    Troca o 'code' do callback por token Microsoft (access_token, refresh_token, etc).
    """
    oauth = _oauth_session(state=state)
    token = oauth.fetch_token(
        TOKEN_URL,
        code=code,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        include_client_id=True,
    )
    return token


# =========================
# Helpers HTTP para Graph
# =========================
def _auth_headers(access_token: str, content_type: Optional[str] = "application/json") -> Dict[str, str]:
    h = {"Authorization": f"Bearer {access_token}"}
    if content_type:
        h["Content-Type"] = content_type
    return h


def graph_get(endpoint: str, access_token: str, params: Optional[Dict[str, Any]] = None) -> dict:
    """
    GET genérico no Graph.
    endpoint: ex. "/me", "/me/contacts", "/users/{id}"
    """
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.get(url, headers=headers, params=params or {})
    r.raise_for_status()
    return r.json()


def call_graph(endpoint: str, access_token: str, params: Optional[Dict[str, Any]] = None) -> dict:
    """
    Conveniência para manter compatibilidade com imports em rotas.
    """
    return graph_get(endpoint, access_token, params)


def graph_post(endpoint: str, access_token: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.post(url, headers=headers, json=payload or {}, params=params or {})
    r.raise_for_status()
    if r.status_code in (202, 204) or not r.content:
        return {"status": r.status_code}
    return r.json()


def graph_patch(endpoint: str, access_token: str, payload: Optional[dict] = None) -> dict:
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.patch(url, headers=headers, json=payload or {})
    r.raise_for_status()
    if not r.content:
        return {"status": r.status_code}
    return r.json()


def graph_delete(endpoint: str, access_token: str) -> dict:
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.delete(url, headers=headers)
    r.raise_for_status()
    return {"status": r.status_code}


def graph_get_binary(endpoint: str, access_token: str, params: Optional[Dict[str, Any]] = None) -> bytes:
    url = f"{GRAPH_BASE}{endpoint}"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params or {}, stream=True)
    r.raise_for_status()
    return r.content


# =========================
# Funcionalidades: Contatos / Email / Perfil
# =========================
def fetch_contacts_grouped_by_domain(access_token: str, top: int = 100) -> Dict[str, List[Dict[str, str]]]:
    """
    Lê contatos pessoais e agrupa por domínio do e-mail.
    Retorna: { "dominio.com": [ { id, displayName, email }, ... ], ... }
    """
    # traga também o id
    params = {"$select": "id,displayName,emailAddresses", "$top": str(top)}
    data = graph_get("/me/contacts", access_token, params=params)
    values = data.get("value", []) or []

    grouped: Dict[str, List[Dict[str, str]]] = {}
    for c in values:
        cid = c.get("id") or ""
        name = c.get("displayName") or ""
        emails = c.get("emailAddresses") or []
        for e in emails:
            addr = (e.get("address") or "").strip()
            if not addr or "@" not in addr:
                continue
            domain = addr.split("@", 1)[1].lower()
            grouped.setdefault(domain, []).append({
                "id": cid,
                "displayName": name,
                "email": addr
            })

    # dedup por (id,email) e ordena
    for d in list(grouped.keys()):
        seen = set()
        dedup = []
        for item in grouped[d]:
            key = (item["id"], item["email"].lower())
            if key in seen:
                continue
            seen.add(key)
            dedup.append(item)
        grouped[d] = sorted(
            dedup,
            key=lambda x: (x["displayName"].lower(), x["email"].lower())
        )

    return dict(sorted(grouped.items(), key=lambda kv: kv[0]))
def create_contact(
    access_token: str,
    givenName: str,
    surname: Optional[str] = None,
    email: Optional[str] = None,
    businessPhones: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Cria um contato pessoal (pasta padrão de contatos do usuário).
    """
    payload: Dict[str, Any] = {"givenName": givenName}
    if surname:
        payload["surname"] = surname
    if email:
        payload["emailAddresses"] = [{"address": email}]
    if businessPhones:
        payload["businessPhones"] = businessPhones
    if extra:
        payload.update(extra)

    return graph_post("/me/contacts", access_token, payload=payload)


def update_contact(access_token: str, contact_id: str, payload: Dict[str, Any]) -> dict:
    """
    Atualiza um contato por ID.
    """
    return graph_patch(f"/me/contacts/{contact_id}", access_token, payload=payload)


def send_email(access_token: str, subject: str, body_html: str, to_recipients: List[str]) -> dict:
    """
    Envia e-mail em nome do usuário autenticado.
    """
    payload = {
        "message": {
            "subject": subject or "(sem assunto)",
            "body": {"contentType": "HTML", "content": body_html or ""},
            "toRecipients": [{"emailAddress": {"address": r}} for r in to_recipients],
        },
        "saveToSentItems": True,
    }
    return graph_post("/me/sendMail", access_token, payload=payload)


def list_sent_emails(access_token: str, top: int = 25) -> dict:
    """
    Lista e-mails da pasta Enviados (Sent Items).
    """
    params = {"$top": str(top), "$select": "id,subject,from,receivedDateTime,toRecipients"}
    return graph_get("/me/mailFolders/SentItems/messages", access_token, params=params)


def get_profile(access_token: str) -> dict:
    """
    Retorna dados básicos do usuário autenticado (/me).
    """
    return graph_get("/me", access_token)


def get_user_photo_bytes(access_token: str) -> bytes:
    """
    Retorna bytes da foto do usuário em /me/photo/$value).
    """
    return graph_get_binary("/me/photo/$value", access_token)