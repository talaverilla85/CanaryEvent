-- Safe, repeatable migration. Link each sponsored event to its already-paid advertiser draft.
ALTER TABLE sponsored_events
  ADD COLUMN IF NOT EXISTS advertiser_draft_id BIGINT REFERENCES advertiser_campaign_drafts(id) ON DELETE SET NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_dp_sponsored_draft
  ON sponsored_events(advertiser_draft_id) WHERE advertiser_draft_id IS NOT NULL;
