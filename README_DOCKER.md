# Vértice · CRM 2 Brasil

**Configuração simplificada:** leia [COMECE_AQUI.md](COMECE_AQUI.md). O arquivo privado de conexão é `.env`; inicie com `python iniciar.py`.

CRM independente para prospectar pequenas e médias empresas brasileiras sem website. Backend Python/FastAPI, painel web responsivo em português, temas claro/escuro e PostgreSQL no Supabase. Não utiliza Streamlit nem qualquer banco, conta ou processo do CRM principal.

## O que já está implementado

- Painel com indicadores reais, base pesquisável e paginação, edição de contatos/notas, seleção e alteração de status em lote, exclusão, importação/exportação CSV.
- Captação Google Maps via Apify com filtros locais: país BR, sem website informado, 50–400 avaliações, sem encerramento informado. Sugestões de nichos locais, sem promessa de conversão.
- Deduplicação por Google Place ID, email normalizado e telefone brasileiro. Exclusões são lógicas para preservar histórico e impedir recaptura. Não é possível identificar com certeza empresas sem identificador, email ou telefone; nesses casos, confira nome/cidade antes de adicionar manualmente.
- Mensagem inicial + follow-ups 1/2/3. Personalização por `{empresa}`, `{cidade}` e `{validade}`; remetente configurável; links, imagens no corpo e anexos.
- Até **60 emails/dia: 30 novos contatos + 30 follow-ups**, contando envios manuais, agendados, reservas e resultados incertos. Limites podem ser reduzidos no modelo, não aumentados além dessas cotas.
- Antes dos envios, verifica respostas no Gmail (conversas anteriores e mensagens do endereço do lead). Qualquer resposta, inclusive um pedido de remoção, interrompe a sequência e bloqueia novos follow-ups. “Sem interesse” também cria bloqueio permanente.
- Trava de execução no banco, unicidade por lead/etapa e reserva persistida antes do envio. Timeout/resultado ambíguo pausa o lead e mantém a cota, sem reenvio automático. O processamento para se a caixa de entrada não puder ser verificada.
- Automação GitHub Actions às **09:00, 09:20 e 09:40 de Brasília**, em lotes de até 20. O backend recusa disparos automáticos fora das 09:00–10:00. O botão manual funciona dentro da validade da campanha, sem restrição de horário e com as mesmas cotas.

O painel inicia vazio e com envios pausados. Não foram enviados emails nem consultados leads reais durante o desenvolvimento. Os textos de exemplo podem ser substituídos pelos seus antes da ativação. A comparação de R$ 2.500–3.000 é uma faixa ilustrativa, depende do escopo e deve ser revisada por você. A oferta de R$ 700 tem início/fim explícitos, até sete dias, sem renovação automática. Após o follow-up 3 não há promessa de novo contato.

## Desenvolvimento local

Requer Python 3.12. Execute na raiz deste checkout, sem criar worktree: cada tarefa na nuvem já é isolada.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn crm.main:app --host 127.0.0.1 --port 8001
```

Sem variáveis, usa SQLite em `data/crm2.db`, sem integração externa. O acesso sem senha é permitido somente em desenvolvimento e em loopback. Para acesso remoto, configure a autenticação e use produção. Não use `http.server`: ele não oferece a API nem a proteção do backend.

O app carrega automaticamente `.env` na raiz do projeto. As variáveis do serviço/terminal têm prioridade. `.env.example` é o modelo sem credenciais. `python iniciar.py` cria `.env` se ele não existir e gera as chaves de acesso ao painel, sem sobrescrever arquivos existentes. Nunca envie `.env` ao GitHub. Use `python iniciar.py --verificar` para conferir conexão de banco e campos pendentes sem enviar emails.

```bash
.venv/bin/python -m pytest -q
node --check crm/static/app.js
```

Os testes de backend não acessam Gmail/Apify: simulam provedores e verificam limites, respostas, cadência, concorrência, falhas, autenticação e CRUD. Os testes de navegador ficam em `scripts/browser_smoke.py`; execute com o servidor local ativo e Playwright/Chromium instalado. Usam somente registros identificados como teste e os removem ao terminar.

## 1. Integrar sua outra conta Supabase

1. Crie um **novo projeto**, exclusivo do CRM Brasil, na conta desejada. Não use o projeto do CRM principal.
2. Abra o **SQL Editor** e execute integralmente [supabase/schema.sql](supabase/schema.sql). O script cria apenas tabelas `crm2_*`, índices, bloqueio de execução e RLS. Pode ser repetido para a instalação inicial; não migra estruturas de versões antigas.
3. As tabelas não têm políticas públicas. `anon` e `authenticated` não recebem acesso. O navegador nunca recebe chave Supabase nem senha do banco. Apenas o backend usa a conexão PostgreSQL do papel proprietário.
4. Em **Connect**, copie a URI PostgreSQL. Para o Render, prefira o **Session pooler (porta 5432)** quando a conexão direta IPv6 não estiver disponível. Use `postgresql+psycopg://` no começo, encode caracteres especiais da senha e mantenha `sslmode=verify-full`.
5. Configure `CRM_DATABASE_URL` no Render. Exemplo sem credenciais reais:

