# Prompt: Revisão Crítica de Código

## Objetivo

Revise criticamente o código fornecido, com foco em riscos técnicos, segurança, preservação de evidências e confiabilidade pericial.

O resultado deve ajudar uma pessoa desenvolvedora ou revisora técnica a identificar problemas concretos e corrigi-los sem reescrever o sistema inteiro.

## Entrada

```text
{{colar_codigo}}
```

## Critérios de Avaliação

Avalie obrigatoriamente:

1. segurança;
2. tratamento de erros;
3. risco de perda de dados;
4. risco de sobrescrever arquivo original;
5. validação de entrada;
6. controle de permissões;
7. logs de auditoria;
8. cadeia de custódia;
9. performance com PDFs grandes;
10. legibilidade;
11. testes ausentes;
12. problemas de arquitetura;
13. risco de usar output de IA como definitivo;
14. risco de conclusão sem prova validada.

## Formato de Saída

Entregue somente:

1. lista de problemas encontrados;
2. severidade de cada problema;
3. correção recomendada;
4. trechos de código corrigidos apenas quando necessário.

Use este formato para cada item:

```markdown
## Problema N: <título curto>

Severidade: crítica | alta | média | baixa

Descrição:
<explique objetivamente o problema e o impacto>

Correção recomendada:
<explique a correção mínima recomendada>

Trecho corrigido, se necessário:
```python
<apenas o trecho essencial>
```
```

## Regras

- Não reescreva o sistema inteiro.
- Não implemente funcionalidades novas.
- Não invente contexto fora do código fornecido.
- Não presuma que validação humana ocorreu se isso não estiver explícito.
- Não aceite output de IA como definitivo sem trilha de revisão/validação.
- Não aceite conclusão técnica sem prova validada ou limitação registrada.
- Quando faltar contexto, registre como risco ou pergunta aberta.
- Prefira correções pequenas, localizadas e compatíveis com o código existente.
- Se não houver problemas em algum critério, diga isso de forma breve.

## Escala de Severidade

- **crítica**: pode causar perda de evidência, exposição grave de dados, sobrescrita do original, conclusão pericial sem base validada ou falha estrutural de autorização.
- **alta**: pode causar inconsistência relevante, quebra de cadeia de custódia, auditoria insuficiente, erro silencioso ou falha significativa em PDFs grandes.
- **média**: fragilidade importante, mas com impacto limitado ou recuperável.
- **baixa**: legibilidade, manutenção, testes complementares ou melhorias preventivas.
