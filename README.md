# 🧠 Conecta-Test-API

Este projeto é uma API desenvolvida em **Python com Flask**, utilizando **Flask-Migrate** para controle de migrações, **SQLAlchemy** como ORM, **Flasgger** para geração automática da documentação Swagger e **SQLite** como banco de dados.  
A aplicação roda dentro de um container **Docker** e é servida por meio do **Gunicorn**, garantindo um ambiente consistente e pronto para deploy em qualquer máquina.

Todo o processo de inicialização, build, e aplicação das migrações é automatizado dentro do container, portanto, basta subir o serviço com o Docker Compose para começar a utilizar.

Para executar o projeto localmente, é necessário ter o **Docker** e o **Docker Compose** instalados na máquina.  
Depois disso, basta seguir o passo a passo abaixo.

## 🚀 Executando o projeto

Primeiro, verifique se você está dentro da pasta raiz do projeto (onde estão os arquivos `Dockerfile` e `docker-compose.yml`).  
Em seguida, construa e suba o container com o comando:

## Build

docker compose up -d --build

## Build sem cache
docker compose build --no-cache

## Up container
docker compose up -d

## URL
http://localhost:8080

## URL Sweggar Docs
http://localhost:8080/api/docs

## URL Health check
http://localhost:8080/api/health