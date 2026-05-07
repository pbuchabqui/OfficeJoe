# Docker Setup - OfficeJoe

Guia completo para executar OfficeJoe com Docker Compose.

## Pré-requisitos

- Docker Engine 20.10+
- Docker Compose 1.29+
- Git
- No mínimo 8GB de RAM disponível

Verificar instalação:
```bash
docker --version
docker-compose --version
```

## Preparação Inicial

### 1. Clonar e Preparar Ambiente

```bash
git clone https://github.com/pbuchabqui/OfficeJoe.git
cd OfficeJoe
```

### 2. Criar arquivo .env

```bash
cp .env.example .env
```

Para **desenvolvimento local**, os valores padrão funcionam. Para produção, altere:
- `APP_SECRET_KEY`
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `MINIO_ACCESS_KEY` e `MINIO_SECRET_KEY`
- `AI_PROVIDER` (se usar IA real)

## Execução

### Stack Completo (Produção)

**Nota:** Use `docker compose` (novo) ou `docker-compose` (antigo):

```bash
# Docker Compose integrado (v1.29+) - RECOMENDADO
docker compose up --build

# Docker Compose standalone (versão antiga)
docker-compose up --build
```

Serviços:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **MinIO Console**: http://localhost:9001
- **Flower (Celery)**: http://localhost:5555
- **Swagger**: http://localhost:8000/docs

### Development com Hot Reload

Recomendado para desenvolvimento local:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# ou (versão antiga): docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Benefícios:
- Hot reload no backend e frontend
- Log level em debug
- Celery com concorrência 1
- Melhor para debugging

### Apenas Dependências (BD, Redis, MinIO)

Se preferir rodar backend/frontend localmente:

```bash
docker-compose up --build db redis minio
```

Depois, no seu computador:
```bash
# Backend
cd backend
python -m venv .venv
. .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Frontend (em outro terminal)
cd frontend
npm install
npm run dev
```

## Inicialização do Banco de Dados

O banco é inicializado automaticamente pela primeira vez que o container backend inicia.

Para reiniciar migrations manualmente:

```bash
docker-compose exec backend alembic upgrade head
```

Para criar nova migration:
```bash
docker-compose exec backend alembic revision --autogenerate -m "Descrição"
```

## Volumes e Persistência

- `postgres_data`: Dados do PostgreSQL
- `redis_data`: Cache e filas do Redis
- `minio_data`: Objetos armazenados no MinIO
- `celery_beat_schedule`: Schedule do Celery Beat

Para limpar tudo (perigoso!):
```bash
docker-compose down -v
```

## Verificação de Saúde

Verificar status dos containers:
```bash
docker-compose ps
```

Verificar logs:
```bash
docker-compose logs -f backend        # Backend logs
docker-compose logs -f celery_worker  # Worker logs
docker-compose logs -f frontend       # Frontend logs
```

Testar health checks:
```bash
curl http://localhost:8000/health
curl http://localhost:3000
curl http://localhost:6379 --user admin:admin  # Redis (não tem auth padrão)
```

## MinIO Setup Inicial

Acessar console: http://localhost:9001

Credenciais padrão: `minioadmin` / `minioadmin`

Criar buckets (se não criados automaticamente):
1. Clique em "Create Bucket"
2. Nome: `officejoe-documents`
3. Repetir para: `officejoe-exports`

## Inicializar Usuário Admin

Criar usuário admin padrão:
```bash
docker-compose exec backend python -c "
from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password
import uuid

db = SessionLocal()
admin = User(
    id=str(uuid.uuid4()),
    email='admin@example.com',
    full_name='Admin',
    hashed_password=hash_password('admin123'),
    is_active=True,
    is_superuser=True
)
db.add(admin)
db.commit()
print('Admin criado!')
"
```

Depois fazer login em http://localhost:3000:
- Email: `admin@example.com`
- Senha: `admin123`

## Troubleshooting

### Backend não inicia

```bash
# Verificar logs
docker-compose logs backend

# Verificar se PostgreSQL está healthy
docker-compose ps db

# Forçar rebuild
docker-compose build backend --no-cache
```

### PostgreSQL connection error

```bash
# Verificar se DB iniciou
docker-compose exec db pg_isready -U officejoe_user

# Esperar mais tempo (pode levar 30 segundos)
docker-compose ps
```

### Celery não processa tasks

```bash
# Verificar worker
docker-compose logs celery_worker

# Verificar Redis
docker-compose logs redis

# Reiniciar worker
docker-compose restart celery_worker
```

### MinIO não funciona

```bash
# Criar buckets manualmente
docker-compose exec minio mc mb minio/officejoe-documents
docker-compose exec minio mc mb minio/officejoe-exports
```

### Porta já em uso

Se portas 8000, 3000, 5432 etc já estão em uso:

```bash
# Mudar .env
PORT_BACKEND=9000
PORT_FRONTEND=3001
PORT_DB=5433

# Atualizar docker-compose.yml or usar override
```

## Performance

Para melhorar performance em dev:

```bash
# Limitar recursos
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Para usar menos RAM:
- Reduzir `PGVECTOR_DIMENSIONS` para 384
- Reduzir `OCR_MAX_PAGES_PER_TASK` para 10

## Comandos Úteis

```bash
# Tudo
docker-compose up -d                    # Rodar em background
docker-compose down                      # Parar tudo
docker-compose restart                   # Reiniciar
docker-compose pull                      # Atualizar imagens

# Específico
docker-compose exec backend bash         # Acessar shell do backend
docker-compose exec db psql -U officejoe_user officejoe  # Acessar BD
docker-compose run --rm backend pytest   # Rodar testes

# Limpeza
docker-compose down -v                   # Deletar volumes
docker system prune -a                   # Limpar imagens não usadas
```

## Proxying para Produção

Para usar com nginx/reverse proxy:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Próximos Passos

1. Verificar endpoint `/health`: `curl http://localhost:8000/health`
2. Acessar Swagger: http://localhost:8000/docs
3. Criar primeiro usuário/processo
4. Testar upload de PDF
5. Monitorar com Flower: http://localhost:5555
