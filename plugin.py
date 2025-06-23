import os
from typing import Optional
from PyQt5.QtCore import QTranslator, QCoreApplication, QSettings
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog, Qgis
from .main_dialog import MainDialog

class Qgis2Mapbender:
    """
        Main plugin class for QGIS2Mapbender, handling GUI integration and dialog management.
    """
    dlg: Optional[MainDialog] = None

    def __init__(self, iface) -> None:
        """
            Initializes the QGIS2Mapbender plugin.

            Args:
                iface: The QGIS interface instance.

            Returns:
                None
        """
        self.translator = None
        self.plugin_dir = None
        self.iface = iface
        self.dlg = None
        self.action = None
        self.toolbar = None
        self.plugin_name = "QGIS2Mapbender"
        self.web_menu = "&QGIS2Mapbender"

    def initGui(self) -> None:
        """
            Initializes the plugin GUI, adding an action to the QGIS interface.

            Returns:
                None
        """

        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'resources/icons/qgis2mapbender.png')
            self.action = QAction(QIcon(icon_path), self.plugin_name, self.iface.mainWindow())
            self.action.triggered.connect(self.run)

            self.iface.addPluginToWebMenu(self.web_menu, self.action)
            self.iface.addToolBarIcon(self.action)

            self.plugin_dir = os.path.dirname(__file__)
            locale = QSettings().value("locale/userLocale")[0:2]
            locale_path = os.path.join(self.plugin_dir,
                                       'i18n',
                                       f'{locale}.qm')

            if os.path.exists(locale_path):
                self.translator = QTranslator()
                self.translator.load(locale_path)
                QCoreApplication.installTranslator(self.translator)

        except Exception as e:
            QgsMessageLog.logMessage(f"{self.plugin_name}: Error in initGui: {e}", self.plugin_name, level=Qgis.Critical)

    def unload(self) -> None:
        """
            Unloads the plugin, removing the action from the menu and toolbar.

            Returns:
                None
        """
        try:
            self.iface.removePluginWebMenu(self.web_menu, self.action)
            self.iface.removeToolBarIcon(self.action)
        except Exception as e:
            QgsMessageLog.logMessage(f"{self.plugin_name}: Error in unload: {e}", self.plugin_name, level=Qgis.Critical)

    def run(self) -> None:
        """
            Runs the plugin, showing the main dialog.

            Returns:
                None
        """
        try:
            if not self.dlg:
                self.dlg = MainDialog()
            self.dlg.show()
            self.dlg.raise_()
            self.dlg.activateWindow()
        except Exception as e:
            QgsMessageLog.logMessage(f"{self.plugin_name}: Error in run: {e}", self.plugin_name, level=Qgis.Critical)