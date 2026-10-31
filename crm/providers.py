"""Integrações externas. Nenhuma credencial é persistida no banco ou retornada à UI."""
import base64
import os
import re
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
        r = self.client.request(method, path, **kwargs)
        if not r.is_success:
            raise ProviderError(f"Apify: verifique acesso, créditos e configuração (HTTP {r.status_code})")
        return r.json()

    def start(self, city, niche, limit):
        result = self.api("POST", "acts/compass~crawler-google-places/runs", json={
            "searchStringsArray": [f"{niche} em {city}, Brasil"],
            "countryCode": "br", "language": "pt-BR",
            "maxCrawledPlacesPerSearch": limit,
            "maxReviews": 0, "skipClosedPlaces": True,
        })
        return result["data"]["id"]

    def poll(self, run_id):
        run = self.api("GET", "actor-runs/" + quote(run_id, safe=""))["data"]
        if run["status"] != "SUCCEEDED":
            return run["status"], []
        data = self.api("GET", "datasets/" + quote(run["defaultDatasetId"], safe="") + "/items", params={"clean": "true", "limit": 500})
        return "SUCCEEDED", data


def map_place(item, city, niche):
    """Rejeita sites e países desconhecidos; não presume emails ou redes inexistentes."""
    if not isinstance(item, dict) or item.get("website") or str(item.get("countryCode", "")).upper() != "BR":
        return None
    if item.get("permanentlyClosed") or item.get("temporarilyClosed"):
        return None
    reviews = int(item.get("reviewsCount") or 0)
    if not 50 <= reviews <= 400:
        return None
    emails = item.get("emails") or []
    if isinstance(emails, str):
        emails = [emails]
    def social(key):
        value = item.get(key) or []
        if isinstance(value, str):
            return value
        return next((x for x in value if isinstance(x, str)), "")
    return LeadInput(
        name=item.get("title", ""), email=emails[0] if emails else None,
        phone=item.get("phoneUnformatted") or item.get("phone"),
        place_id=item.get("placeId"), city=item.get("city") or city,
        niche=niche, reviews=reviews, rating=str(item.get("totalScore") or ""),
        instagram=social("instagrams"), facebook=social("facebooks"),
        source_url=item.get("url") or "", notes="Captado no Google Maps via Apify; sem website informado pela fonte.",
    )
