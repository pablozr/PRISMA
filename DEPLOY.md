# Deploy de Produção — PRISMA

Runbook do stack de produção (`docker-compose.prod.yml`), com o override opcional
de HTTPS (`docker-compose.prod.https.yml`). O modo de desenvolvimento continua em
`docker-compose.yml` e não é afetado por este documento.

Este documento não contém segredos. Nunca faça commit de `.env.prod`.

## 1. Layout de checkout

Os dois repositórios devem ficar lado a lado, pois o build da imagem web usa o
contexto irmão:

```
<parent>/
  PRISMA/            # este repositório (contexto de build da API)
  prisma-front/      # frontend (Dockerfile + nginx/) — contexto de build da web
```

Os comandos abaixo são executados a partir de `<parent>/PRISMA`.

## 2. Serviços, redes e volumes

| Serviço | Imagem | Rede | Porta no host |
|---|---|---|---|
| `prisma-web` | `prisma-web:local` (build `../prisma-front`) | `public`, `internal` | `80` (e `443` no override) |
| `prisma-api` | `prisma-api:local` (build `.`) | `public`, `internal` | — |
| `prisma-worker` | `prisma-api:local` (mesmo build) | `public`, `internal` | — |
| `prisma-postgres` | `postgres:16` | `internal` | — |
| `prisma-redis` | `redis:7-alpine` | `internal` | — |
| `prisma-migrations` | `postgres:16` | `internal` | — (one-shot, `restart: "no"`) |

- `public` é uma bridge comum: dá saída para Google OAuth (api) e SIE (worker).
- `internal` é `internal: true`: Postgres, Redis e migrações não têm saída nem
  entrada externas.
- Volumes nomeados persistentes: `prisma_postgres-data`, `prisma_redis-data`,
  `prisma_project-covers`.
- Capas: a API grava em `/app/project-covers` (rw) e a web lê o mesmo volume em
  `/srv/project-covers` (ro). URL pública: `/assets/project-covers/<arquivo>`.

### Modo desenvolvimento

Produção usa o volume nomeado `prisma_project-covers` e o backend não depende do
código do frontend. O `docker-compose.yml` de desenvolvimento é a **exceção
intencional**: ele mantém o bind
`../prisma-front/src/assets/project-covers:/app/project-covers` para que o Angular
rodando com `npm start` no host continue enxergando as capas recém-enviadas em
`src/assets/project-covers`, sem passo manual. Não replique esse bind em produção:
lá as capas ficam no volume e são servidas pela web via `/srv/project-covers`.

## 3. Arquivo de ambiente `.env.prod`

Crie `<parent>/PRISMA/.env.prod` (ignorado pelo git) com valores reais. Exemplo
com placeholders — não versionar:

```dotenv
# --- Banco ---
DB_USER=prisma
DB_PASSWORD=troque-por-senha-forte
DB_NAME=prisma

# --- Aplicação ---
SECRET_KEY=troque-por-chave-aleatoria-longa
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080
ALLOWED_GOOGLE_DOMAINS=edu.unirio.br,unirio.br
ALLOWED_EMAIL_DOMAIN=edu.unirio.br

# --- Google OAuth (Console > Credenciais > URIs de redirecionamento) ---
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_REDIRECT_URI=https://prisma.exemplo.br/api/v1/unirio/auth/google/callback

# --- URLs do frontend após login ---
FRONTEND_AUTH_SUCCESS_URL=https://prisma.exemplo.br/
FRONTEND_AUTH_ERROR_URL=https://prisma.exemplo.br/signin

# --- CORS (CSV, origens explícitas, sem "*") ---
CORS_ALLOWED_ORIGINS=https://prisma.exemplo.br

# --- Worker de sincronização SIE (obrigatórias no worker) ---
SIE_EMAIL=prisma@unirio.br
SIE_PASSWORD=troque-por-senha-sie
# SIE_API_BASE_URL=https://api.unirio.br/api/v2
# SIE_SYNC_PAGE_SIZE=500
# SIE_SYNC_INTERVAL_DAYS=15
# SIE_SYNC_RETRY_SECONDS=300

# --- Somente para o override HTTPS ---
DOMAIN=prisma.exemplo.br
```

