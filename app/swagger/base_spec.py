base_spec = {
    "swagger": "2.0",
    "info": {
        "title": "Meus Contatos MS API",
        "version": "1.0.0",
        "description": "API do desafio (Flask) com Swagger, migrations e SQLite"
    },
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "cookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "session"
        }
    },
    "paths": {}
}