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


if __name__ == "__main__":
    unittest.main()
