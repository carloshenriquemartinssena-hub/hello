# Alternativa de hospedagem: Northflank

O CRM já é compatível com um serviço Docker no Northflank. O banco e os anexos continuam no Supabase; não é necessário disco persistente na hospedagem.

## Criação do serviço

1. Entre em https://app.northflank.com e conecte seu GitHub.
2. Crie um projeto e um serviço **Combined** (build + execução) usando o repositório `carloshenriquemartinssena-hub/hello`, branch `main`.
3. Use o **Dockerfile** da raiz. Publique a porta **10000**, protocolo HTTP, com acesso público HTTPS.
4. Se sua conta oferecer **Sandbox/gratuito**, selecione essa opção. Não selecione recursos pagos nem confirme cobrança. A disponibilidade e exigências de verificação devem ser conferidas no painel: não foram verificadas nesta conta.
5. Importe suas variáveis `.env` nas variáveis de execução do serviço e faça o deploy. Não envie `.env` aos arquivos do repositório.

## Conferir somente estes campos

- `CRM_ENV=production`.
- `CRM_DATABASE_URL` deve ser uma **URI PostgreSQL** copiada de Supabase → Connect → Session pooler, com `sslmode=verify-full`. A URL `https://…supabase.co` não serve como conexão de banco. Se necessário, configure o certificado raiz oficial conforme `README.md`; não desative a verificação TLS.
- `CRM_PUBLIC_URL` deve ser a URL **HTTPS pública real desse serviço**, sem barra final. Não use GitHub Pages.
- Mantenha os valores de Gmail, Apify, senha e tokens que você já preparou. O arquivo `.env.northflank.example` é apenas uma referência sem credenciais; não substitua valores já preenchidos por campos vazios do modelo.

Quando a hospedagem indicar que o serviço está ativo, `/healthz` deve responder `{"status":"ok","app":"crm2-brasil"}`. A campanha permanece com o estado salvo no seu banco; publicar não aprova nem habilita os emails automaticamente.

## Automação

Em GitHub → repositório → Settings → Secrets and variables → Actions, configure `CRM_BASE_URL` com a nova URL HTTPS e `CRM_WORKER_TOKEN` com o mesmo token do serviço. As chamadas de preparação e os lotes continuam funcionando sem alteração de código. O modo manual não espera a preparação.

## Acesso e limitações desta entrega

Nenhum serviço Northflank foi criado ou contratado pelo assistente: não há conta autorizada, token de administração ou plugin Northflank acessível nesta sessão. A página de preços não pôde ser consultada pela política de rede do ambiente; o plano e eventuais requisitos de cartão precisam ser confirmados na sua conta antes de usar. Não existe garantia de disponibilidade gratuita ou de horário de ativação.

Se o painel exigir pagamento ou cartão para a opção disponível, não confirme: essa opção não atende à sua preferência de não pagar.
