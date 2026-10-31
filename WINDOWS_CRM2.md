# Iniciar o CRM 2 automaticamente no Windows

O comando `python iniciar.py` agora inicia o painel Streamlit e uma rotina Python independente do navegador. O painel local fica em http://localhost:8502. O CRM principal usa seus próprios processos e não é alterado.

## Instalação única

1. Baixe o ZIP atualizado de `main` e extraia os arquivos em `C:\Users\carlo\Downloads\hello-main`. Preserve seu `.env`, a pasta `.streamlit` com seus Secrets e a pasta `data`. Não publique esses arquivos privados.
2. As credenciais precisam existir **neste computador**: preencha `.env` ou crie `.streamlit/secrets.toml` com o mesmo TOML usado nos Secrets do Streamlit. Use `CRM_ENV=production` no `.env` (ou `CRM_ENV = "production"` no TOML), a URI PostgreSQL e o certificado oficial do Supabase, quando necessário. Os Secrets remotos do GitHub/Streamlit não são baixados automaticamente. Variáveis do processo têm prioridade; depois TOML, depois `.env`.
3. Dê dois cliques em **INSTALAR_CRM2.bat**. Ele cria um ambiente Python exclusivo, instala dependências e registra/inicia a tarefa **Vertice CRM2 Brasil**, para o logon e diariamente às 08h50. Requer Python 3.11 ou mais recente; recomendamos 3.12.

Se as dependências já estiverem instaladas, o equivalente no Prompt de Comando é:

```bat
cd /d C:\Users\carlo\Downloads\hello-main
python iniciar.py --instalar-inicio
```

Depois, abra http://localhost:8502. Confira **Configurações → Automação**: cidade, nicho e limite de resultados por busca. A última busca registrada pode fornecer cidade/nicho. Em **Campanha**, revise mensagens e datas, aprove e habilite a campanha. A automação nunca habilita uma campanha pausada por conta própria.

## Regras da rotina

- Preparação às 08h50; novas buscas e envios automáticos somente entre 09h00 e 10h00 de Brasília. Iniciar às 10h46 aguarda a próxima janela; os botões manuais continuam disponíveis imediatamente.
- Uma nova busca automática por dia, no máximo; reaproveita uma busca manual do dia ou em andamento. Apify pode consumir créditos. Somente empresas com email válido e os demais filtros são importadas.
- Lotes de até 20 envios às 09h00, 09h20 e 09h40, com recuperação dos horários perdidos dentro da janela. Máximo diário compartilhado de 60: até 30 contatos novos e até 30 follow-ups. Até três follow-ups; respostas e bloqueios interrompem a sequência.
- Windows e GitHub compartilham reservas no mesmo banco, evitando repetir buscas/lotes. Falhas de resultado incerto conservam reservas; confira Atividades e Gmail antes de qualquer reenvio.
- Busca/envio manual não espera a preparação. Permanecem as cotas, reservas e validações da campanha.

Mantenha o Windows no fuso de Brasília, o usuário conectado, o PC ligado e com internet. A tarefa pode acordar da suspensão se o Windows permitir, mas não liga um computador desligado. Fechar a janela do processo encerra a execução local; para retomá-la, execute `python iniciar.py` ou inicie a tarefa no Agendador do Windows. A tarefa não cria outra instância quando uma já está ativa nesta pasta.

## Conferir problemas

`python iniciar.py --verificar` verifica a configuração e o banco sem enviar emails. Consulte `data\automation.log` e Atividades no painel. Presença de credenciais não comprova autorização nas APIs. Mudanças nos arquivos de configuração exigem reiniciar o CRM 2.

Este instalador precisa ser executado no seu Windows: um push no GitHub não instala tarefas nem atualiza o ZIP já extraído. O registro da tarefa depende das permissões locais do Agendador; a conta usada deve permitir criar suas próprias tarefas.
