#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.integrations.qgis.plugin
~~~~~~~~~~~~~~~

Initial Transformez QGIS plugin implementation.
"""

from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRasterLayer,
    QgsMessageLog,
)

from .dialog import ShiftGridDialog
from .dependencies import cleanup_legacy_runtime, runtime_probe, runtime_python
from .install_dialog import InstallTransformezDialog
from .tasks import BuildShiftGridTask, InstallTransformezTask, UninstallTransformezTask


class TransformezPlugin:
    MENU = "&Transformez"

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.runtime_action = None
        self.dialog = None
        self._tasks = set()

    def initGui(self) -> None:
        self.action = QAction("Build Shift Grid...", self.iface.mainWindow())
        self.action.setObjectName("TransformezBuildShiftGrid")
        self.action.setToolTip("Build a Transformez vertical datum shift grid")
        self.action.triggered.connect(self.run)

        self.iface.addPluginToMenu(self.MENU, self.action)
        self.iface.addToolBarIcon(self.action)

        self.runtime_action = QAction("Manage Runtime...", self.iface.mainWindow())
        self.runtime_action.setObjectName("TransformezManageRuntime")
        self.runtime_action.setToolTip(
            "Install, update, or inspect the isolated Transformez runtime"
        )
        self.runtime_action.triggered.connect(self.manage_runtime)
        self.iface.addPluginToMenu(self.MENU, self.runtime_action)

    def unload(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()

        if self.action is not None:
            self.iface.removePluginMenu(self.MENU, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

        if self.runtime_action is not None:
            self.iface.removePluginMenu(self.MENU, self.runtime_action)
            self.runtime_action.deleteLater()
            self.runtime_action = None

    def run(self) -> None:
        available, detail = runtime_probe()
        if not available:
            self._offer_transformez_install(detail, continue_to_build=True)
            return

        self._open_shift_grid_dialog()

    def manage_runtime(self) -> None:
        """Open the isolated-runtime installer/updater on demand."""
        available, detail = runtime_probe()
        if available:
            status = (
                f"Installed Transformez version: {detail or 'unknown'}\n"
                f"Runtime Python: {runtime_python()}"
            )
        else:
            status = (
                f"Runtime is not currently usable.\n{detail or ''}\n"
                f"Runtime Python: {runtime_python()}"
            ).strip()

        self._offer_transformez_install(status, continue_to_build=False)

    def _open_shift_grid_dialog(self) -> None:
        self.dialog = ShiftGridDialog(self.iface.mainWindow())
        self.dialog.set_extent_text(self._extent_description())

        if not self.dialog.exec():
            return

        if not self.dialog.source_reference or not self.dialog.target_reference:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Missing reference",
                "Both source and target references are required.",
            )
            return

        if not self.dialog.increment:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Missing increment",
                "A grid increment is required (for example, 3s).",
            )
            return

        output_path = self.dialog.output_path
        if not output_path.suffix:
            output_path = output_path.with_suffix(".tif")

        try:
            region = self._canvas_extent_wgs84()
        except Exception as exc:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Extent error",
                f"Could not transform the current map extent to EPSG:4326:\n\n{exc}",
            )
            return

        task = BuildShiftGridTask(
            region=region,
            increment=self.dialog.increment,
            source_reference=self.dialog.source_reference,
            target_reference=self.dialog.target_reference,
            output_path=output_path,
            use_stations=self.dialog.use_stations,
        )
        task.taskCompleted.connect(lambda task=task: self._grid_task_completed(task))
        task.taskTerminated.connect(lambda task=task: self._grid_task_terminated(task))

        self._track_task(task)
        self.iface.messageBar().pushMessage(
            "Transformez",
            "Building vertical datum shift grid in the background...",
            level=Qgis.MessageLevel.Info,
            duration=6,
        )
        QgsApplication.taskManager().addTask(task)

    def _grid_task_completed(self, task: BuildShiftGridTask) -> None:
        self._forget_task(task)

        written_path = task.written_path
        if written_path is None:
            self._show_task_error(
                "Transformez error",
                "Shift-grid generation completed without producing an output file.",
                task,
            )
            return

        layer_name = f"Transformez: {task.source_reference} -> {task.target_reference}"
        layer = QgsRasterLayer(str(written_path), layer_name)

        if not layer.isValid():
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Transformez error",
                f"QGIS could not open the generated raster:\n\n{written_path}",
            )
            return

        QgsProject.instance().addMapLayer(layer)
        self.iface.messageBar().pushMessage(
            "Transformez",
            f"Shift grid added: {written_path.name}",
            level=Qgis.MessageLevel.Success,
            duration=8,
        )

    def _grid_task_terminated(self, task: BuildShiftGridTask) -> None:
        self._forget_task(task)

        if task.isCanceled() and task.error is None:
            self.iface.messageBar().pushMessage(
                "Transformez",
                "Shift-grid task canceled.",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            return

        self._show_task_error(
            "Transformez error",
            "Shift-grid generation failed.",
            task,
        )

    def _offer_transformez_install(
        self,
        import_error: str | None,
        *,
        continue_to_build: bool = False,
    ) -> None:
        dialog = InstallTransformezDialog(
            self.iface.mainWindow(),
            import_error=import_error,
        )

        if not dialog.exec():
            return

        if dialog.requested_action == "uninstall":
            answer = QMessageBox.question(
                self.iface.mainWindow(),
                "Uninstall Transformez",
                "Remove Transformez from the managed isolated runtime?\n\n"
                "The runtime itself and downloaded Transformez cache data will be kept.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._start_uninstall_task()
            return

        source = dialog.source
        if dialog.local_radio.isChecked():
            if source is None or not source.exists():
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    "Invalid Transformez checkout",
                    "Choose an existing local Transformez source directory.",
                )
                return
            if not (source / "pyproject.toml").exists():
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    "Invalid Transformez checkout",
                    "The selected directory does not contain pyproject.toml.",
                )
                return

        task = InstallTransformezTask(source)
        task.continue_to_build = continue_to_build
        task.taskCompleted.connect(lambda task=task: self._install_task_completed(task))
        task.taskTerminated.connect(
            lambda task=task: self._install_task_terminated(task)
        )

        self._track_task(task)
        self.iface.messageBar().pushMessage(
            "Transformez",
            "Creating/updating isolated Transformez runtime in the background...",
            level=Qgis.MessageLevel.Info,
            duration=6,
        )
        QgsApplication.taskManager().addTask(task)

    def _start_uninstall_task(self) -> None:
        task = UninstallTransformezTask()
        task.taskCompleted.connect(
            lambda task=task: self._uninstall_task_completed(task)
        )
        task.taskTerminated.connect(
            lambda task=task: self._uninstall_task_terminated(task)
        )

        self._track_task(task)
        self.iface.messageBar().pushMessage(
            "Transformez",
            "Uninstalling Transformez from the isolated runtime...",
            level=Qgis.MessageLevel.Info,
            duration=5,
        )
        QgsApplication.taskManager().addTask(task)

    def _uninstall_task_completed(self, task: UninstallTransformezTask) -> None:
        self._forget_task(task)

        available, detail = runtime_probe()
        if available:
            self._show_task_error(
                "Transformez uninstall incomplete",
                "pip completed, but Transformez is still importable from the managed runtime.",
                task,
            )
            return

        self.iface.messageBar().pushMessage(
            "Transformez",
            "Transformez was removed from the isolated runtime.",
            level=Qgis.MessageLevel.Success,
            duration=8,
        )
        QgsMessageLog.logMessage(
            f"Transformez uninstalled from managed runtime: {runtime_python()}",
            "Transformez",
            level=Qgis.MessageLevel.Info,
        )

    def _uninstall_task_terminated(self, task: UninstallTransformezTask) -> None:
        self._forget_task(task)

        if task.isCanceled() and task.error is None:
            self.iface.messageBar().pushMessage(
                "Transformez",
                "Transformez uninstall canceled.",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            return

        self._show_task_error(
            "Transformez uninstall failed",
            "Could not remove Transformez from the managed isolated runtime.",
            task,
        )

    def _install_task_completed(self, task: InstallTransformezTask) -> None:
        self._forget_task(task)

        available, detail = runtime_probe()
        if not available:
            output = ""
            if task.result is not None:
                output = (task.result.stdout or task.result.stderr or "").strip()
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Transformez installation incomplete",
                "The runtime install completed, but Transformez still could not be imported there.\n\n"
                f"Import error: {detail}\n\n"
                f"Installer output:\n{output[-4000:]}\n\nRuntime: {runtime_python()}",
            )
            return

        removed, cleanup_detail = cleanup_legacy_runtime()
        if not removed:
            QgsMessageLog.logMessage(
                f"Could not remove legacy in-plugin runtime: {cleanup_detail}",
                "Transformez",
                level=Qgis.MessageLevel.Warning,
            )

        version_text = f" {detail}" if detail else ""
        self.iface.messageBar().pushMessage(
            "Transformez",
            f"Isolated Transformez runtime ready (Transformez{version_text}).",
            level=Qgis.MessageLevel.Success,
            duration=8,
        )

        if getattr(task, "continue_to_build", False):
            # Continue the action that triggered automatic runtime installation.
            self._open_shift_grid_dialog()

    def _install_task_terminated(self, task: InstallTransformezTask) -> None:
        self._forget_task(task)

        if task.isCanceled() and task.error is None:
            self.iface.messageBar().pushMessage(
                "Transformez",
                "Transformez runtime installation canceled.",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            return

        if task.error is not None:
            self._show_task_error(
                "Transformez runtime installation failed",
                "Could not create or update the isolated Transformez runtime.",
                task,
            )
            return

        output = "pip returned no output"
        if task.result is not None:
            output = (task.result.stderr or task.result.stdout or output).strip()

        QMessageBox.critical(
            self.iface.mainWindow(),
            "Transformez runtime installation failed",
            f"The isolated runtime could not install Transformez.\n\n{output[-6000:]}",
        )

    def _track_task(self, task) -> None:
        self._tasks.add(task)

    def _forget_task(self, task) -> None:
        self._tasks.discard(task)

    def _show_task_error(self, title: str, message: str, task) -> None:
        """Show a compact user-facing error and send diagnostics to QGIS logs."""
        if task.error is not None:
            error_type = type(task.error).__name__
            error_text = str(task.error).strip() or repr(task.error)
            summary = f"{error_type}: {error_text}"
        else:
            summary = "Unknown task error"

        diagnostics = []

        if isinstance(task, BuildShiftGridTask):
            diagnostics.extend(
                [
                    "Shift-grid request",
                    f"  Region: {task.region}",
                    f"  Increment: {task.increment}",
                    f"  Source reference: {task.source_reference}",
                    f"  Target reference: {task.target_reference}",
                    f"  Output path: {task.output_path}",
                    f"  Use stations: {task.use_stations}",
                ]
            )

        if getattr(task, "stderr", "").strip():
            diagnostics.extend(["Subprocess stderr:", task.stderr.rstrip()])

        if task.traceback_text:
            diagnostics.extend(["Transformez traceback:", task.traceback_text.rstrip()])

        if diagnostics:
            QgsMessageLog.logMessage(
                "\n".join(diagnostics),
                "Transformez",
                level=Qgis.MessageLevel.Critical,
            )

        QMessageBox.critical(
            self.iface.mainWindow(),
            title,
            f"{message}\n\n{summary}\n\nSee View > Panels > Log Messages for details.",
        )

    def _canvas_extent_wgs84(self) -> list[float]:
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        source_crs = canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        if not source_crs.isValid():
            raise ValueError("The map canvas has no valid destination CRS.")

        if source_crs != wgs84:
            transform = QgsCoordinateTransform(
                source_crs,
                wgs84,
                QgsProject.instance().transformContext(),
            )
            extent = transform.transformBoundingBox(extent)

        return [
            extent.xMinimum(),
            extent.xMaximum(),
            extent.yMinimum(),
            extent.yMaximum(),
        ]

    def _extent_description(self) -> str:
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()
        authid = crs.authid() or crs.description() or "unknown CRS"
        return (
            f"{extent.xMinimum():.6f}, {extent.xMaximum():.6f}, "
            f"{extent.yMinimum():.6f}, {extent.yMaximum():.6f} ({authid})"
        )
