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