```text
postgresql+psycopg://postgres.PROJECT:SENHA_URL_ENCODED@HOST_DO_SESSION_POOLER:5432/postgres?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt
```

Se a cadeia do certificado do seu projeto não estiver no trust store do sistema, baixe o certificado raiz **oficial** nas configurações SSL do Supabase, adicione-o como Secret File no Render e ajuste `sslrootcert=/etc/secrets/NOME_DO_CERTIFICADO`. Preserve a verificação de hostname e certificado; não use `sslmode=disable` ou `no-verify`.

O backend exige PostgreSQL com `sslmode=verify-full` em produção e não cria tabelas PostgreSQL automaticamente: execute o SQL antes de publicar. Não há migração automática dos dados do SQLite para a nuvem; exporte/importe o CSV para transferir os cadastros ainda não contatados. Histórico de envios e bloqueios devem ser migrados separadamente antes de qualquer transferência de operação ativa.

## 2. Hospedar no Render

O GitHub hospeda o **código**; GitHub Pages não executa Python nem protege os dados. O Render executa o painel/backend e o Supabase mantém dados, anexos e histórico. O banco continua existindo após reinícios do Render.

1. Envie este código para o repositório `hello` ou outro repositório exclusivo. Conecte o GitHub à conta Render desejada.
2. Crie um Blueprint a partir de [render.yaml](render.yaml). Ele usa Docker, Python 3.12 e o plano `free`. A disponibilidade do plano depende da conta Render; o serviço pode entrar em repouso e está sujeito às cotas gratuitas. Não há serviço contratado por este código.
3. Preencha as variáveis abaixo. `CRM_SESSION_SECRET` e `CRM_WORKER_TOKEN` são gerados pelo Blueprint; mantenha valores estáveis entre reinícios. A senha do painel precisa ter 16+ caracteres, e os tokens 32+.
4. Configure `CRM_PUBLIC_URL` com o endereço HTTPS final do serviço, sem barra final. Se mudar o domínio, atualize essa variável. Os cookies de produção exigem HTTPS; a origem das alterações no painel é validada.
5. Confirme `/healthz` com status `ok`, entre com a senha e verifique **Configurações**. Variável presente não prova autorização do provedor; teste uma captação e a sincronização da caixa antes de habilitar envios.

| Variável | Uso |
| --- | --- |
| `CRM_ENV=production` | Ativa exigências de banco e autenticação |
| `CRM_DATABASE_URL` | Conexão exclusiva ao Supabase |
| `CRM_PUBLIC_URL` | Origem HTTPS do painel |
| `CRM_ADMIN_PASSWORD` | Senha do administrador |
| `CRM_SESSION_SECRET` | Assinatura das sessões; 32+ caracteres |
| `CRM_WORKER_TOKEN` | Token privado do endpoint de automação; 32+ caracteres |
| `CRM_APIFY_TOKEN` | Token da conta Apify, com créditos para o ator |
| `CRM_GMAIL_CLIENT_ID` | Cliente OAuth Google |
| `CRM_GMAIL_CLIENT_SECRET` | Segredo do cliente OAuth |
| `CRM_GMAIL_REFRESH_TOKEN` | Acesso offline da conta remetente |

Domínios HTTPS necessários: `api.apify.com`, `oauth2.googleapis.com`, `gmail.googleapis.com`; além do host PostgreSQL do seu projeto via TCP/TLS. Na máquina de desenvolvimento com rede restrita, as adições foram salvas no rascunho do ambiente; esse salvamento não aplica a política nem conecta contas automaticamente. A implantação no Render usa sua própria rede/configuração.

