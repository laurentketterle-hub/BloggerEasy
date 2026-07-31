import unittest, os, xml.etree.ElementTree as ET

class TestDarkDevTheme(unittest.TestCase):
    def setUp(self):
        self.theme_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'themes', 'dark_dev')
    
    def test_all_files_exist(self):
        for fname in ['index.html', 'style.css', 'theme.xml']:
            path = os.path.join(self.theme_dir, fname)
            self.assertTrue(os.path.exists(path), f"Missing: {fname}")
    
    def test_html_structure(self):
        with open(os.path.join(self.theme_dir, 'index.html'), encoding='utf-8') as f:
            html = f.read()
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('data-theme="dark_dev"', html)
        self.assertIn('<article class="post">', html)
        self.assertIn('<pre><code', html)
    
    def test_css_has_dark_colors(self):
        with open(os.path.join(self.theme_dir, 'style.css'), encoding='utf-8') as f:
            css = f.read()
        self.assertIn('#0d1117', css)
        self.assertIn('--font-mono', css)
        self.assertIn('@media', css)
    
    def test_xml_valid(self):
        tree = ET.parse(os.path.join(self.theme_dir, 'theme.xml'))
        root = tree.getroot()
        self.assertEqual(root.attrib['name'], 'dark_dev')
        self.assertIsNotNone(root.find('colors'))
        self.assertIsNotNone(root.find('typography'))
    
    def test_theme_pack_minimum_size(self):
        total = 0
        for fname in ['index.html', 'style.css', 'theme.xml']:
            path = os.path.join(self.theme_dir, fname)
            total += os.path.getsize(path)
        self.assertGreater(total, 2000, f"Theme pack too small ({total} bytes)")

if __name__ == '__main__':
    unittest.main()
