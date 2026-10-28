import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telegram_health_alert as notify

START="2026-10-28T22:00:35Z"
END="2026-10-28T22:05:59Z"
CHECK="2026-10-28T22:01:37+00:00"
LINK="https://github.com/talaverilla85/CanaryEvent/actions/runs/40776561930"

def meta():
    return {"checked_at":CHECK,"counts":{"approved":492}}

def quality(*errors):
    return {"checked_at":CHECK,
            "reported_errors":[{"source":n,"error":e} for n,e in errors]}

def make(quality_data=None,metadata=None,**overrides):
    kw=dict(conclusion="success",event="schedule",url=LINK,
            started=START,finished=END,
            quality=quality_data if quality_data is not None else quality(),
            meta=metadata if metadata is not None else meta())
    kw.update(overrides)
    return notify.make_message(**kw)

class TelegramHealthTests(unittest.TestCase):
    def test_clean_daily_sync_sends_no_message(self):
        self.assertIsNone(make())
        self.assertIsNone(make(event="push",quality_data=quality(("Site","Error"))))

    def test_daily_partial_errors_are_not_silenced(self):
        m=make(quality(("Auditorio Alfredo Kraus","RuntimeError"),
                       ("Carteles oficiales","ValueError")))
        self.assertIn("2 fuentes",m)
        self.assertIn("Auditorio Alfredo Kraus",m)
        self.assertIn("ValueError",m)
        self.assertIn("492",m)
        self.assertIn(LINK,m)
        self.assertNotIn("recintos_sin_verificar",m)

    def test_workflow_failure_alert_even_without_fresh_report(self):
        m=make(conclusion="failure",event="push",quality_data={},
               metadata={},started="",finished="")
        self.assertIn("Falló",m)
        self.assertIn(LINK,m)
        self.assertNotIn("492",m)

    def test_no_stale_incidences_attributed_to_current_run(self):
        old=quality(("Previous source","ExpiredError"))
        old["checked_at"]="2026-10-27T22:01:37+00:00"
        text=make(quality_data=old)
        self.assertIn("No se pudo validar",text)
        self.assertNotIn("Previous source",text)

    def test_source_error_lines_cannot_inject_chat_markup(self):
        m=make(quality(("Wrong\nextra line", "Error\nother")))
        self.assertIn("Wrong extra line",m)
        self.assertNotIn("Wrong\nextra",m)

    def test_successful_telegram_delivery(self):
        sent={}
        class Response:
            status_code=200
            def json(self):return {"ok":True}
        class Session:
            def post(self,url,**kw):
                sent.update({"url":url,**kw})
                return Response()
        self.assertTrue(notify.send("fake-token-not-real","12345","A problem",session=Session()))
        self.assertEqual(sent["json"]["chat_id"],"12345")
        self.assertEqual(sent["json"]["text"],"A problem")
        self.assertEqual(sent["timeout"],15)

    def test_http_error_no_token_in_exception(self):
        class Response:
            status_code=403
        class Session:
            def post(self,url,**kw):
                return Response()
        self.assertFalse(notify.send("secret","12345","A problem",session=Session()))

    def test_not_configured_does_not_send_or_fail(self):
        with patch.object(notify,"send") as sender:
            rc=notify.run({"SOURCE_RUN_CONCLUSION":"failure","SOURCE_RUN_EVENT":"push",
                  "SOURCE_RUN_URL":LINK,"SOURCE_RUN_STARTED_AT":START,
                  "SOURCE_RUN_FINISHED_AT":END,"TELEGRAM_BOT_TOKEN":"",
                  "TELEGRAM_CHAT_ID":""})
        self.assertEqual(rc,0)
        sender.assert_not_called()

    def test_manual_test_fails_until_both_secrets_are_present(self):
        self.assertEqual(notify.run({"TELEGRAM_BOT_TOKEN":"","TELEGRAM_CHAT_ID":""},test=True),1)

    def test_test_message_is_sent_only_in_explicit_test(self):
        with patch.object(notify,"send",return_value=True) as sender:
            self.assertEqual(notify.run({"TELEGRAM_BOT_TOKEN":"test",
                                         "TELEGRAM_CHAT_ID":"123"},test=True),0)
            self.assertIn("Prueba",sender.call_args.args[2])

if __name__=="__main__":unittest.main()
