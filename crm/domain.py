import html
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import or_, select

from .db import Config, Lead, Suppression

TZ = ZoneInfo("America/Sao_Paulo")
STATUSES = {"novo", "em_cadencia", "respondeu", "negociacao", "ganho", "pausado", "sem_interesse", "arquivado"}
STOPPED = {"respondeu", "negociacao", "ganho", "pausado", "sem_interesse", "arquivado"}
NICHES = ["Clínicas odontológicas", "Oficinas automotivas", "Clínicas de estética", "Pet shops", "Escritórios de contabilidade", "Academias e estúdios"]
FOOTER = "Se não houver resposta, voltarei em alguns dias.\nSe não tiver interesse ou não quiser mais receber emails, basta responder a este email e interromperei os contatos."
DEFAULT_TEMPLATES = [
    {"subject": "Uma oportunidade para a presença digital da {empresa}", "body": "Olá, equipe da {empresa}!\n\nEstou realizando uma campanha especial nesta semana para empresas com potencial em {cidade}. Um website pode ajudar seus clientes a conhecer seus serviços e entrar em contato.\n\nProjetos em agências podem custar R$ 2.500 a R$ 3.000, conforme o escopo. Nesta campanha, proponho um website por R$ 700, válido até {validade}. Posso enviar o escopo para vocês avaliarem?"},
    {"subject": "Re: presença digital da {empresa}", "body": "Olá, equipe da {empresa}!\n\nRetomando minha mensagem: posso compartilhar uma proposta de website por R$ 700, com o escopo combinado antes da contratação? A condição desta campanha é válida até {validade}."},
    {"subject": "Uma ideia para a {empresa}", "body": "Olá!\n\nUm site pode reunir informações, serviços e os canais de contato da {empresa} em um só lugar. Faz sentido conversarmos sobre a proposta de R$ 700, válida até {validade}?"},
    {"subject": "Último contato sobre a proposta para {empresa}", "body": "Olá, equipe da {empresa}!\n\nEste é o último contato desta sequência. Caso faça sentido, posso explicar o escopo da proposta de website por R$ 700, válida até {validade}."},
]


class LeadInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = None
    place_id: str | None = Field(default=None, max_length=250)
    city: str = Field(default="", max_length=160)
    niche: str = Field(default="", max_length=120)
    reviews: int = Field(default=0, ge=0, le=1000000)
    rating: str = Field(default="", max_length=10)
    instagram: str = Field(default="", max_length=500)
    facebook: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=1000)
    notes: str = Field(default="", max_length=5000)

    @field_validator("name", "city", "niche", mode="before")
    @classmethod
    def trim(cls, v):
        return str(v or "").strip()

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        v = str(v or "").strip().lower()
        if v and not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", v):
            raise ValueError("Email inválido")
        return v or None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        digits = re.sub(r"\D", "", str(v or ""))
        if not digits:
            return None
        if len(digits) in (10, 11):
            digits = "55" + digits
        if len(digits) not in (12, 13) or not digits.startswith("55"):
            raise ValueError("Use um telefone brasileiro com DDD")
        return digits

    @field_validator("instagram", "facebook", "source_url")
    @classmethod
    def safe_url(cls, v):
        if v and (urlsplit(v).scheme not in {"https", "http"} or not urlsplit(v).hostname):
            raise ValueError("Use um link HTTP ou HTTPS completo")
        return v


class Template(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=15000)

    @field_validator("subject")
    @classmethod
    def no_header_injection(cls, v):
        if "\r" in v or "\n" in v:
            raise ValueError("Assunto deve ocupar uma linha")
        return v