Observações:

- `ENVIRONMENT=production` é fixado no compose (não vem do arquivo).
- Em produção os cookies são emitidos com `Secure`; portanto use HTTPS em uso real.
- No Google Cloud Console cadastre exatamente:
  `https://<DOMAIN>/api/v1/unirio/auth/google/callback`.
  Não teste login/OAuth por HTTP em produção: os cookies `Secure` exigem HTTPS.
- `CORS_ALLOWED_ORIGINS` não aceita `*`. Com a API atrás do mesmo domínio (nginx),
  o valor costuma ser apenas a origem pública do frontend.

## 4. Primeiro deploy (HTTP apenas para provisionar TLS)

Pré-requisitos: Docker Engine e Docker Compose `>= 2.24` (o override HTTPS usa a
tag `!override`). Confira com `docker compose version`.

O Dockerfile do frontend usa npm 11.6.2 para executar `npm ci` com o lock atual;
o npm 10 da imagem-base Node 22 rejeita esse lock. Não há fallback para instalação
sem lock. Atualize o lock com npm 11 ao alterar dependências.

```sh
cd <parent>/PRISMA

# valida a configuração sem imprimir valores
docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet

# build + subida
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build

# estado e logs
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f prisma-migrations
```

Na primeira subida o `prisma-migrations` aplica `schema.sql` (somente se a tabela
`users` não existir) e, em seguida, as migrações idempotentes. A API só sobe após
as migrações concluírem (`service_completed_successfully`) e Postgres/Redis
ficarem saudáveis.

O HTTP inicial serve apenas para conferir infraestrutura e emitir certificados.
Não exponha login/OAuth a usuários nem considere o sistema pronto antes de ativar
HTTPS: cookies de produção têm `Secure` e não funcionam em HTTP remoto.

## 5. Migrações

O serviço `prisma-migrations`:

1. cria o schema base **apenas** quando o banco está vazio;
2. aplica sempre `migration_sie_sync_safety.sql`;
3. aplica sempre `migration_user_role_source.sql`.

**Não executadas automaticamente** (de propósito):

- `migration_sie_publish_projects.sql` — reescreve `publication_status`,
  `is_visible` e `published_at` de **todos** os projetos do SIE a cada execução.
  Isso muta estado editorial e não pode rodar em todo restart. Revise e rode
  manualmente quando realmente quiser publicar os itens importados do SIE.
- `migration_responsible_user_id.sql` — legado, incompatível com o schema atual
  (a responsabilidade vive em `project_participations`/permissões). Ignorar.

Rodar uma migração manual (com backup antes):

```sh
# publicação em massa — somente após revisão explícita
# OBS: o .env.prod é lido pelo docker compose, não é exportado para o shell.
# Por isso as credenciais são resolvidas dentro do container via POSTGRES_*.
docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec -T prisma-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f -' \
  < migration_sie_publish_projects.sql
```

Nunca edite uma migração já aplicada em produção; crie uma nova.

## 6. HTTPS

O stack HTTP já funciona sozinho. Só aplique o override depois que o certificado
existir para `<DOMAIN>`. Como o nginx entregue não expõe `/.well-known/acme-challenge`,
emita o certificado em modo `standalone` (ou use um plugin DNS):

```sh
cd <parent>/PRISMA

# 1) DNS do domínio já apontando para o servidor e stack HTTP no ar.

# 2) leia o DOMAIN do .env.prod: o docker compose o consome, mas NÃO o exporta
#    para o shell, então nunca use "$DOMAIN" sem carregá-lo.
DOMAIN=$(sed -n 's/^DOMAIN=//p' .env.prod | head -n1)
[ -n "$DOMAIN" ] || { echo "DOMAIN ausente em .env.prod"; exit 1; }

# 3) libere a porta 80 parando a web e emita o certificado:
docker compose --env-file .env.prod -f docker-compose.prod.yml stop prisma-web
docker run --rm -p 80:80 -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d "$DOMAIN" --agree-tos -m admin@unirio.br

# 4) suba com HTTPS (publica 80 e 443, monta /etc/letsencrypt e o template TLS)
docker compose --env-file .env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.https.yml up -d --build
```

