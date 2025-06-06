
import os
from typing import Optional
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .main_dialog import MainDialog


class Qgis2Mapbender:
    dlg: Optional[MainDialog] = None
    def __init__(self, iface):
        """Constructor of the QGIS2Mapbender."""
        self.dlg = None
        self.iface = iface

    def initGui(self):
        """Create action that will start plugin configuration"""
        icon_path = os.path.join(os.path.dirname(__file__), 'resources/icons/qgis2mapbender.png')
        self.action = QAction(QIcon(icon_path), 'QGIS2Mapbender', self.iface.mainWindow())
        self.iface.addPluginToMenu("&Web", self.action)
        self.iface.addToolBarIcon(self.action)

        # Connect the action to the run method
        self.action.triggered.connect(self.run)

    def unload(self):
        self.iface.removePluginMenu("&Web", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dlg:
            self.dlg.close()
            self.dlg = None

    def run(self):

        self.dlg = MainDialog()
        self.dlg.show()
        # sys.exit(dlg.exec_())
