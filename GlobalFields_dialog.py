# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QLabel,
    QMessageBox,
)

from qgis.core import (
    QgsTask,
    QgsApplication,
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
)

from . import duckdb_task
from . import utils

# 🧱 DIALOG
class GlobalFieldsDialog(QDialog):

    def __init__(self, iface):
        super().__init__()

        self.iface = iface
        self.setWindowTitle("Global Fields Downloader")
        self.resize(300, 150)

        layout = QVBoxLayout()

        self.chkExtent = QCheckBox("Usar extensão atual do mapa")
        self.chkExtent.setChecked(True)

        self.btnSelectFolder = QPushButton("Selecionar pasta de saída")
        self.lblPath = QLabel("Nenhuma pasta selecionada")

        self.btnDownload = QPushButton("Baixar Talhões")

        layout.addWidget(self.chkExtent)
        layout.addWidget(self.btnSelectFolder)
        layout.addWidget(self.lblPath)
        layout.addWidget(self.btnDownload)

        self.setLayout(layout)

        self.output_dir = os.path.expanduser("~")

        # 🔹 eventos
        self.btnSelectFolder.clicked.connect(self.select_folder)
        self.btnDownload.clicked.connect(self.download)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta")
        if folder:
            self.output_dir = folder
            self.lblPath.setText(folder)

    def download(self):
        bbox = utils.get_canvas_bbox_4326(self.iface)
        if not bbox: return

        task = duckdb_task.FTWDuckDBTask("Baixando polígonos FTW", bbox, self.output_dir, self.iface)
        QgsApplication.taskManager().addTask(task)
        QMessageBox.information(self, "Info", "Download iniciado em background.")