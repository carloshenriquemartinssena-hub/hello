# Vértice · CRM 2 Brasil no Streamlit

Painel independente do CRM principal para prospectar empresas brasileiras sem site. Usa o Supabase exclusivo do CRM 2 e preserva deduplicação, cadastro/edição/exclusão em lote, captação no Google Maps via Apify, campanha de R$ 700, anexos, três follow-ups, interrupção por resposta e cotas de 30 novos contatos + 30 follow-ups por dia.

## Publicar o app hello

1. Abra Streamlit Community Cloud e selecione o app do repositório `carloshenriquemartinssena-hub/hello`.
2. Use a branch **main**, o arquivo principal **streamlit_app.py** (ou **app.py**, também compatível) e Python **3.12**. Se o app foi criado com outro arquivo principal, recrie somente o app `hello` com o arquivo correto; não exclua nem altere o CRM principal.
3. Em **Settings → Secrets**, cole o modelo de `.streamlit/secrets.toml.example`, substituindo todos os exemplos pelos seus valores do CRM 2. Salve. Se precisar, use **Reboot app** para reinstalar/atualizar.
4. Entre com a senha `CRM_ADMIN_PASSWORD` configurada nesses Secrets. Verifique as conexões no painel antes de habilitar a campanha.

Não envie `.env` ao repositório. No Streamlit Cloud, o equivalente é **Secrets, em TOML**: `CHAVE = "valor"`, uma por linha. Não coloque `[secrets]` nem copie linhas `CHAVE=valor` sem aspas. Senhas com caracteres especiais devem estar corretamente codificadas na URI PostgreSQL. Os exemplos nunca são credenciais reais.

`CRM_DATABASE_URL` é a URI PostgreSQL do Supabase → Connect → Session pooler. A URL `https://…supabase.co` e a chave `anon` não servem como conexão de banco. Mantenha `sslmode=verify-full`; o modelo usa `sslrootcert=system`. Se o certificado do projeto exigir outra raiz, use a raiz oficial conforme a documentação do Supabase, sem desativar TLS.

O SQL em `supabase/schema.sql` é o mesmo da versão anterior: não precisa apagar ou recriar seu banco. O painel nativo Streamlit reutiliza a aplicação ASGI no próprio processo; não abre porta adicional, não precisa de Render, proxy ou GitHub Pages. Credenciais ficam no servidor e sessões são individuais.

## Automação diária

O painel não deve manter uma thread infinita nem depender de navegador aberto. O workflow `.github/workflows/automation.yml` roda o worker Python no GitHub Actions, diretamente conectado ao mesmo Supabase.

No repositório `hello`, abra **Settings → Secrets and variables → Actions → New repository secret**. Nome: **CRM2_SECRETS_TOML**. Conteúdo: **o mesmo bloco TOML** que você colou em Secrets do Streamlit. Isso é necessário porque o GitHub não tem acesso aos Secrets privados do Streamlit. Não use variáveis públicas para esse bloco.

A rotina prepara/verifica o banco às 08:50/08:55 de Brasília e antes dos lotes seguintes, sem captar ou enviar. Os lotes rodam às 09:00, 09:20 e 09:40, até 20 emails por execução e respeitando 30 novos + 30 follow-ups por dia. O worker opera mesmo se o painel Streamlit estiver em repouso; a preparação não é uma promessa de acordar o painel. O GitHub pode atrasar agendamentos; a execução recusa envios automáticos fora de 09h–10h.

O botão manual de buscar ou enviar executa diretamente, sem aguardar preparação. A busca na fonte é iniciada pelo usuário; o agendamento diário processa emails dos leads já captados, não inicia novas buscas automaticamente.

Envios dependem de campanha aprovada, habilitada e dentro da validade. A primeira mensagem e os três follow-ups podem ser personalizados antes da ativação. Nenhum email é enviado durante instalação ou ao abrir o painel. Não execute `run` como teste de credenciais; use a operação `prepare` e a sincronização de respostas.

## Desenvolvimento

```bash
python -m pip install -r requirements-dev.txt
streamlit run streamlit_app.py
python -m pytest -q
```

Localmente, use `.env` ou copie o modelo para `.streamlit/secrets.toml` (ignorado pelo Git). Não compartilhe esse arquivo. Para o painel, senha mínima de 16 caracteres e tokens de sessão/worker de 32 caracteres. Use valores diferentes dos do CRM principal.

