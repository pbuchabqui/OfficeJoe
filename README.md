# OfficeJoe

OfficeJoe é uma plataforma evidence-first para apoio a perícias contábeis e trabalhistas. O projeto organiza processos, documentos, OCR, evidências, diligências, cálculos, laudos e registros técnicos com foco em rastreabilidade e preservação do documento original.

## Problema Resolvido

Perícias com grande volume documental tendem a perder tempo em tarefas repetitivas: receber PDFs, conferir integridade, localizar informações, controlar diligências, registrar limitações e manter coerência entre evidências, cálculos e laudo.

O OfficeJoe centraliza esse fluxo para reduzir retrabalho e tornar cada conclusão auditável por documento, página, trecho extraído, validação e decisão técnica.

## Filosofia Evidence-First

O sistema parte da evidência, não da conclusão. Cada artefato importante deve manter vínculo com sua origem documental sempre que possível.

Princípios:

- o PDF original não deve ser alterado;
- todo arquivo recebido recebe hash SHA-256;
- ações relevantes geram auditoria;
- extrações automáticas carregam confiança e status de validação;
- limitações técnicas são registradas explicitamente;
- laudos e cálculos devem poder apontar para evidências usadas.

## Stack

Backend:

- Python;
- FastAPI;
- SQLAlchemy async;
- Alembic;
- PostgreSQL com pgvector;
- Redis e Celery;
- MinIO/S3 para storage;
- PyMuPDF, pdfplumber, OCRmyPDF, Tesseract e PaddleOCR;
- pytest.

Frontend:

- React;
- TypeScript;
- Vite;
- CSS Modules;
- TanStack Query;
- Zustand;
- lucide-react.

Infra local:

- Docker Compose;
- PostgreSQL;
- Redis;
- MinIO;
- Flower.

## Requisitos

Para execução local sem Docker:

- Python 3.12;
- Node.js compatível com Vite;
- PostgreSQL;
- Redis;
- MinIO ou storage S3 compatível;
- dependências OCR quando usar processamento real.

Para execução com Docker:

- Docker;
- Docker Compose.

## Instalação Local

Crie o arquivo de ambiente:

```bash
cp .env.example .env
```

Instale o backend:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
```

Instale o frontend:

```bash
cd frontend
npm install
```

Execute o backend:

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Execute o frontend:

```bash
cd frontend
npm run dev
```

## Execução com Docker

Suba o ambiente base:

```bash
docker compose up --build
```

Para desenvolvimento com reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Serviços principais:

- backend: `http://localhost:8000`;
- frontend: `http://localhost:3000`;
- MinIO Console: `http://localhost:9001`;
- Flower: `http://localhost:5555`.

## Comandos Úteis

Rodar backend em modo desenvolvimento:

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port 8000
```

Rodar testes do backend:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
```

Rodar pacote inicial de testes:

```bash
APP_SECRET_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
JWT_SECRET_KEY=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
DATABASE_URL=sqlite+aiosqlite:///:memory: \
MINIO_ACCESS_KEY=test \
MINIO_SECRET_KEY=test \
PYTHONPATH=backend \
.venv/bin/pytest backend/tests/initial
```

Rodar build do frontend:

```bash
cd frontend
npm run build
```

## Testes

O backend usa `pytest` e `pytest-asyncio`. Os testes atuais rodam majoritariamente com SQLite em memória e fixtures locais, evitando dependência de PostgreSQL em cenários unitários e de integração inicial.

O pacote `backend/tests/initial` cobre:

- health check;
- autenticação;
- CRUD de processos;
- upload de PDF via serviço;
- hash SHA-256;
- auditoria de processo;
- cadeia de custódia no upload.

## Observações de Segurança

- Nunca versionar `.env` real.
- Trocar todos os segredos de `.env.example`.
- Preservar o PDF original sem sobrescrita.
- Validar hash SHA-256 antes de confiar em arquivos baixados do storage.
- Tratar saídas de OCR e IA como auxiliares até validação humana.
- Registrar limitações técnicas quando a documentação não permitir conclusão segura.

## Documentação

- Visão técnica inicial: [docs/TECHNICAL_OVERVIEW.md](docs/TECHNICAL_OVERVIEW.md)
- Roadmap técnico: [docs/TECHNICAL_ROADMAP.md](docs/TECHNICAL_ROADMAP.md)
