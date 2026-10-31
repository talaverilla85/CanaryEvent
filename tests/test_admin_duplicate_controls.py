"""Contracts for reversible duplicate moderation in the private admin.

These tests prevent accidentally introducing irreversible SQL deletes and ensure
the public catalog honors manual moderation across source synchronizations.
"""
import unittest
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"
ROOT = PUBLIC.parent


class AdminDuplicateModerationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = (ROOT / "api" / "admin.js").read_text(encoding="utf-8")
        cls.catalog = (ROOT / "api" / "catalog.js").read_text(encoding="utf-8")
        cls.client = (PUBLIC / "admin" / "admin.js").read_text(encoding="utf-8")
        cls.page = (PUBLIC / "admin" / "index.html").read_text(encoding="utf-8")

    def test_admin_has_distinct_remove_and_restore_actions(self):
        self.assertIn("data-hide-duplicate", self.client)
        self.assertIn("data-restore-event", self.client)
        self.assertIn("function changeEventVisibility", self.client)
        self.assertIn("window.confirm", self.client)
        self.assertIn("api('visibility',{id:row.id,hidden})", self.client)
        self.assertIn('<option value="hidden">Ocultos · restaurables</option>', self.page)

    def test_visibility_only_updates_override_state(self):
        visibility = self.admin.split("async function setEventVisibility(", 1)[1].split("async function saveAd(", 1)[0]
        self.assertIn("typeof body.hidden!=='boolean'", visibility)
        self.assertIn("INSERT INTO event_overrides", visibility)
        self.assertIn("ON CONFLICT(event_id) DO UPDATE", visibility)
        self.assertIn("hidden=excluded.hidden", visibility)
        self.assertNotIn("DELETE FROM", visibility)
        self.assertNotIn("UPDATE published_events", visibility)
        self.assertNotIn("title_override=excluded", visibility)

    def test_hidden_events_are_absent_from_public_catalog_and_duplicate_list(self):
        self.assertIn("COALESCE(o.hidden,FALSE)=FALSE", self.catalog)
        self.assertIn("o.canonical_event_id IS NULL", self.catalog)
        self.assertIn("COALESCE(r_override.hidden,FALSE)=FALSE", self.admin)
        self.assertIn("r_override.canonical_event_id IS NULL", self.admin)
        self.assertIn("only==='hidden'", self.admin)
        self.assertIn("!r.hidden && !r.canonical_event_id", self.admin)

    def test_admin_api_requires_authentication_for_visibility(self):
        self.assertIn("if(!authenticated(req))", self.admin)
        self.assertIn("req.method==='POST'&&op==='visibility'", self.admin)


if __name__ == "__main__":
    unittest.main()
