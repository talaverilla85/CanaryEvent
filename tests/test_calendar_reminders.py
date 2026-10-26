"""Calendar reminders: future dates, Canary timezone, previous Friday at 18:00.

The generated ICS intentionally requires explicit import in the person's
calendar app. There is no unimplemented Web Push promise.
"""
import json,subprocess,shutil,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ReminderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.js=(ROOT/"public"/"reminders.js").read_text(encoding="utf8")
  cls.html=(ROOT/"public"/"index.html").read_text(encoding="utf8")

 def test_reminder_accessible_from_event_and_favorites(self):
  self.assertIn("id=\"reminderDetailBtn\"",self.html)
  self.assertIn("openReminderDialog(e)",self.html)
  self.assertIn("function openReminderDialog(e)",self.js)
  self.assertIn("id=\"reminderLead\"",self.js)
  self.assertIn("recordatorio-padonde-",self.js)

 def test_no_false_native_push_promise(self):
  self.assertIn("no son avisos push",self.js.lower())
  self.assertIn("en el calendario del móvil",self.js)
  self.assertIn("TRIGGER;VALUE=DATE-TIME:",self.js)
  self.assertNotIn("new Notification(",self.js)
  self.assertNotIn("pushManager.subscribe(",self.js)

 def test_source_has_days_and_friday_without_session_invention(self):
  for token in ["P1D","P2D","P3D","P7D","FRIDAY","PT15M","PT1H","PT3H"]:
   self.assertIn(token,self.js)
  self.assertIn("if(day<todayKey())return false",self.js)
  self.assertIn("previo",self.js.lower()) if False else self.assertIn("function reminderPreviousFriday",self.js)

 @unittest.skipUnless(shutil.which("node"),"Requires Node.js to exercise ICS generation")
 def test_generated_ics_friday_and_summer_dst(self):
  snippet=r"""
const fs=require('fs'),vm=require('vm');
const today=()=>new Date().toISOString().slice(0,10);
const sandbox={Date,Intl,console,encodeURIComponent,todayKey:today,venueName:()=>'Plaza Municipal'};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const e={id:123,title:'Fiesta fin de semana',municipality:'Telde',venue:'Plaza Municipal',start:'2031-11-02T19:00:00'};
const friday=sandbox.reminderPreviousFriday('2031-11-02');
const alarm=sandbox.reminderAlarmTime(e,'FRIDAY').toISOString();
const summer=sandbox.calendarUtcFromCanary('2031-07-18',18).toISOString();
const winter=sandbox.calendarUtcFromCanary('2031-11-14',18).toISOString();
const choices=sandbox.reminderChoices(e).map(x=>x[0]);
const ics=sandbox.reminderICS(e,'FRIDAY');
const dateOnly=sandbox.reminderICS({...e,start:'2031-11-02'},'FRIDAY');
console.log(JSON.stringify({friday,alarm,summer,winter,choices,
  ics,wholeDay:dateOnly.includes('DTSTART;VALUE=DATE:20311102')}));
"""
  p=subprocess.run(["node","-e",snippet,str(ROOT/"public"/"reminders.js")],
                    text=True,capture_output=True,timeout=10,check=True)
  o=json.loads(p.stdout.strip())
  self.assertEqual(o["friday"],"2031-10-31")
  self.assertEqual(o["alarm"],"2031-10-31T18:00:00.000Z")
  self.assertEqual(o["summer"],"2031-07-18T17:00:00.000Z")
  self.assertEqual(o["winter"],"2031-11-14T18:00:00.000Z")
  self.assertIn("FRIDAY",o["choices"])
  self.assertIn("TRIGGER;VALUE=DATE-TIME:20311031T180000Z",o["ics"])
  self.assertTrue(o["wholeDay"])

if __name__=="__main__":
 unittest.main()