## 3. Conectar Gmail e trocar remetente

Use uma credencial OAuth **nova para o CRM Brasil**. Não reutilize tokens, senhas de app ou clientes OAuth do CRM principal.

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/), habilite a Gmail API e configure a tela de consentimento para sua conta.
2. Crie um cliente OAuth e autorize a conta `maxvirelli@gmail.com`, com acesso offline e os escopos `https://www.googleapis.com/auth/gmail.send` e `https://www.googleapis.com/auth/gmail.readonly`. O fluxo OAuth deve gerar um **refresh token**. Você pode usar o [OAuth Playground](https://developers.google.com/oauthplayground/) com seu próprio cliente e o redirect URI oficial do Playground cadastrado no cliente. Solicite consentimento/offline no fluxo; não copie o access token de curta duração como refresh token.
3. Cadastre ID, segredo e refresh token nas variáveis do Render, nunca no código, painel público ou chat.
4. Em projetos OAuth externos no modo **Testing**, refresh tokens com escopos Gmail podem expirar em sete dias. Configure a publicação/consentimento adequado para sua conta e atenda eventuais exigências do Google para uso contínuo; revise as regras atuais no Console.
5. Clique **Sincronizar respostas** em Configurações. O backend verifica se a conta autorizada coincide exatamente com o remetente da campanha. A primeira sincronização também valida o acesso OAuth.

Para trocar de remetente, pause a campanha, sincronize a caixa antiga e conclua/pare as cadências antigas. Autorize a nova conta, substitua as três variáveis OAuth e mude o remetente no painel. **Não troque de conta com cadências antigas ativas**: uma nova caixa não tem o histórico de threads da anterior. Se isso acontecer, a verificação falha e bloqueia os envios, em vez de ignorar respostas.

Não há envio por SMTP nem dependência de porta 465/587. Usa Gmail API por HTTPS, com MIME para anexos/imagens e referências de conversa. Assuntos diferentes podem criar conversas separadas; as conversas de todas as etapas ficam registradas para verificar respostas. A detecção cobre respostas nas threads enviadas e mensagens do endereço cadastrado após o primeiro contato; mensagens fora dessas conversas e vindas de outro endereço exigem atualização manual. Há uma pequena janela inevitável entre a leitura da caixa e o envio; uma resposta recebida nesse intervalo só poderá ser detectada na próxima verificação.

## 4. Captação de leads

O adaptador usa o ator [Google Maps Scraper · compass/crawler-google-places](https://apify.com/compass/crawler-google-places) na sua própria conta Apify. Defina `CRM_APIFY_TOKEN` e créditos suficientes. No painel, escolha cidade/UF, nicho e quantidade, clique **Buscar empresas** e depois **Atualizar resultado** até concluir. A busca pode gerar cobrança do Apify. O número consultado não é uma promessa de leads aprovados: o filtro 50–400/sem site/Brasil é aplicado antes da importação e pode descartar resultados.

O ator fornece principalmente dados públicos do Maps. **Não existe garantia de obter email, Instagram ou Facebook de empresas sem site.** O adaptador importa esses campos quando estiverem presentes (`emails`, `instagrams`, `facebooks`) e mantém telefone/origem para enriquecimento manual. Nenhum endereço é inventado ou inferido a partir do nome. Para ampliar cobertura, será necessário um fornecedor de enriquecimento ou um ator com extração de contatos contratado e validado na sua conta. A versão atual não navega automaticamente por redes sociais e não faz disparos por WhatsApp.

Quantidade de avaliações é um filtro de prospecção, não uma comprovação formal do porte da empresa. Confirme adequação do negócio antes de contatar.

Para CSV, use cabeçalho em inglês, codificação UTF-8 e até 500 linhas/2 MB. Colunas aceitas:

```csv
name,email,phone,city,niche,reviews,rating,instagram,facebook,source_url,notes,place_id
Empresa de Exemplo,,11999990000,"Campinas, SP",Oficina,120,4.8,,,,Contato a verificar,
```

Não importe contatos de exemplo para envio. Emails ausentes ficam inelegíveis. Telefones são normalizados com prefixo 55, mas a existência de uma conta WhatsApp não é verificada.

## 5. Agendamento e ativação

1. Habilite GitHub Actions no repositório e confira se `main` é a branch padrão. O workflow agendado precisa estar nessa branch.
2. Nos **Actions secrets**, defina `CRM_BASE_URL` (origem HTTPS do Render) e `CRM_WORKER_TOKEN` (o mesmo valor gerado no Render). O GitHub não precisa de credenciais Supabase, Gmail ou Apify.
3. Edite as quatro mensagens no painel, defina a validade, revise a oferta e marque **Revisei**. Os anexos são compartilhados pelas quatro etapas. Só habilite a campanha quando os textos estiverem prontos.
4. Para envio manual, selecione leads e use **Enviar emails**. A confirmação explica que serão mensagens reais. Somente leads com email, sem bloqueio e com etapa devida são enviados.
5. O workflow agendado chama o backend três vezes, em lotes de até 20, com a mesma cota persistida. Cadências vencidas têm prioridade sobre novos contatos. Não significa que serão enviados 60 se não houver contatos elegíveis em ambas as categorias.

GitHub Actions pode atrasar/omitir execuções agendadas e, em repositórios públicos inativos, os agendamentos podem ser desativados pelo GitHub. Não é um relógio com garantia de pontualidade. O backend prefere não enviar fora da janela; disparos não concluídos não são recuperados fora dela. Para horário garantido, troque o gatilho por um scheduler dedicado, mantendo o mesmo endpoint e token.

O workflow não faz captação automática: descoberta/importação é iniciada pelo painel. Não existe automação ativa até que você publique, configure as conexões e habilite a campanha.

## Recuperação e manutenção

- **Envio incerto:** confira Gmail Enviados e o histórico antes de agir. A reserva/etapa não pode ser repetida automaticamente; não apague reservas para liberar cota. A reconciliação exige análise administrativa do registro `crm2_dispatches`. O painel mostra o incidente em Atividades.
- **Processo caiu:** a reserva impede repetição; a trava de execução expira após dez minutos. Uma reserva ainda “reservado” pode corresponder a um email enviado; trate como incerta. Não há recuperação automática dessas reservas.
- **Resposta/remoção:** qualquer resposta interrompe a sequência. Marcar “Sem interesse” mantém o email em `crm2_suppressions`. Voltar visualmente para outro status não remove o bloqueio. Não há interface para reautorizar endereços bloqueados.
- **Backups:** use as opções de backup/exportação do Supabase. CSV do painel contém cadastros, não é um backup integral de envios, configurações e bloqueios.
- **Credenciais:** as conexões ficam apenas no Render. A referência do CRM principal continha credenciais literais antigas; elas não foram reutilizadas nem copiadas para este projeto. Revise/revogue as credenciais ainda válidas no projeto original separadamente.
- **Atualizações:** o SQL fornecido é de instalação inicial. Mudanças futuras de estrutura devem incluir migração, backup e teste separado; não há migração destrutiva automática.

## Estado da entrega

Código implementado e validação local com SQLite/provedores simulados. Publicação no GitHub/Render, execução do SQL na sua conta Supabase e testes reais autorizados de OAuth/captação/envio permanecem para a integração das suas contas. Não há comprovação de entrega de email ou acesso real aos serviços antes dessa conexão.

## Preparação no plano gratuito

O GitHub Actions chama `/api/automation/prepare` às 08:50 e 08:55 de Brasília e às 09:10, 09:15, 09:30 e 09:35 antes dos lotes seguintes. A chamada protegida por `CRM_WORKER_TOKEN` acorda o processo e verifica o banco, sem captar empresas, enviar emails, consumir cotas de envio ou alterar a campanha. Os lotes continuam às 09:00, 09:20 e 09:40.

A busca e o envio manual no painel executam diretamente, sem aguardar preparação. Se o serviço estiver dormindo, o próprio primeiro acesso pode aguardar a inicialização normal do Render; não existe uma espera artificial de 5–10 minutos no modo manual. A captação via Apify ainda depende do tempo de execução da fonte.

O agendamento do GitHub pode atrasar, e o Render Free continua sujeito a limites: a preparação é uma tentativa de reduzir a demora, não uma garantia de horário ou disponibilidade. O workflow manual oferece `prepare` como padrão; escolha `run` apenas para executar um lote real dentro da janela de 09h–10h, com a campanha habilitada. Os secrets `CRM_BASE_URL` e `CRM_WORKER_TOKEN` devem ser cadastrados no GitHub Actions; preencher o `.env` no Render não os cadastra no GitHub automaticamente.
