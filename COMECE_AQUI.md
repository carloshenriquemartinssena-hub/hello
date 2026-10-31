# Publicar o CRM 2 no Streamlit

1. Repositório: `carloshenriquemartinssena-hub/hello`; branch: `main`; arquivo principal: **streamlit_app.py** (ou **app.py**); Python: **3.12**.
2. No app `hello`, abra **Settings → Secrets** e copie `.streamlit/secrets.toml.example`, preenchendo seus valores. O formato é TOML: `CHAVE = "valor"`. Não envie `.env` ao GitHub.
3. Salve, reinicie o app se necessário e entre com `CRM_ADMIN_PASSWORD`. Não altere o app ou banco do CRM principal.

Para a automação, copie o mesmo bloco TOML para um único secret do GitHub Actions chamado **CRM2_SECRETS_TOML**, no repositório `hello`. Sem isso, o painel manual pode funcionar, mas a rotina diária não terá credenciais.

Se senha e tokens estiverem vazios no seu `.env`, execute `python iniciar.py --gerar-acesso`. O comando gera somente os três campos de acesso ausentes/vazios, preserva suas APIs e não imprime valores. Abra `.env` e copie os valores gerados para Secrets, entre aspas. `CRM_ADMIN_PASSWORD` é sua senha para entrar no painel; `CRM_SESSION_SECRET` e `CRM_WORKER_TOKEN` são chaves internas do próprio CRM. Não são fornecidas pelo Gmail ou Supabase. Em Secrets do Streamlit, use `CRM_ENV = "production"`; `CRM_PUBLIC_URL = ""` é válido.

O banco é o PostgreSQL do Supabase, não a URL HTTPS da API. O modelo de Secrets indica o formato correto. Você não precisa de Render, Northflank ou GitHub Pages para este modo.

Se aparecer **DB_CERTIFICATE**, siga [CERTIFICADO_SUPABASE.md](CERTIFICADO_SUPABASE.md): o CRM aceita o certificado raiz oficial como texto multilinha em `CRM_DATABASE_CA_CERT`, sem remover a verificação TLS.

## Teste completo com uma empresa real

Em Encontrar empresas, busque 25 resultados para um nicho/cidade e clique Atualizar resultado até concluir. A consulta pode consumir créditos Apify. Em Campanha & cadência, salve a mensagem inicial e a validade da oferta; a campanha geral pode continuar pausada. Em Meus leads, marque uma empresa nova com email válido e abra **Teste real: somente 1 email, sem follow-ups**. Confira destino, texto e anexos; confirme e use **Enviar teste real de 1 empresa**. A aprovação desse botão vale somente para esse envio inicial, não habilita a campanha geral nem aprova os outros textos.

O teste respeita cotas e bloqueios, envia no máximo um email inicial e pausa o contato sem agendar follow-ups. Repetir o clique no mesmo contato não envia novamente. Se a fonte não fornecer email, o teste não envia nada; não invente endereços. Se houver timeout de envio, confira Gmail Enviados antes de qualquer ação: o sistema mantém a reserva e não repete automaticamente.

O resultado de envio confirmado pelo Gmail não comprova entrega na caixa de entrada ou leitura pelo destinatário. Verifique Atividades e a pasta Enviados. As credenciais nos Secrets do Streamlit/GitHub não ficam acessíveis ao assistente nesta conversa; esta preparação não representa execução de um teste real na sua conta.

## Sua busca do Apify não apareceu no CRM?

Reinicie o app para carregar a versão atual. Em Encontrar empresas, abra **Recuperar busca já executada no Apify**, cole somente o **Run ID** da execução existente e informe cidade/nicho. Se for uma execução antiga já concluída no CRM, marque **Reavaliar**. Isso não inicia outra busca. Confira os contadores e os motivos de descarte: **sem email válido, a empresa não é importada**. O Maps pode não fornecer emails; nesse caso, será necessária outra fonte de contato.

Para salvar campanha, a mensagem agora informa a regra exata caso algum campo esteja inválido. Se a oferta tiver mais de sete dias ou você tentar habilitar sem aprovar, corrija o campo e salve novamente; a campanha anterior não é apagada.

No banco existente, o arquivo complementar `supabase/002_runtime_indexes.sql` protege a unicidade de envios, adiciona índices e alinha sequências de IDs sem apagar registros. Execute apenas no projeto do CRM 2. Não execute o dump marcado como “context only”.
