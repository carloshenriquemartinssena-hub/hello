import hmac
import os
import time
import threading
from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .environment import load_environment
from .secrets_config import apply_secrets, validate_panel_security
from .streamlit_bridge import APIError, LocalAPI

STATUS = {'novo': 'Novo', 'em_cadencia': 'Em cadência', 'respondeu': 'Respondeu',
          'negociacao': 'Em negociação', 'ganho': 'Convertido', 'pausado': 'Pausado',
          'sem_interesse': 'Sem interesse', 'arquivado': 'Arquivado'}


@st.cache_resource
def application():
    from .main import app
    return app


@st.cache_resource
def attempts():
    return [], threading.Lock()


def request(method, path, **kwargs):
    api = LocalAPI(application(), st.session_state.get('api_cookies'),
                   os.getenv('CRM_PUBLIC_URL') or 'https://crm-internal.invalid')
    result = api.request(method, path, **kwargs)
    st.session_state.api_cookies = api.cookies
    return result


def success(message):
    st.session_state.flash = message
    st.rerun()


def login():
    expected = os.environ['CRM_ADMIN_PASSWORD']
    fingerprint = hmac.digest(os.environ['CRM_SESSION_SECRET'].encode(), expected.encode(), 'sha256').hex()
    if st.session_state.get('auth_fingerprint') == fingerprint:
        return
    st.title('Vértice · CRM Brasil')
    st.caption('Uma operação exclusiva. Seu próximo negócio começa aqui.')
    with st.form('login', clear_on_submit=True):
        password = st.text_input('Senha do administrador', type='password')
        submitted = st.form_submit_button('Entrar', type='primary')
    if submitted:
        recent, lock = attempts()
        with lock:
            recent[:] = [x for x in recent if time.time() - x < 60]
            limited = len(recent) >= 5
            if not limited:
                recent.append(time.time())
        if limited:
            st.error('Aguarde um minuto antes de tentar novamente.')
        elif not hmac.compare_digest(password, expected):
            st.error('Senha inválida.')
        else:
            try:
                request('POST', '/auth/login', json={'password': password})
                st.session_state.auth_fingerprint = fingerprint
                st.rerun()
            except APIError as exc:
                st.error(str(exc))
            except Exception:
                st.error('Não foi possível conectar ao banco. Confira CRM_DATABASE_URL e o SQL do Supabase em Secrets.')
    st.stop()


def overview():
    d = request('GET', '/api/dashboard')
    st.title('Pequenas empresas. Grandes possibilidades.')
    st.caption('Prospecção Brasil · Empresas sem website · Oferta de R$ 700')
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Empresas na base', 'Em cadência', 'Emails enviados hoje', 'Taxa de resposta'],
                                  [d['total'], d['counts'].get('em_cadencia', 0), d['sent_today'], f"{d['reply_rate']}%"]):
        col.metric(label, value)
    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        st.subheader('Seu funil de prospecção')
        st.bar_chart(pd.DataFrame({'Leads': {STATUS.get(k, k): v for k, v in d['counts'].items()}})) if d['counts'] else st.info('Sua base começa com uma boa oportunidade. Use Encontrar empresas ou adicione leads.')
    with right, st.container(border=True):
        st.subheader('Seu ritmo, sem excessos')
        st.write('09h–10h · Horário de Brasília')
        st.caption('Preparação às 08h50/08h55 no GitHub Actions. Busca manual executa diretamente.')
        for key, label in [('initial', 'Novos contatos'), ('followup', 'Follow-ups')]:
            cap = d['campaign']['daily_' + key]
            st.progress(min(1.0, d['daily'][key] / max(1, cap)), text=f"{label}: {d['daily'][key]} / {cap}")
        st.caption('Reservas e envios incertos também consomem a cota.')
        st.write('Campanha: ' + ('habilitada' if d['campaign']['enabled'] else 'pausada'))
    st.subheader('Aconteceu por aqui')
    st.dataframe(pd.DataFrame(d['activity']), hide_index=True, width='stretch') if d['activity'] else st.caption('As captações, mensagens e respostas aparecerão aqui.')


