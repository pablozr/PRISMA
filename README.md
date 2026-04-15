# Backlog de Migracao FastAPI e Mapeamento de Endpoints (Unificado)

Projeto: `extensao-unirio`

Objetivo:
- unir o plano arquitetural V3 com o backlog de migracao de endpoints
- transformar o desenho em backlog executavel e priorizado
- padronizar contratos e nomes de rota para evolucao continua

Documentos de referencia:
- `MODELO_DE_DADOS_EXPLICITO_E_USO_REAL.md`

---

## 1) Premissas e decisoes fechadas

1. Visitante consulta projetos publicados sem login.
2. Professor autentica via Google OAuth2 com allowlist em `professor_registry`.
3. Aluno e Admin usam login local (sem OAuth), com o mesmo endpoint de login.
4. Aluno sera apenas pre-cadastrado na base institucional da faculdade (sem auto-cadastro local).
5. Controle de roles ja existe e sera integrado na camada de autorizacao.
6. Banco alvo: PostgreSQL (com `citext` e `pg_trgm`).
7. RabbitMQ ficara em `core` como singleton (padrao igual ao PostgreSQL).
8. Envio de email sera processado em `workers`.
9. OAuth permanece em `core/security`.
10. `integrations` sera dedicado ao provider LLM.
11. `ai` tera apenas prompt, guardrails e orquestracao (sem service interno).
12. Servico de negocio de IA fica em `services/ai`.

---

## 2) Estrutura de pastas alvo

```text
core/
  config/
  logger/
  postgresql/
  rabbitmq/
    rabbitmq.py
  security/

integrations/
  llm/
    base_client.py
    openai_client.py
    factory.py

ai/
  prompts/
    sql_assistant_prompt.txt
  guardrails/
    sql_policy.py
    sql_validator.py
  orchestration/
    tyr_sql_orchestrator.py

services/
  auth/
  users/
  projects/
  imports/
  contact/
    contact_service.py
  ai/
    sql_assistant_service.py

routes/
  auth/
  catalogo/
  projetos/
  contact/
  search/
  admin/

workers/
  email/
    consumer.py
    sender.py
```

---

## 3) Convencoes da API (padrao final)

1. Prefixo unico: `/api/v1`.
2. Paths com substantivos no plural (evitar verbo no path).
3. Filtros via query string.
4. Escrita apenas com `POST`, `PATCH`, `DELETE`.
5. Status de habilitacao via body JSON (`habilitado: true/false`).
6. Endpoints redundantes serao consolidados em endpoint canonico.
7. Autorizacao por dependencia FastAPI (`visitor`, `student`, `professor`, `admin`).
8. Resposta de erro padrao: `code`, `message`, `details`, `request_id`.

---

## 4) Mapa de endpoints alvo (canonico)

## 4.1 Autenticacao

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| POST | `/api/v1/auth/password/send-code` | Publico | Enviar codigo de recuperacao de senha (forget-password) |
| POST | `/api/v1/auth/password/validate-code` | Publico | Validar codigo e redefinir senha |
| POST | `/api/v1/auth/login` | Publico | Login local de aluno/admin (`email + senha`) |
| POST | `/api/v1/auth/refresh` | Publico | Renovar sessao/token usando estado no Redis |
| POST | `/api/v1/auth/google/login` | Publico | Login Google de professor (allowlist) |
| POST | `/api/v1/auth/logout` | Student/Professor/Admin | Encerrar sessao/token |
| GET | `/api/v1/auth/me` | Student/Professor/Admin | Retornar usuario autenticado e roles |

## 4.2 Catalogo e filtros

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| GET | `/api/v1/catalogo/areas-tematicas` | Publico | Listar areas tematicas |
| GET | `/api/v1/catalogo/centros` | Publico | Listar centros |
| GET | `/api/v1/catalogo/unidades?centro_ids=1,2` | Publico | Listar unidades por centros |
| GET | `/api/v1/catalogo/cursos?unidade_ids=10,11` | Publico | Listar cursos por unidades |

## 4.3 Projetos (consulta)

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| GET | `/api/v1/projetos` | Publico | Buscar projetos com filtros e paginacao |
| GET | `/api/v1/projetos/{projeto_id}` | Publico | Obter detalhes de um projeto |
| GET | `/api/v1/projetos/{projeto_id}/atribuicoes` | Publico | Listar atribuicoes do projeto |

Filtros padrao de `GET /api/v1/projetos`:
- `q`
- `area_ids`
- `unidade_ids`
- `curso_ids`
- `ordenacao` (`titulo_asc`, `titulo_desc`, `data_desc`)
- `page`
- `page_size`
- `somente_habilitados` (default `true`)

## 4.4 Projetos (gestao do responsavel)

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| GET | `/api/v1/me/projetos` | Student/Professor/Admin | Listar projetos do usuario logado |
| PATCH | `/api/v1/projetos/{projeto_id}` | Student/Professor/Admin | Atualizar titulo e descricao (com ownership) |
| POST | `/api/v1/projetos/{projeto_id}/logo` | Student/Professor/Admin | Upload/atualizacao da imagem do projeto |
| POST | `/api/v1/projetos/{projeto_id}/atribuicoes` | Student/Professor/Admin | Criar atribuicao para cursos |
| DELETE | `/api/v1/atribuicoes/{atribuicao_id}` | Student/Professor/Admin | Remover atribuicao |

