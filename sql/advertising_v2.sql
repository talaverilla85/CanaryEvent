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