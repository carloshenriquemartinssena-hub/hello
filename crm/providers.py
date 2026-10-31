"""Integrações externas. Nenhuma credencial é persistida no banco ou retornada à UI."""
import base64
import os
import re
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr
from urllib.parse import quote

import httpx

from .domain import LeadInput, render_message


class ProviderError(RuntimeError):
    pass


def required(name):
    value = os.getenv(name)
    if not value:
        raise ProviderError(f"Configure {name} no servidor")
    return value


class Gmail:
    def __init__(self):
        self.client = httpx.Client(timeout=35)
        try:
            r = self.client.post("https://oauth2.googleapis.com/token", data={
                "client_id": required("CRM_GMAIL_CLIENT_ID"),
                "client_secret": required("CRM_GMAIL_CLIENT_SECRET"),
                "refresh_token": required("CRM_GMAIL_REFRESH_TOKEN"),
                "grant_type": "refresh_token",
            })
            if r.status_code != 200:
                raise ProviderError("Gmail: não foi possível renovar o acesso OAuth; revise a conexão")
            self.client.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        except Exception:
            self.client.close()
            raise

    def close(self):
        self.client.close()

    def api(self, method, path, **kwargs):
        r = self.client.request(method, "https://gmail.googleapis.com/gmail/v1/users/me/" + path, **kwargs)
        if not r.is_success:
            raise ProviderError(f"Gmail: operação indisponível (HTTP {r.status_code}). Nenhum reenvio automático será feito.")
        return r.json()

    def verify_sender(self, sender):
        profile = self.api("GET", "profile")
        if profile["emailAddress"].lower() != sender.lower():
            raise ProviderError("A conta Gmail conectada difere do remetente da campanha")
        self.sender = sender.lower()

    def has_reply(self, lead):
        if not lead.first_sent:
            return False
        from datetime import datetime
        stamp = int(datetime.fromisoformat(lead.first_sent).timestamp())
        threads = dict.fromkeys([*getattr(lead, "history_threads", []), lead.thread_id])
        for thread_id in threads:
            if not thread_id:
                continue
            thread = self.api("GET", "threads/" + quote(thread_id, safe=""), params={"format": "metadata", "metadataHeaders": "From"})
            for message in thread.get("messages", []):
                headers = message.get("payload", {}).get("headers", [])
                sender = next((parseaddr(h["value"])[1].lower() for h in headers if h["name"].lower() == "from"), "")
                if sender and sender != self.sender and int(message.get("internalDate", 0)) >= stamp * 1000:
                    return True
        result = self.api("GET", "messages", params={"q": f"from:({lead.email}) after:{stamp}", "maxResults": 1, "includeSpamTrash": "true"})
        return bool(result.get("messages"))

    def send(self, c, lead, stage, attachments):
        subject, plain, content = render_message(c, lead, stage)
        msg = EmailMessage()
        msg["From"] = formataddr((c.sender_name, c.sender))
        msg["To"] = lead.email
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=c.sender.split("@")[-1])
        same_subject = False
        if lead.thread_id:
            thread = self.api("GET", "threads/" + quote(lead.thread_id, safe=""), params={"format": "metadata", "metadataHeaders": ["Message-ID", "Subject"]})
            headers = thread.get("messages", [{}])[0].get("payload", {}).get("headers", [])
            parent = next((h["value"] for h in headers if h["name"].lower() == "message-id"), None)
            original_subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
            normalize_subject = lambda text: re.sub(r"^(?:(?:re|res|fw|fwd):\s*)+", "", text, flags=re.I).strip().casefold()
            same_subject = normalize_subject(original_subject) == normalize_subject(subject)
            if parent:
                msg["In-Reply-To"] = parent
                msg["References"] = parent
        for a in attachments:
            if a.inline:
                content += f'<p><img src="cid:crm2-{a.id}" style="max-width:100%" alt="Imagem da proposta"></p>'
        msg.set_content(plain)
        msg.add_alternative(content, subtype="html")
        for a in attachments:
            main, sub = a.content_type.split("/", 1)
            if a.inline:
                msg.get_payload()[-1].add_related(a.data, maintype=main, subtype=sub, cid=f"<crm2-{a.id}>", filename=a.name)
            else:
                msg.add_attachment(a.data, maintype=main, subtype=sub, filename=a.name)
        payload = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
        if lead.thread_id and same_subject:
            payload["threadId"] = lead.thread_id
        return self.api("POST", "messages/send", json=payload)