## 4.5 Contato por email assicrono (aluno)

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| POST | `/api/v1/contact/email` | Student | Criar solicitacao e publicar evento na fila |
| GET | `/api/v1/contact/email/{request_id}` | Student/Admin | Consultar status da solicitacao |

## 4.6 Pesquisa IA (aluno)

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| POST | `/api/v1/search/ai/sql-suggestion` | Student | Pergunta em linguagem natural e retorno de SQL seguro |
| GET | `/api/v1/search/ai/sessions/{session_id}` | Student/Admin | Consultar historico resumido da sessao |

## 4.7 Administrativo

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| POST | `/api/v1/admin/importacoes/projetos/csv` | Admin | Importar CSV e sincronizar dados |
| PATCH | `/api/v1/admin/projetos/{projeto_id}/status` | Admin | Habilitar/desabilitar projeto |
| PATCH | `/api/v1/admin/usuarios/{usuario_id}/status` | Admin | Habilitar/desabilitar usuario |
| POST | `/api/v1/admin/cursos` | Admin | Criar curso vinculado a unidade |

## 4.8 Operacional

| Metodo | Endpoint | Auth | Objetivo |
|---|---|---|---|
| GET | `/api/v1/health` | Publico | Liveness do servico |
| GET | `/api/v1/ready` | Publico | Readiness (DB + RabbitMQ) |

---

## 5) Contratos minimos recomendados

## 5.1 Recuperacao de senha por codigo (forget-password via Redis)

`POST /api/v1/auth/password/send-code`

```json
{
  "email": "aluno@unirio.br"
}
```

`POST /api/v1/auth/password/validate-code`

```json
{
  "email": "aluno@unirio.br",
  "codigo": "123456",
  "nova_senha": "<SECRET>"
}
```

## 5.2 Login local (aluno/admin)

`POST /api/v1/auth/login`

```json
{
  "email": "aluno@unirio.br",
  "senha": "<SECRET>"
}
```

## 5.3 Refresh de sessao/token (Redis)

`POST /api/v1/auth/refresh`

```json
{
  "refresh_token": "<TOKEN>"
}
```

## 5.4 Login Google (professor)

`POST /api/v1/auth/google/login`

```json
{
  "google_id_token": "<TOKEN>"
}
```

## 5.5 Alterar status (admin)

`PATCH /api/v1/admin/projetos/{projeto_id}/status`

```json
{
  "habilitado": true
}
```

`PATCH /api/v1/admin/usuarios/{usuario_id}/status`

```json
{
  "habilitado": false
}
```

## 5.6 Criar curso (admin)

`POST /api/v1/admin/cursos`

```json
{
  "nome": "Bacharelado em Ciencia de Dados",
  "unidade_id": 12
}
```

## 5.7 Criar atribuicao

`POST /api/v1/projetos/{projeto_id}/atribuicoes`

```json
{
  "descricao": "Atuar no suporte tecnico e levantamento de requisitos",
  "curso_ids": [4, 8, 9]
}
```

## 5.8 Solicitar contato por email

`POST /api/v1/contact/email`

```json
{
  "project_id": 77,
  "to_email": "docente@unirio.br",
  "subject": "Interesse no projeto",
  "body": "Gostaria de participar da proxima selecao."
}
```

## 5.9 Pesquisa IA para SQL

`POST /api/v1/search/ai/sql-suggestion`

```json
{
  "question": "quais projetos ativos da area de saude em 2026?"
}
```

## 5.10 Buscar projetos

`GET /api/v1/projetos?q=extensao&area_ids=1,2&unidade_ids=5&curso_ids=9,10&page=1&page_size=20&ordenacao=data_desc`

---

## 6) Endpoints legados removidos ou consolidados

| Endpoint legado | Acao no novo desenho | Endpoint substituto | Motivo |
|---|---|---|---|
| `/buscar_atribuicao_curso/` | Consolidar | `GET /api/v1/projetos/{id}/atribuicoes` | Duplicidade funcional |
| `/buscar_atribuicao_projeto/` | Consolidar | `GET /api/v1/projetos/{id}/atribuicoes` | Duplicidade funcional |
| `/buscar_cursos_por_centros/` | Remover | `GET /api/v1/catalogo/cursos?unidade_ids=` | Alinhar com schema real (`curso -> unidade`) |
| `/buscar_unidades_por_centros/` | Renomear | `GET /api/v1/catalogo/unidades?centro_ids=` | Padrao de nomenclatura |
| `/alterar_projeto/` | Renomear metodo/rota | `PATCH /api/v1/projetos/{id}` | REST sem verbo no path |
| `/adicionar_atribuicao/` | Renomear metodo/rota | `POST /api/v1/projetos/{id}/atribuicoes` | Recurso aninhado coerente |
| `/remover_atribuicao/` | Renomear metodo/rota | `DELETE /api/v1/atribuicoes/{id}` | Semantica HTTP correta |
| `/habilitar_desabilitar_projeto/` | Renomear metodo/rota | `PATCH /api/v1/admin/projetos/{id}/status` | Evitar escrita via GET |
| `/habilitar_desabilitar_usuario/` | Renomear metodo/rota | `PATCH /api/v1/admin/usuarios/{id}/status` | Evitar escrita via GET |
| `/upload_planilha/` | Renomear metodo/rota | `POST /api/v1/admin/importacoes/projetos/csv` | Nome orientado a dominio |
| `/adicionar_curso/` | Renomear metodo/rota | `POST /api/v1/admin/cursos` | Nome orientado a recurso |

