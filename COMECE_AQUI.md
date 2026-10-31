# Conectar o CRM em três passos

**Alternativa ao Render:** veja [NORTHFLANK.md](NORTHFLANK.md). O mesmo código Docker funciona; você só troca a hospedagem e a URL pública, preservando o Supabase e suas credenciais.

**O arquivo é `.env`, sem `.txt` no final.** Ele fica na mesma pasta de `iniciar.py`. Já foi criado neste ambiente; não envie esse arquivo ao GitHub nem compartilhe suas chaves no chat.

1. Abra `.env` e preencha:
   - `CRM_DATABASE_URL`: conexão PostgreSQL do novo Supabase, em **Connect → Session pooler**. Não é a chave `anon` nem a URL da API. Mantenha `sslmode=verify-full` na URI.
   - `CRM_APIFY_TOKEN`: token do Apify para captar empresas.
   - `CRM_GMAIL_CLIENT_ID`, `CRM_GMAIL_CLIENT_SECRET` e `CRM_GMAIL_REFRESH_TOKEN`: credenciais OAuth do Gmail remetente. O refresh token é diferente de uma senha comum ou senha de aplicativo.
2. Confira: `python iniciar.py --verificar`.
3. Inicie: `python iniciar.py`. Entre com a senha `CRM_ADMIN_PASSWORD` que está no `.env`.

Se necessário, instale antes: `python -m pip install -r requirements.txt`. No ambiente virtual deste projeto, use `.venv/bin/python` no lugar de `python`.

As chaves de acesso ao painel são geradas automaticamente. A verificação não mostra valores nem envia emails. Um `.env` já preenchido é preservado.

## Para ficar online no Render

No **Render → seu serviço → Environment → Add from .env**, importe as variáveis usando o editor seguro do Render. Se a opção não aparecer, adicione as mesmas variáveis individualmente. Não envie `.env` ao repositório.

No Render, use `CRM_ENV=production`, preencha `CRM_PUBLIC_URL` com a URL HTTPS final e use o Supabase em `CRM_DATABASE_URL`. O projeto já inclui `render.yaml` e `Dockerfile`. A conta do Render ainda precisa estar conectada ao repositório com o código atualizado.

O agendamento precisa de dois secrets no GitHub Actions: `CRM_BASE_URL` (URL HTTPS do Render) e `CRM_WORKER_TOKEN` (mesmo valor do `.env`/Render). A rotina respeita 09h–10h de Brasília e 30 novos contatos + 30 follow-ups por dia.

Antes de habilitar a campanha, teste captação e sincronização do Gmail no painel, personalize os quatro emails e defina a validade. Abrir o CRM não executa esses passos automaticamente.

Para gerar as credenciais do Gmail, consulte somente a seção “Conectar Gmail e trocar remetente” de `README.md`. Não é necessário reler o guia inteiro.

A automação prepara o servidor às 08:50/08:55 de Brasília e antes dos lotes seguintes, sem enviar emails. Os botões manuais não passam por essa preparação. A primeira abertura de um Render em repouso ainda pode demorar.

Ao importar o `.env` local no Render, confira: `CRM_ENV=production`, `CRM_DATABASE_URL` PostgreSQL do Supabase com `sslmode=verify-full` e `CRM_PUBLIC_URL` com a URL HTTPS do seu serviço. Não mantenha a conexão SQLite do modelo local.
