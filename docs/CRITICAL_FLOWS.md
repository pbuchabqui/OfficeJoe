# Fluxos Críticos - OfficeJoe

Documentação detalhada dos fluxos principais com exemplos de requisição e resposta.

## 1. Autenticação

### 1.1 Login

**Endpoint**: `POST /api/v1/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "senha123"
}
```

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "Login realizado com sucesso",
  "request_id": "req-uuid"
}
```

**Response (401)**:
```json
{
  "success": false,
  "error": "Email ou senha inválidos",
  "details": [],
  "request_id": "req-uuid"
}
```

### 1.2 Refresh Token

**Endpoint**: `POST /api/v1/auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "request_id": "req-uuid"
}
```

### 1.3 Perfil Atual

**Endpoint**: `GET /api/v1/auth/me`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "full_name": "João Silva",
    "is_active": true,
    "is_superuser": false,
    "permissions": ["case:read", "case:write", "document:read", "document:write"],
    "created_at": "2025-01-01T10:00:00Z"
  },
  "request_id": "req-uuid"
}
```

## 2. Processos (Cases)

### 2.1 Criar Processo

**Endpoint**: `POST /api/v1/cases`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request**:
```json
{
  "case_number": "0000001-00.2025.1.00.0000",
  "case_type": "contábil",
  "title": "Perícia Contábil - Empresa X vs Y",
  "description": "Análise de escrituração e divergências",
  "court": "Tribunal de Justiça de São Paulo",
  "court_district": "1º Distrito Judiciário",
  "judge_name": "Dr. José Oliveira",
  "appointment_date": "2025-01-15",
  "deadline_date": "2025-06-30",
  "filing_date": "2024-12-01",
  "honorarium_proposed": 50000,
  "parties": [
    {
      "name": "Empresa A Ltda",
      "role": "autora",
      "cpf_cnpj": "12.345.678/0001-90",
      "lawyer_name": "Dr. Carlos Silva",
      "lawyer_oab": "SP123456"
    },
    {
      "name": "Empresa B Ltda",
      "role": "ré",
      "cpf_cnpj": "98.765.432/0001-10",
      "lawyer_name": "Dra. Maria Santos",
      "lawyer_oab": "SP654321"
    }
  ]
}
```

**Response (201)**:
```json
{
  "success": true,
  "data": {
    "id": "case-uuid-1",
    "case_number": "0000001-00.2025.1.00.0000",
    "case_type": "contábil",
    "title": "Perícia Contábil - Empresa X vs Y",
    "description": "Análise de escrituração e divergências",
    "status": "active",
    "court": "Tribunal de Justiça de São Paulo",
    "deadline_date": "2025-06-30",
    "responsible_user_id": "user-uuid",
    "created_at": "2025-05-07T10:00:00Z",
    "created_by_id": "user-uuid",
    "parties": [
      {
        "id": "party-uuid-1",
        "case_id": "case-uuid-1",
        "name": "Empresa A Ltda",
        "role": "autora",
        "cpf_cnpj": "12.345.678/0001-90",
        "lawyer_name": "Dr. Carlos Silva",
        "lawyer_oab": "SP123456"
      },
      {
        "id": "party-uuid-2",
        "case_id": "case-uuid-1",
        "name": "Empresa B Ltda",
        "role": "ré",
        "cpf_cnpj": "98.765.432/0001-10",
        "lawyer_name": "Dra. Maria Santos",
        "lawyer_oab": "SP654321"
      }
    ]
  },
  "message": "Processo criado com sucesso",
  "request_id": "req-uuid"
}
```

### 2.2 Listar Processos

**Endpoint**: `GET /api/v1/cases?skip=0&limit=20&sort=-created_at`

**Response (200)**:
```json
{
  "success": true,
  "data": [
    {
      "id": "case-uuid-1",
      "case_number": "0000001-00.2025.1.00.0000",
      "case_type": "contábil",
      "status": "active",
      "title": "Perícia Contábil - Empresa X vs Y",
      "court": "Tribunal de Justiça de São Paulo",
      "deadline_date": "2025-06-30",
      "responsible_user_id": "user-uuid"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20,
  "page": 1,
  "total_pages": 1,
  "request_id": "req-uuid"
}
```

## 3. Documentos

### 3.1 Upload de PDF

**Endpoint**: `POST /api/v1/cases/{case_id}/documents`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Form Data**:
```
file: <arquivo.pdf> (binary)
category: "balanço"
display_name: "Balanço Patrimonial 2024"
description: "Balanço auditado conforme normas IFRS"
```

