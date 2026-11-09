"""Guard the small-text contrast fixes in DParranda's mobile storefront."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/"public/brand/dparranda-editorial.css").read_text("utf-8")
HTML=(ROOT/"public/index.html").read_text("utf-8-sig")

def luminance(hex_color):
    colors=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in colors]
    return .2126*linear[0]+.7152*linear[1]+.0722*linear[2]

def contrast(foreground,background):
    a,b=luminance(foreground),luminance(background)
    return (max(a,b)+.05)/(min(a,b)+.05)

class MobileContrastTests(unittest.TestCase):
    def test_specificity_overrides_problematic_widgets(self):
        for rule in (
            ".result-titles h2 .count{color:#36545E!important}",
            ".footer #sourcesBtn.text-button{color:#07536C!important",
            ".bottom-nav .navtab:not(.selected),.bottom-nav .navtab:not(.selected) small{color:#334F5F}",
            ".bottom-nav .navtab.selected,.bottom-nav .navtab.selected small{color:#075D74!important}",
            "#openFiltersBtn.dp-filter-entry{color:#173E4E}",
            "#openFiltersBtn.dp-filter-entry .filter-entry-copy small{color:#334F59}",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule,CSS)

    def test_aa_normal_text_contrast_with_actual_light_surfaces(self):
        pairs={
            "result count":("#36545E","#F5F5F0"),
            "sources button":("#07536C","#F5F5F0"),
            "inactive navigation":("#334F5F","#FFFDF9"),
            "active navigation":("#075D74","#FFFDF9"),
            "filter description":("#334F59","#FFFFFF"),
            "filter button":("#173E4E","#FFFFFF"),
        }
        for name,(fg,bg) in pairs.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(contrast(fg,bg),4.5)

    def test_updated_stylesheet_is_requested(self):
        self.assertIn('id="dparranda-brand-styles"',HTML)
        self.assertIn('meta name="robots" content="noindex,nofollow"',HTML)

if __name__=="__main__":
    unittest.main()
