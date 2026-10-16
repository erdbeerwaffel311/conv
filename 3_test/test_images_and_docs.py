"""Unit tests for image and document conversion utilities."""

import os
import sys
import unittest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "2_code")))

import image_utils
import document_utils


class TestImageAndDocumentUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_img_doc_test"))
        os.makedirs(cls.test_dir, exist_ok=True)

        # Create source image (PNG)
        cls.img_source = os.path.join(cls.test_dir, "test_input.png")
        im = Image.new("RGBA", (100, 100), color=(255, 0, 0, 200))
        im.save(cls.img_source)

        # Create source CSV
        cls.csv_source = os.path.join(cls.test_dir, "test_table.csv")
        with open(cls.csv_source, "w", encoding="utf-8") as f:
            f.write("Produkt,Preis,Menge\nLaptop,1200,5\nMaus,25,50\nTastatur,80,20\n")

        # Create source TXT
        cls.txt_source = os.path.join(cls.test_dir, "test_text.txt")
        with open(cls.txt_source, "w", encoding="utf-8") as f:
            f.write("Hallo Welt!\nDies ist ein Testdokument für den Universal Converter.\nZeile 3.")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            for f in os.listdir(cls.test_dir):
                os.remove(os.path.join(cls.test_dir, f))
            os.rmdir(cls.test_dir)

    def test_image_conversions(self):
        # Test PNG to JPEG
        jpg_out = os.path.join(self.test_dir, "out.jpg")
        ok, msg = image_utils.convert_image(self.img_source, jpg_out, "JPEG", "Sehr hoch (95%)")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(jpg_out))

        # Test PNG to WEBP
        webp_out = os.path.join(self.test_dir, "out.webp")
        ok, msg = image_utils.convert_image(self.img_source, webp_out, "WEBP")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(webp_out))

        # Test PNG to BMP
        bmp_out = os.path.join(self.test_dir, "out.bmp")
        ok, msg = image_utils.convert_image(self.img_source, bmp_out, "BMP")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(bmp_out))

        # Test PNG to TIFF
        tiff_out = os.path.join(self.test_dir, "out.tiff")
        ok, msg = image_utils.convert_image(self.img_source, tiff_out, "TIFF")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(tiff_out))

        # Test PNG to ICO
        ico_out = os.path.join(self.test_dir, "out.ico")
        ok, msg = image_utils.convert_image(self.img_source, ico_out, "ICO")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(ico_out))

        # Test PNG to PDF
        pdf_out = os.path.join(self.test_dir, "out_img.pdf")
        ok, msg = image_utils.convert_image(self.img_source, pdf_out, "PDF")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(pdf_out))

        # Test PNG to HEIC
        heic_out = os.path.join(self.test_dir, "out.heic")
        ok, msg = image_utils.convert_image(self.img_source, heic_out, "HEIC")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(heic_out))

    def test_table_conversions(self):
        # Test CSV to XLSX
        xlsx_out = os.path.join(self.test_dir, "out.xlsx")
        ok, msg = document_utils.convert_document(self.csv_source, xlsx_out, "XLSX")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(xlsx_out))

        # Test XLSX back to CSV
        csv_back = os.path.join(self.test_dir, "out_back.csv")
        ok, msg = document_utils.convert_document(xlsx_out, csv_back, "CSV")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(csv_back))

        # Test CSV to JSON
        json_out = os.path.join(self.test_dir, "out.json")
        ok, msg = document_utils.convert_document(self.csv_source, json_out, "JSON")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(json_out))

        # Test CSV to PDF (Formatted table)
        table_pdf = os.path.join(self.test_dir, "table.pdf")
        ok, msg = document_utils.convert_document(self.csv_source, table_pdf, "PDF")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(table_pdf))

    def test_document_conversions(self):
        # Test TXT to PDF
        txt_pdf = os.path.join(self.test_dir, "text.pdf")
        ok, msg = document_utils.convert_document(self.txt_source, txt_pdf, "PDF")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(txt_pdf))

        # Test TXT to DOCX
        docx_out = os.path.join(self.test_dir, "out.docx")
        ok, msg = document_utils.convert_document(self.txt_source, docx_out, "DOCX")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(docx_out))

        # Test DOCX back to TXT
        txt_back = os.path.join(self.test_dir, "out_back.txt")
        ok, msg = document_utils.convert_document(docx_out, txt_back, "TXT")
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(txt_back))


if __name__ == "__main__":
    unittest.main()
