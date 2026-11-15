import tempfile
import unittest
from unittest.mock import patch

from soundscrape.downloader import download, validate_url


class DownloadTests(unittest.TestCase):
    def test_shared_links_are_preserved(self):
        for url in ("https://soundcloud.com/artist/track?si=example",
                    "https://on.soundcloud.com/abc123",
                    "https://www.mixcloud.com/dholbach/cryptkeeper/"):
            with self.subTest(url=url):
                self.assertEqual(validate_url("  " + url + "\n"), url)

    def test_rejects_unsupported_or_deceptive_urls(self):
        for url in ("", "artist", "file:///tmp/song", "https://soundcloud.com.evil.test/a",
                    "https://evilmixcloud.com/a", "https://mixcloud.com/",
                    "https://user:password@soundcloud.com/a/b", "https://example.com/a"):
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


if __name__ == "__main__":
    unittest.main()
