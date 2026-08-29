# PRISMA — API

Backend do **PRISMA (Plataforma de Referência e Integração de Saberes e Mediação Acadêmica)**, sistema da UNIRIO para centralizar, divulgar e administrar projetos acadêmicos importados do SIE.

Este documento descreve o que existe hoje no repositório. Funcionalidades futuras não são apresentadas como concluídas.

## Escopo atual

- catálogo público de projetos, detalhes, filtros e catálogos auxiliares;
- autenticação institucional via Google para a comunidade acadêmica;
- autenticação local para administradores;
- sessões com access token, refresh token e Redis;
- área de professor/técnico para consultar e complementar projetos sob sua responsabilidade;
- edição de descrição, imagem de capa e oportunidades vinculadas aos projetos;
- administração de usuários, visibilidade/publicação de projetos, métricas e execuções de sincronização;
- sincronização periódica de dados institucionais com a API do SIE.

## Fora do escopo do projeto-base

- notificações internas;
- envio automático de e-mails;
- recuperação de senha por e-mail;
- filas de mensageria destinadas a e-mail;
- inscrição e seleção completa de candidatos;
- gestão de bolsas ou pagamentos;
- substituição do SIE e de outros sistemas oficiais.

O e-mail institucional continua sendo usado como identificador de acesso, vínculo de pessoas e informação pública de contato dos responsáveis pelo projeto. Isso não representa um módulo de envio automático de mensagens.

## Perfis

| Perfil | Acesso | Capacidades principais |
|---|---|---|
| Visitante | Sem autenticação | Consultar catálogo e detalhes públicos |
| Aluno | Google institucional | Acessar o sistema como membro da comunidade acadêmica |
| Professor/técnico | Google institucional e vínculo importado | Gerenciar conteúdo editorial de seus projetos |
| Administrador | E-mail e senha locais | Administrar usuários, projetos e acompanhar sincronizações |

## API disponível

A aplicação usa o prefixo `/api/v1/unirio` e expõe, entre outros, estes grupos:

- `/auth`: login local, OAuth Google, sessão, logout e renovação;
- `/projects` e `/me/projects`: catálogo público e gestão pelo responsável;
- `/catalogues`: áreas temáticas, centros, unidades e cursos;
- `/admin`: métricas, usuários, projetos e histórico da sincronização.

Com a aplicação em execução, a documentação OpenAPI fica em:

```text
http://localhost:5685/api/v1/unirio/docs
```

## Tecnologias

- Python e FastAPI;
- PostgreSQL;
- Redis;
- Pydantic;
- Google OAuth;
- pytest;
- Docker Compose.

## Estrutura

```text
core/          configuração, segurança e conexões
integrations/  integração com Google e SIE
repositories/ acesso ao PostgreSQL
routes/        endpoints HTTP
schemas/       contratos de entrada e saída
services/      regras de negócio
tests/         testes automatizados
workers/       sincronização periódica com o SIE
main.py        inicialização da API
schema.sql     modelo inicial do banco
```

## Execução com Docker

1. Copie `.env.example` para `.env` e preencha as credenciais necessárias.
2. Na pasta deste repositório, execute:

```bash
docker compose up --build
```

O Compose inicia API, PostgreSQL, Redis, preparação do schema e o worker de sincronização. RabbitMQ não faz parte da arquitetura atual.

## Testes

```bash
python -m pytest
```

## Regra de documentação

O código e este README representam o produto implementado. Ideias ainda não desenvolvidas devem aparecer no TCC como trabalhos futuros, limitações ou itens planejados — nunca como funcionalidades disponíveis.