Observacao de transicao:
- opcionalmente manter aliases legados por 1 ciclo de release com deprecation warning.

---

## 7) Modelo de dados e migracoes (resumo unificado)

Base principal:
- manter modelo V2.1 como nucleo (`users`, `professor_registry`, `projects`, `import_batches`, `project_change_logs` etc)
- ajustar para login local de aluno/admin e novos modulos de email/IA

Entidades novas/revisadas:
1. referencia de aluno em base institucional externa (somente leitura)
2. `email_dispatch_requests` (outbox + rastreabilidade de envio)
3. `ai_chat_sessions`
4. `ai_chat_messages`
5. `ai_sql_suggestions`
6. estado de reset/refresh em Redis (nao persistido no PostgreSQL)

Regras obrigatorias:
- `citext` para emails
- trilha de auditoria em alteracoes manuais
- indices para filtros de catalogo e status de fila
- importacao semestral rastreavel e reversivel

Migracoes:
1. baseline Alembic
2. criacao de tabelas novas
3. backfill de dados legados
4. corte de endpoints antigos

---

## 8) Backlog do produto (priorizado e executavel)

Legenda:
- Tipo: `TECH`, `API`, `DATA`, `QA`, `OPS`, `AI`, `WORKER`
- Prioridade: `P0` (critico), `P1` (alto), `P2` (medio)
- Status inicial: `TODO`

