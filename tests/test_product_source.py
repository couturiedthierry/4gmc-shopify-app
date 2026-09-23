import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import product_source
import data_validator


class TestProductSourceAndValidator(unittest.TestCase):

    def setUp(self):
        self.supplier_data_1 = {
            "title": "Industrial Cordless Pressure Washer 20V",
            "description": "High pressure washer operating at 20V with 500 PSI maximum pressure. Heavy-duty 2000mAh battery pack included.",
            "images": ["https://cdn.example.com/washer.jpg"],
        }
        self.supplier_data_2 = {
            "title": "Modern Utility Canvas Tote Bag",
            "description": "Durable cotton canvas tote bag with reinforced handles for everyday shopping.",
            "images": ["https://cdn.example.com/bag.jpg"],
        }

    def test_product_source_extraction(self):
        ps = product_source.ProductSourceExtractor.extract("101", self.supplier_data_1)
        self.assertEqual(ps.product_id, "101")
        self.assertIn("voltage", ps.verified_attributes)
        self.assertEqual(ps.verified_attributes["voltage"].value, "20V")
        self.assertIn("pressure", ps.verified_attributes)
        self.assertEqual(ps.verified_attributes["pressure"].value, "500 PSI")
        self.assertIn("battery_capacity", ps.verified_attributes)
        self.assertEqual(ps.verified_attributes["battery_capacity"].value, "2000mAh")
        self.assertIn("wattage", ps.unknown_attributes)

    def test_data_validator_strips_unverified_claims(self):
        ps = product_source.ProductSourceExtractor.extract("102", self.supplier_data_2)
        # Bag has no voltage/wattage/HEPA in source facts!
        ai_generated_title = "VYROX PowerClean Tote Bag 2400W HEPA"
        ai_generated_desc = "Features 20V 2400W brushless motor and HEPA filtration."

        res = data_validator.ProductDataValidator.validate_and_clean(ai_generated_title, ai_generated_desc, ps)
        # Unverified claims must be stripped
        self.assertNotIn("2400W", res.title)
        self.assertNotIn("HEPA", res.title)
        self.assertNotIn("20V", res.description)
        self.assertTrue(res.passed)
        self.assertTrue(len(res.stripped_claims) > 0)


if __name__ == "__main__":
    unittest.main()
