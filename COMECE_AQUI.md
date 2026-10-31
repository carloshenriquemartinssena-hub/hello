# Publicar o CRM 2 no Streamlit

1. Repositório: `carloshenriquemartinssena-hub/hello`; branch: `main`; arquivo principal: **streamlit_app.py** (ou **app.py**); Python: **3.12**.
2. No app `hello`, abra **Settings → Secrets** e copie `.streamlit/secrets.toml.example`, preenchendo seus valores. O formato é TOML: `CHAVE = "valor"`. Não envie `.env` ao GitHub.
3. Salve, reinicie o app se necessário e entre com `CRM_ADMIN_PASSWORD`. Não altere o app ou banco do CRM principal.

Para a automação, copie o mesmo bloco TOML para um único secret do GitHub Actions chamado **CRM2_SECRETS_TOML**, no repositório `hello`. Sem isso, o painel manual pode funcionar, mas a rotina diária não terá credenciais.

O banco é o PostgreSQL do Supabase, não a URL HTTPS da API. O modelo de Secrets indica o formato correto. Você não precisa de Render, Northflank ou GitHub Pages para este modo.
