# Roadmap Técnico

## Fase 1: Fundação Pericial

Objetivo:

Estabelecer base segura para processos, usuários, documentos, hash e auditoria.

Entregáveis:

- autenticação e permissões;
- CRUD de processos;
- upload de PDF;
- hash SHA-256;
- storage S3 compatível;
- auditoria básica;
- health checks;
- pacote inicial de testes.

Dependências:

- banco relacional;
- storage;
- configuração de ambiente;
- modelo de permissões.

Critérios de aceite:

- processo pode ser criado, consultado, atualizado e auditado;
- PDF original é preservado;
- hash é calculado e persistido;
- upload registra cadeia de custódia;
- testes iniciais passam.

## Fase 2: Processamento Documental

Objetivo:

Transformar PDFs recebidos em páginas, texto OCR e inventário documental rastreável.

Entregáveis:

- registro de páginas do PDF;
- previews por página;
- OCR básico;
- blocos de texto por página;
- classificação de páginas;
- inventário documental;
- busca textual e semântica inicial.

Dependências:

- Fase 1;
- Celery e Redis;
- ferramentas OCR;
- storage para derivados.

Critérios de aceite:

- PDF gera páginas rastreáveis;
- OCR mantém vínculo com arquivo e página;
- páginas podem ser classificadas;
- inventário pode ser revisado;
- itens relevantes podem virar evidências.

## Fase 3: Evidências e Diligências

Objetivo:

Criar camada operacional para transformar documentos em evidências e controlar lacunas documentais.

Entregáveis:

- evidências;
- matriz de prova;
- validação de evidências;
- diligências;
- recebimento de documentos;
- limitações técnicas;
- vínculos entre decisões técnicas e evidências.

Dependências:

- Fase 2;
- regras de validação;
- auditoria operacional.

Critérios de aceite:

- evidências possuem status claro;
- matriz aponta para evidências;
- diligências registram pendências;
- limitações críticas podem ser documentadas;
- decisões técnicas ficam rastreáveis.

## Fase 4: Extrações Estruturadas

Objetivo:

Extrair dados iniciais de documentos frequentes de forma mockável e validável.

Entregáveis:

- extração inicial de holerites;
- modelagem e extração inicial de cartões ponto;
- modelagem de fichas financeiras;
- confiança por campo;
- marcação de campos ilegíveis;
- contradições documentais iniciais.

Dependências:

- OCR por página;
- documentos classificados;
- modelos de dados de extração;
- validação humana por campo.

Critérios de aceite:

- textos OCR simulados geram dados estruturados;
- confiança por campo é retornada;
- campos ilegíveis são marcados;
- comparação inicial entre holerite e ficha financeira identifica divergências.

## Fase 5: Cálculos e Rastreabilidade

Objetivo:

Controlar versões de cálculos e evidências usadas sem implementar motor de cálculo.

Entregáveis:

- cadastro de cálculos;
- upload de versões;
- hash por arquivo;
- premissas e metodologia;
- vínculos entre cálculo e evidências;
- alertas para evidências não validadas.

Dependências:

- Fase 3;
- storage;
- hash;
- permissões.

Critérios de aceite:

- versões não sobrescrevem arquivos anteriores;
- cada versão possui hash;
- evidências usadas são vinculáveis;
- sistema alerta sobre evidência não validada.

## Fase 6: Laudos

Objetivo:

Organizar estrutura de laudos, seções, checklist, anexos, apêndices e esclarecimentos.

Entregáveis:

- laudos e seções;
- versionamento simples;
- vínculo de seção com matriz de prova;
- minuta de seção com provider mockado;
- prompt interno documentado;
- checklist normativo;
- validação de exportação por checklist;
- anexos e apêndices;
- exportação DOCX simples;
- esclarecimentos ao laudo.

Dependências:

- Fases 3 e 5;
- matriz de prova;
- checklist normativo;
- storage/exportação local em memória.

Critérios de aceite:

- laudo é composto por seções ordenadas;
- seções podem apontar para itens da matriz;
- checklist bloqueia exportação quando há pendências críticas;
- DOCX simples contém seções e anexos;
- esclarecimentos ficam vinculados ao laudo e versão.

## Fase 7: Operação e Gestão

Objetivo:

Dar visibilidade operacional ao trabalho pericial sem substituir a análise técnica.

Entregáveis:

- honorários iniciais;
- dashboard inicial;
- alertas operacionais;
- consolidação de pendências;
- documentação técnica inicial;
- README inicial.

Dependências:

- módulos anteriores;
- contratos de dados estáveis para dashboard real;
- critérios de status por módulo.

Critérios de aceite:

- honorários têm CRUD e filtro por status;
- dashboard mockado apresenta os principais blocos operacionais;
- documentação orienta execução local e testes;
- próximos passos técnicos ficam claros.

## Fase 8: Consolidação

Objetivo:

Reduzir inconsistências, ampliar testes e preparar módulos para uso integrado.

Entregáveis:

- revisão de schemas;
- padronização de status;
- endurecimento de validações;
- testes de fluxo ponta a ponta;
- observabilidade básica;
- documentação técnica incremental.

Dependências:

- fases anteriores;
- decisões de produto sobre fluxos prioritários;
- feedback de uso técnico.

Critérios de aceite:

- fluxos críticos têm testes automatizados;
- respostas de API são consistentes;
- auditoria cobre ações relevantes;
- falhas comuns retornam erros previsíveis;
- documentação acompanha o comportamento implementado.
