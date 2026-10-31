-- Complemento não destrutivo para o esquema já existente do CRM 2.
-- Não recria tabelas nem apaga registros. Execute no SQL Editor do projeto CRM 2.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $$
BEGIN
  IF to_regclass('public.crm2_dispatches_lead_id_stage_key') IS NULL
     AND to_regclass('public.uq_crm2_dispatches_lead_stage') IS NULL THEN
    IF EXISTS (
      SELECT 1 FROM public.crm2_dispatches GROUP BY lead_id, stage HAVING count(*) > 1
    ) THEN
      RAISE EXCEPTION 'Existem etapas duplicadas em crm2_dispatches. Preserve o histórico e revise os registros antes de criar o índice; nenhuma linha foi apagada.';
    END IF;
    CREATE UNIQUE INDEX uq_crm2_dispatches_lead_stage ON public.crm2_dispatches (lead_id, stage);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_crm2_leads_status ON public.crm2_leads (status);
CREATE INDEX IF NOT EXISTS ix_crm2_leads_next_send ON public.crm2_leads (next_send);
CREATE INDEX IF NOT EXISTS ix_crm2_dispatches_day ON public.crm2_dispatches (day);
CREATE INDEX IF NOT EXISTS ix_crm2_dispatches_lead_id ON public.crm2_dispatches (lead_id);

-- Alinha somente para frente as sequências após eventuais importações manuais de IDs.
DO $$
DECLARE
  table_name text;
  sequence_name text;
  largest_id bigint;
  current_id bigint;
  was_called boolean;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['crm2_leads', 'crm2_activity', 'crm2_attachments', 'crm2_dispatches'] LOOP
    EXECUTE 'LOCK TABLE public.' || quote_ident(table_name) || ' IN SHARE ROW EXCLUSIVE MODE';
    sequence_name := pg_get_serial_sequence('public.' || table_name, 'id');
    IF sequence_name IS NOT NULL THEN
      EXECUTE 'SELECT coalesce(max(id), 0) FROM public.' || quote_ident(table_name) INTO largest_id;
      EXECUTE 'SELECT last_value, is_called FROM ' || sequence_name INTO current_id, was_called;
      IF largest_id > current_id OR (largest_id = current_id AND NOT was_called) THEN
        PERFORM setval(sequence_name::regclass, largest_id, true);
      END IF;
    END IF;
  END LOOP;
END $$;

INSERT INTO public.crm2_lease (id, owner, expires) VALUES (1, '', '') ON CONFLICT (id) DO NOTHING;

COMMIT;
