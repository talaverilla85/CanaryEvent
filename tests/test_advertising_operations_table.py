"""Ad operations table and editorial approval before Stripe checkout."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AdvertisingOperationsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'public/admin/index.html').read_text('utf8')
        cls.front=(ROOT/'public/admin/admin.js').read_text('utf8')
        cls.css=(ROOT/'public/admin/admin.css').read_text('utf8')
        cls.admin=(ROOT/'api/admin.js').read_text('utf8')
        cls.intake=(ROOT/'api/advertise-interest.js').read_text('utf8')
        cls.portal=(ROOT/'api/advertiser.js').read_text('utf8')
        cls.sim=(ROOT/'public/anunciate/simulador/simulator.js').read_text('utf8')
        cls.sim_html=(ROOT/'public/anunciate/simulador/index.html').read_text('utf8')
        cls.schema=(ROOT/'sql/advertising_v2.sql').read_text('utf8')

    def test_single_spreadsheet_with_summary_filters_and_preview(self):
        for id in ('adOpsInterested','adOpsPending','adOpsActive','adOpsFinished','adOpsSearch',
                   'adOpsFilter','adOpsExport','adOpsRows','adOpsCount'):
            self.assertIn('id="'+id+'"',self.html)
        for column in ('Empresa / anuncio','Solicitud','Estado','Pago','Días','Tipo / cobertura','Importe','Vista previa','Gestión'):
            self.assertIn(column,self.html)
        self.assertIn('adops-table-scroll',self.css)
        self.assertIn('overflow-x:auto',self.css)
        for status in ('interest','submitted','changes_requested','approved_for_payment','paid_review','active','finished','rejected'):
            self.assertIn('st-'+status,self.css)
        self.assertIn('renderAdOperations()',self.front)
        self.assertIn('opsOpenPreview(',self.front)
        self.assertIn('loadAdvertiserDrafts()',self.front)
        self.assertIn("text/csv;charset=utf-8",self.front)
        self.assertIn('^[\\s]*[=+\\-@]',self.front)

    def test_preview_submission_preserves_image_only_when_selected(self):
        self.assertIn('id="proposalSubmit"',self.sim_html)
        self.assertIn("proposal:proposal",self.sim.replace("proposal,","proposal:proposal,"))
        self.assertIn('image_data:proposal?draft.image:null',self.sim)
        self.assertIn('config.proposal_enabled===true',self.sim)
        self.assertIn('const proposalEnabled=()=>enabled()',self.intake)
        self.assertIn('Solicitar contratación y revisión del anuncio',self.sim_html)
        self.assertIn('const proposal=true',self.sim)
        self.assertIn("if(proposal&&!proposalEnabled())",self.intake)
        self.assertIn("review_status",self.intake)
        self.assertIn("advertising_enquiry_images",self.intake)
        self.assertIn('new_proposal',self.intake)
        self.assertIn("payment_required:false",self.intake)

    def test_revision_can_return_to_admin_without_checkout(self):
        self.assertIn("op==='submit'",self.portal)
        self.assertIn("status='submitted'",self.portal)
        self.assertIn("has_image",self.portal)
        self.assertIn("status IN ('draft','changes_requested')",self.portal)
        self.assertIn("status='draft'",self.portal)
        self.assertIn("source_lead_id",self.admin)
        self.assertIn("advertiser_campaign_draft_images",self.admin)
        self.assertIn("op==='enquiry-review'",self.admin)
        self.assertIn("op==='advertiser-review'",self.admin)
        self.assertIn("review_note",self.admin)
        self.assertIn("approved_for_payment",self.admin)
        self.assertIn("payment_enabled:false",self.admin)
        self.assertNotIn('checkout.sessions.create',self.admin)
        self.assertNotIn('payment_intent.succeeded',self.admin)

    def test_private_image_view_and_no_fake_payment(self):
        self.assertIn("if(!authenticated(req))",self.admin)
        self.assertIn('sameOrigin(req)',self.admin)
        self.assertIn("op==='advertiser-draft-image'",self.admin)
        self.assertIn("op==='leadimage'",self.admin)
        self.assertIn("DPARRANDA_LEADS_ENABLED",self.intake)
        self.assertIn("legalPrivacyUrl()",self.intake)
        self.assertIn("review_status TEXT NOT NULL DEFAULT 'interest'",self.schema)
        self.assertIn("advertiser_campaign_drafts_status_check",self.schema)
        self.assertIn("width=1000 AND height=563",self.schema)
        self.assertIn("width=1200 AND height=675",self.schema)
        self.assertIn('approved_for_payment',self.schema)
if __name__=="__main__":unittest.main()
