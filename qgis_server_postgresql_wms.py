"""PostgreSQL project WMS URL construction for QGIS Server."""

from urllib.parse import urlencode

from qgis.core import QgsMessageLog, Qgis, QgsProject

from .helpers import append_query_to_url
from .server_config import ServerConfig
from .settings import TAG


def get_postgresql_project_wms_url(server_config: ServerConfig) -> str:
    """Builds a WMS URL that passes the PostgreSQL project URI to QGIS Server."""
    QgsMessageLog.logMessage(
        "Preparing WMS URL for PostgreSQL project...",
        TAG,
        level=Qgis.MessageLevel.Info
    )
    project_uri = QgsProject.instance().fileName()
    QgsMessageLog.logMessage(
        f"QGIS-Project uri: {project_uri}",
        TAG,
        level=Qgis.MessageLevel.Info
    )
    if not project_uri:
        return ""

    query = urlencode({
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetCapabilities",
        "MAP": project_uri,
    })
    wms_url = append_query_to_url(server_config.qgis_server_path, query)
    QgsMessageLog.logMessage(f"WMS URL: {wms_url}", TAG, level=Qgis.MessageLevel.Info)
    return wms_url