def lead_form(row=None):
    row = row or {}
    with st.form('lead_editor_' + str(row.get('id', 'new'))):
        a, b = st.columns(2)
        name = a.text_input('Nome da empresa', value=row.get('name', ''), max_chars=200)
        email = b.text_input('Email comercial', value=row.get('email') or '')
        phone = a.text_input('Telefone / WhatsApp com DDD', value=row.get('phone') or '')
        city = b.text_input('Cidade / UF', value=row.get('city', ''))
        niche = a.text_input('Nicho', value=row.get('niche', ''))
        reviews = b.number_input('Avaliações no Google', min_value=0, max_value=1000000, value=row.get('reviews', 0))
        rating = a.text_input('Nota no Google', value=row.get('rating', ''))
        instagram = b.text_input('Instagram (URL)', value=row.get('instagram', ''))
        facebook = a.text_input('Facebook (URL)', value=row.get('facebook', ''))
        source_url = b.text_input('Link de origem', value=row.get('source_url', ''))
        notes = st.text_area('Notas', value=row.get('notes', ''))
        if st.form_submit_button('Salvar lead', type='primary'):
            data = dict(name=name, email=email, phone=phone, city=city, niche=niche, reviews=int(reviews),
                        rating=rating, instagram=instagram, facebook=facebook, source_url=source_url, notes=notes,
                        place_id=row.get('place_id'))
            request('PUT' if row else 'POST', '/api/leads' + (f"/{row['id']}" if row else ''), json=data)
            success('Lead salvo.')


def leads():
    st.title('Cada lead, uma possibilidade.')
    a, b, c = st.columns([3, 2, 1])
    query = a.text_input('Buscar empresa, email ou cidade')
    status = b.selectbox('Status', ['', *STATUS], format_func=lambda x: STATUS.get(x, 'Todos'))
    page = c.number_input('Página', min_value=1, value=1, step=1)
    from urllib.parse import urlencode
    data = request('GET', '/api/leads?' + urlencode({'q': query, 'status': status, 'page': page}))
    rows = data['items']
    selected = []
    if rows:
        frame = pd.DataFrame([{'Selecionar': False, 'ID': x['id'], 'Empresa': x['name'], 'Email': x['email'] or '',
                               'Telefone': x['phone'] or '', 'Cidade': x['city'], 'Nicho': x['niche'],
                               'Avaliações': x['reviews'], 'Status': STATUS[x['status']],
                               'Etapa': 'Não iniciada' if x['stage'] < 0 else ('Inicial' if x['stage'] == 0 else f"Follow-up {x['stage']}")}
                              for x in rows])
        edited = st.data_editor(frame, disabled=[x for x in frame.columns if x != 'Selecionar'],
                                hide_index=True, width='stretch', key=f'lead_selection_{page}_{status}_{query}')
        selected = [int(x) for x in edited.loc[edited['Selecionar'], 'ID'].tolist()]
        st.caption(f"{data['total']} empresas encontradas · {len(selected)} selecionadas · 25 por página")
        with st.expander('Ações para os leads selecionados', expanded=bool(selected)):
            new_status = st.selectbox('Novo status', list(STATUS), format_func=STATUS.get)
            a, b = st.columns(2)
            if a.button('Atualizar status', disabled=not selected):
                request('POST', '/api/leads/bulk', json={'ids': selected, 'action': 'status', 'status': new_status})
                success('Status atualizado.')
            confirm_delete = st.checkbox('Confirmo excluir os selecionados e manter o bloqueio de recaptura')
            if b.button('Excluir selecionados', disabled=not selected or not confirm_delete):
                request('POST', '/api/leads/bulk', json={'ids': selected, 'action': 'delete'})
                success('Leads excluídos da base visível.')
            st.divider()
            confirm_send = st.checkbox('Confirmo o envio de emails reais aos contatos selecionados elegíveis')
            if st.button('Enviar emails selecionados', type='primary', disabled=not selected or not confirm_send):
                with st.spinner('Verificando respostas e executando os envios elegíveis…'):
                    result = request('POST', '/api/send', json={'ids': selected})
                success(f"{result['sent']} email(s). {result['reason']}")
    else:
        st.info('Nenhum lead encontrado. Adicione um contato ou faça uma captação.')
    with st.expander('Adicionar lead'):
        lead_form()
    if rows:
        with st.expander('Editar um lead desta página'):
            lead_id = st.selectbox('Lead para editar', [x['id'] for x in rows], format_func=lambda i: next(x['name'] for x in rows if x['id'] == i))
            lead_form(next(x for x in rows if x['id'] == lead_id))
    with st.expander('Importar e exportar CSV'):
        uploaded = st.file_uploader('CSV UTF-8, até 500 linhas e 2 MB', type=['csv'])
        if st.button('Importar CSV', disabled=uploaded is None):
            result = request('POST', '/api/import', files={'file': (uploaded.name, uploaded.getvalue(), 'text/csv')})
            st.success(f"{result['added']} adicionados; {result['duplicates']} duplicados; {len(result['errors'])} inválidos.")
            if result['errors']:
                st.dataframe(result['errors'])
        st.download_button('Exportar todos os leads', request('GET', '/api/export', raw=True), 'leads-brasil.csv', 'text/csv')


