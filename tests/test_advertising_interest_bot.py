"""Commercial-interest intake stays private, and Telegram sends no personal data."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telegram_advertising_leads as alerts

class FakeSQL:
    def __init__(self,rows):
        self.rows=rows;self.queries=[];self.sent=[]
    def cursor(self):
        class Cursor:
            def __init__(self,outer):self.outer=outer
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def execute(self,query,parameters=None):
                self.outer.queries.append((query,parameters))
                if "INSERT INTO advertising_interest_notifications" in query:
                    self.outer.sent.append(parameters[0])
            def fetchall(self):return self.outer.rows
        return Cursor(self)

class InterestBotContract(unittest.TestCase):
    def test_alert_is_minimal_and_private(self):
        msg=alerts.make_message(123,"INTERES_INICIAL|zona|98|60|banner")
        self.assertIn("Solicitud #123",msg)
        self.assertIn("98 €",msg)
        self.assertIn("admin/#publicidad",msg)
        self.assertNotIn("@",msg)
        self.assertNotIn("correo@",msg.lower())
        self.assertNotIn("gmail",msg)
        self.assertIsNone(alerts.make_message(1,"proposal"))
        self.assertIsNone(alerts.make_message(1,"INTERES_INICIAL|otro|99|60|banner"))

    def test_mark_only_after_telegram_success(self):
        sql=FakeSQL([(7,"INTERES_INICIAL|local|19|30|evento")])
        count,ok=alerts.poll(sql,"token","chat",send_message=lambda *args:False)
        self.assertEqual((count,ok),(0,False))
        self.assertEqual(sql.sent,[])
        count,ok=alerts.poll(sql,"token","chat",send_message=lambda *args:True)
        self.assertEqual((count,ok),(1,True))
        self.assertEqual(sql.sent,[7])

    def test_no_secrets_no_test_message(self):
        self.assertEqual(alerts.run({"TELEGRAM_BOT_TOKEN":"","TELEGRAM_CHAT_ID":""},test=True),1)
        out=[]
        self.assertEqual(alerts.run({"TELEGRAM_BOT_TOKEN":"token","TELEGRAM_CHAT_ID":"id"},
                 test=True,send_message=lambda a,b,msg:out.append(msg) or True),0)
        self.assertEqual(len(out),1)
        self.assertIn("conectados",out[0])

    def test_pages_and_api_contract(self):
        api=(ROOT/"api/advertise-interest.js").read_text("utf8")
        html=(ROOT/"public/anunciate/simulador/index.html").read_text("utf8")
        front=(ROOT/"public/anunciate/simulador/simulator.js").read_text("utf8")
        panel=(ROOT/"public/admin/admin.js").read_text("utf8")
        wf=(ROOT/".github/workflows/telegram-advertising-leads.yml").read_text("utf8")
        self.assertIn("DPARRANDA_LEADS_ENABLED",api)
        self.assertIn("legalPrivacyUrl()",api)
        self.assertIn("sameOrigin(req)",api)
        self.assertIn("privacy_accepted_at",api)
        self.assertIn("INTERES_INICIAL|",api)
        self.assertNotIn("TELEGRAM_BOT_TOKEN",api)
        self.assertIn('id="interestForm"',html)
        self.assertIn("'/api/advertise-interest'",front)
        self.assertNotIn("image:draft.image",front)
        self.assertIn("INTERES_INICIAL|",panel)
        self.assertIn('Pausado durante el lanzamiento orgánico',wf)
        self.assertNotIn('cron: "*/5 * * * *"',wf)
        self.assertIn("secrets.DPARRANDA_DATABASE_URL",wf)
        self.assertIn("secrets.TELEGRAM_BOT_TOKEN",wf)



class PaymentBotContract(unittest.TestCase):
    def sample(self,session="cs_live_abcdef123",start="2026-11-20",end="2026-12-19"):
        return (81,"Comercio ejemplo","Campaña de Navidad","zona",30,"banner",
                4900,["Agüimes","Ingenio"],start,end,session)

    def test_confirmed_payment_content(self):
        msg=alerts.make_payment_message(self.sample())
        self.assertIn("PAGO CONFIRMADO",msg)
        self.assertIn("Comercio ejemplo",msg)
        self.assertIn("Campaña de Navidad",msg)
        self.assertIn("Zona",msg)
        self.assertIn("49,00 €",msg)
        self.assertIn("20/11/2026",msg)
        self.assertIn("19/12/2026",msg)
        self.assertIn("Agüimes, Ingenio",msg)
        self.assertIn("admin/#publicidad",msg)
        self.assertNotIn("gmail",msg.lower())

    def test_test_payment_is_clearly_fictitious(self):
        msg=alerts.make_payment_message(self.sample(session="cs_test_xyzABC123"))
        self.assertIn("PRUEBA",msg)
        self.assertIn("No se ha cobrado",msg)
        self.assertNotIn("💶",msg)

    def test_no_alert_for_unconfirmed_or_unscheduled_payments(self):
        self.assertIsNone(alerts.make_payment_message(self.sample(session="unconfirmed")))
        self.assertIsNone(alerts.make_payment_message(self.sample(start=None)))
        self.assertIsNone(alerts.make_payment_message(self.sample(end=None)))

    def test_payment_alert_is_marked_only_after_delivery(self):
        class FakePaidSQL:
            def __init__(self,row):
                self.row=row;self.delivered=[]
            def cursor(self):
                outer=self
                class Cursor:
                    def __enter__(self):return self
                    def __exit__(self,*args):return False
                    def execute(self,query,params=None):
                        if "INSERT INTO advertising_payment_notifications" in query:
                            outer.delivered.append(params[0])
                    def fetchall(self):return [outer.row]
                return Cursor()
        sql=FakePaidSQL(self.sample())
        self.assertEqual(alerts.poll_payments(sql,"token","chat",send_message=lambda *args:False),(0,False))
        self.assertEqual(sql.delivered,[])
        self.assertEqual(alerts.poll_payments(sql,"token","chat",send_message=lambda *args:True),(1,True))
        self.assertEqual(sql.delivered,[81])

    def test_submitted_request_has_a_review_link(self):
        msg=alerts.make_message(123,"INTERES_INICIAL|local|19|30|evento",
            company="AriMar",title="Anuncio",zone="Agüimes",
            start="2026-11-20",review_status="submitted")
        self.assertIn("Nueva solicitud de publicidad",msg)
        self.assertIn("AriMar",msg)
        self.assertIn("pendiente de revisión",msg)
        self.assertIn("admin/#publicidad",msg)

    def test_polling_contract_requires_stripe_confirmation_and_schedule(self):
        source=(ROOT/"scripts/telegram_advertising_leads.py").read_text("utf8")
        self.assertIn("d.payment_status='paid'",source)
        self.assertIn("d.paid_at IS NOT NULL",source)
        self.assertIn("d.actual_starts_at IS NOT NULL",source)
        self.assertIn("advertising_payment_notifications",source)

if __name__=="__main__":unittest.main()
