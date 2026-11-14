"""Private issuer profile for self-employed D’Parranda. Fiscal issuance stays disabled."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class SelfEmployedIssuerContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.schema=(ROOT/'sql/advertising-invoice-issuer.sql').read_text('utf8')
  cls.issuer=(ROOT/'lib/advertising-invoice-issuer.js').read_text('utf8')
  cls.preview=(ROOT/'lib/advertising-invoice-reviews.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.panel=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.html=(ROOT/'public/admin/index.html').read_text('utf8')
 def test_issuer_is_person_and_single_profile(self):
  self.assertIn("CHECK (issuer_type='individual')",self.schema)
  self.assertIn("CHECK (id=1)",self.schema)
  self.assertIn("INSERT INTO advertising_invoice_issuer",self.schema)
  self.assertIn("ON CONFLICT (id) DO NOTHING",self.schema)
  self.assertIn("issuer_type:'individual'",self.issuer)
  self.assertNotIn("issuer_type:'company'",self.issuer)
 def test_details_are_saved_only_by_authenticated_admin(self):
  self.assertIn("if(!authenticated(req))return json",self.admin)
  self.assertIn("op==='invoice-issuer'",self.admin)
  self.assertIn("op==='invoice-issuer-update'",self.admin)
  self.assertIn("if(req.method==='POST' && !sameOrigin(req))",self.admin)
  self.assertIn("saveInvoiceIssuer(sql,data(req))",self.admin)
  self.assertIn('invoiceIssuerForm',self.html)
  self.assertIn("loadInvoiceIssuerProfile()",self.panel)
  self.assertIn("invoice-issuer-update",self.panel)
  self.assertIn('admin.js?v=8',self.html)
 def test_invoice_preview_uses_actual_individual_data_but_is_not_fiscal(self):
  self.assertIn("await loadInvoiceIssuer(sql)",self.preview)
  self.assertIn("Emisor · autónomo",self.preview)
  self.assertIn("v(issuer.tax_id)",self.preview)
  self.assertIn("BORRADOR INTERNO · NO ES FACTURA",self.preview)
  self.assertIn("Impuestos e IGIC:",self.preview)
  self.assertIn("fiscal_issuance_enabled:false",self.issuer)
  self.assertIn("emails_sent:false",self.issuer)
  self.assertIn("copy_email TEXT NOT NULL DEFAULT 'hola@dparranda.es'",self.schema)
  self.assertIn('igic_general_rate_percent SMALLINT NOT NULL DEFAULT 7',self.schema)
  self.assertIn('prices_include_igic:true',self.issuer)
 def test_config_validation_does_not_auto_apply_igic(self):
  self.assertIn("tax_treatment:'pending'",self.issuer)
  self.assertIn('igic_general_rate_percent:7',self.issuer)
  self.assertIn('taxIdPattern',self.issuer)
  self.assertIn("validEmail(profile.copy_email)",self.issuer)

if __name__=='__main__':
 unittest.main()
