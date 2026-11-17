-- Fiscal issuance runs only through a compliant external billing system.
-- Never emit a legal invoice or trigger email merely by saving issuer profile.
ALTER TABLE advertising_invoice_issuer ADD COLUMN IF NOT EXISTS general_igic_confirmed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE advertising_invoice_issuer ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS advertising_invoice_issuance (
 draft_id BIGINT PRIMARY KEY REFERENCES advertising_invoice_reviews(draft_id) ON DELETE RESTRICT,
 provider TEXT NOT NULL DEFAULT 'facturadirecta',
 status TEXT NOT NULL DEFAULT 'pending'
   CHECK(status IN ('pending','issuing','issued','sending','sent','error')),
 provider_invoice_id TEXT,
 provider_invoice_url TEXT,
 provider_contact_id TEXT,
 processing_started_at TIMESTAMPTZ,
 issued_at TIMESTAMPTZ,
 sent_at TIMESTAMPTZ,
 error_note TEXT NOT NULL DEFAULT '',
 attempt_count INTEGER NOT NULL DEFAULT 0,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_advertising_invoice_issuance_ref ON advertising_invoice_issuance(provider, provider_invoice_id)
 WHERE provider_invoice_id IS NOT NULL;