- O override publica `80:80` e `443:443` com `!override`, evitando porta duplicada.
- O template `nginx/https.conf.template` redireciona `http -> https` e usa
  `/etc/letsencrypt/live/<DOMAIN>/{fullchain,privkey}.pem`.
- Renovação: rode `certbot renew` no host (cron/systemd) e recarregue o nginx:
  `docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.https.yml exec prisma-web nginx -s reload`.
- Se o certificado ainda não existir, o override falha ao subir — volte ao HTTP
  (`docker compose ... -f docker-compose.prod.yml up -d`) enquanto provisiona.

## 7. Comandos do dia a dia

### Hostinger VPS com Caddy existente

Se o servidor já executa o projeto `caddy` e sua rede externa é
`caddy_default_network`, use `docker-compose.prod.caddy.yml` no lugar do
override HTTPS. O Caddy existente continua responsável pelas portas 80/443 e
pelos certificados. O serviço `prisma-web` entra na rede do Caddy sem publicar
portas no host; API, PostgreSQL e Redis permanecem sem portas públicas.

Antes da subida, confirme que a rede existe com `docker network inspect
caddy_default_network` e que o domínio aponta para o IP da VPS. Configure
`.env.prod` com o mesmo domínio nas URLs públicas e no redirect do Google.
Nesta VPS, o endereço escolhido é `prisma.projetosccetunirio.com.br`:

```dotenv
GOOGLE_REDIRECT_URI=https://prisma.projetosccetunirio.com.br/api/v1/unirio/auth/google/callback
FRONTEND_AUTH_SUCCESS_URL=https://prisma.projetosccetunirio.com.br/
FRONTEND_AUTH_ERROR_URL=https://prisma.projetosccetunirio.com.br/signin
CORS_ALLOWED_ORIGINS=https://prisma.projetosccetunirio.com.br
```

```sh
docker compose --env-file .env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.caddy.yml config --quiet
docker compose --env-file .env.prod \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.caddy.yml up -d --build
```

Adicione um bloco de site ao Caddyfile existente, preservando os outros blocos:

```caddyfile
prisma.projetosccetunirio.com.br {
    reverse_proxy prisma-web:80
}
```

Valide e recarregue o Caddy após editar o arquivo montado no container:

```sh
docker exec caddy-caddy-1 caddy validate --config /etc/caddy/Caddyfile
docker exec caddy-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

Não aplique `docker-compose.prod.https.yml` nesse servidor, pois ele tentaria
publicar 80/443 novamente. Para comandos posteriores de `ps`, `logs` e `up`,
inclua sempre os dois arquivos Compose acima.

Sempre a partir de `<parent>/PRISMA`. Prefixo comum:
`docker compose --env-file .env.prod -f docker-compose.prod.yml`.

| Ação | Comando |
|---|---|
| Build das imagens | `... build` |
| Build sem cache | `... build --no-cache prisma-api prisma-worker prisma-web` |
| Subir/atualizar | `... up -d --build` |
| Status | `... ps` |
| Logs de um serviço | `... logs -f prisma-api` |
| Reiniciar um serviço | `... restart prisma-api` |
| Parar sem remover | `... stop` |
| Remover containers (mantém volumes) | `... down` |
| Remover tudo, **inclusive dados** | `... down -v` (destrutivo) |
| Atualizar imagens de terceiros | `... pull prisma-postgres prisma-redis` |
| Rodar migrações de novo | `... run --rm prisma-migrations` |

Atualização de código (api/worker/web):

```sh
cd <parent>/PRISMA && git pull
cd ../prisma-front && git pull && cd ../PRISMA
docker compose --env-file .env.prod -f docker-compose.prod.yml build --no-cache prisma-api prisma-worker prisma-web
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

> Faça backup do banco **antes** de qualquer atualização que rode migrações.

