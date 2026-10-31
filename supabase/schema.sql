-- Vértice CRM Brasil · executar somente no NOVO projeto Supabase.
-- Idempotente para instalação inicial; não altera tabelas existentes.
BEGIN;
SET LOCAL search_path = public;


CREATE TABLE IF NOT EXISTS crm2_activity (
	id SERIAL NOT NULL,
	kind VARCHAR(40) NOT NULL,
	detail TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id)
);

ALTER TABLE public.crm2_activity ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_activity FROM anon, authenticated;


CREATE TABLE IF NOT EXISTS crm2_attachments (
	id SERIAL NOT NULL,
	name VARCHAR(200) NOT NULL,
	content_type VARCHAR(100) NOT NULL,
	data BYTEA NOT NULL,
	inline BOOLEAN NOT NULL,
	PRIMARY KEY (id)
);

ALTER TABLE public.crm2_attachments ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_attachments FROM anon, authenticated;


CREATE TABLE IF NOT EXISTS crm2_config (
	key VARCHAR(100) NOT NULL,
	value TEXT NOT NULL,
	PRIMARY KEY (key)
);

ALTER TABLE public.crm2_config ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_config FROM anon, authenticated;


CREATE TABLE IF NOT EXISTS crm2_leads (
	id SERIAL NOT NULL,
	name VARCHAR(200) NOT NULL,
	email VARCHAR(254),
	phone VARCHAR(20),
	place_id VARCHAR(250),
	city VARCHAR(160) NOT NULL,
	niche VARCHAR(120) NOT NULL,
	reviews INTEGER NOT NULL,
	rating VARCHAR(10) NOT NULL,
	instagram VARCHAR(500) NOT NULL,
	facebook VARCHAR(500) NOT NULL,
	source_url VARCHAR(1000) NOT NULL,
	notes TEXT NOT NULL,
	status VARCHAR(30) NOT NULL,
	stage INTEGER NOT NULL,
	first_sent VARCHAR(40),
	next_send VARCHAR(40),
	thread_id VARCHAR(200),
	deleted BOOLEAN NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email),
	UNIQUE (phone),
	UNIQUE (place_id)
);

CREATE INDEX IF NOT EXISTS ix_crm2_leads_status ON crm2_leads (status);

CREATE INDEX IF NOT EXISTS ix_crm2_leads_next_send ON crm2_leads (next_send);

ALTER TABLE public.crm2_leads ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_leads FROM anon, authenticated;


CREATE TABLE IF NOT EXISTS crm2_lease (
	id SERIAL NOT NULL,
	owner VARCHAR(40) NOT NULL,
	expires VARCHAR(40) NOT NULL,
	PRIMARY KEY (id)
);

ALTER TABLE public.crm2_lease ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_lease FROM anon, authenticated;


CREATE TABLE IF NOT EXISTS crm2_suppressions (
	email VARCHAR(254) NOT NULL,
	reason VARCHAR(50) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (email)
);

ALTER TABLE public.crm2_suppressions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_suppressions FROM anon, authenticated;


CREATE TABLE IF NOT EXISTS crm2_dispatches (
	id SERIAL NOT NULL,
	lead_id INTEGER NOT NULL,
	stage INTEGER NOT NULL,
	day VARCHAR(10) NOT NULL,
	state VARCHAR(30) NOT NULL,
	message_id VARCHAR(200),
	thread_id VARCHAR(200),
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (lead_id, stage),
	FOREIGN KEY(lead_id) REFERENCES crm2_leads (id)
);

CREATE INDEX IF NOT EXISTS ix_crm2_dispatches_day ON crm2_dispatches (day);

CREATE INDEX IF NOT EXISTS ix_crm2_dispatches_lead_id ON crm2_dispatches (lead_id);

ALTER TABLE public.crm2_dispatches ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.crm2_dispatches FROM anon, authenticated;

INSERT INTO public.crm2_lease (id, owner, expires) VALUES (1, '', '') ON CONFLICT (id) DO NOTHING;

COMMIT;

-- Sem políticas públicas: somente a conexão PostgreSQL do backend (papel proprietário) acessa os dados.