class Apify:
    def __init__(self):
        token = required('CRM_APIFY_TOKEN').strip()
        if token.startswith(('http://', 'https://')):
            raise ProviderError('CRM_APIFY_TOKEN deve conter somente o token do Apify, não uma URL com ?token=.')
        self.client = httpx.Client(base_url="https://api.apify.com/v2/", headers={"Authorization": "Bearer " + token}, timeout=40)

    def close(self):
        self.client.close()

    def api(self, method, path, **kwargs):
        # Somente leituras podem ser repetidas: repetir POST de criação pode cobrar duas buscas.
        for attempt in range(3 if method == 'GET' else 1):
            try:
                r = self.client.request(method, path, **kwargs)
            except httpx.TransportError:
                if method == 'GET' and attempt < 2:
                    time.sleep(0.25 * (attempt + 1))
                    continue
                raise ProviderError('Apify: falha de rede. Se você estava iniciando uma busca, confira a execução no Console Apify e recupere pelo Run ID; não inicie outra automaticamente.') from None
            if method == 'GET' and r.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(0.25 * (attempt + 1))
                continue
            break
        if not r.is_success:
            raise ProviderError(f"Apify: verifique acesso, créditos e configuração (HTTP {r.status_code})")
        try:
            return r.json()
        except ValueError:
            raise ProviderError('Apify retornou uma resposta inválida. A execução existente pode ser recuperada pelo Run ID; não inicie outra busca automaticamente.') from None

    def start(self, city, niche, limit):
        result = self.api("POST", "acts/compass~crawler-google-places/runs", json={
            "searchStringsArray": [f"{niche} em {city}, Brasil"],
            "countryCode": "br", "language": "pt-BR",
            "maxCrawledPlacesPerSearch": limit,
            "maxReviews": 0, "skipClosedPlaces": True,
        })
        payload = result.get('data') if isinstance(result, dict) else None
        run_id = payload.get('id') if isinstance(payload, dict) else None
        if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{5,88}', run_id):
            raise ProviderError('Não foi possível confirmar o Run ID. Confira Runs no Console Apify para recuperar a execução, sem iniciar outra busca.')
        return run_id

    def poll(self, run_id):
        response = self.api("GET", "actor-runs/" + quote(run_id, safe=""))
        run = response.get('data') if isinstance(response, dict) else None
        if not isinstance(run, dict) or not isinstance(run.get('status'), str):
            raise ProviderError('Apify retornou metadados de execução inválidos. O Run ID foi preservado para nova consulta.')
        if run["status"] not in {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}:
            return run["status"], []
        if not run.get('defaultDatasetId'):
            if run['status'] == 'SUCCEEDED':
                raise ProviderError('Apify concluiu, mas não retornou um dataset. Confira o Run ID e tente atualizar o resultado novamente.')
            return run['status'], []
        data = self.api("GET", "datasets/" + quote(run["defaultDatasetId"], safe="") + "/items", params={"clean": "true", "limit": 500})
        if not isinstance(data, list):
            raise ProviderError('O dataset Apify não retornou uma lista válida de empresas. Confira a execução e tente recuperar pelo Run ID.')
        if len(data) == 500:
            extra = self.api('GET', 'datasets/' + quote(run['defaultDatasetId'], safe='') + '/items', params={'clean': 'true', 'limit': 1, 'offset': 500})
            if extra:
                raise ProviderError('A execução tem mais de 500 registros. Exporte os resultados em lotes menores; a importação não foi truncada nem marcada como concluída.')
        return run['status'], data


REJECTION_LABELS = {'sem_email': 'Sem email válido fornecido pela fonte', 'fora_brasil': 'País ausente ou fora do Brasil',
                    'com_site': 'Website informado', 'avaliacoes': 'Fora de 50–400 avaliações ou contagem inválida',
                    'fechada': 'Empresa fechada', 'dados_invalidos': 'Nome/dados obrigatórios inválidos',
                    'erro_registro': 'Registro não salvo; consulte diagnóstico de integridade'}


def classify_place(item, city, niche):
    """Email é obrigatório. Campos opcionais ruins não apagam um contato válido."""
    if not isinstance(item, dict):
        return None, 'dados_invalidos', []
    candidates = []
    for key in ('emails', 'email', 'businessEmail'):
        value = item.get(key)
        candidates.extend(value if isinstance(value, list) else [value])
    email = None
    for value in candidates:
        if isinstance(value, dict):
            value = value.get('email') or value.get('value')
        try:
            email = LeadInput.normalize_email(value)
        except ValueError:
            continue
        if email and len(email) <= 254:
            break
        email = None
    if not email:
        return None, 'sem_email', []
    raw_name = item.get('title') or item.get('name')
    if not isinstance(raw_name, str) or len(raw_name.strip()) < 2:
        return None, 'dados_invalidos', []
    country = str(item.get('countryCode') or item.get('country') or '').strip().upper()
    if country not in {'BR', 'BRASIL', 'BRAZIL'}:
        return None, 'fora_brasil', []
    if item.get('website') and str(item['website']).strip():
        return None, 'com_site', []
    if item.get("permanentlyClosed") or item.get("temporarilyClosed"):
        return None, 'fechada', []
    try:
        count = float(str(item.get('reviewsCount', item.get('reviews_count', 0)) or 0).replace(',', '.'))
        reviews = int(count)
        if count != reviews:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        return None, 'avaliacoes', []
    if not 50 <= reviews <= 400:
        return None, 'avaliacoes', []
    warnings = []
    raw_phone = item.get('phoneUnformatted') or item.get('phone')
    try:
        phone = LeadInput.normalize_phone(raw_phone)
        if raw_phone and phone is None:
            warnings.append('Telefone inválido não importado')
    except ValueError:
        phone = None
        warnings.append('Telefone inválido não importado')
    def social(key):
        value = item.get(key) or item.get(key.rstrip('s')) or []
        if isinstance(value, list):
            value = next((x for x in value if isinstance(x, str)), '')
        try:
            return LeadInput.safe_url(str(value or ''))
        except ValueError:
            return ''
    try:
        source_url = LeadInput.safe_url(str(item.get('url') or ''))
    except ValueError:
        source_url = ''
    try:
        raw_score = item.get('totalScore')
        score = float(raw_score) if raw_score is not None else None
        rating = str(score) if score is not None and 0 <= score <= 5 else ''
    except (ValueError, TypeError, OverflowError):
        rating = ''
    try:
        lead = LeadInput(
            name=raw_name[:200], email=email, phone=phone,
            place_id=str(item['placeId'])[:250] if item.get('placeId') else None,
            city=str(item.get('city') or city)[:160], niche=niche,
            reviews=reviews, rating=rating,
            instagram=social('instagrams'), facebook=social('facebooks'),
            source_url=source_url,
            notes='Captado no Google Maps via Apify; email informado pela fonte; sem website informado. ' + '; '.join(warnings),
        )
    except ValueError:
        return None, 'dados_invalidos', warnings
    return lead, None, warnings


def map_place(item, city, niche):
    return classify_place(item, city, niche)[0]
