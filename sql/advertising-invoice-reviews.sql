-- Internal pre-invoicing queue. These are NOT legally issued invoices.
-- No invoice numbers, VAT/IGIC computation, invoice PDF or customer mail is created here.
-- Future issuance must integrate an invoice system that meets Spanish invoicing rules.
CREATE TABLE IF NOT EXISTS advertising_invoice_reviews (
 draft_id BIGINT PRIMARY KEY REFERENCES advertiser_campaign_drafts(id) ON DELETE RESTRICT,
 stripe_checkout_session_id TEXT NOT NULL UNIQUE,
 total_cents INTEGER NOT NULL CHECK(total_cents>0),
 currency TEXT NOT NULL DEFAULT 'eur' CHECK(currency='eur'),
 company_name TEXT NOT NULL DEFAULT '',
 customer_tax_id TEXT NOT NULL DEFAULT '',
 billing_address TEXT NOT NULL DEFAULT '',
 billing_postal TEXT NOT NULL DEFAULT '',
 billing_city TEXT NOT NULL DEFAULT '',
 billing_region TEXT NOT NULL DEFAULT '',
 billing_country TEXT NOT NULL DEFAULT '',
 billing_email TEXT NOT NULL DEFAULT '',
 review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','checked')),
 internal_note TEXT NOT NULL DEFAULT '',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 checked_at TIMESTAMPTZ,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invoice_review_pending ON advertising_invoice_reviews(review_status,created_at DESC);
