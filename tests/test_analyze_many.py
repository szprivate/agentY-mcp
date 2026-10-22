"""analyze_image(file_paths=[...]) returns ONE numbered contact sheet.

    python -m unittest tests.test_analyze_many
"""
import os
import tempfile
import unittest

from PIL import Image

from src.tools import image_handling as ih


class Many(unittest.TestCase):
    def test_a_list_comes_back_as_one_sheet_with_a_legend(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i in range(3):
                p = os.path.join(d, f"s{i}.png")
                Image.new("RGB", (64, 48), (i * 90, 10, 10)).save(p)
                paths.append(p)
            out = ih.analyze_image(file_paths=paths, question="which is darkest?")
        text = str(out)
        self.assertIn("Contact sheet of 3 images", text)
        self.assertIn("1 = ", text)
        self.assertIn("which is darkest?", text)

    def test_no_readable_image_is_an_error(self):
        out = ih.analyze_image(file_paths=["nope1.png", "nope2.png"])
        self.assertEqual(out["status"], "error")


if __name__ == "__main__":
    unittest.main()
