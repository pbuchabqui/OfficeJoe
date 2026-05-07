# Documentação Técnica Inicial

## Visão Geral

OfficeJoe é uma aplicação para apoio a perícias contábeis, trabalhistas e documentais. O núcleo do sistema organiza processos, documentos, evidências, extrações, diligências, cálculos e laudos com rastreabilidade.

A premissa central é evidence-first: nenhuma análise deve ficar solta da base documental quando houver documento, página, trecho ou extração que a sustente.

## Arquitetura Resumida

A arquitetura atual é composta por:

- backend FastAPI para API, regras de negócio e persistência;
- banco relacional para processos, documentos, evidências, laudos e auditoria;
- storage S3 compatível para PDFs originais e arquivos derivados;
- fila Celery para processamento assíncrono;
- Redis como broker/result backend;
- frontend React para interfaces operacionais;
- módulos de OCR, classificação e extração estruturada.

O fluxo pesado de processamento de arquivos é assíncrono. O upload registra metadados e agenda tarefas; etapas como páginas, previews, OCR e classificação podem evoluir independentemente.

## Stack

Backend:

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy async;
- Alembic;
- PostgreSQL com pgvector;
- SQLite em memória para testes;
- Redis;
- Celery;
- MinIO/S3;
- PyMuPDF, pdfplumber, OCRMyPDF, Tesseract e PaddleOCR;
- pytest e httpx.

Frontend:

- React;
- TypeScript;
- Vite;
- CSS Modules;
- TanStack Query;
- Zustand;
- lucide-react.

## Módulos

Módulos principais já representados no código:

- autenticação e RBAC;
- processos e partes;
- documentos e upload de PDF;
- hash, integridade e auditoria;
- páginas de arquivo, previews e OCR;
- classificação de páginas;
- inventário documental;
- evidências e matriz de prova;
- diligências;
- limitações técnicas;
- extrações de holerites, cartões ponto e fichas financeiras;
- contradições documentais;
- cálculos, versões e vínculos com evidências;
- diário técnico;
- laudos, seções, checklist, anexos, apêndices e esclarecimentos;
- honorários;
- dashboard inicial mockado.

## Fluxo do PDF

Fluxo básico atual:

1. Usuário envia PDF vinculado a um processo.
2. Backend valida tipo e tamanho.
3. Sistema calcula SHA-256 do arquivo recebido.
4. Metadados iniciais do PDF são extraídos sem alterar o arquivo.
5. Registro `documents` é criado com status inicial.
6. Arquivo original é armazenado em MinIO/S3.
7. Evento de auditoria é persistido.
8. Job de processamento é criado e enviado para Celery.
9. Processamentos posteriores podem registrar páginas, previews, OCR e classificações.

O PDF original é tratado como peça de custódia. Derivados como OCR, previews e extrações ficam em registros próprios.

## Cadeia de Custódia

A cadeia de custódia inicial no upload inclui:

- identificação do processo;
- nome original do arquivo;
- hash SHA-256;
- tamanho em bytes;
- bucket e chave de storage;
- validade básica do PDF;
- quantidade de páginas quando detectada;
- indicação de texto nativo quando detectada;
- marcador `original_received_hashed_stored`.

Essa informação é registrada em `audit_logs` com ação `document.upload`.

## Níveis de Confiabilidade

O sistema separa confiança técnica em camadas:

- **Integridade do arquivo**: SHA-256 e preservação do original.
- **Confiança OCR**: confiança média e marcação de trechos de baixa confiança.
- **Confiança de classificação**: score de classificação de páginas/documentos.
- **Confiança de extração**: confiança por campo extraído em holerites, cartões ponto e fichas financeiras.
- **Validação humana**: status de validação por evidência, matriz, campos extraídos e itens do laudo.
- **Limitação técnica**: registro explícito quando a documentação não permite conclusão robusta.

Confiança automática não substitui validação técnica.

## Como Rodar Localmente

Crie `.env`:

```bash
cp .env.example .env
```

Backend:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Como Rodar Testes

Todos os testes backend:

```bash
APP_SECRET_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
JWT_SECRET_KEY=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
DATABASE_URL=sqlite+aiosqlite:///:memory: \
MINIO_ACCESS_KEY=test \
MINIO_SECRET_KEY=test \
PYTHONPATH=backend \
.venv/bin/pytest backend/tests
```

Pacote inicial:

```bash
APP_SECRET_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
JWT_SECRET_KEY=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
DATABASE_URL=sqlite+aiosqlite:///:memory: \
MINIO_ACCESS_KEY=test \
MINIO_SECRET_KEY=test \
PYTHONPATH=backend \
.venv/bin/pytest backend/tests/initial
```

Frontend:

```bash
cd frontend
npm test
```

## Próximos Passos

- Consolidar contratos de API para módulos já existentes.
- Corrigir inconsistências de schemas de resposta antigas.
- Ampliar cobertura de testes por fluxo crítico.
- Evoluir validações humanas de evidências e extrações.
- Integrar o dashboard mockado a endpoints reais quando os contratos estiverem estáveis.
- Fortalecer trilhas de auditoria em operações de laudo, cálculo e esclarecimentos.
