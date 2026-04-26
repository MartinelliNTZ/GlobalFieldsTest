# -*- coding: utf-8 -*-
"""
Global Fields of The World (FTW) — General utilities.
"""

from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsProject


def get_canvas_extent_wkt(iface):
    """Return the current map canvas extent as a WKT POLYGON string.
    :param iface: QGIS interface instance.
    :returns: WKT POLYGON string in the canvas CRS, or None.
    """
    canvas = iface.mapCanvas()
    if canvas is None:
        return None
    extent = canvas.extent()
    crs = canvas.mapSettings().destinationCrs().authid()
    # Build WKT
    wkt = (
        f"POLYGON(("
        f"{extent.xMinimum()} {extent.yMinimum()}, "
        f"{extent.xMinimum()} {extent.yMaximum()}, "
        f"{extent.xMaximum()} {extent.yMaximum()}, "
        f"{extent.xMaximum()} {extent.yMinimum()}, "
        f"{extent.xMinimum()} {extent.yMinimum()}"
        f"))"
    )
    return wkt


def get_canvas_bbox_4326(iface):
    """Return the current map canvas extent as a bbox tuple in EPSG:4326.
    :param iface: QGIS interface instance.
    :returns: (xmin, ymin, xmax, ymax) floats or None.
    """
    canvas = iface.mapCanvas()
    if canvas is None:
        return None
    extent = canvas.extent()
    src_crs = canvas.mapSettings().destinationCrs()
    dst_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    if src_crs != dst_crs:
        transform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
        extent = transform.transformBoundingBox(extent)
    return (
        extent.xMinimum(),
        extent.yMinimum(),
        extent.xMaximum(),
        extent.yMaximum(),
    )


def check_bbox_area(xmin, ymin, xmax, ymax, max_area_deg2=25.0):
    """Check if the bbox area exceeds a threshold.
    :returns: (is_valid: bool, area: float, message: str)
    """
    width = abs(xmax - xmin)
    height = abs(ymax - ymin)
    area = width * height
    if area > max_area_deg2:
        msg = (
            f"The selected area is very large ({area:.2f} deg²). "
            f"Maximum recommended is {max_area_deg2} deg². "
            "Zoom in to a smaller area to avoid heavy downloads."
        )
        return False, area, msg
    return True, area, ""


def get_scl_mask_info():
    """Return a human-readable description of the SCL masking applied in FTW."""
    lines = [
        "Sentinel-2 SCL pixel values masked before computing medians:",
        ""
    ]
    scl_desc = {
        0: "No Data",
        1: "Saturated Defective",
        3: "Cloud Shadow",
        7: "Cloud Low Probability / Unclassified",
        8: "Cloud Medium Probability",
        9: "Cloud High Probability",
        10: "Thin Cirrus",
    }
    for val, desc in scl_desc.items():
        lines.append(f"  {val}: {desc}")
    return "\n".join(lines)
