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
    show_fail_box, show_success_box, show_success_link_box, \
    list_qgs_settings_child_groups, show_question_box, \
    update_mb_slug_in_settings
from .paths import Paths
from .server_config import ServerConfig
from .settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG

# Dialog from .ui file
WIDGET, BASE = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialogs/ui/main_dialog.ui'))


class MainDialog(BASE, WIDGET):
    """
        Main dialog window for the QGIS2Mapbender plugin.

        Handles user interactions for server configuration, project publishing, and updating Mapbender applications.
    """
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
        """
            Initializes the main dialog and sets up the UI and signal connections.

            Args:
                parent: Optional parent widget.
            """
        super().__init__(parent)
        self.setupUi(self)
        self.setupConnections()

    def setupUi(self, widget) -> None:
        """
            Sets up the user interface for the main dialog.

            Args:
                widget: The parent widget for the dialog.
            Returns:
                None
        """
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
                                "Mapbender URL"]  # "QGIS Servre path" ,
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
        """
            Connects UI signals to their respective slots for user interaction.

            Returns:
                None
        """
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
        """
            Updates the server configuration table with current settings.

            Returns:
                None
        """
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
        """
            Updates the server configuration dropdown menu

            Returns:
                None
        """
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
        """
            Updates the Mapbender slug combo box with available slugs from settings.

            Returns:
                None
        """
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
        """
            Disables the Mapbender parameters input fields and toggles button states for update mode.

            Returns:
                None
        """
        self.mbParamsFrame.setEnabled(False)
        self.updateButton.setEnabled(True)
        self.publishButton.setEnabled(False)

    def enable_publish_parameters(self) -> None:
        """
            Enables the Mapbender parameters input fields and toggles button states for publish mode.

            Returns:
                None
        """
        self.mbParamsFrame.setEnabled(True)
        self.updateButton.setEnabled(False)
        self.publishButton.setEnabled(True)

    def validate_slug_not_empty(self) -> None:
        """
            Enables the publish button only if the Mapbender slug field is not empty.

            Returns:
                None
        """
        self.publishButton.setEnabled(self.mbSlugComboBox.currentText() != '')

    def open_server_config_dialog(self, config_name: Optional[str] = None, mode: Optional[str] = None) -> None:
        """
            Opens the server configuration dialog for adding, editing, or duplicating a server config.

            Args:
                config_name (Optional[str]): The name of the server configuration to edit or duplicate.
                mode (Optional[str]): The mode for the dialog ('edit', 'duplicate', or None for new).

            Returns:
                None
        """
        new_server_config_dialog = ServerConfigDialog(server_config_name=config_name, mode=mode) #, parent=iface.mainWindow())
        new_server_config_dialog.exec()
        self.update_server_table()
        self.update_server_combo_box()

    def on_add_server_config_clicked(self) -> None:
        """
            Slot for adding a new server configuration.

            Returns:
                None
        """
        self.open_server_config_dialog()

    def get_selected_server_config(self) -> Optional[str]:
        """
            Returns the name of the currently selected server configuration in the table.

            Returns:
                Optional[str]: The selected server configuration name, or None if none is selected.
        """
        selected_row = self.serverTableWidget.currentRow()
        if selected_row == -1:
            return None
        return self.serverTableWidget.item(selected_row, 0).text()

    def on_duplicate_server_config_clicked(self) -> None:
        """
            Slot for duplicating the selected server configuration.

            Returns:
                None
        """
        selected_server_config = self.get_selected_server_config()
        self.open_server_config_dialog(selected_server_config, mode='duplicate')

    def on_edit_server_config_clicked(self) -> None:
        """
            Slot for editing the selected server configuration.

            Returns:
                None
        """
        selected_server_config = self.get_selected_server_config()
        self.open_server_config_dialog(selected_server_config, mode='edit')

    def on_remove_server_config_clicked(self) -> None:
        """
            Slot for removing the selected server configuration after user confirmation.

            Returns:
                None
        """
        selected_row = self.serverTableWidget.currentRow()
        if selected_row == -1:
            return
        selected_server_config = self.serverTableWidget.item(selected_row, 0).text()
        if show_question_box(
                f"Are you sure you want to remove the server configuration '{selected_server_config}'?") != QMessageBox.StandardButton.Yes:
            return
        s = QSettings()
        s.remove(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{selected_server_config}")
        show_success_box('Success', 'Server configuration successfully removed')
        self.update_server_table()
        self.update_server_combo_box()

    def initialize_api_request(self) -> tuple[ServerConfig, ApiRequest]:
        """
            Initializes and returns the server configuration and ApiRequest instance.

            Returns:
                tuple[ServerConfig, ApiRequest]: The server configuration and API request objects.
        """
        server_config = ServerConfig.getParamsFromSettings(self.serverConfigComboBox.currentText())
        api_request = ApiRequest(server_config)
        return server_config, api_request

    def run(self) -> None:
        """
            Executes the publishing or updating process for the current QGIS project.

            Handles project validation, API initialization, upload, and Mapbender operations.
            Provides user feedback and error handling.

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
                show_fail_box("Please complete Mapbender parameters",
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

                show_success_link_box(
                    "Success report",
                    f"""
                    WMS already existed as a Mapbender source(s) and was successfully reloaded: {', '.join(f'#{i}' for i in source_ids if i)}
                    <br><br>
                    Link to Capabilities:
                    <br><br>
                    <a href = "{wms_url}" style = "color: black; " > {wms_url} </a>
                    <br><br>
                    Link to Mapbender application:
                    <br><br>
                    <a href = "{server_config.mb_basis_url}/application/{slug}" style = "color: black; " > {server_config.mb_basis_url}/application/{slug}</a>
                    """
                )
            else:
                QgsMessageLog.logMessage(
                    f"WMS successfully created: {wms_url} and added to Mapbender application : {slug}", TAG,
                    level=Qgis.MessageLevel.Info)

                show_success_link_box(
                    "Success report",
                    f"""
                    WMS successfully created
                    <br><br>
                    Link to Capabilities:
                    <br><br>
                    <a href = "{wms_url}" style = "color: black; " > {wms_url} </a>
                    <br><br>
                    Link to Mapbender application:
                    <br><br>
                    <a href = "{server_config.mb_basis_url}/application/{slug}" style = "color: black; " > {server_config.mb_basis_url}/application/{slug}</a>
                    """
                )
            #self.close()
        except Exception as e:
            show_fail_box("Failed", f"An error occurred during Mapbender publish: {e}")
            QgsMessageLog.logMessage(f"Error in mb_publish: {e}", TAG, level=Qgis.MessageLevel.Critical)
        return

    @staticmethod
    def mb_update(server_config: ServerConfig, api_request: ApiRequest, wms_url: str)-> None:
        """
        Updates an existing WMS in Mapbender by reloading its source.

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
                show_fail_box("Failed", f"No source to update. WMS {wms_url} is not an existing source in Mapbender.")
                QgsMessageLog.logMessage(f"FAILED mb_update: No source to update. WMS {wms_url} is not an existing source in Mapbender.", TAG, level=Qgis.MessageLevel.Info)
                return
            else:
                source_ids_msg = ", ".join(map(str, source_ids))
                QgsMessageLog.logMessage(
                    f"WMS successfully updated and successfully updated in Mapbender source(s): {source_ids_msg}!", TAG,
                    level=Qgis.MessageLevel.Info)
                show_success_link_box(
                    "Success report",
                    f"""
                    WMS successfully updated in QGIS Server and successfully updated in Mapbender source(s): {', '.join(f'#{i}' for i in source_ids if i)}
                    <br><br>
                    Link to Capabilities:
                    <br><br>
                    <a href = "{wms_url}" style = "color: black; " > {wms_url} </a>
                    """
                )

        except Exception as e:
            show_fail_box("Failed", f"An error occurred during Mapbender update: {e}")
            QgsMessageLog.logMessage(f"Error in mb_update: {e}", TAG, level=Qgis.MessageLevel.Critical)
        return