## 8. Backup e restauração

Sempre faça backup antes de migrar/atualizar. O `pg_dump` gera um snapshot
consistente e **não** exige parar a API. Pare `prisma-api` e `prisma-worker`
apenas na **restauração**, para evitar escrita concorrente.

OBS: `.env.prod` é lido pelo `docker compose` para interpolar o compose, mas não é
exportado para o shell. Não use `$DB_USER`/`$DB_NAME` no host — resolva as
credenciais dentro do container via `POSTGRES_USER`/`POSTGRES_DB`.

### Banco — shell POSIX (sh/bash)

```sh
mkdir -p backups
docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec -T prisma-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "backups/prisma-$(date +%F).dump"
```

### Banco — PowerShell (cuidado com binário)

No Windows PowerShell 5.1, `>` (`Out-File`) grava texto, corrompendo dumps
binários. Faça o dump dentro do container e copie com `docker cp`. Use aspas
simples em `sh -c` para o PowerShell não expandir `$POSTGRES_*` para vazio:

```powershell
docker compose --env-file .env.prod -f docker-compose.prod.yml `
  exec -T prisma-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/prisma.dump'
docker cp prisma-postgres:/tmp/prisma.dump .\backups\prisma.dump
```

### Restauração

sh/bash:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml stop prisma-api prisma-worker
cat backups/prisma-2026-01-01.dump | docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec -T prisma-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists'
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

PowerShell:

```powershell
docker cp .\backups\prisma.dump prisma-postgres:/tmp/prisma.dump
docker compose --env-file .env.prod -f docker-compose.prod.yml stop prisma-api prisma-worker
docker compose --env-file .env.prod -f docker-compose.prod.yml `
  exec -T prisma-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/prisma.dump'
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

`--clean --if-exists` apaga objetos antes de recriar. Confirme que está restaurando
no banco correto e mantenha o dump íntegro.

### Capas (volume `prisma_project-covers`)

```sh
docker run --rm -v prisma_project-covers:/data -v "$PWD/backups":/backup alpine \
  tar czf /backup/project-covers.tgz -C /data .
```

Restaure as capas junto com o banco, antes de retomar API e web, usando um arquivo
de backup confiável; a extração sobrescreve arquivos de mesmo nome. Revise seu
conteúdo antes de executar e mantenha o volume existente separado se necessário:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml stop prisma-api prisma-web
docker run --rm -v prisma_project-covers:/data -v "$PWD/backups":/backup alpine \
  tar xzf /backup/project-covers.tgz -C /data
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

## 9. Persistência de volumes

`docker compose ... down` preserva os volumes nomeados. Apenas `down -v` remove
os dados. Confirme antes com `docker volume ls | grep prisma`. Não use `down -v`
em produção sem backup e intenção explícita.

## 10. Verificação pós-deploy

```sh
# status de saúde (api e postgres/redis devem aparecer como healthy)
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

# healthcheck interno da API (não é exposto pelo nginx)
docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec prisma-api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5685/health').read())"

# docs, OpenAPI e auth via web
curl -I http://localhost/api/v1/unirio/docs
curl -s http://localhost/api/v1/unirio/openapi.json | head
curl -sI http://localhost/api/v1/unirio/auth/google/start

# capa: envie pelo endpoint autenticado e busque a URL pública
curl -I http://localhost/assets/project-covers/<arquivo>.png
```

No override HTTPS, troque `http://localhost` por `https://<DOMAIN>`.

## 11. Segurança

- Nunca versione `.env.prod`; restrinja permissões (`chmod 600 .env.prod`).
- Gere `SECRET_KEY` longa e aleatória, e rotacione ao trocar pessoas.
- Postgres e Redis não publicam portas no host.
- `CORS_ALLOWED_ORIGINS` sempre com origens explícitas, sem `*`.
- Use o override HTTPS em produção; os cookies exigem `Secure`.
- Valide alterações sem vazar segredos:
  `docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet`.
- Faça backup antes de migrar e guarde cópias fora do servidor.
