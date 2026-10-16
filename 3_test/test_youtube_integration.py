"""Integration test for YouTube downloading & audio conversion."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "2_code")))

import socket
import youtube_engine


def is_online():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1.5)
        return True
    except OSError:
        return False


@unittest.skipUnless(is_online(), "Online-Test übersprungen: Keine Internetverbindung vorhanden")
class TestYouTubeEngineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_yt_test"))
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            for f in os.listdir(cls.test_dir):
                os.remove(os.path.join(cls.test_dir, f))
            os.rmdir(cls.test_dir)

    def test_youtube_metadata_fetch(self):
        # Video: "Me at the zoo" (jNQXAC9IVRw)
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        meta = youtube_engine.fetch_video_metadata(url)
        self.assertIn("title", meta)
        self.assertIn("Me at the zoo", meta["title"])

    def test_youtube_download_mp3(self):
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        success, msg, out_file = youtube_engine.download_youtube_media(
            url=url,
            output_dir=self.test_dir,
            target_format="MP3",
            quality="320k",
            embed_thumbnail=True,
        )
        self.assertTrue(success, f"Download failed: {msg}")
        self.assertIsNotNone(out_file)
        self.assertTrue(os.path.isfile(out_file))
        self.assertTrue(out_file.endswith(".mp3"))
        self.assertGreater(os.path.getsize(out_file), 50000)  # > 50KB


if __name__ == "__main__":
    unittest.main()
