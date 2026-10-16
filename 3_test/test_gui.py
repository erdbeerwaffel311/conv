"""Headless UI test to verify GUI widget initialization, format picker per row, and no emojis."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "2_code")))

from PyQt6.QtWidgets import QApplication, QComboBox
import gui

# Initialize single QApplication in headless mode (offscreen)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)


class TestGUI(unittest.TestCase):
    def test_main_window_init(self):
        window = gui.MainWindow()
        window.show()
        self.assertIsNotNone(window)
        # Verify 5 pages
        self.assertEqual(window.pages.count(), 5)
        # Verify sidebar exists and has 5 navigation buttons
        self.assertIsNotNone(window.sidebar_frame)
        self.assertEqual(len(window.nav_buttons), 5)
        # Verify sidebar toggle button
        self.assertTrue(window.sidebar_frame.isVisible())
        window.toggle_sidebar()
        self.assertFalse(window.sidebar_frame.isVisible())
        window.toggle_sidebar()
        self.assertTrue(window.sidebar_frame.isVisible())

    def test_row_format_dropdown_and_incompatible_filtering(self):
        window = gui.MainWindow()

        # Add Excel file: budget.xlsx
        window.on_files_dropped_handler(["/fake/path/budget.xlsx"])
        self.assertEqual(window.table.rowCount(), 1)
        self.assertEqual(window.table.item(0, 0).text(), "Tabelle")

        # Check that Cell 2 is a QComboBox with compatible options only
        fmt_combo: QComboBox = window.table.cellWidget(0, 2)
        self.assertIsInstance(fmt_combo, QComboBox)
        items = [fmt_combo.itemText(i) for i in range(fmt_combo.count())]
        self.assertIn("CSV", items)
        self.assertIn("PDF", items)
        # Verify DOCX is NOT present for XLSX
        self.assertNotIn("DOCX", items)

        # Change target format to PDF via dropdown
        fmt_combo.setCurrentText("PDF")
        task = window.current_tasks[0]
        self.assertEqual(task.target_format, "PDF")

        # Add image file: photo.heic
        window.on_files_dropped_handler(["/fake/path/photo.heic"])
        self.assertEqual(window.table.rowCount(), 2)
        self.assertEqual(window.table.item(1, 0).text(), "Bild")

        img_fmt_combo: QComboBox = window.table.cellWidget(1, 2)
        img_items = [img_fmt_combo.itemText(i) for i in range(img_fmt_combo.count())]
        self.assertIn("JPEG", img_items)
        self.assertIn("PNG", img_items)
        self.assertNotIn("DOCX", img_items)
        self.assertNotIn("XLSX", img_items)

        # Test remove task
        window.remove_task(window.current_tasks[0].task_id)
        self.assertEqual(window.table.rowCount(), 1)


if __name__ == "__main__":
    unittest.main()
