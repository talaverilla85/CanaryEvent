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
        self.assertIn("DPARRANDA_PRIVACY_URL",api)
        self.assertIn("sameOrigin(req)",api)
        self.assertIn("privacy_accepted_at",api)
        self.assertIn("INTERES_INICIAL|",api)
        self.assertNotIn("TELEGRAM_BOT_TOKEN",api)
        self.assertIn('id="interestForm"',html)
        self.assertIn("'/api/advertise-interest'",front)
        self.assertNotIn("image:draft.image",front)
        self.assertIn("INTERES_INICIAL|",panel)
        self.assertIn('cron: "*/5 * * * *"',wf)
        self.assertIn("secrets.DPARRANDA_DATABASE_URL",wf)
        self.assertIn("secrets.TELEGRAM_BOT_TOKEN",wf)

if __name__=="__main__":unittest.main()
