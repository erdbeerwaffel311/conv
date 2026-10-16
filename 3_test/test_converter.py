"""Automated unit and integration tests for converter backend."""

import os
import sys
import subprocess
import unittest

# Add 2_code to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "2_code")))

import ffmpeg_utils
import converter_models


class TestConverterBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_test_media"))
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.ffmpeg = ffmpeg_utils.find_binary("ffmpeg")
        assert cls.ffmpeg, "FFmpeg must be installed and found."

        # Create a 1-second audio test file
        cls.audio_source = os.path.join(cls.test_dir, "synth_audio.wav")
        subprocess.run([
            cls.ffmpeg, "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            cls.audio_source
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Create a 1-second video test file
        cls.video_source = os.path.join(cls.test_dir, "synth_video.mp4")
        subprocess.run([
            cls.ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            cls.video_source
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        # Cleanup
        if os.path.exists(cls.test_dir):
            for f in os.listdir(cls.test_dir):
                os.remove(os.path.join(cls.test_dir, f))
            os.rmdir(cls.test_dir)

    def test_ffmpeg_detected(self):
        self.assertIsNotNone(ffmpeg_utils.FFMPEG_PATH)
        self.assertTrue(os.path.isfile(ffmpeg_utils.FFMPEG_PATH))

    def test_audio_conversions(self):
        # Test converting to MP3 320k
        mp3_out = os.path.join(self.test_dir, "out.mp3")
        success, msg = ffmpeg_utils.convert_file(self.audio_source, mp3_out, "MP3", quality="320k")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(mp3_out))
        self.assertGreater(os.path.getsize(mp3_out), 1000)

        # Test converting to FLAC
        flac_out = os.path.join(self.test_dir, "out.flac")
        success, msg = ffmpeg_utils.convert_file(self.audio_source, flac_out, "FLAC")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(flac_out))

        # Test converting to AIFF
        aiff_out = os.path.join(self.test_dir, "out.aiff")
        success, msg = ffmpeg_utils.convert_file(self.audio_source, aiff_out, "AIFF")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(aiff_out))

        # Test converting to WAV
        wav_out = os.path.join(self.test_dir, "out.wav")
        success, msg = ffmpeg_utils.convert_file(self.audio_source, wav_out, "WAV")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(wav_out))

        # Test converting to AAC
        aac_out = os.path.join(self.test_dir, "out.aac")
        success, msg = ffmpeg_utils.convert_file(self.audio_source, aac_out, "AAC", quality="256k")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(aac_out))

        # Test converting to OGG
        ogg_out = os.path.join(self.test_dir, "out.ogg")
        success, msg = ffmpeg_utils.convert_file(self.audio_source, ogg_out, "OGG", quality="192k")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(ogg_out))

    def test_video_conversions(self):
        # Test MP4 to MOV
        mov_out = os.path.join(self.test_dir, "out.mov")
        success, msg = ffmpeg_utils.convert_file(self.video_source, mov_out, "MOV")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(mov_out))

        # Test MP4 to MKV
        mkv_out = os.path.join(self.test_dir, "out.mkv")
        success, msg = ffmpeg_utils.convert_file(self.video_source, mkv_out, "MKV")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(mkv_out))

        # Test MP4 to MP4 scaled 480p
        scaled_out = os.path.join(self.test_dir, "scaled_480p.mp4")
        success, msg = ffmpeg_utils.convert_file(self.video_source, scaled_out, "MP4", custom_scale="480p")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(scaled_out))

        # Test MP4 to MP3 (Audio extraction from video)
        extracted_mp3 = os.path.join(self.test_dir, "extracted.mp3")
        success, msg = ffmpeg_utils.convert_file(self.video_source, extracted_mp3, "MP3", quality="320k")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(extracted_mp3))

        # Test MP4 to animated GIF
        gif_out = os.path.join(self.test_dir, "out.gif")
        success, msg = ffmpeg_utils.convert_file(self.video_source, gif_out, "GIF")
        self.assertTrue(success, msg)
        self.assertTrue(os.path.isfile(gif_out))


if __name__ == "__main__":
    unittest.main()