O código FastAPI/Docker continua disponível para uma eventual migração futura; suas instruções anteriores estão em `README_DOCKER.md`. No Streamlit, siga este README. Não é necessário contratar outra hospedagem.

## Limites da captação e entrega

- Filtra Brasil, sem site informado, 50–400 avaliações, sem encerramento informado. Nichos sugeridos não garantem conversão e avaliações não comprovam porte formal.
- Email é obrigatório na captação automática. Empresas sem email fornecido pela fonte e válido no formato são descartadas com motivo visível. Telefones e redes são opcionais. O ator de Maps pode retornar zero emails: isso exige outra fonte/enriquecimento, não endereços inventados. Cadastros antigos/manuais não são apagados. Não há disparos automáticos de WhatsApp.
- Acesso às APIs, entrega de emails e execução na sua conta só podem ser confirmados após configurar suas credenciais e publicar. Não confunda testes locais com implantação concluída.
- Exclusões e bloqueios preservam histórico. Timeout de envio mantém a reserva e pausa o contato; não remova reservas para tentar reenviar. Qualquer resposta detectada interrompe a sequência.

## Painel pessoal sem digitar senha

Por padrão, o painel pede senha. Para usar somente a restrição de acesso do Streamlit Cloud, deixe o app **privado** nas configurações de compartilhamento e adicione `CRM_REQUIRE_LOGIN = false` em Secrets. Essa opção dispensa a tela de login do CRM, mas não configura nem verifica a privacidade da plataforma. Se o app estiver público, visitantes poderão acessar e operar o CRM. As chaves internas `CRM_ADMIN_PASSWORD`, `CRM_SESSION_SECRET` e `CRM_WORKER_TOKEN` continuam necessárias; apenas não precisam ser digitadas ao abrir o painel. O backend ASGI mantém a autenticação interna.

Se aparecer erro de banco, confira primeiro a URI PostgreSQL e o sufixo `?sslmode=verify-full&sslrootcert=system`. Sem parâmetros SSL, a aplicação recusa a conexão em produção antes de acessar a rede. Se já existir `?` na URI, acrescente parâmetros com `&`. O token do Apify deve ser apenas o token, nunca a URL de uma chamada da API. Em Secrets, coloque os valores de texto entre aspas.

## Recuperar a busca e entender o salvamento

A página Encontrar empresas acompanha a execução e tenta importar os resultados automaticamente enquanto estiver aberta. Exibe total recebido, salvos, duplicados e motivos de descarte; email é o primeiro requisito. Você também pode atualizar manualmente.

Se a busca foi iniciada diretamente no Console Apify ou a importação foi interrompida, abra Recuperar busca já executada e informe o Run ID, cidade e nicho. Isso consulta a execução existente sem criar outra busca. Para reavaliar uma execução antiga com as regras atuais, marque a opção de reavaliação. Resultados já cadastrados continuam protegidos pela deduplicação. Resultados parciais de execuções encerradas com falha são identificados como parciais e passam pelos mesmos filtros. Execuções com mais de 500 resultados não são truncadas silenciosamente: é necessário exportar/dividir os dados.

Falhas de transporte e respostas 429/5xx em leituras Apify podem ser repetidas até duas vezes. Criação de busca e envio de email nunca são repetidos automaticamente, pois uma resposta perdida não prova que a operação não ocorreu. O Run ID permanece registrado para recuperação. Campos opcionais inválidos podem ser omitidos; email obrigatório inválido impede a entrada do lead. Falhas estruturais do banco interrompem a importação e preservam a execução para nova tentativa.

Erros de formulário agora mostram o campo/regra: por exemplo, validade máxima de sete dias e aprovação antes de habilitar a campanha. Uma configuração inválida não substitui a campanha salva anteriormente. Erros do banco têm códigos seguros, sem imprimir credenciais.

O esquema de contexto informado é compatível com os campos utilizados. O complemento `supabase/002_runtime_indexes.sql` adiciona, se faltar, a unicidade por lead/etapa e os índices operacionais, além de alinhar sequências de IDs somente para frente, sem recriar tabelas ou apagar dados. Se já existirem etapas duplicadas, ele interrompe e solicita revisão do histórico. Não execute um dump de contexto como migração.

A suíte inclui PostgreSQL 17 isolado, com estrutura equivalente ao contexto informado, além de testes do formulário Streamlit, recuperação/importação e falhas de rede. Esses testes não acessam as contas reais e não garantem disponibilidade de serviços externos nem obtenção de emails ausentes na fonte.