| ID | Item | Tipo | Prioridade | Estimativa (SP) | Dependencias | Criterios de aceite |
|---|---|---|---|---:|---|---|
| BL-001 | Criar boilerplate FastAPI em camadas e incluir routers | TECH | P0 | 3 | - | API sobe com `/api/v1/health` |
| BL-002 | Configurar settings por ambiente (`dev/hml/prod`) | TECH | P0 | 2 | BL-001 | Sem segredo hardcoded |
| BL-003 | Configurar singleton PostgreSQL (pool + dependencia de conexao) | DATA | P0 | 3 | BL-001 | Conexao estavel em carga basica |
| BL-004 | Configurar singleton RabbitMQ em `core/rabbitmq` | TECH | P0 | 3 | BL-001 | `publish` e `consume` funcionais |
| BL-005 | Implementar tratamento global de erros padrao unico | TECH | P0 | 2 | BL-001 | Erros com `code/message/details/request_id` |
| BL-006 | Padronizar logs estruturados com `request_id` | OPS | P0 | 2 | BL-001 | Logs rastreaveis por chamada |
| BL-007 | Organizar estrutura de pastas alvo (`core/integrations/ai/services/workers`) | TECH | P0 | 2 | BL-001 | Estrutura refletida no repo |
| BL-008 | Configurar CORS inicial e middlewares base | OPS | P0 | 2 | BL-001 | Frontend homologacao consome API |
| BL-009 | Modelar entidades base alinhadas ao schema real | DATA | P0 | 5 | BL-003 | Models validados contra dados reais |
| BL-010 | Modelar `atribuicao_curso` com chave composta | DATA | P0 | 3 | BL-009 | CRUD sem OneToOne indevido |
| BL-011 | Integrar referencia de alunos da base institucional (somente leitura) | DATA | P0 | 3 | BL-009 | Login local so permite email existente na base da faculdade |
| BL-012 | Revisar allowlist de `professor_registry` no fluxo de auth | DATA | P0 | 2 | BL-009 | Professor fora da lista nao autentica |
| BL-012A | Configurar Redis para codigos de verificacao e refresh token | TECH | P0 | 2 | BL-001 | Chaves com TTL e namespace padronizado |
| BL-013 | Criar tabela `email_dispatch_requests` | DATA | P0 | 3 | BL-009 | Solicitacao rastreavel por status |
| BL-014 | Criar tabelas `ai_chat_sessions/messages/sql_suggestions` | DATA | P0 | 3 | BL-009 | Historico de IA persistido |
| BL-015 | Criar indices e constraints essenciais (`citext`, `pg_trgm`, filtros) | DATA | P0 | 3 | BL-009 | Consultas e unicidade corretas |
| BL-016 | Configurar Alembic e baseline de migracoes | DATA | P0 | 3 | BL-009 | `alembic upgrade head` funcional |
| BL-017 | Implementar login local (`POST /auth/login`) | API | P0 | 5 | BL-011, BL-016 | Aluno/admin autenticam com email+senha |
| BL-018 | Implementar login Google professor (`POST /auth/google/login`) | API | P0 | 5 | BL-012, BL-016 | Token Google validado e allowlist aplicada |
| BL-019 | Implementar `POST /auth/logout` | API | P0 | 2 | BL-017 | Sessao/token invalidados |
| BL-020 | Implementar `GET /auth/me` | API | P0 | 2 | BL-017 | Retorna usuario e roles corretos |
| BL-021 | Implementar hash de senha (argon2) + rate limiting de login (Redis/Cloudflare) | API | P0 | 3 | BL-017 | Login protegido contra brute force |
| BL-021A | Implementar `POST /auth/password/send-code` (forget-password) com template existente | API | P0 | 3 | BL-012A, BL-021 | Codigo de reset enviado com TTL e rate limit |
| BL-021B | Implementar `POST /auth/password/validate-code` para redefinir senha | API | P0 | 3 | BL-012A, BL-021A | Codigo validado no Redis e senha atualizada |
| BL-021C | Implementar `POST /auth/refresh` com controle em Redis | API | P0 | 2 | BL-012A, BL-017 | Sessao renovada com token valido |
| BL-022 | Integrar RBAC por dependencia (`student/professor/admin`) | API | P0 | 3 | BL-017, BL-018 | Endpoints bloqueiam papel indevido |
| BL-023 | Implementar regras de ownership de projeto | API | P0 | 3 | BL-022 | Usuario altera apenas recurso autorizado |
| BL-024 | Implementar catalogo: areas e centros | API | P0 | 3 | BL-009 | Respostas consistentes |
| BL-025 | Implementar catalogo: unidades por centro | API | P0 | 2 | BL-009 | Query por `centro_ids` funcional |
| BL-026 | Implementar catalogo: cursos por unidade | API | P0 | 2 | BL-009 | Query por `unidade_ids` funcional |
| BL-027 | Implementar `GET /projetos` com filtros e paginacao | API | P0 | 5 | BL-009 | Paridade com busca esperada |
| BL-028 | Implementar `GET /projetos/{id}` | API | P0 | 2 | BL-027 | Detalhes completos retornados |
| BL-029 | Implementar `GET /projetos/{id}/atribuicoes` unificado | API | P0 | 3 | BL-010 | Substitui endpoints duplicados |
| BL-030 | Implementar `GET /me/projetos` | API | P0 | 2 | BL-022 | Lista por usuario logado |
| BL-031 | Implementar `PATCH /projetos/{id}` | API | P0 | 3 | BL-023 | Atualiza com ownership e auditoria |
| BL-032 | Implementar upload de logo (`POST /projetos/{id}/logo`) | API | P0 | 3 | BL-031 | Valida tipo/tamanho e salva |
| BL-033 | Implementar criacao de atribuicao (`POST /projetos/{id}/atribuicoes`) | API | P0 | 3 | BL-031 | Cria atribuicao + vinculos |
| BL-034 | Implementar remocao de atribuicao (`DELETE /atribuicoes/{id}`) | API | P0 | 2 | BL-033 | Remove com autorizacao |
| BL-035 | Implementar importacao CSV admin (`POST /admin/importacoes/projetos/csv`) | API | P0 | 8 | BL-022, BL-016 | Upsert + desabilita ausentes |
| BL-036 | Implementar `PATCH /admin/projetos/{id}/status` | API | P0 | 2 | BL-022 | Ativa/desativa por JSON |
| BL-037 | Implementar `PATCH /admin/usuarios/{id}/status` | API | P0 | 2 | BL-022 | Ativa/desativa por JSON |
| BL-038 | Implementar `POST /admin/cursos` | API | P0 | 2 | BL-026, BL-022 | Cria curso corretamente |
| BL-039 | Integrar `project_change_logs` em edicoes manuais | DATA | P0 | 2 | BL-031 | Toda alteracao manual e auditada |
| BL-040 | Implementar `POST /contact/email` com persistencia + publish | API | P0 | 4 | BL-013, BL-004, BL-022 | Solicita envio e retorna `request_id` |
| BL-041 | Implementar `GET /contact/email/{request_id}` | API | P0 | 2 | BL-040 | Status de fila consultavel |
| BL-042 | Implementar worker de email com retry e DLQ | WORKER | P0 | 5 | BL-004, BL-013 | Consome fila e atualiza status |
| BL-043 | Garantir idempotencia de envio por `request_id` | WORKER | P0 | 2 | BL-042 | Nao duplica envio em reprocesso |
| BL-044 | Criar camada `integrations/llm` (`base/openai/factory`) | AI | P0 | 3 | BL-007 | Provider substituivel por interface |
| BL-045 | Implementar prompt base e guardrails SQL em `ai/guardrails` | AI | P0 | 4 | BL-044 | Bloqueia SQL nao permitido |
| BL-046 | Implementar orquestrador Tyr em `ai/orchestration` | AI | P0 | 4 | BL-045 | Gera SQL com politica aplicada |
| BL-047 | Implementar `services/ai/sql_assistant_service.py` | AI | P0 | 3 | BL-046 | Caso de uso pronto para rota |
| BL-048 | Implementar `POST /search/ai/sql-suggestion` | API | P0 | 3 | BL-047, BL-022 | Disponivel so para aluno |
| BL-049 | Implementar `GET /search/ai/sessions/{session_id}` | API | P1 | 2 | BL-014, BL-048 | Historico resumido retornado |
| BL-050 | Configurar usuario de banco read-only para IA | DATA | P1 | 2 | BL-045 | Consultas IA sem risco de escrita |
| BL-051 | Whitelist de views/tabelas para IA | DATA | P1 | 2 | BL-050 | SQL fora da whitelist e bloqueado |
| BL-052 | Validacao forte de CSV (colunas, tipos, relatorio de erros) | API | P1 | 5 | BL-035 | Erros detalhados por linha |
| BL-053 | Performance: reduzir N+1 e ajustar indices de consulta | DATA | P1 | 5 | BL-027, BL-029 | Latencia dentro da meta |
| BL-054 | Testes de integracao endpoints P0 | QA | P0 | 8 | BL-017..BL-048, BL-021A, BL-021B, BL-021C | Fluxos criticos cobertos |
| BL-055 | Testes de autorizacao (RBAC + ownership) | QA | P0 | 5 | BL-022, BL-031..BL-038 | Bloqueio indevido validado |
| BL-055A | Testes de codigo de verificacao e refresh via Redis | QA | P0 | 3 | BL-021A, BL-021B, BL-021C | Codigo expira, nao reutiliza e refresh funciona |
| BL-056 | Testes do fluxo assicrono de email (fila + retry + DLQ) | QA | P0 | 5 | BL-042, BL-043 | Entrega e retentativa validadas |
| BL-057 | Testes de guardrail IA (injection e comandos proibidos) | QA | P0 | 5 | BL-048, BL-051 | SQL inseguro sempre negado |
| BL-058 | Publicar OpenAPI com exemplos por endpoint | API | P1 | 3 | BL-024..BL-049 | Docs prontas para frontend |
| BL-059 | Compatibilidade temporaria para rotas legadas (opcional) | API | P1 | 3 | BL-027..BL-038 | Frontend nao quebra na transicao |
| BL-060 | Plano de corte e rollback para producao | OPS | P1 | 3 | BL-054..BL-058 | Deploy com contingencia |
| BL-061 | Hardening final (headers, CORS definitivo, rate limit) | OPS | P2 | 3 | BL-060 | Checklist de seguranca aprovado |
| BL-062 | Limpeza de artefatos legados e duplicados no repo | TECH | P2 | 3 | BL-060 | Repositorio sem conflito |
| BL-063 | Desativar endpoints antigos apos janela de transicao | TECH | P2 | 2 | BL-060, BL-059 | Trafego 100% no canonico |
| BL-064 | Observabilidade final (dashboards, alertas, runbook) | OPS | P2 | 3 | BL-060 | Operacao assistida por alerta |