def capture():
    st.title('Boas oportunidades estão perto.')
    st.caption('Brasil · Sem website informado · 50–400 avaliações · Sem duplicar contatos')
    settings = request('GET', '/api/settings')
    with st.form('capture'):
        city = st.text_input('Cidade / UF', placeholder='Campinas, SP')
        niche = st.selectbox('Nicho de atuação', settings['niches'])
        limit = st.selectbox('Resultados a consultar', [25, 50, 100], index=1)
        if st.form_submit_button('Buscar empresas', type='primary'):
            with st.spinner('Iniciando a busca na fonte…'):
                result = request('POST', '/api/capture', json={'city': city, 'niche': niche, 'limit': limit})
            st.success('Busca iniciada. Atualize o resultado para importar os contatos quando a fonte concluir.')
    if st.button('Atualizar resultado da captação'):
        with st.spinner('Consultando a captação…'):
            result = request('POST', '/api/capture/poll')
        if result.get('status') == 'SUCCEEDED':
            st.success(f"{result['added']} novos leads, {result['duplicates']} duplicados e {result['rejected']} fora do perfil ou inválidos.")
        else:
            st.info('Status: ' + result.get('status', 'Sem captação'))
    st.info('Emails e redes sociais só são preenchidos quando fornecidos pela fonte. Sem email, o contato não recebe disparos. As consultas podem consumir créditos do Apify.')


def campaign_view():
    st.title('Uma proposta. Uma boa primeira impressão.')
    c = request('GET', '/api/campaign')
    with st.form('campaign'):
        c['name'] = st.text_input('Nome da campanha', value=c['name'])
        a, b = st.columns(2)
        c['sender_name'] = a.text_input('Nome do remetente', value=c['sender_name'])
        c['sender'] = b.text_input('Email remetente', value=c['sender'])
        start = a.date_input('Início da oferta', value=date.fromisoformat(c['start_date']) if c['start_date'] else None)
        end = b.date_input('Último dia da oferta (até 7 dias)', value=date.fromisoformat(c['end_date']) if c['end_date'] else None)
        c['cta_url'] = st.text_input('Link da proposta (opcional)', value=c['cta_url'])
        st.caption('Variáveis disponíveis: {empresa}, {cidade} e {validade}. Assinatura e opção de parar contatos são adicionadas automaticamente.')
        for i, tab in enumerate(st.tabs(['Primeiro contato', 'Follow-up 1', 'Follow-up 2', 'Follow-up 3'])):
            with tab:
                c['templates'][i]['subject'] = st.text_input('Assunto', value=c['templates'][i]['subject'], key=f'subject_{i}')
                c['templates'][i]['body'] = st.text_area('Mensagem', value=c['templates'][i]['body'], height=230, key=f'body_{i}')
        c['intervals'] = [col.number_input(f'Dias até follow-up {i+1}', min_value=1, max_value=30, value=c['intervals'][i]) for i, col in enumerate(st.columns(3))]
        c['approved'] = st.checkbox('Revisei os quatro textos, a oferta e a validade', value=c['approved'])
        c['enabled'] = st.checkbox('Habilitar envios desta campanha', value=c['enabled'])
        if st.form_submit_button('Salvar campanha', type='primary'):
            c['start_date'], c['end_date'] = start.isoformat() if start else '', end.isoformat() if end else ''
            request('PUT', '/api/campaign', json=c)
            success('Campanha salva.')
    st.caption('Limites: 30 novos + 30 follow-ups/dia. Respostas param a sequência. Oferta vencida não é enviada.')
    with st.expander('Prévia da versão salva'):
        stage = st.selectbox('Mensagem da prévia', [0, 1, 2, 3], format_func=lambda x: 'Primeiro contato' if x == 0 else f'Follow-up {x}')
        p = request('GET', f'/api/preview/{stage}')
        st.write('Assunto: ' + p['subject'])
        # Conteúdo é escapado pelo renderizador comum; preview isolado em iframe.
        components.html(request('GET', f'/api/preview/{stage}/document', raw=True).decode(), height=420, scrolling=True)
    with st.expander('Imagens e anexos'):
        for item in request('GET', '/api/attachments'):
            a, b = st.columns([4, 1])
            a.write(f"{item['name']} · {item['size']//1024} KB" + (' · Imagem no corpo' if item['inline'] else ''))
            if b.button('Remover', key=f"attachment_{item['id']}"):
                request('DELETE', f"/api/attachments/{item['id']}")
                success('Anexo removido.')
        uploaded = st.file_uploader('Adicionar arquivo (até 5 MB)', type=['png', 'jpg', 'jpeg', 'webp', 'pdf', 'txt', 'zip', 'docx', 'xlsx'])
        inline = st.checkbox('Exibir imagem no corpo do email')
        if st.button('Salvar anexo', disabled=uploaded is None):
            request('POST', '/api/attachments?inline=' + str(inline).lower(), files={'file': (uploaded.name, uploaded.getvalue(), uploaded.type)})
            success('Anexo salvo para as quatro mensagens.')


