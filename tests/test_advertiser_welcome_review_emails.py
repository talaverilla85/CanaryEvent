"""Advertiser on-boarding and edit request mailflow contract."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AdvertiserWelcomeReviewEmails(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.intake=(ROOT/'api/advertise-interest.js').read_text('utf8')
  cls.workspace=(ROOT/'lib/advertiser-workspace.js').read_text('utf8')
  cls.mail=(ROOT/'lib/advertiser-mail.js').read_text('utf8')
  cls.portal=(ROOT/'api/advertiser.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.simulator=(ROOT/'public/anunciate/simulador/simulator.js').read_text('utf8')
  cls.simulator_html=(ROOT/'public/anunciate/simulador/index.html').read_text('utf8')

 def test_welcome_created_only_after_submitted_campaign(self):
  self.assertIn("const workspace=await ensureAdvertiserWorkspace(sql,Number(row.enquiry_id))",self.intake)
  self.assertIn("await sendWelcomeEmail(workspace)",self.intake)
  self.assertIn("welcome_email:emailStatus",self.intake)
  self.assertIn("ON CONFLICT(lead_id)",self.workspace)
  self.assertIn("ON CONFLICT(source_lead_id)",self.workspace)
  self.assertIn("advertising_enquiry_images",self.workspace)
  self.assertIn("advertiser_campaign_draft_images",self.workspace)

 def test_signed_links_are_server_only_and_revocable(self):
  self.assertIn("createHmac('sha256',SECRET())",self.mail)
  self.assertIn("timingSafeEqual",self.mail)
  self.assertIn("expires<=Math.floor(Date.now()/1000)",self.mail)
  self.assertIn("parseEmailAccessToken(t)",self.portal)
  self.assertIn("access_version",self.portal)
  self.assertIn("if(!a)return json(res,401",self.portal)
  self.assertNotIn("RESEND_API_KEY",self.simulator)

 def test_revision_emails_are_sent_only_when_requested(self):
  self.assertIn("sendChangesRequestedEmail(workspace,note",self.admin)
  self.assertIn("if(decision==='changes_requested')",self.admin)
  self.assertIn("const workspace=await workspaceForDraft(sql,id)",self.admin)
  self.assertIn("const workspace=await ensureAdvertiserWorkspace(sql,id)",self.admin)
  self.assertIn("notification_status:emailStatus",self.admin)
  self.assertIn("review_note",self.admin)
  self.assertIn("Revisar y corregir mi anuncio",self.mail)

 def test_domain_gate_and_resend_test_sandbox(self):
  self.assertIn("RESEND_CUSTOMER_EMAILS_ENABLED",self.mail)
  self.assertIn("RESEND_FROM_EMAIL",self.mail)
  self.assertIn("sandboxRecipient()",self.mail)
  self.assertIn("String(to||'').trim().toLowerCase()===sandboxRecipient()",self.mail)
  self.assertIn("onboarding@resend.dev",self.mail)
  self.assertIn("if(!canSendTo(to))return {status:'pending_domain'}",self.mail)
  self.assertIn("idempotencyKey",self.mail)
  self.assertIn("No se ha cobrado ni publicado nada.",self.simulator)

 def test_public_confirmation_does_not_promise_email_unless_sent(self):
  self.assertIn("result.welcome_email==='sent'",self.simulator)
  self.assertIn("private_area_ready",self.simulator)
  self.assertIn("interest-success",self.simulator_html)
  self.assertIn("No se ha cobrado ni publicado nada.",self.simulator)
if __name__=='__main__':
 unittest.main()
