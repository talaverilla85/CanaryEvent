-- Non-destructive, reversible removal of advertising from the management UI.
-- Paid records remain in their original tables for fiscal and payment traceability.
CREATE TABLE IF NOT EXISTS advertising_archives (
  source TEXT NOT NULL CHECK(source IN ('lead','draft','house','published')),
  record_id TEXT NOT NULL,
  archived_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(source,record_id)
);
CREATE INDEX IF NOT EXISTS idx_advertising_archives_time ON advertising_archives(archived_at DESC);