def settings_view():
    st.title('Sua operação, bem conectada.')
    settings = request('GET', '/api/settings')
    st.write('Banco: ' + settings['database'])
    st.dataframe([{'Variável': name, 'Estado': 'Definida' if defined else 'Pendente'} for name, defined in settings['variables'].items()], hide_index=True, width='stretch')
    st.caption('Presença de variável não comprova acesso ao provedor. Valores de credenciais não são exibidos.')
    if st.button('Sincronizar respostas do Gmail'):
        with st.spinner('Verificando respostas…'):
            result = request('POST', '/api/inbox/sync')
        st.success(f"{result['replies']} resposta(s) detectada(s).")
    st.info('Configure credenciais em Streamlit Cloud → seu app hello → Settings → Secrets. Para a rotina diária, copie o mesmo TOML para o secret CRM2_SECRETS_TOML do GitHub Actions. Não altere o CRM principal.')


def main():
    st.set_page_config(page_title='Vértice · CRM Brasil', page_icon='🇧🇷', layout='wide')
    try:
        try:
            settings = dict(st.secrets)
        except FileNotFoundError:
            settings = {}
        apply_secrets(settings)
        load_environment()
        validate_panel_security()
    except (ValueError, FileNotFoundError) as exc:
        st.title('Configurar o CRM Brasil')
        st.error(str(exc))
        st.info('Abra Settings → Secrets do app hello e use .streamlit/secrets.toml.example como modelo. O formato é TOML: CHAVE = "valor".')
        st.stop()
    login()
    with st.sidebar:
        st.title('vértice 🇧🇷')
        st.caption('CRM 2 · Operação Brasil')
        nav = st.radio('Espaço de trabalho', ['Visão geral', 'Meus leads', 'Encontrar empresas', 'Campanha & cadência', 'Atividades', 'Configurações'])
        theme = st.radio('Tema', ['Claro', 'Escuro'], horizontal=True)
        st.caption('Base e automação independentes do CRM principal.')
        if st.button('Sair'):
            st.session_state.pop('auth_fingerprint', None)
            st.session_state.pop('api_cookies', None)
            st.rerun()
    if theme == 'Escuro':
        st.markdown('<style>.stApp,[data-testid="stSidebar"]{background:#131d19;color:#e0e9e2} .stApp [data-testid="stMarkdownContainer"],.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp [data-testid="stMetricValue"]{color:#e0e9e2} .stApp input,.stApp textarea,.stApp [data-baseweb="select"]>div{background:#263d2e;color:#e0e9e2}</style>', unsafe_allow_html=True)
    if 'flash' in st.session_state:
        st.success(st.session_state.pop('flash'))
    try:
        if nav == 'Visão geral': overview()
        elif nav == 'Meus leads': leads()
        elif nav == 'Encontrar empresas': capture()
        elif nav == 'Campanha & cadência': campaign_view()
        elif nav == 'Configurações': settings_view()
        else:
            st.title('O histórico das suas conexões.')
            st.dataframe(request('GET', '/api/activity'), hide_index=True, width='stretch')
    except APIError as exc:
        st.error(str(exc))
    except Exception:
        st.error('Não foi possível concluir. Confira a conexão do banco e as credenciais em Secrets. Nenhuma credencial será exibida.')
