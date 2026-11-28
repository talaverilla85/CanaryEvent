"""Two separate installable DParranda PWAs, preserving private administration."""
from pathlib import Path
import json
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]

class DualPwaInstallContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.public_manifest=json.loads((ROOT/'public/manifest.webmanifest').read_text('utf-8'))
  cls.admin_manifest=json.loads((ROOT/'public/admin/manifest.webmanifest').read_text('utf-8'))
  cls.public_html=(ROOT/'public/index.html').read_text('utf-8-sig')
  cls.admin_html=(ROOT/'public/admin/index.html').read_text('utf-8')
  cls.public_install=(ROOT/'public/install_prompt.js').read_text('utf-8')
  cls.admin_install=(ROOT/'public/admin/install.js').read_text('utf-8')
  cls.public_sw=(ROOT/'public/sw.js').read_text('utf-8')
  cls.admin_sw=(ROOT/'public/admin/sw.js').read_text('utf-8')
  cls.vercel=json.loads((ROOT/'vercel.json').read_text('utf-8'))

 def test_manifests_have_distinct_identity_launch_and_scope(self):
  self.assertEqual(self.public_manifest['id'],'/')
  self.assertEqual(self.public_manifest['start_url'],'/')
  self.assertEqual(self.admin_manifest['id'],'/admin/')
  self.assertEqual(self.admin_manifest['start_url'],'/admin/')
  self.assertEqual(self.admin_manifest['scope'],'/admin/')
  self.assertEqual(self.admin_manifest['display'],'standalone')
  self.assertNotEqual(self.public_manifest['id'],self.admin_manifest['id'])
  self.assertIn('Admin',self.admin_manifest['short_name'])

 def test_admin_icons_exist_in_actual_png_dimensions(self):
  icons={(int(i['sizes'].split('x')[0]),i['src']) for i in self.admin_manifest['icons'] if i['type']=='image/png'}
  for px in (192,512):
   icon='/admin/icons/admin-'+str(px)+'.png'
   self.assertIn((px,icon),icons)
  for px in (180,192,512):
   image=ROOT/'public/admin/icons'/('admin-'+str(px)+'.png')
   data=image.read_bytes()
   self.assertTrue(data.startswith(bytes([137,80,78,71,13,10,26,10])))
   self.assertEqual(struct.unpack('>II',data[16:24]),(px,px))

 def test_public_install_button_is_preserved_and_remembers_confirmation(self):
  self.assertIn('id="dpInstallDock"',self.public_html)
  self.assertIn('id="dpInstallAction"',self.public_html)
  self.assertIn('src="/install_prompt.js?v=4"',self.public_html)
  self.assertIn("window.addEventListener('appinstalled',markInstalled)",self.public_install)
  self.assertIn("localStorage.setItem(installedKey,String(Date.now()))",self.public_install)
  self.assertIn("!installedInThisVisit && !installedRecently()",self.public_install)

 def test_admin_has_own_install_button_guide_and_home_screen_icon(self):
  self.assertIn('href="/admin/manifest.webmanifest?v=1"',self.admin_html)
  self.assertIn('href="/admin/icons/admin-180.png"',self.admin_html)
  self.assertIn('id="adminInstallDock"',self.admin_html)
  self.assertIn('id="adminInstallBtn"',self.admin_html)
  self.assertIn('id="adminInstallGuide"',self.admin_html)
  self.assertIn('src="/admin/install.js?v=1"',self.admin_html)
  self.assertIn('window.addEventListener(\'beforeinstallprompt\'',self.admin_install)
  self.assertIn("window.addEventListener('appinstalled',installed)",self.admin_install)
  self.assertIn("if(!deferred){showGuide();return}",self.admin_install)
  self.assertIn("installedRecently()",self.admin_install)
  self.assertIn("display-mode: standalone",self.admin_install)
  self.assertIn("navigator.serviceWorker.register('/admin/sw.js',{scope:'/admin/'})",self.admin_install)
  self.assertIn('id="loginForm"',self.admin_html)

 def test_admin_never_caches_private_data(self):
  self.assertNotIn('caches.open(',self.admin_sw)
  self.assertNotIn("caches.match(",self.admin_sw)
  self.assertIn("u.pathname.startsWith('/admin/')",self.public_sw)
  self.assertNotIn('DPARRANDA_SESSION_SECRET',self.admin_html)
  self.assertIn('noindex,nofollow,noarchive',self.admin_html)

 def test_correct_manifest_mime_types_configured(self):
  headers={rule['source']:rule['headers'] for rule in self.vercel['headers']}
  for route in ('/manifest.webmanifest','/admin/manifest.webmanifest'):
   self.assertIn(route,headers)
   self.assertTrue(any(h['key']=='Content-Type' and 'manifest+json' in h['value'] for h in headers[route]))

if __name__=='__main__':
 unittest.main()
