"""Contracts for invited advertisers, safety gates and campaign lifecycle."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class AdvertiserPortalContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=(ROOT/'api/advertiser.js').read_text('utf8')
        cls.admin=(ROOT/'api/admin.js').read_text('utf8')
        cls.html=(ROOT/'public/anunciantes/index.html').read_text('utf8')
        cls.front=(ROOT/'public/anunciantes/portal.js').read_text('utf8')
        cls.sql=(ROOT/'sql/advertising_v2.sql').read_text('utf8')
        cls.admin_html=(ROOT/'public/admin/index.html').read_text('utf8')
        cls.admin_front=(ROOT/'public/admin/admin.js').read_text('utf8')

    def test_invite_is_admin_only_and_not_emailed_automatically(self):
        self.assertIn("op==='advertiser-invite'",self.admin)
        self.assertIn("if(!authenticated(req))",self.admin)
        self.assertIn("randomBytes(32).toString('hex')",self.admin)
        self.assertIn("createHash('sha256')",self.admin)
        self.assertIn("access_version=access_version+1",self.admin)
        self.assertIn("invitation_url",self.admin)
        self.assertIn("showAdvertiserLink",self.admin_front)
        self.assertIn("Crear acceso privado",self.admin_front)
        self.assertNotIn("nodemailer",self.admin)
        self.assertNotIn("resend.com",self.admin)

    def test_portal_tokens_stay_private_with_server_side_session(self):
        self.assertIn('noindex,nofollow,noarchive',self.html)
        self.assertIn('no-referrer',self.html)
        self.assertIn("new URLSearchParams(location.hash",self.front)
        self.assertIn("history.replaceState",self.front)
        self.assertIn('HttpOnly; Secure; SameSite=Strict',self.api)
        self.assertIn("token_hash",self.api)
        self.assertIn('access_version',self.api)
        self.assertIn('WHERE d.id=',self.api)
        self.assertIn('advertiser_id=',self.api)
        self.assertIn("sameOrigin(req)",self.api)
        self.assertIn("DPARRANDA_ADVERTISER_PORTAL_ENABLED",self.api)

    def test_drafts_not_paid_or_published_by_default(self):
        self.assertIn("payment_enabled:false",self.api)
        self.assertNotIn('stripe.com',self.api)
        self.assertIn("status TEXT NOT NULL DEFAULT 'draft'",self.sql)
        self.assertIn("payment_status TEXT NOT NULL DEFAULT 'unavailable'",self.sql)
        self.assertIn("if(decision==='approved_for_payment'&&!draft.has_image)",self.admin)
        self.assertIn("El enlace de pago estará disponible",self.admin)
        self.assertIn("payment_enabled:false",self.admin)
        self.assertIn('pending_payment',self.html + self.api + self.sql)
        self.assertIn('stats_available:false',self.api)
        self.assertIn('actual_ends_at',self.api)
        self.assertIn("estadísticas",self.html.lower())

    def test_image_and_privacy_guards(self):
        self.assertIn('1200',self.api)
        self.assertIn('675',self.api)
        self.assertIn('image/webp',self.api)
        self.assertIn('privacy_accepted_at',self.sql)
        self.assertIn('DPARRANDA_PRIVACY_URL',self.api)
        self.assertIn("req.body?.consent!==true",self.api)
        self.assertIn('id="portalConsent"',self.html)
        self.assertIn('id="advertiserAccountsList"',self.admin_html)
        self.assertIn('id="advertiserDraftsList"',self.admin_html)

if __name__=="__main__":
    unittest.main()
