# Padrões de API - OfficeJoe

## Visão Geral

Este documento define os padrões para todos os endpoints da API do OfficeJoe, garantindo consistência e previsibilidade.

## Estrutura de Resposta

### Resposta de Sucesso com Dados

```json
{
  "success": true,
  "data": { /* dados */ },
  "message": "Operação realizada com sucesso",
  "request_id": "uuid-da-requisição"
}
```

### Resposta de Sucesso sem Dados

```json
{
  "success": true,
  "message": "Recurso deletado com sucesso",
  "request_id": "uuid-da-requisição"
}
```

### Resposta Paginada

```json
{
  "success": true,
  "data": [ /* array de items */ ],
  "total": 100,
  "skip": 0,
  "limit": 20,
  "page": 1,
  "total_pages": 5,
  "request_id": "uuid-da-requisição"
}
```

### Resposta de Erro

```json
{
  "success": false,
  "error": "Mensagem de erro genérica",
  "details": [
    {
      "field": "email",
      "message": "Email já está registrado",
      "code": "DUPLICATE_EMAIL"
    }
  ],
  "request_id": "uuid-da-requisição"
}
```

## Status HTTP

- **200 OK**: Sucesso em GET, PUT, PATCH
- **201 Created**: Sucesso em POST (criação)
- **204 No Content**: Sucesso em DELETE
- **400 Bad Request**: Erro de validação ou sintaxe
- **401 Unauthorized**: Autenticação falhou
- **403 Forbidden**: Autorização falhou
- **404 Not Found**: Recurso não encontrado
- **409 Conflict**: Conflito (ex: duplicata)
- **422 Unprocessable Entity**: Validação de negócio falhou
- **500 Internal Server Error**: Erro no servidor

## Convenções de Roteamento

```
GET    /api/v1/{recurso}              # Listar (com paginação)
POST   /api/v1/{recurso}              # Criar
GET    /api/v1/{recurso}/{id}         # Obter um
PUT    /api/v1/{recurso}/{id}         # Atualizar completo
PATCH  /api/v1/{recurso}/{id}         # Atualizar parcial
DELETE /api/v1/{recurso}/{id}         # Deletar
```

### Ações Especiais

```
POST   /api/v1/{recurso}/{id}/action  # Ação customizada
GET    /api/v1/{recurso}/search       # Busca
POST   /api/v1/{recurso}/bulk         # Operação em lote
```

## Parâmetros de Paginação

Todos os endpoints GET que listam devem suportar:

```
?skip=0      # Quantos itens pular
?limit=50    # Quantos itens retornar (máx 200)
?sort=-created_at  # Campo para ordenar (- para descendente)
?filter[status]=active  # Filtro por campo
```

## Autenticação

Todos os endpoints (exceto `/login` e `/refresh`) requerem:

```
Authorization: Bearer {jwt_token}
```

## Permissões

As permissões devem estar no token JWT:

```
{
  "permissions": ["case:read", "case:write", "document:read", ...]
}
```

## Campos Padrão em Recursos

Todos os recursos devem incluir:

```json
{
  "id": "uuid",
  "created_at": "2025-05-07T10:00:00Z",
  "updated_at": "2025-05-07T10:00:00Z",
  "created_by_id": "user-uuid",
  "status": "active"
}
```

## Tratamento de Erros

1. **Validação de entrada**: 400 + detalhes
2. **Falha de autorização**: 403
3. **Recurso não encontrado**: 404
4. **Conflito de negócio**: 409 ou 422
5. **Erro do servidor**: 500 + request_id para logging

## Documentação OpenAPI

Todos os endpoints devem incluir:

```python
@router.get("/", response_model=PaginatedResponse[CaseResponse])
async def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user = Depends(require_permission("case:read")),
    db = Depends(get_db),
):
    """
    Lista todos os processos.
    
    - **skip**: Quantos itens pular
    - **limit**: Quantos itens retornar
    
    Requer permissão: `case:read`
    """
```

## Versionamento

A API atual é `v1`. Mudanças breaking devem resultar em `v2`.

## Taxa de Requisição

- Não implementado ainda, mas planejado
- Será adicionado como middleware

## Cache

- Respostas GET podem incluir header `Cache-Control`
- Usar `ETag` para GET /resource/{id}

## Exemplo Completo

### Criar Processo

**Request:**
```http
POST /api/v1/cases HTTP/1.1
Authorization: Bearer {token}
Content-Type: application/json

{
  "case_number": "0000001-00.2025.1.00.0000",
  "case_type": "contábil",
  "title": "Perícia Contábil",
  "court": "Tribunal de Justiça",
  "parties": [
    {
      "name": "Empresa A",
      "role": "autora",
      "cpf_cnpj": "00.000.000/0000-00"
    }
  ]
}
```

**Response (201):**
```json
{
  "success": true,
  "data": {
    "id": "case-uuid",
    "case_number": "0000001-00.2025.1.00.0000",
    "case_type": "contábil",
    "title": "Perícia Contábil",
    "status": "active",
    "created_at": "2025-05-07T10:00:00Z",
    "created_by_id": "user-uuid",
    "parties": [...]
  },
  "message": "Processo criado com sucesso",
  "request_id": "req-uuid"
}
```

### Listar Processos

**Request:**
```http
GET /api/v1/cases?skip=0&limit=20&sort=-created_at HTTP/1.1
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "case-uuid-1",
      "case_number": "0000001-00.2025.1.00.0000",
      "status": "active",
      ...
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20,
  "page": 1,
  "total_pages": 8,
  "request_id": "req-uuid"
}
```

### Erro de Validação

**Response (400):**
```json
{
  "success": false,
  "error": "Erro de validação",
  "details": [
    {
      "field": "case_number",
      "message": "Formato inválido de número de processo",
      "code": "INVALID_FORMAT"
    },
    {
      "field": "parties",
      "message": "Deve ter pelo menos uma parte",
      "code": "REQUIRED"
    }
  ],
  "request_id": "req-uuid"
}
```

## Roadmap

- [ ] Rate limiting por usuário
- [ ] Cache com ETag
- [ ] Batch operations
- [ ] Webhooks
- [ ] GraphQL layer (opcional)
