-- Stripe Checkout Payment Links (testmode first).
-- Apply in Neon before deploying approval/payment backend.
-- One Stripe link per advertiser draft. This migration is safe to rerun.
ALTER TABLE advertiser_campaign_drafts
  ADD COLUMN IF NOT EXISTS stripe_payment_link_id TEXT;
ALTER TABLE advertiser_campaign_drafts
  ADD COLUMN IF NOT EXISTS stripe_payment_url TEXT;
ALTER TABLE advertiser_campaign_drafts
  ADD COLUMN IF NOT EXISTS stripe_checkout_session_id TEXT;
ALTER TABLE advertiser_campaign_drafts
  ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS idx_dp_campaign_stripe_link
  ON advertiser_campaign_drafts(stripe_payment_link_id)
  WHERE stripe_payment_link_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_dp_campaign_stripe_checkout
  ON advertiser_campaign_drafts(stripe_checkout_session_id)
  WHERE stripe_checkout_session_id IS NOT NULL;
