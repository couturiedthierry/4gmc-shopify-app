import base64
import io
import sys
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gmc_engine


class TestGMCImageEngine(unittest.TestCase):

    def setUp(self):
        # Create a sample product image (200x200 red box on white background)
        image = Image.new("RGBA", (300, 300), (255, 255, 255, 255))
        for x in range(50, 250):
            for y in range(50, 250):
                image.putpixel((x, y), (220, 30, 40, 255))
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        self.source_bytes = buf.getvalue()

    def test_product_identity_building(self):
        identity = gmc_engine.build_product_identity(
            self.source_bytes, source_title="Zyplan Lawn Mower 5000",
            product_facts="Heavy-duty steel deck and rubber tires.", sku="MOWER-123"
        )
        self.assertEqual(identity.sku, "MOWER-123")
        self.assertEqual(identity.source_title, "Zyplan Lawn Mower 5000")
        self.assertTrue(len(identity.dominant_colors) > 0)
        self.assertTrue(all(c.startswith("#") for c in identity.dominant_colors))
        self.assertEqual(identity.dimensions, (300, 300))
        self.assertIn("steel", identity.material_hints)

    def test_segment_product(self):
        subject, bbox = gmc_engine.segment_product(self.source_bytes)
        self.assertEqual(subject.size, (300, 300))
        self.assertGreater(bbox[2], bbox[0])
        self.assertGreater(bbox[3], bbox[1])
        # Check center pixel is red
        px = subject.getpixel((150, 150))
        self.assertEqual(px[:3], (220, 30, 40))

    def test_scene_generation_modes(self):
        bg_main = gmc_engine.generate_background_scene("gmc_main", (1500, 1500))
        self.assertEqual(bg_main.size, (1500, 1500))
        bg_add = gmc_engine.generate_background_scene("gmc_additional", (1500, 1500))
        self.assertEqual(bg_add.size, (1500, 1500))

    def test_compositing_and_corner_logo(self):
        subject, bbox = gmc_engine.segment_product(self.source_bytes)
        scene = gmc_engine.generate_background_scene("gmc_main", (1500, 1500))
        
        logo_img = Image.new("RGBA", (100, 30), (10, 10, 10, 255))
        l_buf = io.BytesIO()
        logo_img.save(l_buf, format="PNG")
        logo_dark_bytes = l_buf.getvalue()

        composited = gmc_engine.composite_product_on_scene(
            subject, scene, mode="gmc_main", logo_dark_bytes=logo_dark_bytes
        )
        self.assertEqual(composited.size, (1500, 1500))

    def test_validation_pipeline(self):
        identity = gmc_engine.build_product_identity(self.source_bytes)
        subject, _ = gmc_engine.segment_product(self.source_bytes)
        scene = gmc_engine.generate_background_scene("gmc_main", (1500, 1500))
        composited = gmc_engine.composite_product_on_scene(subject, scene, mode="gmc_main")
        
        out = io.BytesIO()
        composited.save(out, format="PNG")
        gen_bytes = out.getvalue()

        validation = gmc_engine.validateProductImage(self.source_bytes, gen_bytes, identity, mode="gmc_main")
        self.assertTrue(validation["passed"], f"Validation failed: {validation['problems']}")
        self.assertGreaterEqual(validation["product_accuracy"], 95.0)
        self.assertGreaterEqual(validation["realism"], 90.0)
        self.assertEqual(validation["gmc_compliance"], 100.0)
        self.assertEqual(len(validation["problems"]), 0)

    def test_iptc_metadata_embedding(self):
        meta_bytes = gmc_engine.embed_gmc_ai_metadata(self.source_bytes, mode="gmc_main")
        self.assertTrue(len(meta_bytes) > 0)
        with Image.open(io.BytesIO(meta_bytes)) as img:
            self.assertEqual(img.info.get("DigitalSourceType"), "http://cv.iptc.org/newscodes/digitalsourcetype/compositeSynthetic")

    def test_brand_compositor(self):
        compositor = gmc_engine.BrandCompositor()
        base_img = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
        logo_img = Image.new("RGBA", (80, 25), (10, 10, 10, 255))
        l_buf = io.BytesIO()
        logo_img.save(l_buf, format="PNG")
        logo_bytes = l_buf.getvalue()

        result = compositor.composite(base_img, role="hero", logo_bytes=logo_bytes)
        self.assertEqual(result.size, (512, 512))
        negs = compositor.get_negative_prompts()
        self.assertIn("watermark", negs)
        self.assertIn("logo", negs)

    def test_structured_image_review(self):
        identity = gmc_engine.build_product_identity(self.source_bytes, sku="SKU-999")
        profile = gmc_engine.create_product_image_profile("999", ["https://cdn.example.com/src.jpg"], "Item", "Item")
        
        # Test review against original source bytes
        review = gmc_engine.perform_structured_image_review(
            self.source_bytes, self.source_bytes, profile=profile, product_identity=identity, role="hero"
        )
        d = review.to_dict()
        
        # Assert exact 13 required fields are present
        required_keys = [
            "geometry_match", "component_count_match", "material_zone_match",
            "approved_color_match", "logo_count", "logo_artwork_match",
            "logo_surface_match", "old_branding_removed", "invented_parts",
            "duplicate_products", "unexpected_text", "scene_quality", "decision"
        ]
        for key in required_keys:
            self.assertIn(key, d, f"Missing required review key: {key}")
            
        self.assertIn(review.decision, {"approved", "rejected", "needs_review"})
        self.assertTrue(d["source_verification"]["source_verified"])
        self.assertEqual(d["source_verification"]["authority"], "supplier_source_image")

        # Verify fail-closed behavior on corrupted bytes
        corrupted_review = gmc_engine.perform_structured_image_review(
            self.source_bytes, b"corrupted-bytes", profile=profile, product_identity=identity
        )
        self.assertEqual(corrupted_review.decision, "rejected")
        self.assertFalse(corrupted_review.geometry_match)


if __name__ == "__main__":
    unittest.main()
