# SIEPA

Plataforma institucional para gestao, divulgacao e consulta de projetos academicos da UNIRIO.

Neste repositorio, o termo **projetos academicos** abrange principalmente:

- projetos de extensao
- projetos de iniciacao cientifica

---

## 1. Finalidade deste repositorio

Este `README.md` tem funcao tecnica. Ele resume:

- o objetivo do sistema
- o escopo funcional previsto para a V1
- o estado atual de implementacao do repositorio
- o roadmap tecnico de evolucao

Para a versao mais formal e academica do levantamento de requisitos, consultar `REQUISITOS.md`.

---

## 2. Visao geral do produto

O SIEPA foi concebido para centralizar informacoes sobre projetos academicos da universidade em um unico ambiente digital. A proposta e permitir que estudantes, docentes, gestores e visitantes consultem oportunidades e acompanhem informacoes institucionais com mais clareza, organizacao e rastreabilidade.

O sistema busca atender, de forma integrada, necessidades como:

- divulgacao publica de projetos
- identificacao de oportunidades para estudantes
- gestao de dados pelos docentes responsaveis
- atualizacao administrativa por meio de importacoes institucionais
- registro de alteracoes relevantes
- apoio a busca por linguagem natural

---

## 3. Escopo funcional da V1

O escopo previsto para a primeira versao inclui:

- catalogo publico de projetos academicos
- diferenciacao da modalidade do projeto, com destaque para extensao e iniciacao cientifica
- autenticacao por perfil de usuario
- consulta detalhada de projetos com filtros
- area autenticada para professores e administradores
- contato entre aluno e docente responsavel
- importacao administrativa de dados institucionais
- auditoria de alteracoes relevantes
- busca assistida por inteligencia artificial

Ficam fora do escopo da V1:

- aplicativo movel nativo
- gestao de bolsas e pagamentos
- processo completo de inscricao e selecao de candidatos
- substituicao dos sistemas academicos oficiais da instituicao

---

## 4. Perfis de acesso

| Perfil | Forma de acesso | Papel principal |
|---|---|---|
| Visitante | Sem login | Consulta publica do catalogo |
| Aluno | Login institucional Google | Consulta, busca assistida e manifestacao de interesse |
| Professor | Login institucional Google | Acompanhamento e edicao de projetos sob sua responsabilidade |
| Administrador | Login local com e-mail e senha | Rotinas administrativas e manutencao institucional |

### Regras fechadas de autenticacao

1. Alunos e professores usam autenticacao institucional via Google.
2. A distincao entre aluno e professor ocorre pela identificacao institucional do usuario.
3. Professores dependem de validacao em registro docente autorizado pelo sistema.
4. Administradores utilizam autenticacao local.

---

## 5. Estado atual do repositorio

Hoje o repositorio esta em uma fase parcial de implementacao.

### Ja implementado

- estrutura base da aplicacao FastAPI
- conexoes com PostgreSQL, Redis e RabbitMQ no ciclo de vida da aplicacao
- autenticacao local para administrador
- autenticacao Google para professor e aluno
- criacao de sessao com `access token` e `refresh token`
- renovacao de sessao, logout e consulta do usuario autenticado
- recuperacao de senha por codigo para acesso local
- publicacao em fila para envio de e-mail de recuperacao
- validacoes de seguranca e testes automatizados para fluxos centrais de autenticacao
- `schema.sql` com o modelo de dados planejado para dominios como projetos, importacoes, auditoria, contato e IA

### Parcial ou ainda nao implementado

- catalogo publico de projetos
- filtros de consulta por area, curso e unidade
- gestao de projetos pelo professor
- modulos administrativos alem da autenticacao
- worker de processamento de e-mails
- fluxo completo de solicitacoes de contato
- endpoints de busca assistida por IA
- endpoints publicos de monitoramento e modulos de catalogo

### Observacao importante sobre o estado atual

O modelo de dados ja contempla partes amplas do dominio, mas a API ainda nao expoe todos esses modulos. Atualmente, os routers ativos no `main.py` concentram-se principalmente em autenticacao e usuario autenticado.

---

## 6. Comportamentos atualmente refletidos no codigo

As decisoes abaixo representam o comportamento hoje visivel no repositorio:

- login local aceita apenas o perfil administrativo
- login Google atende professor e aluno
- quando o usuario autenticado via Google nao corresponde a um professor autorizado, o fluxo atual o trata como aluno
- professores dependem de correspondencia com o registro institucional de docentes ja carregado no banco
- recuperacao de senha esta voltada ao acesso local

Esses pontos devem permanecer coerentes com `REQUISITOS.md` e com a evolucao futura do produto.

---

## 7. Estrutura atual do projeto

```text
core/           # configuracao, seguranca, conexoes e logger
functions/      # funcoes utilitarias
repositories/   # acesso a dados
routes/         # endpoints HTTP
schemas/        # modelos de entrada e saida
services/       # regras de negocio
templates/      # templates de e-mail
tests/          # testes automatizados
main.py         # bootstrap da aplicacao
schema.sql      # definicao do banco de dados
```

Observacao:

- existem diretorios de rotas e servicos para dominios como `projects`, `courses` e `readonly`, mas esses modulos ainda nao foram concluidos

---

## 8. Stack atual

- Python
- FastAPI
- PostgreSQL
- Redis
- RabbitMQ
- Pydantic
- bcrypt
- Google OAuth
- pytest

---

## 9. Roadmap tecnico sugerido

### Fase 1 - Consolidacao da base autenticada

- estabilizar os fluxos atuais de autenticacao
- manter testes de seguranca e sessao
- padronizar mensagens, erros e documentacao minima dos endpoints existentes

### Fase 2 - Catalogo publico

- implementar consulta publica de projetos
- disponibilizar filtros por modalidade, area, unidade e curso
- publicar detalhamento de projetos

### Fase 3 - Gestao de projetos

- listar projetos do professor autenticado
- permitir edicao controlada por responsabilidade
- incluir imagens e vinculos academicos quando aplicavel
- registrar alteracoes para auditoria

### Fase 4 - Fluxos assincronos de contato

- registrar solicitacoes de contato
- concluir worker de processamento de e-mails
- permitir acompanhamento do status das solicitacoes

### Fase 5 - Rotinas administrativas

- importar dados institucionais em lote
- habilitar ou desabilitar projetos e usuarios
- manter estruturas de apoio do catalogo

### Fase 6 - Busca assistida por IA

- implementar o servico de interpretacao de perguntas em linguagem natural
- restringir o recurso a consultas seguras
- registrar historico de uso e validacao

---

## 10. Diretrizes de documentacao

Para evitar novas contradicoes entre codigo e documentacao:

- `REQUISITOS.md` deve representar a visao funcional e academica do produto
- `README.md` deve representar a visao tecnica do repositorio
- funcionalidades planejadas nao devem ser descritas como se ja estivessem prontas
- mudancas de regra de autenticacao ou escopo devem ser refletidas nos dois documentos

---

## 11. Referencias principais

Os documentos centrais do projeto passam a ser:

- `REQUISITOS.md` - visao funcional e academica do sistema
- `ARQUITETURA.md` - visao tecnica da arquitetura utilizada
