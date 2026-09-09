#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.integrations.qgis.install_dialog
~~~~~~~~~~~~~~~

Transformez isolated-runtime installer dialog.
"""

from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class InstallTransformezDialog(QDialog):
    def __init__(self, parent=None, import_error: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Install Transformez Runtime")
        self.setMinimumWidth(620)

        intro = QLabel(
            "The Transformez QGIS plugin uses an isolated Python runtime so QGIS's "
            "GDAL/PROJ stack never shares a process with Transformez/Rasterio. The "
            "plugin can create and manage that runtime automatically."
        )
        intro.setWordWrap(True)

        self.pypi_radio = QRadioButton("Install Transformez from PyPI")
        self.local_radio = QRadioButton("Install from a local Transformez checkout")
        self.pypi_radio.setChecked(True)

        self.local_edit = QLineEdit()
        self.local_edit.setPlaceholderText("/path/to/transformez")
        self.local_edit.setEnabled(False)

        browse = QPushButton("Browse...")
        browse.setEnabled(False)
        browse.clicked.connect(self._browse_source)

        self.local_radio.toggled.connect(self.local_edit.setEnabled)
        self.local_radio.toggled.connect(browse.setEnabled)

        local_widget = QWidget()
        local_layout = QHBoxLayout(local_widget)
        local_layout.setContentsMargins(24, 0, 0, 0)
        local_layout.addWidget(self.local_edit, 1)
        local_layout.addWidget(browse)

        note = QLabel(
            "A private virtual environment is stored in the active QGIS profile, "
            "outside the plugin directory. Transformez and its Python dependencies "
            "run only in subprocesses launched from that environment; they are never "
            "imported into the QGIS process."
        )
        note.setWordWrap(True)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(110)
        self.details.setVisible(bool(import_error))
        if import_error:
            self.details.setPlainText(f"Current runtime status:\n{import_error}")

        self.requested_action = "install"

        self.uninstall_button = QPushButton("Uninstall Transformez")
        self.uninstall_button.setToolTip(
            "Remove Transformez from the managed isolated runtime"
        )
        self.uninstall_button.setEnabled(
            bool(import_error and "Installed Transformez version:" in import_error)
        )
        self.uninstall_button.clicked.connect(self._request_uninstall)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Create / Update Runtime"
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addSpacing(8)
        layout.addWidget(self.pypi_radio)
        layout.addWidget(self.local_radio)
        layout.addWidget(local_widget)
        layout.addSpacing(8)
        layout.addWidget(note)
        layout.addWidget(self.details)
        layout.addWidget(self.uninstall_button)
        layout.addWidget(self.buttons)

    def _request_uninstall(self) -> None:
        self.requested_action = "uninstall"
        self.accept()

    @property
    def source(self) -> Path | None:
        if not self.local_radio.isChecked():
            return None
        text = self.local_edit.text().strip()
        return Path(text).expanduser() if text else None

    def _browse_source(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Transformez checkout",
            str(Path.home()),
        )
        if directory:
            self.local_edit.setText(directory)
