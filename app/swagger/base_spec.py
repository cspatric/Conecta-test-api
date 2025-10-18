base_spec = {
    "openapi": "3.0.2",
    "info": {
        "title": "Meus Contatos MS API",
        "version": "1.0.0",
        "description": "API do desafio (Flask) com Swagger, migrations e SQLite"
    },
    "servers": [
        {"url": "/"}
    ],
    "components": {
        "securitySchemes": {
            "cookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session"
            }
        }
    }
}