---

## 9) Agrupamento por sprint (sugestao)

## Sprint 1 - Fundacao tecnica
- BL-001 a BL-008

## Sprint 2 - Dados e autenticacao
- BL-009 a BL-023 (incluindo BL-012A, BL-021A, BL-021B e BL-021C)

## Sprint 3 - Catalogo e consulta de projetos
- BL-024 a BL-034

## Sprint 4 - Admin e importacao
- BL-035 a BL-039 + BL-052

## Sprint 5 - Contato assicrono por email
- BL-040 a BL-043 + BL-056

## Sprint 6 - IA SQL para pesquisa (aluno)
- BL-044 a BL-051 + BL-057

## Sprint 7 - Qualidade, corte e operacao
- BL-054, BL-055, BL-055A, BL-058 a BL-064

---

## 10) Definicao de pronto (DoD)

Cada item so pode ser concluido quando:
1. Endpoint/feature implementado com contrato validado.
2. Testes de sucesso e erro cobrindo regra principal.
3. Regras de permissao aplicadas e testadas.
4. Logs com contexto suficiente (`request_id`, `user_id` quando aplicavel).
5. OpenAPI atualizada com exemplos.
6. Para item assicrono: status rastreavel e retry testado.
7. Para item IA: guardrail bloqueando comandos proibidos e SQL fora da whitelist.
8. Para auth local: endpoints de `send-code`/`validate-code` nao expoem se o email existe (anti-user-enumeration).

---

## 11) Riscos principais e mitigacao

1. Ambiguidade de regra de login por perfil.
   - Mitigacao: manter contrato fechado deste documento (local para aluno/admin, Google para professor).

2. Uso abusivo do envio de email.
   - Mitigacao: rate limit, quota diaria e DLQ com monitoramento.

3. SQL inseguro gerado pela IA.
   - Mitigacao: guardrail estrito, whitelist de objetos e usuario read-only no banco.

