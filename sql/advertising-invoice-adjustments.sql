-- Queue of fiscal corrections and Stripe returns.
-- Creating an adjustment is always an administrative request, never a refund.
-- All external writes require explicit administrator confirmation.
ALTER TABLE advertising_invoice_reviews
 ADD COLUMN IF NOT EXISTS stripe_payment_intent_id TEXT;

CREATE TABLE IF NOT EXISTS advertising_invoice_adjustments (
 id BIGSERIAL PRIMARY KEY,
 request_key TEXT NOT NULL UNIQUE CHECK(length(request_key) BETWEEN 12 AND 100),
 draft_id BIGINT NOT NULL REFERENCES advertising_invoice_reviews(draft_id) ON DELETE RESTRICT,
 kind TEXT NOT NULL CHECK(kind IN ('billing_details','refund_full','refund_partial')),
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
 reason TEXT NOT NULL CHECK(length(reason) BETWEEN 10 AND 700),
 replacement_details JSONB NOT NULL DEFAULT '{}'::jsonb,
 status TEXT NOT NULL DEFAULT 'pending_review' CHECK(status IN (
  'pending_review','processing','refund_pending','refund_failed',
  'refund_succeeded','correction_issued','replacement_issued',
  'needs_attention','completed','rejected')),
 stripe_refund_id TEXT UNIQUE,
 correction_invoice_id TEXT UNIQUE,
 correction_invoice_url TEXT,
 correction_sent_at TIMESTAMPTZ,
 replacement_invoice_id TEXT UNIQUE,
 replacement_invoice_url TEXT,
 replacement_sent_at TIMESTAMPTZ,
 processing_started_at TIMESTAMPTZ,
 issue_date DATE NOT NULL DEFAULT (now() AT TIME ZONE 'Atlantic/Canary')::date,
 reviewed_at TIMESTAMPTZ,
 completed_at TIMESTAMPTZ,
 error_note TEXT NOT NULL DEFAULT '',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_advertising_adjustments_draft ON advertising_invoice_adjustments(draft_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_advertising_adjustments_pending ON advertising_invoice_adjustments(status,updated_at DESC);
-- Prevent overlapping operations on the same paid invoice; fiscal adjustments must
-- be processed one at a time, because a later request depends on earlier invoices.
CREATE UNIQUE INDEX IF NOT EXISTS idx_advertising_adjustments_one_open
 ON advertising_invoice_adjustments(draft_id)
 WHERE status NOT IN ('completed','rejected','refund_failed');
