"""Contract tests for the private DParranda administration panel."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AdminPanelContract(unittest.TestCase):
    def test_private_panel_assets(self):
        html=(ROOT/'public/admin/index.html').read_text('utf-8')
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"',html)
        self.assertIn('Content-Security-Policy',html)
        self.assertIn('id="loginForm"',html)
        self.assertIn('id="eventsSection"',html)
        self.assertIn('id="adsSection"',html)
        self.assertIn('src="/admin/admin.js?',html)
        self.assertTrue((ROOT/'public/admin/admin.js').exists())
        self.assertTrue((ROOT/'public/admin/admin.css').exists())

    def test_api_requires_explicit_auth_config(self):
        source=(ROOT/'lib/admin-auth.js').read_text('utf-8')
        self.assertIn('DPARRANDA_ADMIN_PASSWORD_SCRYPT',source)
        self.assertIn('DPARRANDA_SESSION_SECRET',source)
        self.assertIn('timingSafeEqual',source)
        self.assertIn('SameSite=Strict',source)
        self.assertIn('HttpOnly',source)
        self.assertIn('Secure',source)
        admin=(ROOT/'api/admin.js').read_text('utf-8')
        self.assertIn('if(!isConfigured())',admin)
        self.assertIn('if(!authenticated(req))',admin)
        self.assertIn('!sameOrigin(req)',admin)
        self.assertIn('admin_login_limits',admin)

    def test_public_fallback_remains(self):
        source=(ROOT/'public/index.html').read_text('utf-8')
        self.assertIn("'/api/catalog'",source)
        self.assertIn("'/events.json'",source)
        self.assertIn("'/api/ads'",source)
        self.assertIn("'/ads.json'",source)
        api=(ROOT/'api/catalog.js').read_text('utf-8')
        self.assertIn('event_overrides',api)
        self.assertIn('o.canonical_event_id IS NULL',api)

    def test_secret_paths_are_not_public(self):
        for key in ('DPARRANDA_SESSION_SECRET','DPARRANDA_ADMIN_PASSWORD_SCRYPT','DATABASE_URL'):
            html=(ROOT/'public/admin/index.html').read_text('utf-8')
            self.assertNotIn(key,html)
        self.assertFalse((ROOT/'public/admin/.env').exists())

if __name__=="__main__":
    unittest.main()
