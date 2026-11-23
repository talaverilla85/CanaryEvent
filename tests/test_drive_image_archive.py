import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_event_images_drive as mod


class DriveImageArchiveTests(unittest.TestCase):
    def test_explicit_archiving_permission_only(self):
        self.assertTrue(mod.authorized('Autorizado'))
        for state in ['', 'Pendiente', 'Denegado', 'Pendiente de verificar', 'Autorizado para redes']:
            self.assertFalse(mod.authorized(state), state)

    def test_groups_same_poster_for_multiple_event_sessions(self):
        url = 'https://ayuntamiento.example/cartel.webp'
        base = {'title': 'Mercado de Navidad', 'start': '2026-12-10',
                'end': '2026-12-10', 'municipality': 'Telde',
                'image_url': url, 'image_status': 'official_remote'}
        events = [dict(base, id=10), dict(base, id=11),
                  dict(base, id=12, image_status='not_available'),
                  dict(base, id=13, end='2026-10-15')]
        found = mod.discover({'events': events}, today=date(2026, 11, 23))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[url]['event_ids'], {'10', '11'})

    def test_rejects_unsafe_image_addresses(self):
        for url in ['http://example.com/x.jpg', 'https://127.0.0.1/x.jpg',
                    'https://localhost/x.jpg', 'https://user:pass@example.com/x.jpg',
                    'file:///etc/passwd', 'https://example.com:8080/a.jpg']:
            with self.assertRaises(ValueError, msg=url):
                mod.valid_https(url)
        self.assertEqual(mod.valid_https('https://municipio.example/img.webp'),
                         'municipio.example')

    def test_municipality_filename_is_safe(self):
        value = mod.slug('Feria de Navidad: Agüimes / 2026')
        self.assertNotIn('/', value)
        self.assertNotIn(':', value)
        self.assertIn('Ag', value)


if __name__ == '__main__':
    unittest.main()
