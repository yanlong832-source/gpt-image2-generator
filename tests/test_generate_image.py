import base64
import importlib.util
import io
import json
import os
import sys
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

    def test_build_multipart_body_uses_image_and_mask_file_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "source.png")
            mask_path = os.path.join(temp_dir, "mask.png")
            Path(image_path).write_bytes(b"image-bytes")
            Path(mask_path).write_bytes(b"mask-bytes")

            body, content_type = generate_image.build_multipart_body(
                {
                    "model": "gpt-image-2",
                    "prompt": "replace the background",
                    "n": 1,
                    "size": "1024x1024",
                },
                [("image", image_path), ("mask", mask_path)],
                boundary="test-boundary",
            )

            self.assertEqual(
                content_type, "multipart/form-data; boundary=test-boundary"
            )
            self.assertIn(b'name="image"; filename="source.png"', body)
            self.assertIn(b'name="mask"; filename="mask.png"', body)
            self.assertIn(b"Content-Type: image/png", body)
            self.assertIn(b"image-bytes", body)
            self.assertIn(b"mask-bytes", body)
            self.assertIn(b'name="model"', body)
            self.assertIn(b"gpt-image-2", body)
            self.assertTrue(body.endswith(b"--test-boundary--\r\n"))

    def test_multipart_post_sets_multipart_content_type(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self):
                return b'{"data": []}'

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "source.png")
            Path(image_path).write_bytes(b"image-bytes")

            with patch.object(
                generate_image.urllib.request, "urlopen", return_value=FakeResponse()
            ) as urlopen:
                response = generate_image.api_multipart_post(
                    "https://gateway.example/v1/images/edits",
                    {"model": "gpt-image-2", "prompt": "replace the background"},
                    [("image", image_path)],
                    "test-key",
                    "https://gateway.example",
                )

            request = urlopen.call_args.args[0]
            self.assertEqual(response, {"data": []})
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            self.assertTrue(
                request.get_header("Content-type").startswith("multipart/form-data;")
            )

    def test_main_multipart_edit_uses_file_upload_fields(self):
        image_data = base64.b64encode(b"edited-image").decode("ascii")

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "source.png")
            mask_path = os.path.join(temp_dir, "mask.png")
            output_path = os.path.join(temp_dir, "edited.png")
            Path(image_path).write_bytes(b"image-bytes")
            Path(mask_path).write_bytes(b"mask-bytes")

            arguments = [
                "generate_image.py",
                "--prompt",
                "replace the background",
                "--edit",
                image_path,
                "--mask",
                mask_path,
                "--edit-transport",
                "multipart",
                "--output",
                output_path,
            ]
            with patch.object(generate_image, "load_config", return_value=(
                "https://gateway.example", "test-key"
            )), patch.object(
                generate_image, "api_multipart_post", return_value={
                    "data": [{"b64_json": image_data}]
                }
            ) as multipart_post, patch.object(sys, "argv", arguments):
                generate_image.main()

            endpoint, fields, files, api_key, base_url = multipart_post.call_args.args
            self.assertEqual(endpoint, "https://gateway.example/v1/images/edits")
            self.assertEqual(
                fields,
                {
                    "model": "gpt-image-2",
                    "prompt": "replace the background",
                    "n": 1,
                    "size": "1024x1024",
                },
            )
            self.assertEqual(files, [("image", image_path), ("mask", mask_path)])
            self.assertEqual(api_key, "test-key")
            self.assertEqual(base_url, "https://gateway.example")

    def test_main_multipart_edit_rejects_a_remote_image_url(self):
        arguments = [
            "generate_image.py",
            "--prompt",
            "replace the background",
            "--edit",
            "https://example.com/source.png",
            "--edit-transport",
            "multipart",
        ]
        stdout = io.StringIO()

        with patch.object(generate_image, "load_config", return_value=(
            "https://gateway.example", "test-key"
        )), patch.object(generate_image, "api_multipart_post") as multipart_post, patch.object(
            sys, "argv", arguments
        ), redirect_stdout(stdout), self.assertRaises(SystemExit) as error:
            generate_image.main()

        self.assertEqual(error.exception.code, 2)
        self.assertIn("必须是存在的本地图片文件", stdout.getvalue())
        multipart_post.assert_not_called()

    def test_main_json_edit_keeps_data_url_transport_by_default(self):
        image_data = base64.b64encode(b"edited-image").decode("ascii")

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "source.png")
            output_path = os.path.join(temp_dir, "edited.png")
            source_bytes = b"image-bytes"
            Path(image_path).write_bytes(source_bytes)

            arguments = [
                "generate_image.py",
                "--prompt",
                "replace the background",
                "--edit",
                image_path,
                "--output",
                output_path,
            ]
            with patch.object(generate_image, "load_config", return_value=(
                "https://gateway.example", "test-key"
            )), patch.object(
                generate_image, "api_post", return_value={
                    "data": [{"b64_json": image_data}]
                }
            ) as json_post, patch.object(sys, "argv", arguments):
                generate_image.main()

            endpoint, payload, api_key, base_url = json_post.call_args.args
            expected_data_url = "data:image/png;base64," + base64.b64encode(
                source_bytes
            ).decode("ascii")
            self.assertEqual(endpoint, "https://gateway.example/v1/images/edits")
            self.assertEqual(payload["images"], [{"image_url": expected_data_url}])
            self.assertEqual(payload["n"], 1)
            self.assertEqual(payload["size"], "1024x1024")
            self.assertEqual(api_key, "test-key")
            self.assertEqual(base_url, "https://gateway.example")


if __name__ == "__main__":
    unittest.main()