**Response (201)**:
```json
{
  "success": true,
  "data": {
    "id": "doc-uuid-1",
    "case_id": "case-uuid-1",
    "original_filename": "arquivo.pdf",
    "display_name": "Balanço Patrimonial 2024",
    "description": "Balanço auditado conforme normas IFRS",
    "file_size_bytes": 2048576,
    "mime_type": "application/pdf",
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "category": "balanço",
    "status": "uploaded",
    "page_count": 15,
    "has_native_text": true,
    "uploaded_by_id": "user-uuid",
    "created_at": "2025-05-07T10:00:00Z",
    "updated_at": "2025-05-07T10:00:00Z"
  },
  "message": "Documento enviado com sucesso",
  "request_id": "req-uuid"
}
```

### 3.2 Verificar Integridade

**Endpoint**: `GET /api/v1/cases/{case_id}/documents/{document_id}/integrity`

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "document_id": "doc-uuid-1",
    "original_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "current_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "is_valid": true,
    "message": "Arquivo íntegro"
  },
  "request_id": "req-uuid"
}
```

### 3.3 Listar Páginas

**Endpoint**: `GET /api/v1/cases/{case_id}/documents/{document_id}/file-pages`

**Response (200)**:
```json
{
  "success": true,
  "data": [
    {
      "id": "page-uuid-1",
      "document_id": "doc-uuid-1",
      "page_number": 1,
      "ocr_status": "completed",
      "ocr_confidence": 0.95,
      "classification": {
        "category": "balanço",
        "confidence": 0.92,
        "validated": false,
        "validated_by_id": null
      },
      "created_at": "2025-05-07T10:01:00Z"
    },
    {
      "id": "page-uuid-2",
      "document_id": "doc-uuid-1",
      "page_number": 2,
      "ocr_status": "completed",
      "ocr_confidence": 0.93,
      "classification": {
        "category": "balanço",
        "confidence": 0.91,
        "validated": true,
        "validated_by_id": "user-uuid"
      },
      "created_at": "2025-05-07T10:01:05Z"
    }
  ],
  "total": 15,
  "skip": 0,
  "limit": 20,
  "page": 1,
  "total_pages": 1,
  "request_id": "req-uuid"
}
```

## 4. Evidências

### 4.1 Criar Evidência

**Endpoint**: `POST /api/v1/cases/{case_id}/evidence`

**Request**:
```json
{
  "title": "Balanço 2024 - Ativo Circulante",
  "description": "Demonstração contábil do ativo circulante conforme balanço auditado",
  "document_id": "doc-uuid-1",
  "page_number": 1,
  "snippet": "Ativo Circulante: R$ 500.000,00",
  "evidence_type": "accounting_document",
  "relevance": "high"
}
```

**Response (201)**:
```json
{
  "success": true,
  "data": {
    "id": "evidence-uuid-1",
    "case_id": "case-uuid-1",
    "title": "Balanço 2024 - Ativo Circulante",
    "description": "Demonstração contábil do ativo circulante conforme balanço auditado",
    "document_id": "doc-uuid-1",
    "page_number": 1,
    "snippet": "Ativo Circulante: R$ 500.000,00",
    "evidence_type": "accounting_document",
    "relevance": "high",
    "status": "unvalidated",
    "validated_by_id": null,
    "validated_at": null,
    "created_at": "2025-05-07T10:00:00Z"
  },
  "message": "Evidência criada com sucesso",
  "request_id": "req-uuid"
}
```

### 4.2 Validar Evidência

**Endpoint**: `PATCH /api/v1/cases/{case_id}/evidence/{evidence_id}/validate`

**Request**:
```json
{
  "status": "validated",
  "notes": "Documentação conforme com normas contábeis"
}
```

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "id": "evidence-uuid-1",
    "status": "validated",
    "validated_by_id": "user-uuid",
    "validated_at": "2025-05-07T10:05:00Z",
    "notes": "Documentação conforme com normas contábeis",
    "updated_at": "2025-05-07T10:05:00Z"
  },
  "message": "Evidência validada com sucesso",
  "request_id": "req-uuid"
}
```

## 5. Matriz de Prova

### 5.1 Listar Quesitos

**Endpoint**: `GET /api/v1/cases/{case_id}/quesitos`

**Response (200)**:
```json
{
  "success": true,
  "data": [
    {
      "id": "quesito-uuid-1",
      "case_id": "case-uuid-1",
      "numero": "1",
      "texto": "Qual o patrimônio líquido da empresa?",
      "tema": "situação_patrimonial",
      "tipo": "pertinente",
      "status": "pending",
      "evidence_count": 0,
      "created_at": "2025-05-07T10:00:00Z"
    },
    {
      "id": "quesito-uuid-2",
      "case_id": "case-uuid-1",
      "numero": "2",
      "texto": "Houve alteração de capital social no período?",
      "tema": "alterações_sociais",
      "tipo": "pertinente",
      "status": "pending",
      "evidence_count": 0,
      "created_at": "2025-05-07T10:00:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 20,
  "page": 1,
  "total_pages": 1,
  "request_id": "req-uuid"
}
```

### 5.2 Vincular Evidência a Quesito

