"""Classificação de erros sem devolver mensagens de drivers ou credenciais."""


def database_diagnostic(error):
    pending, seen, codes, texts = [error], set(), set(), []
    while pending and len(seen) < 30:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        codes.add(getattr(item, 'sqlstate', None))
        # Somente para comparação local. Este texto NUNCA é exibido ou registrado.
        texts.append(str(item).lower())
        for name in ('orig', '__cause__', '__context__'):
            nested = getattr(item, name, None)
            if isinstance(nested, BaseException):
                pending.append(nested)
    text = '\n'.join(texts)
    if codes & {'28P01', '28000'} or 'password authentication failed' in text or 'invalid password' in text:
        return 'DB_AUTH', 'O PostgreSQL recusou a autenticação. Atualize Secrets com a senha atual do banco, não a senha do painel CRM. Codifique caracteres especiais da senha na URI.'
    if 'tenant or user not found' in text or 'tenant not found' in text:
        return 'DB_POOLER', 'O pooler não reconheceu o projeto/usuário. Copie novamente a URI completa de Supabase → Connect → Session pooler. Não monte o host, a região ou o usuário manualmente.'
    if '42P01' in codes:
        return 'DB_TABLES', 'A conexão foi aberta, mas faltam tabelas do CRM 2. Execute supabase/schema.sql no SQL Editor desse mesmo projeto Supabase.'
    if '42703' in codes:
        return 'DB_COLUMNS', 'A conexão foi aberta, mas uma tabela tem estrutura diferente da versão atual. Confira o esquema do CRM 2; não apague tabelas com dados para tentar corrigir.'
    if '42501' in codes:
        return 'DB_PERMISSION', 'O usuário do PostgreSQL não tem permissão nas tabelas. Use a conexão do proprietário fornecida em Connect; não use uma chave anon nem a conexão de outro projeto.'
    if any(marker in text for marker in ('certificate verify failed', 'root certificate file', 'sslrootcert', 'self-signed certificate', 'could not read certificate')):
        return 'DB_CERTIFICATE', 'O certificado do banco não foi validado. Baixe o certificado raiz oficial nas configurações SSL do Supabase e cole o PEM em CRM_DATABASE_CA_CERT, usando aspas triplas nos Secrets. Mantenha sslmode=verify-full.'
    if 'sslmode=verify-full' in text:
        return 'DB_TLS_CONFIG', 'A URI precisa de sslmode=verify-full. Use também sslrootcert=system ou o certificado raiz oficial do projeto.'
    if any(marker in text for marker in ('could not translate host name', 'name or service not known', 'temporary failure in name resolution', 'nodename nor servname')):
        return 'DB_DNS', 'Não foi possível localizar o host do banco. Copie o endereço real do Session pooler no Supabase, sem placeholders ou espaços.'
    if '53300' in codes or 'too many clients' in text or 'max client connections' in text:
        return 'DB_CONNECTION_LIMIT', 'O banco/pooler atingiu o limite de conexões. Confira as conexões no Supabase e utilize o Session pooler correto.'
    if 'timeout' in text or 'timed out' in text:
        return 'DB_TIMEOUT', 'O banco não respondeu no prazo. Confira se o projeto Supabase está ativo, o host/porta do Session pooler e as restrições de rede.'
    if any(marker in text for marker in ('network is unreachable', 'connection refused', 'no route to host')):
        return 'DB_NETWORK', 'Não foi possível alcançar o banco. Use o Session pooler na porta 5432 e confira se o projeto está ativo e permite a conexão.'
    if 'could not parse sqlalchemy url' in text or 'invalid dsn' in text:
        return 'DB_URI', 'O formato da URI PostgreSQL está inválido. Copie a URI de Connect e codifique caracteres especiais da senha.'
    if isinstance(error, ModuleNotFoundError) and (error.name or '').startswith(('psycopg', 'sqlalchemy')):
        return 'DB_DRIVER', 'Falta uma dependência do banco. No Streamlit, use Reboot app para instalar os requirements atualizados da main.'
    return 'DB_UNKNOWN', 'A inicialização do banco falhou por uma causa ainda não identificada. Informe somente este código; não envie URI com senha, Secrets ou logs completos.'
