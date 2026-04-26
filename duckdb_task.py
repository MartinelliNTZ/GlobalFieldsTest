# -*- coding: utf-8 -*-
"""
FTW DuckDB Background Task — Downloads field polygons for the current canvas extent.

IMPORTANT: This module does NOT use wildcards (*.parquet) or s3://.
It builds an explicit list of HTTPS URLs via a regular-grid heuristic
and queries only those files with DuckDB.
"""

import os
import math
import duckdb
import urllib.request

from qgis.core import QgsTask, QgsVectorLayer, QgsProject
from qgis.PyQt.QtWidgets import QMessageBox

# Configurações do Data Source incorporadas para evitar erros de import
GEOPARQUET_HTTPS_BASE = "https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results"
GEOPARQUET_TILE_SIZE = 10.0
GEOPARQUET_MAX_CANDIDATES = 50

def get_candidate_parquet_urls(xmin, ymin, xmax, ymax):
    """Gera lista de URLs baseada na grade heurística."""
    urls = []
    tile_size = GEOPARQUET_TILE_SIZE
    
    x_start = math.floor(xmin / tile_size) * tile_size
    y_start = math.floor(ymin / tile_size) * tile_size

    x = x_start
    while x - 1e-9 < xmax + tile_size:
        y = y_start
        while y - 1e-9 < ymax + tile_size:
            # Padrão: fields_{lat}_{lon}.parquet
            url = f"{GEOPARQUET_HTTPS_BASE}/fields_{int(y)}_{int(x)}.parquet"
            urls.append(url)
            y += tile_size
        x += tile_size

    return urls

class FTWDuckDBTask(QgsTask):
    """QgsTask that queries remote FTW GeoParquet via DuckDB and loads the result into QGIS."""

    def __init__(self, description, bbox, cache_dir, iface):
        """
        :param description: Task description shown in the QGIS task manager.
        :param bbox: Tuple (xmin, ymin, xmax, ymax) in EPSG:4326.
        :param cache_dir: Local directory to write the clipped output.
        :param iface: QGIS interface instance (used for UI feedback).
        """
        super().__init__(description, QgsTask.CanCancel)
        self.xmin, self.ymin, self.xmax, self.ymax = bbox
        self.cache_dir = cache_dir
        self.iface = iface

        self.output_parquet = None
        self.output_gpkg = None
        self.exception = None
        self.row_count = 0
        self.candidate_urls = []

    def run(self):
        try:
            self.setProgress(5)

            # Ensure cache directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            self.output_parquet = os.path.join(self.cache_dir, "ftw_clip.parquet")
            self.output_gpkg = os.path.join(self.cache_dir, "ftw_clip.gpkg")

            # 1. Build explicit candidate URL list (heuristic, no wildcards)
            self.candidate_urls = get_candidate_parquet_urls(
                self.xmin, self.ymin, self.xmax, self.ymax
            )

            if not self.candidate_urls:
                self.exception = Exception(
                    "No candidate GeoParquet files found for the selected extent.\n"
                    "Try zooming to a different area."
                )
                return False

            if len(self.candidate_urls) > GEOPARQUET_MAX_CANDIDATES:
                self.exception = Exception(
                    f"Too many candidate files ({len(self.candidate_urls)}).\n"
                    f"Maximum allowed is {GEOPARQUET_MAX_CANDIDATES}.\n"
                    "Zoom in to reduce the number of tiles."
                )
                return False

            # Filtra URLs inexistentes (404) para evitar erros de IO no DuckDB.
            # A heurística de grade gera URLs candidatas que podem não existir no servidor.
            self.setProgress(15)
            valid_urls = []
            for url in self.candidate_urls:
                if self.isCanceled():
                    return False
                try:
                    # Verifica existência do arquivo
                    req = urllib.request.Request(url, method='HEAD')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        if response.status == 200:
                            valid_urls.append(url)
                except Exception:
                    continue
            self.candidate_urls = valid_urls

            if not self.candidate_urls:
                self.exception = Exception(
                    "Nenhum arquivo de dados foi encontrado para esta extensão (todos os tiles retornaram 404)."
                )
                return False

            self.setProgress(25)

            # In-memory DuckDB connection - simplificado
            con = duckdb.connect(':memory:')

            self.setProgress(35)
            # Install and load required extensions
            con.execute("INSTALL spatial;")
            con.execute("LOAD spatial;")
            con.execute("INSTALL httpfs;")
            con.execute("LOAD httpfs;")

            self.setProgress(45)

            # Build DuckDB SQL array literal: ['url1', 'url2', ...]
            url_list_sql = ", ".join(f"'{u}'" for u in self.candidate_urls)
            read_parquet_expr = f"read_parquet([{url_list_sql}])"
            
            # Common WHERE clause for spatial filtering
            where_clause = f"""
                label = 'field'
                AND struct_extract(bbox, 'xmax') >= {self.xmin}
                AND struct_extract(bbox, 'xmin') <= {self.xmax}
                AND struct_extract(bbox, 'ymax') >= {self.ymin}
                AND struct_extract(bbox, 'ymin') <= {self.ymax}
            """

            # 2. Count matching rows before exporting
            count_query = f"""
                SELECT COUNT(*)
                FROM {read_parquet_expr}
                WHERE {where_clause}
            """
            self.row_count = con.execute(count_query).fetchone()[0]

            if self.row_count == 0:
                self.exception = Exception(
                    "No field polygons found for the selected canvas extent.\n"
                    "Try zooming to an agricultural area."
                )
                return False

            self.setProgress(60)

            # 3. Export filtered result to local Parquet
            export_query = f"""
                COPY (
                    SELECT *
                    FROM {read_parquet_expr}
                    WHERE {where_clause}
                ) TO '{self.output_parquet}' (FORMAT PARQUET)
            """
            con.execute(export_query)

            self.setProgress(80)

            # 4. Attempt GeoPackage conversion for easier QGIS handling
            try:
                gpkg_query = f"""
                    COPY (
                        SELECT *
                        FROM {read_parquet_expr}
                        WHERE {where_clause}
                    ) TO '{self.output_gpkg}' (FORMAT GDAL, DRIVER 'GPKG')
                """
                con.execute(gpkg_query)
            except Exception:
                # GPKG conversion is optional; fall back to Parquet
                self.output_gpkg = None

            con.close()
            self.setProgress(100)
            return True

        except Exception as e:
            self.exception = e
            return False

    def finished(self, result):
        """Executed in the main thread when run() completes. Safe to touch GUI."""
        if not result:
            msg = str(self.exception) if self.exception else "Unknown error during background processing."
            QMessageBox.critical(self.iface.mainWindow(), "FTW Download Error", msg)
            return

        # Prefer GPKG if successfully created, otherwise Parquet
        if self.output_gpkg and os.path.exists(self.output_gpkg):
            layer_path = self.output_gpkg
        else:
            layer_path = self.output_parquet

        layer_name = "FTW Fields (by extent)"
        layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if not layer.isValid():
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Layer Error",
                f"Failed to load the downloaded layer:\n{layer_path}"
            )
            return

        QgsProject.instance().addMapLayer(layer)
        self.iface.messageBar().pushMessage(
            "FTW",
            f"Downloaded {self.row_count} field polygons ({len(self.candidate_urls)} files queried) and added to project.",
            level=0,  # Info
            duration=5
        )
