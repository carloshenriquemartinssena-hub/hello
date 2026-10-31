"""Smoke test sem emails reais. Execute contra uma instância LOCAL de desenvolvimento.

python3 scripts/browser_smoke.py
CHROMIUM_PATH=/usr/bin/chromium python3 scripts/browser_smoke.py
Gera screenshots em test-results/ e remove os leads de teste da base visível.
"""
import os
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)
    base = "http://127.0.0.1:8001"
    marker = "Teste navegador " + uuid.uuid4().hex[:8]
    out = Path("test-results")
    out.mkdir(exist_ok=True)
    created = []
    errors = []
    client = httpx.Client(base_url=base, trust_env=False, headers={'Origin': base})
    password = os.getenv('CRM_ADMIN_PASSWORD', '')
    if password:
        client.post('/auth/login', json={'password': password}).raise_for_status()
    original_campaign = client.get('/api/campaign').json()
    assert not client.get('/api/settings').json()['production'], 'Use somente uma instância local de desenvolvimento'
    assert not original_campaign['enabled'], 'Pause a campanha antes de executar testes do navegador'
    try:
        with sync_playwright() as p:
            executable = os.getenv("CHROMIUM_PATH")
            browser = p.chromium.launch(headless=True, executable_path=executable, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda e: errors.append(str(e)))
            if password:
                page.goto(base + '/login', wait_until='networkidle')
                page.get_by_label('Senha do administrador', exact=True).fill(password)
                page.get_by_role('button', name='Entrar no meu espaço →', exact=True).click()
            else:
                page.goto(base, wait_until="networkidle")
            page.get_by_role("heading", name="Pequenas empresas. Grandes possibilidades.").wait_for()
            page.get_by_role("button", name="Adicionar lead").click()
            page.get_by_label("Nome da empresa", exact=True).fill(marker)
            page.get_by_label("Email comercial", exact=True).fill("teste-" + uuid.uuid4().hex[:8] + "@example.invalid")
            page.get_by_label("Cidade / UF", exact=True).fill("Campinas, SP")
            page.get_by_label("Nicho", exact=True).fill("Oficinas automotivas")
            page.get_by_label("Avaliações no Google", exact=True).fill("120")
            page.get_by_role("button", name="Salvar lead", exact=True).click()
            page.wait_for_selector("#lead-dialog:not([open])", state="attached")
            page.wait_for_load_state("networkidle")
            rows = client.get('/api/leads', params={'q':marker}).json()['items']
            assert len(rows) == 1
            created = [rows[0]['id']]
            page.goto(base + '/#leads', wait_until='networkidle')
            page.get_by_role('button',name='Editar '+marker,exact=True).wait_for()
            page.get_by_role('button',name='Editar '+marker,exact=True).click()
            page.get_by_label('Notas',exact=True).fill('Cadastro atualizado pelo navegador; não enviar.')
            page.get_by_role('button',name='Salvar lead',exact=True).click()
            page.wait_for_selector('#lead-dialog:not([open])',state='attached')
            page.wait_for_load_state('networkidle')
            page.get_by_role('checkbox',name='Selecionar '+marker,exact=True).check()
            page.locator('#bulk-status').select_option('pausado')
            page.get_by_role('button',name='Atualizar status',exact=True).click()
            page.locator('td .pill.pausado').first.wait_for()
            assert client.get('/api/leads',params={'q':marker}).json()['items'][0]['status']=='pausado'
            page.screenshot(path=str(out/'leads-light.png'),full_page=True)
            page.locator('#theme-toggle').click()
            assert page.locator('html').get_attribute('data-theme')=='dark'
            page.screenshot(path=str(out/'leads-dark.png'),full_page=True)
            page.reload(wait_until='networkidle')
            assert page.locator('html').get_attribute('data-theme')=='dark'
            page.locator('#theme-toggle').click()
            for view, heading in [('capture','Boas oportunidades estão perto.'),('campaign','Uma proposta. Uma boa primeira impressão.'),('activity','O histórico das suas conexões.'),('settings','Sua operação, bem conectada.')]:
                page.goto(base+'/#'+view,wait_until='networkidle')
                page.get_by_role('heading',name=heading,exact=True).wait_for()
            page.goto(base+'/#capture',wait_until='networkidle')
            page.get_by_role('button',name='Oficinas automotivas Contato local · Serviços recorrentes',exact=True).click()
            assert page.locator('#capture-niche').input_value()=='Oficinas automotivas'
            page.goto(base+'/#campaign',wait_until='networkidle')
            page.locator('#campaign-name').fill(marker)
            with page.expect_response(lambda r: r.url.endswith('/api/campaign') and r.request.method=='PUT') as saved:
                page.get_by_role('button',name='Salvar campanha',exact=True).click()
            assert saved.value.status==200
            page.locator('#campaign-name').wait_for()
            assert client.get('/api/campaign').json()['name']==marker
            page.get_by_role('button',name='Follow-up 2',exact=True).click()
            assert 'Uma ideia' in page.locator('#template-subject').input_value()
            page.get_by_role('button',name='Prévia salva',exact=True).click()
            page.locator('#preview-panel:not([hidden])').wait_for()
            assert 'Assunto:' in page.locator('#preview-subject').inner_text()
            page.frame_locator('#email-preview').get_by_text('Um site pode reunir',exact=False).wait_for()
            page.screenshot(path=str(out/'campaign-light.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.goto(base+'/#overview',wait_until='networkidle')
            page.get_by_role('heading',name='Pequenas empresas. Grandes possibilidades.').wait_for()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.get_by_role('button',name='Abrir navegação',exact=True).click()
            assert 'open' in page.locator('#sidebar').get_attribute('class')
            page.locator('#sidebar a[data-nav=leads]').click()
            page.get_by_role('heading',name='Cada lead, uma possibilidade.').wait_for()
            page.wait_for_function("() => document.querySelector('#sidebar').getBoundingClientRect().right <= 0")
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(out/'mobile-light.png'),full_page=True)
            assert errors == [], errors
            browser.close()
            print('PASS: criação/edição/status de lead, navegação, temas, prévia e mobile; nenhum erro JavaScript.')
    finally:
        client.put('/api/campaign',json=original_campaign).raise_for_status()
        if not created:
            created = [x['id'] for x in client.get('/api/leads',params={'q':marker}).json()['items']]
        if created:
            r=client.post('/api/leads/bulk',json={'ids':created,'action':'delete'})
            r.raise_for_status()
        client.close()


if __name__ == '__main__':
    main()
