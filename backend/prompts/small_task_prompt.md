# Prompt: Tarefa Pequena

## Instrução

Implemente apenas a seguinte função do sistema:

```text
FUNÇÃO:
{{descrever função pequena}}
```

## Contexto

Sistema evidence-first de gestão de perícias contábeis com FastAPI, PostgreSQL, React, OCR, cadeia de custódia, inventário dos autos, matriz de prova, diligências, limitações técnicas, quesitos, cálculos, diário técnico e laudos.

## Requisitos Específicos

```text
{{listar requisitos}}
```

## Restrições Obrigatórias

1. Não alterar PDF original.
2. Manter rastreabilidade.
3. Registrar log de auditoria quando houver alteração.
4. Validar permissões.
5. Incluir testes.
6. Não criar funcionalidades fora do escopo desta tarefa.
7. Não permitir conclusão técnica sem evidência validada.
8. Não tratar output de IA como definitivo.

## Limite de Entrega

Entregue somente:

1. arquivos diretamente necessários;
2. código da função solicitada;
3. migration, se indispensável;
4. teste mínimo;
5. exemplo de uso;
6. observações de segurança.

## Não Entregar

- módulos futuros;
- frontend, salvo se solicitado;
- refatoração ampla;
- funcionalidades extras.

## Orientação de Implementação

- Antes de alterar arquivos, liste exatamente quais arquivos serão criados ou modificados.
- Faça a menor alteração capaz de cumprir a função solicitada.
- Preserve padrões existentes do projeto.
- Prefira validações explícitas a suposições implícitas.
- Ao usar IA, marque o resultado como preliminar e dependente de validação humana.
- Ao usar evidências, verifique o status de validação antes de permitir conclusão técnica.
- Se a tarefa exigir algo fora do escopo, registre a limitação em vez de implementar.
