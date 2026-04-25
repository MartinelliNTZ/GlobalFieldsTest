# -*- coding: utf-8 -*-
import os
import duckdb

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


# 🔹 arquivos parquet (MVP)
PARQUET_FILES = [
    "https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results/part-00000.parquet",
    "https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results/part-00001.parquet",
    "https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results/part-00002.parquet"
]


# 🔥 TASK
class FTWDownloadTask(QgsTask):

    def __init__(self, iface, output_path):
        super().__init__("Baixando FTW", QgsTask.CanCancel)
        self.iface = iface
        self.output_path = output_path

    def run(self):
        try:
            xmin, ymin, xmax, ymax = self.get_canvas_bbox()

            con = duckdb.connect()
            con.execute("INSTALL httpfs; LOAD httpfs;")

            query = f"""
            SELECT *
            FROM read_parquet({PARQUET_FILES})
            WHERE label = 'field'
              AND struct_extract(bbox, 'xmax') >= {xmin}
              AND struct_extract(bbox, 'xmin') <= {xmax}
              AND struct_extract(bbox, 'ymax') >= {ymin}
              AND struct_extract(bbox, 'ymin') <= {ymax}
            """

            df = con.execute(query).fetchdf()

            if df.empty:
                self.error_msg = "Nenhum dado encontrado."
                return False

            df.to_parquet(self.output_path)
            return True

        except Exception as e:
            self.error_msg = str(e)
            return False

    def finished(self, result):
        if result:
            layer = QgsVectorLayer(self.output_path, "FTW Fields", "ogr")
            QgsProject.instance().addMapLayer(layer)
        else:
            QMessageBox.critical(None, "Erro", getattr(self, "error_msg", "Erro desconhecido"))

    def get_canvas_bbox(self):
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        crs = canvas.mapSettings().destinationCrs()

        transform = QgsCoordinateTransform(
            crs,
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsProject.instance()
        )

        rect = transform.transformBoundingBox(extent)

        return rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()


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
        output_path = os.path.join(self.output_dir, "ftw_result.parquet")

        task = FTWDownloadTask(self.iface, output_path)
        QgsApplication.taskManager().addTask(task)

        QMessageBox.information(self, "Info", "Download iniciado em background.")