4. Divergencia entre schema real e contratos da API.
   - Mitigacao: migracoes versionadas + testes de integracao antes de corte.

5. Dependencia da base institucional externa de alunos.
   - Mitigacao: timeout curto, cache controlado e fallback de indisponibilidade.

6. Crescimento de tabelas de fila/chat (custo de storage e consulta).
   - Mitigacao: politica de retencao, arquivamento periodico e indices focados em leitura recente.

---

## 12) Resultado esperado apos execucao do backlog

1. API FastAPI organizada, sem endpoint redundante.
2. Nomes de rota consistentes e orientados a recurso.
3. Fluxos de visitante, aluno, professor e admin cobertos com RBAC.
4. Fila assicrona de email operacional com rastreabilidade ponta a ponta.
5. Pesquisa com IA disponivel para aluno com SQL seguro e auditavel.
6. Modelo de dados alinhado ao uso real e pronto para evolucao continua.

---

## 13) Anexo de banco de dados (completo)

Este anexo adiciona o desenho de dados no final do backlog, com foco no escopo atual.

Observacao importante:
- O modulo de roles ja existe e sera plugado depois.
- Por isso, o `users` abaixo nao fixa role unica em coluna.

## 13.1 Entidades do modelo

### 13.1.1 Identidade e autorizacao

#### `users`
Conta autenticada do sistema.

Campos principais:
- `id`
- `institutional_email` (UQ)
- `full_name`
- `password_hash` (login local aluno/admin)
- `google_sub` (UQ, professor OAuth)
- `is_active`
- `last_login_at`
- `created_at`, `updated_at`

#### `professor_registry`
Allowlist oficial de professores permitidos a autenticar via Google.

Campos principais:
- `id`
- `institutional_email` (UQ)
- `full_name`
- `siape` (UQ opcional)
- `unit_id` (FK)
- `user_id` (FK UQ, nullable ate primeiro login)
- `source_import_batch_id` (FK)
- `is_active`
- `created_at`, `updated_at`

Regra:
- `professor_registry` e fonte de verdade de allowlist.
- `users` representa quem efetivamente autenticou.

#### `student_directory_ref` (externo)
Referencia de aluno/admin em base institucional da faculdade (fora do PostgreSQL da API).

Campos esperados para consulta:
- `institutional_email` (UQ)
- `full_name`
- `is_active`
- `is_admin_candidate` (opcional, se vier da base)

### 13.1.2 Importacao semestral

#### `import_batches`
Historico de cada upload/importacao.

Campos principais:
- `id`
- `reference_year`
- `reference_term` (`1 | 2`)
- `uploaded_by_user_id` (FK)
- `source_filename`
- `source_hash`
- `status` (`processing | success | partial | failed`)
- `total_rows`
- `imported_rows`
- `rejected_rows`
- `created_at`, `finished_at`

#### `import_row_errors`
Linhas rejeitadas na importacao.

Campos principais:
- `id`
- `import_batch_id` (FK)
- `row_number`
- `raw_payload` (JSONB)
- `error_reason`
- `created_at`

#### `project_import_links`
Vinculo entre projeto e batch em que apareceu.

Campos principais:
- `project_id` (FK)
- `import_batch_id` (FK)
- `created_at`

### 13.1.3 Catalogo publico

#### `projects`
Entidade central do portal.

Campos principais:
- `id`
- `process_code`
- `title`
- `short_description`
- `full_description`
- `contact_email`
- `owner_professor_id` (FK)
- `executing_unit_id` (FK)
- `source_import_batch_id` (FK)
- `status` (`draft | published | archived`)
- `is_active`
- `starts_at`, `ends_at`
- `created_at`, `updated_at`, `published_at`
- `deactivated_at`

#### `project_images`
Imagens do projeto.

Campos principais:
- `id`
- `project_id` (FK)
- `image_type` (`cover | gallery`)
- `image_url`
- `alt_text`
- `sort_order`
- `created_at`

Regra:
- no maximo uma imagem `cover` por projeto.

### 13.1.4 Classificacao academica

#### `organizational_units`
Estrutura unica para centro/departamento/instituto.

#### `courses`
Cursos vinculados a unidade.

#### `project_areas`
Taxonomia de areas tematicas.

#### `project_area_links`
Relacao N:M entre projeto e area.

#### `project_course_links`
Relacao N:M entre projeto e curso.

### 13.1.5 Auditoria

#### `project_change_logs`
Historico de alteracoes manuais em projetos.

Campos principais:
- `id`
- `project_id` (FK)
- `changed_by_user_id` (FK)
- `change_type` (`manual_edit | status_change | import_override`)
- `field_name`
- `old_value` (JSONB)
- `new_value` (JSONB)
- `reason`
- `created_at`

### 13.1.6 Contato por email assicrono

#### `email_dispatch_requests`
Outbox/fila logica de solicitacoes de email.