class Campaign(BaseModel):
    name: str = Field(default="Presença digital • Brasil", min_length=1, max_length=120)
    enabled: bool = False
    approved: bool = False
    sender: str = "maxvirelli@gmail.com"
    sender_name: str = Field(default="Max Virelli", min_length=1, max_length=80)
    daily_total: int = Field(default=60, ge=1, le=60)
    daily_initial: int = Field(default=30, ge=0, le=30)
    daily_followup: int = Field(default=30, ge=0, le=30)
    intervals: list[int] = Field(default=[2, 2, 2], min_length=3, max_length=3)
    start_date: str = ""
    end_date: str = ""
    cta_url: str = Field(default="", max_length=1000)
    templates: list[Template] = Field(default_factory=lambda: [Template(**t) for t in DEFAULT_TEMPLATES], min_length=4, max_length=4)

    @field_validator("sender")
    @classmethod
    def sender_email(cls, v):
        return LeadInput.normalize_email(v) or "maxvirelli@gmail.com"

    @field_validator("sender_name")
    @classmethod
    def sender_line(cls, v):
        if "\n" in v or "\r" in v:
            raise ValueError("Nome inválido")
        return v

    @field_validator("cta_url")
    @classmethod
    def cta(cls, v):
        return LeadInput.safe_url(v)

    @model_validator(mode="after")
    def check_period(self):
        if any(x < 1 or x > 30 for x in self.intervals):
            raise ValueError("Intervalos devem ser de 1 a 30 dias")
        if self.start_date or self.end_date or self.enabled:
            try:
                start = datetime.strptime(self.start_date, "%Y-%m-%d").date()
                end = datetime.strptime(self.end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Defina início e fim da campanha")
            if not 0 <= (end - start).days <= 6:
                raise ValueError("A oferta semanal deve durar no máximo 7 dias")
        if self.enabled and not self.approved:
            raise ValueError("Revise os textos e aprove a campanha antes de ativar")
        return self


def campaign(s):
    row = s.get(Config, "campaign")
    return Campaign.model_validate_json(row.value) if row else Campaign()


def set_config(s, key, value):
    row = s.get(Config, key)
    if row:
        row.value = json.dumps(value, ensure_ascii=False)
    else:
        s.add(Config(key=key, value=json.dumps(value, ensure_ascii=False)))


def duplicate(s, data, exclude=None):
    fields = [getattr(Lead, k) == data[k] for k in ("email", "phone", "place_id") if data.get(k)]
    if not fields:
        return None
    q = select(Lead).where(or_(*fields))
    if exclude:
        q = q.where(Lead.id != exclude)
    return s.scalar(q)


def add_lead(s, item):
    data = item.model_dump()
    if duplicate(s, data):
        return None
    row = Lead(**data)
    if row.email and s.get(Suppression, row.email):
        row.status = "sem_interesse"
    s.add(row)
    s.flush()
    return row


def serialize(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name != "data"}


def render_message(c, lead, stage):
    end = datetime.strptime(c.end_date, "%Y-%m-%d").strftime("%d/%m/%Y") if c.end_date else "[defina a validade]"
    values = {"empresa": lead.name, "cidade": lead.city or "sua região", "validade": end}
    t = c.templates[stage]
    def interpolate(text):
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        return text
    body = interpolate(t.body)
    footer = FOOTER if stage < 3 else "Se não tiver interesse ou não quiser mais receber emails, basta responder a este email e interromperei os contatos."
    plain = body + "\n\n" + c.sender_name + "\n\n" + footer
    safe = "".join(
        '<a href="' + html.escape(part, quote=True) + '">' + html.escape(part) + '</a>'
        if re.fullmatch(r"https?://[^\s<>]+", part) else html.escape(part)
        for part in re.split(r"(https?://[^\s<>]+)", plain)
    )
    content = '<div style="font:16px/1.7 Arial,sans-serif;color:#213b36;max-width:620px;margin:auto;white-space:pre-line">' + safe + "</div>"
    if c.cta_url:
        content += '<p><a href="' + html.escape(c.cta_url, quote=True) + '">Conhecer a proposta</a></p>'
        plain += "\n\n" + c.cta_url
    return interpolate(t.subject), plain, content
