from qgis.PyQt.QtCore import QCoreApplication


def tr(message: str) -> str:
    return QCoreApplication.translate('Qgis2Mapbender', message)