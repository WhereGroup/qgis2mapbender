
import os
from typing import Optional
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
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
        self.dlg = None
        self.iface = iface

    def initGui(self) -> None:
        """
            Initializes the plugin GUI, adding an action to the QGIS interface.

            Returns:
                None
        """
        icon_path = os.path.join(os.path.dirname(__file__), 'resources/icons/qgis2mapbender.png')
        self.action = QAction(QIcon(icon_path), 'QGIS2Mapbender', self.iface.mainWindow())
        self.iface.addPluginToMenu("&Web", self.action)
        self.iface.addToolBarIcon(self.action)

        # Connect the action to the run method
        self.action.triggered.connect(self.run)

    def unload(self) -> None:
        """
            Unloads the plugin, removing the action from the menu and toolbar.

            Returns:
                None
        """
        self.iface.removePluginMenu("&Web", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dlg:
            self.dlg.close()
            self.dlg = None

    def run(self) -> None:
        """
            Runs the plugin, showing the main dialog.

            Returns:
                None
        """
        self.dlg = MainDialog()
        self.dlg.show()
        # sys.exit(dlg.exec_())
