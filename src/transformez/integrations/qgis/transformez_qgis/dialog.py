#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.integrations.qgis.dialog
~~~~~~~~~~~~~~~

Small programmatic dialog for building a Transformez shift grid.
"""

from pathlib import Path

from qgis.PyQt.QtCore import QStandardPaths
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ShiftGridDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Build Transformez Shift Grid")
        self.setMinimumWidth(520)

        self.source_edit = QLineEdit("vdatum:mllw")
        self.target_edit = QLineEdit("EPSG:5703")
        self.increment_edit = QLineEdit("3s")
        self.output_edit = QLineEdit(str(self._default_output()))
        self.use_stations_check = QCheckBox(
            "Use tide-station interpolation when available"
        )
        self.extent_label = QLabel("Current map canvas extent")
        self.extent_label.setWordWrap(True)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output)

        output_widget = QWidget()
        output_layout = QHBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_edit, 1)
        output_layout.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Source reference:", self.source_edit)
        form.addRow("Target reference:", self.target_edit)
        form.addRow("Increment:", self.increment_edit)
        form.addRow("Region:", self.extent_label)
        form.addRow("Output GeoTIFF:", output_widget)
        form.addRow("", self.use_stations_check)

        note = QLabel(
            "The current map extent is transformed to EPSG:4326 before the "
            "Transformez grid is generated."
        )
        note.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Build Grid")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(self.buttons)

    def set_extent_text(self, text: str) -> None:
        self.extent_label.setText(text)

    @property
    def source_reference(self) -> str:
        return self.source_edit.text().strip()

    @property
    def target_reference(self) -> str:
        return self.target_edit.text().strip()

    @property
    def increment(self) -> str:
        return self.increment_edit.text().strip()

    @property
    def output_path(self) -> Path:
        return Path(self.output_edit.text().strip()).expanduser()

    @property
    def use_stations(self) -> bool:
        return self.use_stations_check.isChecked()

    def _browse_output(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transformez shift grid",
            str(self.output_path),
            "GeoTIFF (*.tif *.tiff)",
        )
        if filename:
            self.output_edit.setText(filename)

    @staticmethod
    def _default_output() -> Path:
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        root = Path(documents) if documents else Path.home()
        return root / "transformez_shift.tif"