Campos principais:
- `id`
- `requested_by_user_id` (FK)
- `project_id` (FK)
- `to_email`
- `subject`
- `body`
- `payload` (JSONB)
- `status` (`queued | processing | sent | failed | dead_letter`)
- `attempt_count`
- `next_attempt_at`
- `last_error`
- `provider_message_id`
- `created_at`, `updated_at`, `sent_at`

### 13.1.7 Pesquisa IA

#### `ai_chat_sessions`
Sessao de conversa do aluno com IA.

#### `ai_chat_messages`
Mensagens da sessao (`user | assistant | system`).

#### `ai_sql_suggestions`
Pergunta + SQL sugerido + resultado de validacao.

---

## 13.2 Regras de dominio importantes

### 13.2.1 Login professor
1. Usuario autentica via Google.
2. Backend extrai email institucional.
3. Email precisa existir em `professor_registry` com `is_active = true`.
4. Se aprovado:
   - cria/atualiza `users`
   - vincula `professor_registry.user_id`
5. Caso contrario, acesso negado.

### 13.2.2 Login aluno/admin
1. Email precisa existir na base institucional externa com status ativo.
2. Fluxo de recuperacao de senha (forget-password) usa Redis:
   - `POST /auth/password/send-code`
   - `POST /auth/password/validate-code`
3. Com senha definida, autentica por login local (`email + senha`).
4. Backend cria/atualiza `users`.
5. Roles definem privilegios de aluno/admin.

### 13.2.3 Importacao semestral
1. Admin cria `import_batches`.
2. Sistema faz upsert em `professor_registry`.
3. Sistema faz upsert em `projects`.
4. Sistema registra presenca em `project_import_links`.
5. Linhas invalidas vao para `import_row_errors`.
6. Projetos ausentes no batch atual podem virar inativos/arquivados.

### 13.2.4 Contato assicrono por email
1. Aluno cria solicitacao.
2. API grava em `email_dispatch_requests` com status `queued`.
3. Evento vai para RabbitMQ.
4. Worker processa envio e atualiza status/tentativas.

### 13.2.5 Pesquisa IA SQL
1. Aluno pergunta em linguagem natural.
2. Orquestrador IA gera SQL.
3. Guardrail valida (somente leitura).
4. Sistema salva trilha em `ai_sql_suggestions`.

### 13.2.6 Refresh de sessao
1. Cliente chama `POST /auth/refresh` com refresh token.
2. Backend valida token e estado no Redis.
3. Se valido, emite novo access token e renova TTL do refresh.
4. Se invalido/expirado, exige novo login.

---

## 13.3 Regras de integridade essenciais

1. Unicidade:
   - `users.institutional_email`
   - `users.google_sub`
   - `professor_registry.institutional_email`
   - `project_areas.name`
   - `project_areas.slug`
   - `courses.code`

2. Status:
   - `projects.status IN ('draft', 'published', 'archived')`
   - `import_batches.status IN ('processing', 'success', 'partial', 'failed')`
   - `email_dispatch_requests.status IN ('queued', 'processing', 'sent', 'failed', 'dead_letter')`

3. Importacao:
   - `reference_term IN (1, 2)`

4. Relacionamentos:
   - tabelas link com `ON DELETE CASCADE` no lado do projeto

5. Auditoria:
   - toda alteracao manual em projeto gera `project_change_logs`

6. IA:
   - sugestoes de SQL exigem status de validacao (`approved` ou `rejected`)

7. Login:
   - `users` precisa de credencial local ou Google (`password_hash` ou `google_sub`)

8. Tokens/codigos em Redis:
   - codigo de verificacao e refresh token com TTL
   - codigo nao pode ser reutilizado apos validacao

---

## 13.4 Ajuste sobre `process_code`

Recomendacao para primeira versao:
- manter `process_code` sem `UNIQUE` global imediato
- indexar e validar regra real com historico de planilhas
- se comprovadamente unico na instituicao, evoluir para `UNIQUE`

---

## 13.5 DDL base revisada (PostgreSQL)

Observacao:
- a base institucional de alunos (fonte externa) e o estado de codigo/refresh no Redis nao aparecem neste DDL.

