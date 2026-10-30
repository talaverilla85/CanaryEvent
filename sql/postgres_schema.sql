-- DParranda PostgreSQL (safe/idempotent; existing SQLite remains unchanged).
CREATE TABLE IF NOT EXISTS events (
 id BIGINT PRIMARY KEY,
 dedup_key TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL,
 start TEXT NOT NULL,
 "end" TEXT,
 municipality TEXT NOT NULL,
 venue TEXT NOT NULL DEFAULT '',
 category TEXT NOT NULL,
 free SMALLINT,
 price TEXT,
 details TEXT,
 lat DOUBLE PRECISION,
 lng DOUBLE PRECISION,
 accuracy TEXT,
 source_name TEXT NOT NULL,
 source_url TEXT NOT NULL,
 status TEXT NOT NULL,
 image_url TEXT NOT NULL DEFAULT '',
 image_alt TEXT NOT NULL DEFAULT '',
 image_origin TEXT NOT NULL DEFAULT '',
 image_status TEXT NOT NULL DEFAULT '',
 organizer_url TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dp_events_start ON events (start);
CREATE INDEX IF NOT EXISTS idx_dp_events_municipality ON events (municipality);
CREATE INDEX IF NOT EXISTS idx_dp_events_status ON events (status);

CREATE TABLE IF NOT EXISTS source_log (
 source TEXT PRIMARY KEY,
 checked_at TEXT,
 found INTEGER NOT NULL DEFAULT 0,
 added INTEGER NOT NULL DEFAULT 0,
 changed INTEGER NOT NULL DEFAULT 0,
 error TEXT NOT NULL DEFAULT ''
);

-- Editorial overrides survive all future automated source refreshes.
CREATE TABLE IF NOT EXISTS event_overrides (
 event_id BIGINT PRIMARY KEY,
 hidden BOOLEAN NOT NULL DEFAULT FALSE,
 title_override TEXT,
 details_override TEXT,
 venue_override TEXT,
 price_override TEXT,
 free_override SMALLINT,
 category_override TEXT,
 canonical_event_id BIGINT,
 review_status TEXT NOT NULL DEFAULT 'unreviewed'
  CHECK(review_status IN ('unreviewed','approved','needs_review','rejected')),
 reviewed_at TIMESTAMPTZ,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(canonical_event_id IS NULL OR canonical_event_id<>event_id)
);

-- Published occurrence cards can have their own negative IDs.
CREATE TABLE IF NOT EXISTS published_events (
 id BIGINT PRIMARY KEY,
 payload JSONB NOT NULL,
 active BOOLEAN NOT NULL DEFAULT TRUE,
 synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dp_pub_active ON published_events(active);
CREATE INDEX IF NOT EXISTS idx_dp_pub_municipality
 ON published_events ((payload->>'municipality'));

CREATE TABLE IF NOT EXISTS ad_campaigns (
 id TEXT PRIMARY KEY,
 enabled BOOLEAN NOT NULL DEFAULT FALSE,
 advertiser TEXT NOT NULL,
 kind TEXT NOT NULL DEFAULT 'paid',
 permanent BOOLEAN NOT NULL DEFAULT FALSE,
 starts_at DATE,
 ends_at DATE,
 municipalities JSONB NOT NULL DEFAULT '[]'::jsonb,
 headline TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 location TEXT NOT NULL DEFAULT '',
 button_text TEXT NOT NULL DEFAULT 'Descubrir',
 button_url TEXT NOT NULL,
 image TEXT NOT NULL DEFAULT '',
 image_alt TEXT NOT NULL DEFAULT '',
 disclosure TEXT NOT NULL DEFAULT 'Publicidad',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(starts_at IS NULL OR ends_at IS NULL OR starts_at<=ends_at)
);

CREATE TABLE IF NOT EXISTS ad_daily_stats (
 campaign_id TEXT NOT NULL REFERENCES ad_campaigns(id),
 day DATE NOT NULL,
 impressions BIGINT NOT NULL DEFAULT 0 CHECK(impressions>=0),
 clicks BIGINT NOT NULL DEFAULT 0 CHECK(clicks>=0),
 PRIMARY KEY(campaign_id,day)
);

CREATE TABLE IF NOT EXISTS catalog_sync (
 id SMALLINT PRIMARY KEY DEFAULT 1 CHECK(id=1),
 generated_at TEXT,
 event_count INTEGER NOT NULL DEFAULT 0,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Existing Neon tables may predate these editorial fields.
ALTER TABLE event_overrides ADD COLUMN IF NOT EXISTS free_override SMALLINT;
ALTER TABLE event_overrides ADD COLUMN IF NOT EXISTS category_override TEXT;
ALTER TABLE event_overrides ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
-- Apply constraints to newly created records in the admin service.
CREATE INDEX IF NOT EXISTS idx_dp_overrides_review ON event_overrides(review_status);
