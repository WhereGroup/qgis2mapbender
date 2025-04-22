import os
from typing import Optional


from PyQt5 import uic
from PyQt5.QtCore import QSettings, QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator, QPixmap, QIcon
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QWidget, QTabWidget, QRadioButton, QPushButton, \
    QTableWidget, QComboBox, QDialogButtonBox, QToolButton, QLabel, QApplication

from qgis.core import Qgis, QgsSettings, QgsMessageLog
from qgis.utils import iface

from .api_request import ApiRequest
from .qgis_server_api_upload import QgisServerApiUpload
from .dialogs.server_config_dialog import ServerConfigDialog
from .helpers import qgis_project_is_saved, \
    show_fail_box_ok, show_fail_box_yes_no, show_succes_box_ok, \
    list_qgs_settings_child_groups, show_question_box, \
    update_mb_slug_in_settings
from .paths import Paths
from .server_config import ServerConfig
from .settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG

# Dialog from .ui file
WIDGET, BASE = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialogs/ui/main_dialog.ui'))


class MainDialog(BASE, WIDGET):
    tabWidget: QTabWidget
    serverUploadTab: QWidget
    serverConfigTab: QWidget
    publishRadioButton: QRadioButton
    cloneTemplateRadioButton: QRadioButton
    serverTableWidget: QTableWidget
    warningFirstServerLabel: QLabel
    serverConfigComboBox: QComboBox
    mbSlugComboBox: QComboBox
    buttonBoxTab1: QDialogButtonBox
    publishButton: QPushButton
    updateButton: QPushButton
    addServerConfigButton: QToolButton
    duplicateServerConfigButton: QToolButton
    editServerConfigButton: QToolButton
    removeServerConfigButton: QToolButton
    buttonBoxTab2: QDialogButtonBox

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setupConnections()

        # initialize API request
        self.server_config = ServerConfig.getParamsFromSettings(self.serverConfigComboBox.currentText())
        self.api_request = ApiRequest(self.server_config)


    def setupUi(self, widget) -> None:
        super().setupUi(widget)
        self.warningFirstServerLabel.setPixmap(QPixmap(':/images/themes/default/mIconWarning.svg'))
        # Tabs
        self.tabWidget.setCurrentWidget(self.serverUploadTab)

        # Tab
        self.publishButton.setIcon(QIcon(':/images/themes/default/mActionSharingExport.svg'))
        self.updateButton.setIcon(QIcon(':/images/themes/default/mActionRefresh.svg'))
        self.update_server_combo_box()
        self.publishRadioButton.setChecked(True)
        self.update_slug_combo_box()
        self.mbSlugComboBox.setCurrentIndex(-1)
        self.cloneTemplateRadioButton.setChecked(True)
        self.publishButton.setEnabled(False)  # Enabled only if mbSlugComboBox has a value
        self.updateButton.setEnabled(False)
        # QLineValidator for slug:
        regex_slug_layer_set = QRegExp("[^\\s;\\\\/]*")
        regex_slug_layer_set_validator = QRegExpValidator(regex_slug_layer_set)
        self.mbSlugComboBox.setValidator(regex_slug_layer_set_validator)
        self.layerSetLineEdit.setValidator(regex_slug_layer_set_validator)

        # Tab2
        self.addServerConfigButton.setIcon(QIcon(':/images/themes/default/mActionAdd.svg'))
        self.duplicateServerConfigButton.setIcon(QIcon(':/images/themes/default/mActionEditCopy.svg'))
        self.removeServerConfigButton.setIcon(QIcon(':/images/themes/default/mIconDelete.svg'))
        self.editServerConfigButton.setIcon(QIcon(':/images/themes/default/mActionAllEdits.svg'))
        server_table_headers = ["Name",
                                "URL"]  # , "QGIS-Projects path", "QGIS-Server path" , "Mapbender app path", "Mapbender basis URL"
        self.serverTableWidget.setColumnCount(len(server_table_headers))
        self.serverTableWidget.setHorizontalHeaderLabels(server_table_headers)
        self.serverTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.update_server_table()

        # Buttons
        self.addServerConfigButton.setToolTip("Add server configuration")
        self.duplicateServerConfigButton.setToolTip("Duplicate selected server configuration")
        self.editServerConfigButton.setToolTip("Edit selected server configuration")
        self.removeServerConfigButton.setToolTip("Remove selected server configuration")
        self.buttonBoxTab2.rejected.connect(self.reject)

    def setupConnections(self) -> None:
        self.tabWidget.currentChanged.connect(self.update_server_combo_box)
        self.publishRadioButton.clicked.connect(self.enable_publish_parameters)
        self.updateRadioButton.clicked.connect(self.disable_publish_parameters)
        self.mbSlugComboBox.lineEdit().textChanged.connect(self.validate_slug_not_empty)
        self.mbSlugComboBox.currentIndexChanged.connect(self.validate_slug_not_empty)
        self.publishButton.clicked.connect(self.publish_project)
        #self.updateButton.clicked.connect(self.update_project)
        self.buttonBoxTab1.rejected.connect(self.reject)
        self.addServerConfigButton.clicked.connect(self.on_add_server_config_clicked)
        self.duplicateServerConfigButton.clicked.connect(self.on_duplicate_server_config_clicked)
        self.editServerConfigButton.clicked.connect(self.on_edit_server_config_clicked)
        self.removeServerConfigButton.clicked.connect(self.on_remove_server_config_clicked)
        self.serverTableWidget.doubleClicked.connect(self.on_edit_server_config_clicked)

    def update_server_table(self) -> None:
        server_config_list = list_qgs_settings_child_groups(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection")
        self.serverTableWidget.setRowCount(len(server_config_list))
        for i, (name) in enumerate(server_config_list):
            item_name = QTableWidgetItem(name)
            item_name.setText(server_config_list[i])
            self.serverTableWidget.setItem(i, 0, item_name)

            server_config = ServerConfig.getParamsFromSettings(name)

            item_url = QTableWidgetItem()
            item_url.setText(server_config.url)
            self.serverTableWidget.setItem(i, 1, item_url)

            # Further columns (see settings.py SERVER_TABLE_HEADERS)
            # item_path_qgis_projects = QTableWidgetItem()
            # item_path_qgis_projects.setText(server_config.projects_path)
            # self.serverTableWidget.setItem(i, 2, item_path_qgis_projects)
            #
            # item_qgis_server_path = QTableWidgetItem()
            # item_qgis_server_path.setText(server_config.qgis_server_path)
            # self.serverTableWidget.setItem(i, 3, item_qgis_server_path)
            #
            # item_mb_app_path = QTableWidgetItem()
            # item_mb_app_path.setText(server_config.mb_app_path)
            # self.serverTableWidget.setItem(i, 4, item_mb_app_path)
            #
            # item_mb_basis_url = QTableWidgetItem()
            # item_mb_basis_url.setText(server_config.mb_basis_url)
            # self.serverTableWidget.setItem(i, 5, item_mb_basis_url)

        self.update_server_combo_box()

    def update_server_combo_box(self) -> None:
        """ Updates the server configuration dropdown menu """
        # Read server configurations
        server_config_list = list_qgs_settings_child_groups(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection")
        if len(server_config_list) == 0:
            self.warningFirstServerLabel.show()
            self.serverComboBoxLabel.setText("Please add a server")
            self.serverConfigComboBox.clear()
            return

        # Update server configuration-combobox
        self.serverComboBoxLabel.setText("Server")
        self.warningFirstServerLabel.hide()
        self.serverConfigComboBox.clear()
        self.serverConfigComboBox.addItems(server_config_list)

    def update_slug_combo_box(self) -> None:
        s = QgsSettings()
        if not s.contains(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/mb_templates"):
            return
        s.beginGroup(PLUGIN_SETTINGS_SERVER_CONFIG_KEY)
        mb_slugs = s.value('mb_templates')
        s.endGroup()
        if isinstance(mb_slugs, str):
            mb_slugs_list = mb_slugs.split(", ")
        else:
            mb_slugs_list = mb_slugs
        self.mbSlugComboBox.clear()
        if len(mb_slugs) > 0:
            self.mbSlugComboBox.addItems(mb_slugs_list)
            self.mbSlugComboBox.setCurrentIndex(-1)

    def disable_publish_parameters(self) -> None:
        self.mbParamsFrame.setEnabled(False)
        self.updateButton.setEnabled(True)
        self.publishButton.setEnabled(False)

    def enable_publish_parameters(self) -> None:
        self.mbParamsFrame.setEnabled(True)
        self.updateButton.setEnabled(False)
        self.publishButton.setEnabled(True)

    def validate_slug_not_empty(self) -> None:
        """
        Enable the publish button only "URL Title" has a value
        :return:
        """
        self.publishButton.setEnabled(self.mbSlugComboBox.currentText() != '')

    def open_server_config_dialog(self, config_name: Optional[str] = None, mode: Optional[str] = None) -> None:
        new_server_config_dialog = ServerConfigDialog(server_config_name=config_name, mode=mode, parent=iface.mainWindow())
        new_server_config_dialog.exec()
        self.update_server_table()
        self.update_server_combo_box()

    def on_add_server_config_clicked(self) -> None:
        self.open_server_config_dialog()

    def get_selected_server_config(self) -> str:
        selected_row = self.serverTableWidget.currentRow()
        if selected_row == -1:
            return
        return self.serverTableWidget.item(selected_row, 0).text()

    def on_duplicate_server_config_clicked(self) -> None:
        selected_server_config = self.get_selected_server_config()
        self.open_server_config_dialog(selected_server_config, mode='duplicate')

    def on_edit_server_config_clicked(self) -> None:
        selected_server_config = self.get_selected_server_config()
        self.open_server_config_dialog(selected_server_config, mode='edit')

    def on_remove_server_config_clicked(self) -> None:
        selected_row = self.serverTableWidget.currentRow()
        if selected_row == -1:
            return
        selected_server_config = self.serverTableWidget.item(selected_row, 0).text()
        if show_question_box(
                f"Are you sure you want to remove the server configuration '{selected_server_config}'?") != QMessageBox.Yes:
            return
        s = QSettings()
        s.remove(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{selected_server_config}")
        show_succes_box_ok('Success', 'Server configuration successfully removed')
        self.update_server_table()
        self.update_server_combo_box()


    def publish_project(self) -> None:
        if not qgis_project_is_saved():
            return

        # Check Mapbender params:
        if self.mbSlugComboBox.currentText() == '':
            show_fail_box_ok("Please complete Mapbender parameters",
                             "Please enter a valid Mapbender URL title")
            return

        # Set waiting cursor
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.upload_project_qgis_server()
        finally:
            # Restore default cursor
            QApplication.restoreOverrideCursor()

    # # Update project option wil be no longer available in the API Version of the plugin
    # def update_project(self) -> None:
    #     if not qgis_project_is_saved():
    #         return
    #
    #     # Set waiting cursor
    #     QApplication.setOverrideCursor(Qt.WaitCursor)
    #     try:
    #         self.upload_project_qgis_server()
    #     finally:
    #         # Restore default cursor
    #         QApplication.restoreOverrideCursor()

    def upload_project_qgis_server(self) -> None:
        QgsMessageLog.logMessage("Preparing for project upload to QGIS server...", TAG, level=Qgis.Info)

        # Get server config params and project paths
        paths = Paths.get_paths(self.server_config.projects_path)

        upload = QgisServerApiUpload(paths)
        result = upload.process_and_upload_project(self.server_config)
        if result:
            show_fail_box_ok("Failed", result)
        else:
            wms_url = upload.get_wms_url(self.server_config)
            #tests only
            #wms_url = "http://mapbender-qgis.wheregroup.lan/cgi-bin/qgis_mapserv.fcgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities&map=/data/qgis-projects/projekt_shp.qgz"
            self.mb_publish(wms_url)
        return

    def mb_publish(self, wms_url: str) -> None:
        """
        Publishes the WMS on Mapbender using the ApiRequest class.

        Args:
            wms_url: The WMS URL to be published.
        """
        QgsMessageLog.logMessage(f"Starting Mapbender publish", TAG, level=Qgis.Info)

        # Get Mapbender params:
        if self.cloneTemplateRadioButton.isChecked():
            clone_app = True
        if self.addToAppRadioButton.isChecked():
            clone_app = False
        # Template slug:
        layer_set = self.layerSetLineEdit.text()

        # check if source already exists in Mapbender as a source (with endpoint wms/show)
        exit_status_wms_show, output = self.api_request.wms_show(wms_url)
        QgsMessageLog.logMessage(f"exit_status_wms_show: {exit_status_wms_show}, output: {output}", TAG, level=Qgis.Info)



        return

    def mb_update(self, wms_url):
        # TODO please review new logic according to the new API and develop accordingly
        return