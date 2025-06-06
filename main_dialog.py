import os
from typing import Optional

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, QRegularExpression, Qt
from qgis.PyQt.QtGui import QRegularExpressionValidator, QPixmap, QIcon
from qgis.PyQt.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QWidget, QTabWidget, QRadioButton, QPushButton, \
    QTableWidget, QComboBox, QDialogButtonBox, QToolButton, QLabel, QApplication

from qgis.core import Qgis, QgsSettings, QgsMessageLog

from .api_request import ApiRequest
from .qgis_server_api_upload import QgisServerApiUpload
from .mapbender_api_upload import MapbenderApiUpload
from .dialogs.server_config_dialog import ServerConfigDialog
from .helpers import qgis_project_is_saved, check_if_qgis_project_is_dirty_and_save, \
    show_fail_box_ok, show_succes_box_ok, \
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
        regex_slug_url = QRegularExpression("[^\\s;\\\\/]*")
        regex_layer_set = QRegularExpression("^(?!\\s)[^;/\\\\]*$")
        regex_slug_url_validator = QRegularExpressionValidator(regex_slug_url)
        regex_layer_set_validator = QRegularExpressionValidator(regex_layer_set)
        self.mbSlugComboBox.setValidator(regex_slug_url_validator)
        self.layerSetLineEdit.setValidator(regex_layer_set_validator)

        # Tab2
        self.addServerConfigButton.setIcon(QIcon(':/images/themes/default/mActionAdd.svg'))
        self.duplicateServerConfigButton.setIcon(QIcon(':/images/themes/default/mActionEditCopy.svg'))
        self.removeServerConfigButton.setIcon(QIcon(':/images/themes/default/mIconDelete.svg'))
        self.editServerConfigButton.setIcon(QIcon(':/images/themes/default/mActionAllEdits.svg'))
        server_table_headers = ["Name",
                                "Mapbender URL"]  # "QGIS-Server path" ,
        self.serverTableWidget.setColumnCount(len(server_table_headers))
        self.serverTableWidget.setHorizontalHeaderLabels(server_table_headers)
        self.serverTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.update_server_table()

        # Buttons
        self.addServerConfigButton.setToolTip("Add server configuration")
        self.duplicateServerConfigButton.setToolTip("Duplicate selected server configuration")
        self.editServerConfigButton.setToolTip("Edit selected server configuration")
        self.removeServerConfigButton.setToolTip("Remove selected server configuration")
        self.buttonBoxTab2.rejected.connect(self.reject)

        # Set Button Tab2 to english
        button_close_tab2 = self.buttonBoxTab2.button(QDialogButtonBox.Close)
        button_close_tab2.setText("Close")

    def setupConnections(self) -> None:
        self.tabWidget.currentChanged.connect(self.update_server_combo_box)
        self.publishRadioButton.clicked.connect(self.enable_publish_parameters)
        self.updateRadioButton.clicked.connect(self.disable_publish_parameters)
        self.mbSlugComboBox.lineEdit().textChanged.connect(self.validate_slug_not_empty)
        self.mbSlugComboBox.currentIndexChanged.connect(self.validate_slug_not_empty)
        self.publishButton.clicked.connect(self.run)
        self.updateButton.clicked.connect(self.run)
        self.buttonBoxTab1.rejected.connect(self.reject)
        self.addServerConfigButton.clicked.connect(self.on_add_server_config_clicked)
        self.duplicateServerConfigButton.clicked.connect(self.on_duplicate_server_config_clicked)
        self.editServerConfigButton.clicked.connect(self.on_edit_server_config_clicked)
        self.removeServerConfigButton.clicked.connect(self.on_remove_server_config_clicked)
        self.serverTableWidget.doubleClicked.connect(self.on_edit_server_config_clicked)

        # Set Button Tab1 to english
        button_close_tab1 = self.buttonBoxTab1.button(QDialogButtonBox.Close)
        button_close_tab1.setText("Close")
        # Button had a blue background
        button_close_tab1.setAutoDefault(False)
        button_close_tab1.setDefault(False)

    def update_server_table(self) -> None:
        server_config_list = list_qgs_settings_child_groups(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection")
        self.serverTableWidget.setRowCount(len(server_config_list))
        for i, (name) in enumerate(server_config_list):
            item_name = QTableWidgetItem(name)
            item_name.setText(server_config_list[i])
            self.serverTableWidget.setItem(i, 0, item_name)

            server_config = ServerConfig.getParamsFromSettings(name)

            item_mb_basis_url = QTableWidgetItem()
            item_mb_basis_url.setText(server_config.mb_basis_url)
            self.serverTableWidget.setItem(i, 1, item_mb_basis_url)

            # Further columns
            # item_qgis_server_path = QTableWidgetItem()
            # item_qgis_server_path.setText(server_config.qgis_server_path)
            # self.serverTableWidget.setItem(i, 2, item_qgis_server_path)

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
        new_server_config_dialog = ServerConfigDialog(server_config_name=config_name, mode=mode) #, parent=iface.mainWindow())
        new_server_config_dialog.exec()
        self.update_server_table()
        self.update_server_combo_box()

    def on_add_server_config_clicked(self) -> None:
        self.open_server_config_dialog()

    def get_selected_server_config(self) -> Optional[str]:
        selected_row = self.serverTableWidget.currentRow()
        if selected_row == -1:
            return None
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
                f"Are you sure you want to remove the server configuration '{selected_server_config}'?") != QMessageBox.StandardButton.Yes:
            return
        s = QSettings()
        s.remove(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{selected_server_config}")
        show_succes_box_ok('Success', 'Server configuration successfully removed')
        self.update_server_table()
        self.update_server_combo_box()

    def initialize_api_request(self) -> tuple[ServerConfig, ApiRequest]:
        """Initializes the ApiRequest instance."""
        server_config = ServerConfig.getParamsFromSettings(self.serverConfigComboBox.currentText())
        api_request = ApiRequest(server_config)
        return server_config, api_request

    def run(self) -> None:
        """
        Executes the publishing or updating process for the current QGIS project.

        This method:
        - Verifies the QGIS project is saved and prompts for saving if needed
        - Sets the cursor to indicate an ongoing process
        - Validates input parameters based on selected mode (Publish/Update)
        - Initializes API connection using server configuration
        - Uploads the project to QGIS-Server
        - Performs either publication (mb_publish) or update (mb_update) on Mapbender

        The method uses the current dialog state (selected radio buttons,
        server configuration, and input fields) for processing.

        Error handling occurs throughout the various steps with appropriate feedback
        to the user. The cursor is restored at the end regardless of outcome.

        Returns:
            None
        """

        if not qgis_project_is_saved():
            return

        if not check_if_qgis_project_is_dirty_and_save():
            QgsMessageLog.logMessage("Publish/Update cancelled by the user (unsaved changes).", TAG, level=Qgis.MessageLevel.Info)
            return

        # Set waiting cursor
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        wms_url = None
        api_request = None
        try:
            action = "publish" if self.publishRadioButton.isChecked() else "update"
            if action == "publish" and self.mbSlugComboBox.currentText() == '':
                show_fail_box_ok("Please complete Mapbender parameters",
                                 "Please enter a valid Mapbender URL title")
                return

            server_config, api_request = self.initialize_api_request()
            if not api_request.token:
                return

            QgsMessageLog.logMessage("Preparing upload to QGIS server...", TAG, level=Qgis.MessageLevel.Info)
            # Get server config: project paths
            paths = Paths.get_paths()
            qgis_server_upload = QgisServerApiUpload(api_request, paths)
            status_code_server_upload, upload_dir = qgis_server_upload.process_and_upload_project()

            if status_code_server_upload == 200:
                wms_url = qgis_server_upload.get_wms_url(server_config, upload_dir)
            if not wms_url:
                return

            if action == "publish":
                self.mb_publish(server_config, api_request, wms_url)
            else:
                self.mb_update(server_config, api_request, wms_url)
        finally:
            # Restore default cursor
            QApplication.restoreOverrideCursor()
            if api_request is not None:
                api_request.mark_api_requests_done()


    def mb_publish(self, server_config: ServerConfig, api_request: ApiRequest, wms_url: str) -> None:
        """
        Publishes a WMS to Mapbender and assigns it to an application.

        This method performs the following steps:
        - Initializes a MapbenderApiUpload instance with server configuration and API request.
        - Uploads the WMS to Mapbender.
        - Clones an application if requested, or assigns the WMS to an existing application.
        - Handles success or failure scenarios with appropriate user feedback.

        Args:
            server_config (ServerConfig): The server configuration object.
            api_request (ApiRequest): The API request object.
            wms_url (str): The URL of the WMS to be published.

        Returns:
            None
        """
        # Parameters
        is_clone_app = self.cloneTemplateRadioButton.isChecked()
        layer_set = self.layerSetLineEdit.text()
        input_slug = self.mbSlugComboBox.currentText()

        try:
            mb_upload = MapbenderApiUpload(server_config, api_request, wms_url)
            exit_status_mb_upload, source_ids, is_reloaded = mb_upload.mb_upload()
            if exit_status_mb_upload != 0 or not source_ids:
                QgsMessageLog.logMessage(f"FAILED mb_upload", TAG, level=Qgis.MessageLevel.Info)
                return

            if is_clone_app:
                exit_status_app_clone, slug = mb_upload.clone_app_and_get_slug(input_slug)
                if exit_status_app_clone != 200:
                    show_fail_box_ok("Failed", f"WMS {wms_url}  was successfully created and uploaded to "
                                               f"Mapbender, but not assigned to an application. \n \nError by copying "
                                               f"the given application. Application {input_slug}' not found.")
                    update_mb_slug_in_settings(input_slug, is_mb_slug=False)
                    self.update_slug_combo_box()
                    return
                QgsMessageLog.logMessage(f"Application was cloned to {slug}", TAG,
                                         level=Qgis.MessageLevel.Info)

                update_mb_slug_in_settings(input_slug, is_mb_slug=True)
                self.update_slug_combo_box()
            else:
                slug = input_slug

            exit_status_wms_assign = mb_upload.assign_wms_to_source(slug, source_ids[0], layer_set)
            if exit_status_wms_assign != 200:
                return
            if is_reloaded:
                QgsMessageLog.logMessage(
                    f"WMS {wms_url} already existed as a Mapbender source(s) and was successfully reloaded (source(s) {source_ids}) and added to Mapbender application : {slug}", TAG,
                    level=Qgis.MessageLevel.Info)
                show_succes_box_ok(
                    "Success report",
                    f"WMS \n\n{wms_url}\n\nalready existed as a Mapbender source(s) and was successfully reloaded (source(s) {source_ids}) and added to Mapbender application:\n\n"
                    f"{slug}"
                )
            else:
                QgsMessageLog.logMessage(
                    f"WMS successfully created: {wms_url} and added to Mapbender application : {slug}", TAG,
                    level=Qgis.MessageLevel.Info)
                show_succes_box_ok(
                    "Success report",
                    f"WMS successfully created:\n\n{wms_url}\n\nAnd added to Mapbender application:\n\n"
                    f"{slug}"
                )
            #self.close()
        except Exception as e:
            show_fail_box_ok("Failed", f"An error occurred during Mapbender publish: {e}")
            QgsMessageLog.logMessage(f"Error in mb_publish: {e}", TAG, level=Qgis.MessageLevel.Critical)
        return

    @staticmethod
    def mb_update(server_config: ServerConfig, api_request: ApiRequest, wms_url: str)-> None:
        """
        Updates an existing WMS in Mapbender by reloading its source.

        This method performs the following steps:
        - Initializes a MapbenderApiUpload instance with server configuration and API request.
        - Attempts to reload the WMS source.
        - Handles success or failure scenarios with appropriate user feedback.

        Args:
            server_config (ServerConfig): The server configuration object.
            api_request (ApiRequest): The API request object.
            wms_url (str): The URL of the WMS to be updated.

        Returns:
            None
        """
        try:
            mb_reload = MapbenderApiUpload(server_config, api_request, wms_url)
            exit_status, source_ids = mb_reload.mb_reload()
            if exit_status != 0 or not source_ids:
                show_fail_box_ok("Failed", f"No source to update. WMS {wms_url} is not an existing source in Mapbender.")
                QgsMessageLog.logMessage(f"FAILED mb_update: No source to update. WMS {wms_url} is not an existing source in Mapbender.", TAG, level=Qgis.MessageLevel.Info)
                return
            else:
                source_ids_msg = ", ".join(map(str, source_ids))
                show_succes_box_ok(
                    "Success report",
                    f"WMS successfully updated in QGIS-Server : \n\n{wms_url}\n\n And successfully updated in Mapbender source(s): {source_ids_msg}"
                )
                #self.close()
        except Exception as e:
            show_fail_box_ok("Failed", f"An error occurred during Mapbender update: {e}")
            QgsMessageLog.logMessage(f"Error in mb_update: {e}", TAG, level=Qgis.MessageLevel.Critical)
        return