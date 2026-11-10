-- Campaign-backed paid events, independent of official imported data.
CREATE TABLE IF NOT EXISTS sponsored_events (
 id BIGSERIAL PRIMARY KEY,
 enabled BOOLEAN NOT NULL DEFAULT FALSE,
 review_status TEXT NOT NULL DEFAULT 'draft' CHECK(review_status IN ('draft','approved','rejected')),
 advertiser TEXT NOT NULL,
 title TEXT NOT NULL,
 start TEXT NOT NULL,
 "end" TEXT,
 municipality TEXT NOT NULL,
 venue TEXT NOT NULL,
 category TEXT NOT NULL DEFAULT 'ocio',
 details TEXT NOT NULL DEFAULT '',
 price TEXT NOT NULL DEFAULT '',
 free SMALLINT,
 source_url TEXT NOT NULL,
 image_url TEXT NOT NULL DEFAULT '',
 image_alt TEXT NOT NULL DEFAULT '',
 campaign_starts_at DATE,
 campaign_ends_at DATE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (campaign_starts_at IS NULL OR campaign_ends_at IS NULL OR campaign_starts_at <= campaign_ends_at)
);
CREATE INDEX IF NOT EXISTS idx_dp_sponsored_active ON sponsored_events(enabled,review_status,start);
CREATE TABLE IF NOT EXISTS advertising_enquiries (
 id BIGSERIAL PRIMARY KEY,
 company TEXT NOT NULL,
 contact_name TEXT NOT NULL,
 email TEXT NOT NULL,
 municipality TEXT,
 format TEXT NOT NULL,
 dates_text TEXT,
 message TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','contacted','closed')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Private company/billing details never appear in public event payloads.
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_type TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS legal_name TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS tax_id TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_address TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_postal TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_city TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_region TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_country TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS billing_email TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS telephone TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS campaign_name TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS campaign_start DATE;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS campaign_days INTEGER;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS event_start TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS event_end TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS event_venue TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS event_price TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS action_url TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS banner_text TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS creative_alt TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS image_name TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS advertising_enquiry_images (
 enquiry_id BIGINT PRIMARY KEY REFERENCES advertising_enquiries(id) ON DELETE CASCADE,
 mime_type TEXT NOT NULL CHECK (mime_type IN ('image/jpeg','image/png','image/webp')),
 width INTEGER NOT NULL CHECK (width BETWEEN 200 AND 2400),
 height INTEGER NOT NULL CHECK (height BETWEEN 150 AND 2400),
 image_data BYTEA NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS event_title TEXT;
ALTER TABLE sponsored_events ADD COLUMN IF NOT EXISTS enquiry_id BIGINT REFERENCES advertising_enquiries(id);
ALTER TABLE ad_campaigns ADD COLUMN IF NOT EXISTS enquiry_id BIGINT REFERENCES advertising_enquiries(id);
CREATE INDEX IF NOT EXISTS idx_dp_ads_enquiry ON ad_campaigns(enquiry_id);
CREATE INDEX IF NOT EXISTS idx_dp_sponsored_enquiry ON sponsored_events(enquiry_id);
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS event_municipality TEXT;


-- Private, individually invited advertiser workspaces. The invite's raw token is
-- returned to the administrator once and is never stored in plaintext.
CREATE TABLE IF NOT EXISTS advertiser_accounts (
 id BIGSERIAL PRIMARY KEY,
 lead_id BIGINT UNIQUE REFERENCES advertising_enquiries(id) ON DELETE SET NULL,
 company TEXT NOT NULL,
 contact_name TEXT NOT NULL DEFAULT '',
 email TEXT NOT NULL,
 token_hash TEXT NOT NULL UNIQUE,
 access_version INTEGER NOT NULL DEFAULT 1,
 active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dp_advertiser_accounts_lead ON advertiser_accounts(lead_id);

-- Advertisers only prepare unpublished drafts until a confirmed payment flow
-- exists. Payment and editorial state are separate to avoid accidental go-live.
CREATE TABLE IF NOT EXISTS advertiser_campaign_drafts (
 id BIGSERIAL PRIMARY KEY,
 advertiser_id BIGINT NOT NULL REFERENCES advertiser_accounts(id) ON DELETE CASCADE,
 plan TEXT NOT NULL CHECK(plan IN ('local','zona','insular')),
 days INTEGER NOT NULL CHECK(days IN (30,60)),
 price_cents INTEGER NOT NULL CHECK(price_cents>0),
 municipalities JSONB NOT NULL DEFAULT '[]'::jsonb,
 placement TEXT NOT NULL CHECK(placement IN ('banner','evento')),
 advertiser TEXT NOT NULL,
 title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 destination TEXT NOT NULL,
 campaign_start DATE,
 event_start TEXT,
 event_town TEXT,
 event_venue TEXT,
 image_alt TEXT,
 status TEXT NOT NULL DEFAULT 'draft'
   CHECK(status IN ('draft','pending_payment','paid_review','changes_requested','approved','active','finished','rejected','cancelled')),
 payment_status TEXT NOT NULL DEFAULT 'unavailable'
   CHECK(payment_status IN ('unavailable','pending','paid','refunded')),
 actual_starts_at DATE,
 actual_ends_at DATE,
 published_ad_id TEXT REFERENCES ad_campaigns(id),
 published_event_id BIGINT REFERENCES sponsored_events(id),
 review_note TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (actual_starts_at IS NULL OR actual_ends_at IS NULL OR actual_starts_at<=actual_ends_at)
);
CREATE INDEX IF NOT EXISTS idx_dp_advertiser_drafts_account ON advertiser_campaign_drafts(advertiser_id,updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_dp_advertiser_drafts_review ON advertiser_campaign_drafts(status,payment_status);

CREATE TABLE IF NOT EXISTS advertiser_campaign_draft_images (
 draft_id BIGINT PRIMARY KEY REFERENCES advertiser_campaign_drafts(id) ON DELETE CASCADE,
 mime_type TEXT NOT NULL CHECK(mime_type IN ('image/webp','image/jpeg','image/png')),
 width INTEGER NOT NULL CHECK(width=1200),
 height INTEGER NOT NULL CHECK(height=675),
 image_data BYTEA NOT NULL,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- Editorial review is independent from payment and active advertising.
-- Legacy leads stay informational until they explicitly send a proposal.
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'interest';
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS review_note TEXT;
ALTER TABLE advertising_enquiries ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'unavailable';
CREATE INDEX IF NOT EXISTS idx_dp_enquiries_review_status ON advertising_enquiries(review_status,created_at DESC);

-- The final action before checkout is editorial approval, not publication.
ALTER TABLE advertiser_campaign_drafts DROP CONSTRAINT IF EXISTS advertiser_campaign_drafts_status_check;
ALTER TABLE advertiser_campaign_drafts ADD CONSTRAINT advertiser_campaign_drafts_status_check
  CHECK(status IN ('draft','submitted','approved_for_payment','pending_payment','paid_review',
   'changes_requested','approved','active','finished','rejected','cancelled'));
ALTER TABLE advertiser_campaign_drafts ADD COLUMN IF NOT EXISTS source_lead_id BIGINT UNIQUE REFERENCES advertising_enquiries(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_dp_drafts_source_lead ON advertiser_campaign_drafts(source_lead_id);

-- Public preview artwork uses an optimized 1000 x 563 WebP image. Workspace
-- edits use 1200 x 675; preserve real dimensions when migrating an enquiry.
ALTER TABLE advertiser_campaign_draft_images DROP CONSTRAINT IF EXISTS advertiser_campaign_draft_images_width_check;
ALTER TABLE advertiser_campaign_draft_images DROP CONSTRAINT IF EXISTS advertiser_campaign_draft_images_height_check;
ALTER TABLE advertiser_campaign_draft_images ADD CONSTRAINT advertiser_campaign_draft_images_width_check
 CHECK((width=1000 AND height=563) OR (width=1200 AND height=675));
