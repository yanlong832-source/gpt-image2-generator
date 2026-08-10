import base64
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "generate_image.py"
SPEC = importlib.util.spec_from_file_location("generate_image", SCRIPT_PATH)
generate_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_image)


class GenerateImageTests(unittest.TestCase):
    def test_first_use_creates_config_template_and_explains_required_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".gpt-image2" / "config.json"
            stdout = io.StringIO()

            with patch.dict(os.environ, {}, clear=True), patch.object(
                generate_image, "CONFIG_FILE", str(config_path)
            ), redirect_stdout(stdout), self.assertRaises(SystemExit) as error:
                generate_image.load_config()

            self.assertEqual(error.exception.code, 2)
            self.assertEqual(
                json.loads(config_path.read_text(encoding="utf-8")),
                {"base_url": "", "api_key": ""},
            )
            self.assertIn(str(config_path), stdout.getvalue())
            self.assertIn("base_url", stdout.getvalue())
            self.assertIn("api_key", stdout.getvalue())

    def test_preview_markdown_uses_an_absolute_path(self):
        relative_path = os.path.join("output", "preview.png")

        preview = generate_image.preview_markdown([relative_path])

        expected_path = os.path.abspath(relative_path).replace(os.sep, "/")
        self.assertIn(expected_path, preview)
        self.assertIn("![", preview)

    def test_save_images_does_not_duplicate_png_extension(self):
        image_data = base64.b64encode(b"image-bytes").decode("ascii")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "campaign.png")

            saved = generate_image.save_images([{"b64_json": image_data}], output_path)

            self.assertEqual(saved, [output_path])
            self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main()
