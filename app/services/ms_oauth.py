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
    Cria uma OAuth2Session configurada para Authorization Code + refresh automático.
    OBS: Se precisar persistir o token atualizado, troque o token_updater por um callback seu.
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
        scope=SCOPES,
        state=state,
        token=token,
        auto_refresh_url=TOKEN_URL,
        auto_refresh_kwargs={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        token_updater=lambda t: None,
    )


# =========================
# OAuth: authorize + token
# =========================
def build_auth_url() -> Tuple[str, str]:
    """
    Gera (auth_url, state) para iniciar o login Microsoft.
    O 'state' deve ser salvo na sessão para validação no callback (CSRF).
    """
    oauth = _oauth_session()
    auth_url, state = oauth.authorization_url(
    AUTHORIZE_URL,
    prompt="select_account"
)
    return auth_url, state


def fetch_token_by_code(code: str, state: Optional[str] = None) -> dict:
    """
    Troca o 'code' recebido no callback por um token (access_token, refresh_token, etc).
    Use o MESMO 'state' gerado no authorize.
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
    Wrapper compatível com o import usado em auth.py.
    """
    return graph_get(endpoint, access_token, params)


def graph_post(endpoint: str, access_token: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    """
    POST genérico no Graph.
    """
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.post(url, headers=headers, json=payload or {}, params=params or {})
    r.raise_for_status()
    if r.status_code in (202, 204) or not r.content:
        return {"status": r.status_code}
    return r.json()


def graph_patch(endpoint: str, access_token: str, payload: Optional[dict] = None) -> dict:
    """
    PATCH genérico no Graph.
    """
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.patch(url, headers=headers, json=payload or {})
    r.raise_for_status()
    if not r.content:
        return {"status": r.status_code}
    return r.json()


def graph_delete(endpoint: str, access_token: str) -> dict:
    """
    DELETE genérico no Graph.
    """
    url = f"{GRAPH_BASE}{endpoint}"
    headers = _auth_headers(access_token)
    r = requests.delete(url, headers=headers)
    r.raise_for_status()
    return {"status": r.status_code}


def graph_get_binary(endpoint: str, access_token: str, params: Optional[Dict[str, Any]] = None) -> bytes:
    """
    GET que retorna bytes (ex.: /me/photo/$value).
    """
    url = f"{GRAPH_BASE}{endpoint}"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params or {}, stream=True)
    r.raise_for_status()
    return r.content


# =========================
# Específicos: Contatos
# =========================
def fetch_contacts_grouped_by_domain(access_token: str, top: int = 100) -> Dict[str, List[Dict[str, str]]]:
    """
    Lê contatos pessoais e agrupa por domínio do e-mail.
    Retorna: { "dominio.com": [ { displayName, email }, ... ], ... }
    """
    params = {"$select": "displayName,emailAddresses", "$top": str(top)}
    data = graph_get("/me/contacts", access_token, params=params)
    values = data.get("value", []) or []

    grouped: Dict[str, List[Dict[str, str]]] = {}
    for c in values:
        name = c.get("displayName") or ""
        emails = c.get("emailAddresses") or []
        for e in emails:
            addr = (e.get("address") or "").strip()
            if not addr or "@" not in addr:
                continue
            domain = addr.split("@", 1)[1].lower()
            grouped.setdefault(domain, []).append({"displayName": name, "email": addr})

    for d in list(grouped.keys()):
        seen = set()
        dedup = []
        for item in grouped[d]:
            key = item["email"].lower()
            if key in seen:
                continue
            seen.add(key)
            dedup.append(item)
        grouped[d] = sorted(dedup, key=lambda x: (x["displayName"].lower(), x["email"].lower()))

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
    Campos comuns: givenName, surname, emailAddresses, businessPhones, companyName, jobTitle...
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
    Atualiza um contato por ID. Exemplo payload:
    {
      "givenName": "Novo",
      "emailAddresses": [{"address": "novo@exemplo.com"}],
      "jobTitle": "Dev"
    }
    """
    return graph_patch(f"/me/contacts/{contact_id}", access_token, payload=payload)


# =========================
# Específicos: Email
# =========================
def send_email(access_token: str, subject: str, body_html: str, to_recipients: List[str]) -> dict:
    """
    Envia e-mail em nome do usuário autenticado.
    to_recipients: lista de strings (emails).
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
    Retorna um objeto com 'value': [ { id, subject, from, receivedDateTime, toRecipients, ... } ]
    """
    params = {"$top": str(top), "$select": "id,subject,from,receivedDateTime,toRecipients"}
    return graph_get("/me/mailFolders/SentItems/messages", access_token, params=params)


# =========================
# Específicos: Perfil/Foto
# =========================
def get_profile(access_token: str) -> dict:
    """
    Retorna dados básicos do usuário autenticado (/me).
    """
    return graph_get("/me", access_token)


def get_user_photo_bytes(access_token: str) -> bytes:
    """
    Retorna bytes da foto do usuário em /me/photo/$value.
    Pode gerar 404 se o usuário não tiver foto.
    """
    return graph_get_binary("/me/photo/$value", access_token)