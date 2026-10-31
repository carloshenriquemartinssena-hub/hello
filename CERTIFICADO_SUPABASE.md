# Corrigir DB_CERTIFICATE no Streamlit

Esse erro indica que a verificação do certificado TLS falhou; ele não comprova senha incorreta nem tabelas ausentes. Não altere para `sslmode=require`, `disable` ou `no-verify`.

1. Abra seu projeto no painel Supabase e procure **SSL Configuration** nas configurações do banco. Use a opção **Download certificate** para baixar o certificado raiz oficial.
2. Abra o arquivo baixado em um editor de texto. Copie o conteúdo completo, de `-----BEGIN CERTIFICATE-----` até `-----END CERTIFICATE-----`. Use somente o certificado público, nunca uma chave privada.
3. No Streamlit, abra **Settings → Secrets** do app `hello`. Acrescente o campo abaixo, substituindo o texto intermediário pelo conteúdo real do arquivo. As aspas triplas são necessárias para várias linhas:

```toml
CRM_DATABASE_CA_CERT = """
-----BEGIN CERTIFICATE-----
COLE_AQUI_O_CONTEUDO_REAL_DO_CERTIFICADO_OFICIAL
-----END CERTIFICATE-----
"""
```

Se o campo já existir como `CRM_DATABASE_CA_CERT = ""`, substitua essa linha pelo bloco completo; não repita a mesma chave duas vezes.

4. Preserve `sslmode=verify-full` na `CRM_DATABASE_URL`. Não precisa trocar `sslrootcert=system` por um caminho do seu computador: o CRM cria o arquivo temporário no servidor e passa o caminho correto ao driver, com prioridade sobre o valor da URI.
5. Salve e use **Reboot app**. O certificado é validado como PEM antes da conexão, e o PostgreSQL continua verificando cadeia de confiança e nome do servidor.

Para a rotina diária, atualize também o secret **CRM2_SECRETS_TOML** do GitHub Actions com esse mesmo campo e os demais valores. Os Secrets privados de uma plataforma não são copiados automaticamente para a outra.

O certificado específico do seu projeto ainda precisa ser fornecido por você pelo painel oficial do Supabase. Os testes locais validaram leitura, arquivo temporário e preservação de `verify-full`; não constituem validação da conexão real da sua conta. Se o erro persistir com a raiz oficial correta, confirme que o host da URI é exatamente o da opção Session pooler do mesmo projeto, e informe apenas o novo código de erro.
