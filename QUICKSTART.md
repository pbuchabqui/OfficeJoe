# OfficeJoe - Quick Start

Comece em 5 minutos.

## Pré-requisitos

- Docker e Docker Compose
- Git

## Setup

```bash
# 1. Clonar
git clone https://github.com/pbuchabqui/OfficeJoe.git
cd OfficeJoe

# 2. Configurar ambiente
cp .env.example .env

# 3. Rodar com Docker (escolha uma opção)

# Opção A: Script automático (recomendado)
./scripts/init-dev.sh    # Linux/Mac
.\scripts\init-dev.bat   # Windows

# Opção B: Manual
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# ou (versão antiga)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Acessar

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | admin@example.com / admin123 |
| API Docs | http://localhost:8000/docs | - |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| Flower (Celery) | http://localhost:5555 | - |

## Primeiro Uso

### 1. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }'
```

### 2. Criar Processo
```bash
TOKEN="seu_token_aqui"
curl -X POST http://localhost:8000/api/v1/cases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "0000001-00.2025.1.00.0000",
    "case_type": "contábil",
    "title": "Primeira Perícia"
  }'
```

### 3. Upload de PDF
```bash
CASE_ID="seu_case_id"
curl -X POST http://localhost:8000/api/v1/cases/$CASE_ID/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@documento.pdf" \
  -F "category=balanço"
```

## Parar

```bash
docker-compose down
```

Limpar tudo (cuidado!):
```bash
docker-compose down -v
```

## Documentação

- [API Standards](docs/API_STANDARDS.md) - Padrões de API
- [Docker Setup](docs/DOCKER_SETUP.md) - Guia completo Docker
- [Critical Flows](docs/CRITICAL_FLOWS.md) - Fluxos com exemplos
- [Technical Overview](docs/TECHNICAL_OVERVIEW.md) - Arquitetura
- [Roadmap](docs/TECHNICAL_ROADMAP.md) - Plano

## Troubleshooting

**Backend não inicia?**
```bash
docker-compose logs backend
```

**Precisa criar admin?**
```bash
# Usuario admin já vem pré-criado: admin@example.com / admin123
```

**Portas em conflito?**
Editar `.env` e mudar `PORT_BACKEND`, `PORT_FRONTEND`, etc.

## Próximos Passos

1. Ler [API Standards](docs/API_STANDARDS.md)
2. Explorar [Critical Flows](docs/CRITICAL_FLOWS.md)
3. Acessar http://localhost:8000/docs (Swagger)
4. Criar primeiro processo e fazer upload
5. Validar evidências

---

**Dúvidas?** Ver [docs](docs/) para documentação completa.
