import tempfile
import unittest
from unittest.mock import patch

from soundscrape.downloader import download, node_runtime, validate_url


class DownloadTests(unittest.TestCase):
    def test_shared_links_are_preserved(self):
        for url in ("https://soundcloud.com/artist/track?si=example",
                    "https://on.soundcloud.com/abc123",
                    "https://www.mixcloud.com/dholbach/cryptkeeper/",
                    "https://www.youtube.com/watch?v=BaW_jenozKc&list=example",
                    "https://youtu.be/BaW_jenozKc?si=example",
                    "https://music.youtube.com/watch?v=BaW_jenozKc",
                    "https://m.youtube.com/shorts/BaW_jenozKc",
                    "https://youtube.com/live/BaW_jenozKc"):
            with self.subTest(url=url):
                self.assertEqual(validate_url("  " + url + "\n"), url)

    def test_rejects_unsupported_or_deceptive_urls(self):
        for url in ("", "artist", "file:///tmp/song", "https://soundcloud.com.evil.test/a",
                    "https://evilmixcloud.com/a", "https://mixcloud.com/",
                    "https://user:password@soundcloud.com/a/b", "https://example.com/a",
                    "https://youtube.com.evil.test/watch?v=BaW_jenozKc",
                    "https://notyoutube.com/watch?v=BaW_jenozKc",
                    "https://youtube.com/playlist?list=example",
                    "https://youtube.com/@artist", "https://youtu.be/invalid",
                    "https://youtube.com/watch?list=example"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_invalid_url_never_creates_output(self):
        with patch("soundscrape.downloader.Path.mkdir") as mkdir, self.assertRaises(ValueError):
            download("https://example.com/song", "unused")
        mkdir.assert_not_called()

    def test_extraction_failure_is_propagated(self):
        with tempfile.TemporaryDirectory() as output, patch("soundscrape.downloader.YoutubeDL") as client:
            client.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError("HTTP 403")
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                download("https://soundcloud.com/artist/track", output)

    def test_empty_result_is_not_success(self):
        with tempfile.TemporaryDirectory() as output, patch("soundscrape.downloader.YoutubeDL") as client:
            client.return_value.__enter__.return_value.extract_info.return_value = None
            with self.assertRaises(RuntimeError):
                download("https://www.mixcloud.com/artist/mix/", output)

    def test_youtube_uses_audio_only_and_configured_runtime(self):
        with tempfile.TemporaryDirectory() as output, patch("soundscrape.downloader.YoutubeDL") as client, patch("soundscrape.downloader.node_runtime", return_value="bundled/node.exe"):
            download("https://youtu.be/BaW_jenozKc", output)
            options = client.call_args.args[0]
            self.assertEqual(options["format"], "bestaudio")
            self.assertTrue(options["noplaylist"])
            self.assertEqual(options["js_runtimes"], {"node": {"path": "bundled/node.exe"}})

    def test_frozen_runtime_does_not_require_system_node(self):
        with tempfile.TemporaryDirectory() as bundle, patch("soundscrape.downloader.sys.frozen", True, create=True), patch("soundscrape.downloader.sys._MEIPASS", bundle, create=True), patch("soundscrape.downloader.shutil.which") as lookup:
            from pathlib import Path
            runtime = Path(bundle) / "runtime" / "node.exe"
            runtime.parent.mkdir()
            runtime.write_bytes(b"test-runtime")
            self.assertEqual(node_runtime(), str(runtime))
            runtime.unlink()
            with self.assertRaises(RuntimeError):
                node_runtime()
            lookup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
