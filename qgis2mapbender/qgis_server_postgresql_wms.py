"""PostgreSQL project WMS URL construction for QGIS Server."""

from urllib.parse import parse_qs, urlencode, urlparse

from qgis.core import QgsMessageLog, Qgis, QgsProject

from .helpers import append_query_to_url
from .server_config import ServerConfig
from .settings import TAG


def get_postgresql_project_wms_url(server_config: ServerConfig) -> str:
    """Builds the public WMS URL expected by the PostgreSQL QGIS Server wrapper."""
    QgsMessageLog.logMessage(
        "Preparing WMS URL for PostgreSQL project...",
        TAG,
        level=Qgis.MessageLevel.Info
    )
    project_uri = QgsProject.instance().fileName()
    print(f"Project URI: {project_uri}")
    if not project_uri:
        return ""

    project_parameters = parse_qs(
        urlparse(project_uri).query,
        keep_blank_values=True
    )
    project_name = project_parameters.get("project", [None])[0]
    schema = project_parameters.get("schema", [None])[0]
    service = project_parameters.get("service", [None])[0]
    print(project_parameters)
    print(service)
    if not project_name or not schema:
        QgsMessageLog.logMessage(
            "The PostgreSQL project URI does not contain a project name and schema.",
            TAG,
            level=Qgis.MessageLevel.Critical
        )
        return ""
    map = f"postgresql://?service={service}&schema={schema}&project={project_name}"
    query = urlencode({
        "map": map,
        "schema": schema,
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetCapabilities",
    })

    wms_url = append_query_to_url(server_config.qgis_server_path, query)
    print(f"WMS URL: {wms_url}")
    QgsMessageLog.logMessage(f"WMS URL: {wms_url}", TAG, level=Qgis.MessageLevel.Info)
    return wms_url
