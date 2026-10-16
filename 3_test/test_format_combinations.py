"""Automated tests for format detection and strict compatibility validation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "2_code")))

import format_detector
import document_utils


class TestFormatCombinations(unittest.TestCase):
    def test_xlsx_compatibility(self):
        cat, allowed, default, task_type = format_detector.detect_file_info("budget.xlsx")
        self.assertEqual(cat, "Tabelle")
        self.assertIn("CSV", allowed)
        self.assertIn("PDF", allowed)
        self.assertIn("JSON", allowed)
        self.assertIn("HTML", allowed)
        # XLSX to DOCX must be strictly forbidden
        self.assertNotIn("DOCX", allowed)
        self.assertFalse(format_detector.is_valid_conversion("budget.xlsx", "DOCX"))
        self.assertTrue(format_detector.is_valid_conversion("budget.xlsx", "CSV"))

    def test_docx_compatibility(self):
        cat, allowed, default, task_type = format_detector.detect_file_info("report.docx")
        self.assertEqual(cat, "Dokument")
        self.assertIn("PDF", allowed)
        self.assertIn("TXT", allowed)
        self.assertIn("HTML", allowed)
        # DOCX to XLSX must be strictly forbidden
        self.assertNotIn("XLSX", allowed)
        self.assertNotIn("CSV", allowed)
        self.assertFalse(format_detector.is_valid_conversion("report.docx", "XLSX"))
        self.assertTrue(format_detector.is_valid_conversion("report.docx", "PDF"))

    def test_pdf_compatibility(self):
        cat, allowed, default, task_type = format_detector.detect_file_info("document.pdf")
        self.assertEqual(cat, "Dokument")
        self.assertIn("DOCX", allowed)
        self.assertIn("TXT", allowed)
        self.assertIn("PNG", allowed)
        # PDF to XLSX or MP3 must be forbidden
        self.assertNotIn("XLSX", allowed)
        self.assertNotIn("MP3", allowed)
        self.assertTrue(format_detector.is_valid_conversion("document.pdf", "DOCX"))
        self.assertFalse(format_detector.is_valid_conversion("document.pdf", "XLSX"))

    def test_csv_compatibility(self):
        cat, allowed, default, task_type = format_detector.detect_file_info("data.csv")
        self.assertEqual(cat, "Tabelle")
        self.assertIn("XLSX", allowed)
        self.assertIn("PDF", allowed)
        self.assertIn("JSON", allowed)
        # CSV to DOCX must be forbidden
        self.assertNotIn("DOCX", allowed)
        self.assertFalse(format_detector.is_valid_conversion("data.csv", "DOCX"))
        self.assertTrue(format_detector.is_valid_conversion("data.csv", "XLSX"))

    def test_image_compatibility(self):
        cat, allowed, default, task_type = format_detector.detect_file_info("photo.heic")
        self.assertEqual(cat, "Bild")
        self.assertIn("JPEG", allowed)
        self.assertIn("PNG", allowed)
        self.assertIn("WEBP", allowed)
        # Image to DOCX or XLSX must be forbidden
        self.assertNotIn("DOCX", allowed)
        self.assertNotIn("XLSX", allowed)
        self.assertNotIn("MP3", allowed)
        self.assertTrue(format_detector.is_valid_conversion("photo.heic", "JPEG"))
        self.assertFalse(format_detector.is_valid_conversion("photo.heic", "DOCX"))

    def test_video_and_audio_compatibility(self):
        # Video
        cat, allowed, default, task_type = format_detector.detect_file_info("clip.mp4")
        self.assertEqual(cat, "Video")
        self.assertIn("MOV", allowed)
        self.assertIn("MP3", allowed)
        self.assertNotIn("DOCX", allowed)
        self.assertNotIn("XLSX", allowed)

        # Audio
        cat, allowed, default, task_type = format_detector.detect_file_info("song.mp3")
        self.assertEqual(cat, "Audio")
        self.assertIn("WAV", allowed)
        self.assertIn("FLAC", allowed)
        self.assertNotIn("DOCX", allowed)
        self.assertNotIn("MP4", allowed)

    def test_document_utils_rejection(self):
        # Verify document_utils actually rejects invalid conversion attempts
        dummy_in = "/fake/budget.xlsx"
        dummy_out = "/fake/budget.docx"
        ok, msg = document_utils.convert_document(dummy_in, dummy_out, "DOCX")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