```sql
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  institutional_email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT,
  google_sub TEXT UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL)
);

CREATE TABLE import_batches (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  reference_year SMALLINT NOT NULL,
  reference_term SMALLINT NOT NULL CHECK (reference_term IN (1, 2)),
  uploaded_by_user_id BIGINT NOT NULL REFERENCES users(id),
  source_filename TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('processing', 'success', 'partial', 'failed')),
  total_rows INTEGER NOT NULL DEFAULT 0,
  imported_rows INTEGER NOT NULL DEFAULT 0,
  rejected_rows INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE organizational_units (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL,
  short_name TEXT,
  type TEXT NOT NULL CHECK (type IN ('centro', 'departamento', 'instituto')),
  parent_unit_id BIGINT REFERENCES organizational_units(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE professor_registry (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  institutional_email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  siape TEXT UNIQUE,
  unit_id BIGINT REFERENCES organizational_units(id),
  user_id BIGINT UNIQUE REFERENCES users(id),
  source_import_batch_id BIGINT REFERENCES import_batches(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  process_code TEXT,
  title TEXT NOT NULL,
  short_description TEXT,
  full_description TEXT,
  contact_email CITEXT NOT NULL,
  owner_professor_id BIGINT NOT NULL REFERENCES professor_registry(id),
  executing_unit_id BIGINT REFERENCES organizational_units(id),
  source_import_batch_id BIGINT REFERENCES import_batches(id),
  status TEXT NOT NULL CHECK (status IN ('draft', 'published', 'archived')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  starts_at DATE,
  ends_at DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  deactivated_at TIMESTAMPTZ,
  CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);

CREATE TABLE project_images (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  image_type TEXT NOT NULL CHECK (image_type IN ('cover', 'gallery')),
  image_url TEXT NOT NULL,
  alt_text TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_project_single_cover
  ON project_images(project_id)
  WHERE image_type = 'cover';

CREATE TABLE courses (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  unit_id BIGINT REFERENCES organizational_units(id),
  name TEXT NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('graduacao', 'pos')),
  code TEXT UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_areas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_area_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  area_id BIGINT NOT NULL REFERENCES project_areas(id),
  PRIMARY KEY (project_id, area_id)
);

CREATE TABLE project_course_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  course_id BIGINT NOT NULL REFERENCES courses(id),
  PRIMARY KEY (project_id, course_id)
);

CREATE TABLE import_row_errors (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  import_batch_id BIGINT NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  raw_payload JSONB NOT NULL,
  error_reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_import_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  import_batch_id BIGINT NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (project_id, import_batch_id)
);

CREATE TABLE project_change_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  changed_by_user_id BIGINT NOT NULL REFERENCES users(id),
  change_type TEXT NOT NULL CHECK (change_type IN ('manual_edit', 'status_change', 'import_override')),
  field_name TEXT NOT NULL,
  old_value JSONB,
  new_value JSONB,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE email_dispatch_requests (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  requested_by_user_id BIGINT NOT NULL REFERENCES users(id),
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  to_email CITEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  payload JSONB,
  status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'sent', 'failed', 'dead_letter')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_attempt_at TIMESTAMPTZ,
  last_error TEXT,
  provider_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ
);

CREATE TABLE ai_chat_sessions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_chat_messages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_sql_suggestions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id),
  question TEXT NOT NULL,
  generated_sql TEXT NOT NULL,
  validation_status TEXT NOT NULL CHECK (validation_status IN ('approved', 'rejected')),
  validation_errors JSONB,
  model_name TEXT,
  feedback_score SMALLINT CHECK (feedback_score BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_public_listing
  ON projects(is_active, status, published_at DESC);

CREATE INDEX idx_projects_title_trgm
  ON projects USING gin (title gin_trgm_ops);

CREATE INDEX idx_projects_owner_professor
  ON projects(owner_professor_id);

CREATE INDEX idx_projects_executing_unit
  ON projects(executing_unit_id);

CREATE INDEX idx_org_units_parent
  ON organizational_units(parent_unit_id);

CREATE INDEX idx_courses_unit
  ON courses(unit_id);

CREATE INDEX idx_project_area_links_area
  ON project_area_links(area_id);

CREATE INDEX idx_project_course_links_course
  ON project_course_links(course_id);

CREATE INDEX idx_import_batches_ref
  ON import_batches(reference_year, reference_term);

CREATE INDEX idx_import_row_errors_batch_row
  ON import_row_errors(import_batch_id, row_number);

CREATE INDEX idx_project_import_links_batch
  ON project_import_links(import_batch_id);

CREATE INDEX idx_project_change_logs_project_created
  ON project_change_logs(project_id, created_at DESC);

CREATE INDEX idx_project_change_logs_user_created
  ON project_change_logs(changed_by_user_id, created_at DESC);

CREATE INDEX idx_email_dispatch_status_next
  ON email_dispatch_requests(status, next_attempt_at);

CREATE INDEX idx_email_dispatch_user_created
  ON email_dispatch_requests(requested_by_user_id, created_at DESC);

CREATE INDEX idx_ai_sessions_user_created
  ON ai_chat_sessions(user_id, created_at DESC);

CREATE INDEX idx_ai_messages_session_created
  ON ai_chat_messages(session_id, created_at DESC);

CREATE INDEX idx_ai_sql_suggestions_user_created
  ON ai_sql_suggestions(user_id, created_at DESC);
```

---

## 13.6 Politica de retencao e custo (recomendado)

Para evitar crescimento inutil de dados operacionais:

1. `email_dispatch_requests`
   - manter 180 dias em tabela quente
   - arquivar registros antigos para storage frio

2. `ai_chat_messages`
   - manter 30 a 90 dias em tabela quente
   - truncar/arquivar por lote mensal

3. `ai_sql_suggestions`
   - manter 180 dias para auditoria de seguranca
   - anonimizar pergunta se houver requisito de privacidade

4. Job de manutencao
   - executar diariamente (janela noturna)
   - monitorar volume por tabela e latencia de consulta
