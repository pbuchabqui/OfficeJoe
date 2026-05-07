# Pacote inicial de testes automatizados

Este pacote cobre somente:

- health check;
- autenticação;
- CRUD de processos;
- upload de PDF;
- hash SHA-256;
- auditoria de processo;
- cadeia de custódia no upload.

## Rodar apenas este pacote

```bash
APP_SECRET_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
JWT_SECRET_KEY=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
DATABASE_URL=sqlite+aiosqlite:///:memory: \
MINIO_ACCESS_KEY=test \
MINIO_SECRET_KEY=test \
PYTHONPATH=backend \
.venv/bin/pytest backend/tests/initial
```

## Rodar um arquivo específico

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/initial/test_health_check.py
```