**Endpoint**: `POST /api/v1/cases/{case_id}/quesitos/{quesito_id}/evidence`

**Request**:
```json
{
  "evidence_id": "evidence-uuid-1"
}
```

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "quesito_id": "quesito-uuid-1",
    "evidence_id": "evidence-uuid-1",
    "linked_at": "2025-05-07T10:06:00Z"
  },
  "message": "Evidência vinculada ao quesito com sucesso",
  "request_id": "req-uuid"
}
```

## 6. Laudos

### 6.1 Criar Laudo

**Endpoint**: `POST /api/v1/cases/{case_id}/reports`

**Request**:
```json
{
  "title": "Laudo Pericial - Perícia Contábil",
  "case_id": "case-uuid-1",
  "expert_id": "user-uuid",
  "expert_name": "João Silva, CRC 1SP123456"
}
```

**Response (201)**:
```json
{
  "success": true,
  "data": {
    "id": "report-uuid-1",
    "case_id": "case-uuid-1",
    "title": "Laudo Pericial - Perícia Contábil",
    "status": "draft",
    "expert_id": "user-uuid",
    "expert_name": "João Silva, CRC 1SP123456",
    "version": 1,
    "created_at": "2025-05-07T10:00:00Z"
  },
  "message": "Laudo criado com sucesso",
  "request_id": "req-uuid"
}
```

### 6.2 Adicionar Seção

**Endpoint**: `POST /api/v1/cases/{case_id}/reports/{report_id}/sections`

**Request**:
```json
{
  "title": "Analítica de Receitas",
  "content": "A empresa apresentou crescimento de 15% no período...",
  "order": 1,
  "section_type": "analysis"
}
```

**Response (201)**:
```json
{
  "success": true,
  "data": {
    "id": "section-uuid-1",
    "report_id": "report-uuid-1",
    "title": "Analítica de Receitas",
    "content": "A empresa apresentou crescimento de 15% no período...",
    "order": 1,
    "section_type": "analysis",
    "created_at": "2025-05-07T10:07:00Z"
  },
  "message": "Seção adicionada com sucesso",
  "request_id": "req-uuid"
}
```

### 6.3 Exportar Laudo (DOCX)

**Endpoint**: `POST /api/v1/cases/{case_id}/reports/{report_id}/export`

**Request**:
```json
{
  "format": "docx",
  "include_annexes": true,
  "include_evidence": true
}
```

**Response (200)** - Binary DOCX file
```
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="laudo-2025-05-07.docx"
```

## 7. Erros Comuns

### 400 - Validação de entrada

```json
{
  "success": false,
  "error": "Erro de validação",
  "details": [
    {
      "field": "case_number",
      "message": "Formato inválido de número de processo",
      "code": "INVALID_FORMAT"
    }
  ],
  "request_id": "req-uuid"
}
```

### 401 - Não autenticado

```json
{
  "success": false,
  "error": "Autenticação necessária",
  "details": [
    {
      "message": "Token inválido ou expirado",
      "code": "INVALID_TOKEN"
    }
  ],
  "request_id": "req-uuid"
}
```

### 403 - Sem permissão

```json
{
  "success": false,
  "error": "Acesso negado",
  "details": [
    {
      "message": "Você não tem permissão para esta ação",
      "code": "PERMISSION_DENIED"
    }
  ],
  "request_id": "req-uuid"
}
```

### 404 - Não encontrado

```json
{
  "success": false,
  "error": "Recurso não encontrado",
  "details": [
    {
      "field": "case_id",
      "message": "Processo com ID fornecido não existe",
      "code": "NOT_FOUND"
    }
  ],
  "request_id": "req-uuid"
}
```

### 409 - Conflito

```json
{
  "success": false,
  "error": "Conflito com dados existentes",
  "details": [
    {
      "field": "case_number",
      "message": "Já existe um processo com este número",
      "code": "DUPLICATE"
    }
  ],
  "request_id": "req-uuid"
}
```

### 500 - Erro do servidor

```json
{
  "success": false,
  "error": "Erro interno do servidor",
  "details": [
    {
      "message": "Ocorreu um erro ao processar a requisição",
      "code": "INTERNAL_ERROR"
    }
  ],
  "request_id": "req-uuid"
}
```

## Testes com cURL

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }'

# Salvar token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.data.access_token')

# Listar processos
curl -X GET http://localhost:8000/api/v1/cases \
  -H "Authorization: Bearer $TOKEN"

# Criar processo
curl -X POST http://localhost:8000/api/v1/cases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "0000001-00.2025.1.00.0000",
    "case_type": "contábil",
    "title": "Perícia Contábil"
  }'
```

## Próximos Passos

1. Implementar busca semântica com pgvector
2. Adicionar webhooks para notificações
3. Implementar rate limiting
4. Adicionar batch operations
5. Implementar GraphQL
