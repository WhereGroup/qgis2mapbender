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
from .qgis_server_postgresql_wms import get_postgresql_project_wms_url
from .mapbender_api_upload import MapbenderApiUpload
from .dialogs.server_config_dialog import ServerConfigDialog
from .helpers import get_qgis_project_storage_type, qgis_project_is_saved, \
    check_if_qgis_project_is_dirty_and_save, \
    show_fail_box, show_success_box, show_success_link_box, \
    list_qgs_settings_child_groups, show_question_box, \
    update_mb_slug_in_settings, is_postgresql_qgis_server_url
from .paths import Paths
from .server_config import ServerConfig
from .settings import (
    PLUGIN_SETTINGS_SERVER_CONFIG_KEY,
    PROJECT_STORAGE_UNSAVED,
    PROJECT_STORAGE_POSTGRESQL,
    PROJECT_STORAGE_LOCAL,
    TAG,
)

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
    projectStorageHintLabel: QLabel
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
        self.update_project_storage_hint()
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
        server_table_headers = [self.tr("Name"),
                                self.tr("Mapbender URL")]  # "QGIS Server path" ,
        self.serverTableWidget.setColumnCount(len(server_table_headers))
        self.serverTableWidget.setHorizontalHeaderLabels(server_table_headers)
        self.serverTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.update_server_table()

        # Buttons
        self.addServerConfigButton.setToolTip(self.tr("Add server configuration"))
        self.duplicateServerConfigButton.setToolTip(self.tr("Duplicate selected server configuration"))
        self.editServerConfigButton.setToolTip(self.tr("Edit selected server configuration"))
        self.removeServerConfigButton.setToolTip(self.tr("Remove selected server configuration"))
        self.buttonBoxTab2.rejected.connect(self.reject)

        # Set Button Tab2 to english
        button_close_tab2 = self.buttonBoxTab2.button(QDialogButtonBox.StandardButton.Close)
        button_close_tab2.setText(self.tr("Close"))

    def update_project_storage_hint(self) -> None:
        """Updates the upload hint for the currently open QGIS project."""
        project_storage_type = get_qgis_project_storage_type()
        hint_style = ""

        if project_storage_type == PROJECT_STORAGE_POSTGRESQL:
            hint = self.tr(
                "The QGIS project is stored in a database ({project_storage_type})."
            ).format(project_storage_type=project_storage_type)
        elif project_storage_type == PROJECT_STORAGE_LOCAL:
            hint = self.tr("The QGIS project is stored locally and will be uploaded to the server. If the QGIS project "
                           "already exists on the server, it will be overwritten")
        elif project_storage_type == PROJECT_STORAGE_UNSAVED:
            hint = self.tr(
                "The QGIS project has not been saved. Please save the project before publishing or updating.")
            hint_style = "color: red;"
        else:
            hint = self.tr(
                "The storage type of the current QGIS project ({project_storage_type}) is not supported."
            ).format(project_storage_type=project_storage_type)
            hint_style = "color: red;"
        self.projectStorageHintLabel.setText(hint)
        self.projectStorageHintLabel.setStyleSheet(hint_style)

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
        button_close_tab1 = self.buttonBoxTab1.button(QDialogButtonBox.StandardButton.Close)
        button_close_tab1.setText(self.tr("Close"))
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
        for i, name in enumerate(server_config_list):
            server_config = ServerConfig.getParamsFromSettings(name)
            item_name = QTableWidgetItem(server_config.name)
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
            self.serverComboBoxLabel.setText(self.tr("Please add a server"))
            self.serverConfigComboBox.clear()
            return

        # fetch the original names for each config
        original_names = []
        for key in server_config_list:
            config = ServerConfig.getParamsFromSettings(key)
            original_names.append(config.name)  # .name is original name

        # Update server configuration-combobox
        self.serverComboBoxLabel.setText(self.tr("Server"))
        self.warningFirstServerLabel.hide()
        self.serverConfigComboBox.clear()
        self.serverConfigComboBox.addItems(original_names)

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
        if show_question_box(self.tr(
                    "Are you sure you want to remove the server configuration '{selected_server_config}'?").format(
                    selected_server_config=selected_server_config)) != QMessageBox.StandardButton.Yes:
            return
        s = QSettings()
        clean_name = ServerConfig.clean_name_for_storage(selected_server_config)
        s.remove(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}")
        show_success_box(self.tr('Success'),
                         self.tr('Server configuration successfully removed'))
        self.update_server_table()
        self.update_server_combo_box()

    def initialize_api_request(self, server_config: Optional[ServerConfig] = None) -> tuple[ServerConfig, ApiRequest]:
        """
            Initializes and returns the server configuration and ApiRequest instance.

            Args:
                server_config: Optional server configuration. If omitted, the selected
                    configuration is loaded from QGIS settings.

            Returns:
                tuple[ServerConfig, ApiRequest]: The server configuration and API request objects.
        """
        selected_server_config = server_config
        if selected_server_config is None:
            selected_server_config = ServerConfig.getParamsFromSettings(self.serverConfigComboBox.currentText())
        api_request = ApiRequest(selected_server_config)
        return selected_server_config, api_request

    def validate_project_storage(self, project_storage_type: str) -> bool:
        """Validates that the current QGIS project storage is supported."""
        if project_storage_type not in PROJECT_STORAGE_LOCAL and project_storage_type not in PROJECT_STORAGE_POSTGRESQL:
            show_fail_box(
                self.tr("Unsupported QGIS project storage"),
                self.tr(
                    "The storage type  of the current QGIS project ({project_storage_type}) is not supported."
                ).format(project_storage_type=project_storage_type)
            )
            return False

        return True

    def validate_server_url_for_project_storage(
        self, project_storage_type: str, server_config: ServerConfig
    ) -> bool:
        """Validates that the server endpoint matches the project's storage type."""
        uses_postgresql_wrapper = is_postgresql_qgis_server_url(server_config.qgis_server_path)

        if project_storage_type == PROJECT_STORAGE_LOCAL and uses_postgresql_wrapper:
            show_fail_box(
                self.tr("Failed"),
                self.tr(
                    "The QGIS project is stored locally and requires a direct QGIS Server "
                    "base URL, for example /cgi-bin/qgis_mapserv.fcgi. The /qgis/ URL is "
                    "reserved for PostgreSQL projects."
                )
            )
            return False

        if project_storage_type == PROJECT_STORAGE_POSTGRESQL and not uses_postgresql_wrapper:
            show_fail_box(
                self.tr("Failed"),
                self.tr(
                    "The QGIS project is stored in PostgreSQL and requires a QGIS Server "
                    "base URL containing /qgis/."
                )
            )
            return False

        return True


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
            project_storage_type = get_qgis_project_storage_type()
            QgsMessageLog.logMessage(
                f"Evaluated QGIS project storage: {project_storage_type}",
                TAG,
                level=Qgis.MessageLevel.Info
            )
            if not self.validate_project_storage(project_storage_type):
                return
            server_config = ServerConfig.getParamsFromSettings(self.serverConfigComboBox.currentText())
            if not self.validate_server_url_for_project_storage(project_storage_type, server_config):
                return
            if action == "publish" and self.mbSlugComboBox.currentText() == '':
                show_fail_box(self.tr("Please complete Mapbender parameters"),
                              self.tr("Please enter a valid Mapbender URL title"))
                return
            server_config, api_request = self.initialize_api_request(server_config)
            if not api_request.token:
                return

            if project_storage_type == PROJECT_STORAGE_POSTGRESQL:
                QgsMessageLog.logMessage(
                    f"Upload skipped. No project upload needed. Project storage: {project_storage_type}",
                    TAG,
                    level=Qgis.MessageLevel.Info
                )
                wms_url = get_postgresql_project_wms_url(server_config)
            elif project_storage_type == PROJECT_STORAGE_LOCAL:
                QgsMessageLog.logMessage(
                    "Preparing upload to QGIS server...",
                    TAG,
                    level=Qgis.MessageLevel.Info
                )
                # Get server config: project paths
                paths = Paths.get_paths()
                qgis_server_upload = QgisServerApiUpload(api_request, paths)
                status_code_server_upload, upload_dir = qgis_server_upload.process_and_upload_project()

                if status_code_server_upload == 200 and upload_dir:
                    wms_url = qgis_server_upload.get_wms_url(server_config, upload_dir)
            else:
                return
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
                if exit_status_app_clone != 200 or not slug:
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

                name_source = ', '.join(f'#{i}' for i in source_ids if i)
                link = f"{server_config.mb_basis_url}/application/{slug}"
                show_success_link_box(
                    self.tr("Success report"),
                    self.tr("""
                        WMS already existed as a Mapbender source(s) and was successfully reloaded: {name}
                        <br><br>
                        Link to Capabilities:
                        <br><br>
                        <a href="{wms_url}" style="color:black;">{wms_url}</a>
                        <br><br>
                        Link to Mapbender application:
                        <br><br>
                        <a href="{link}" style="color:black;">{link}</a>
                    """).format(
                        name=name_source,
                        wms_url=wms_url,
                        link=link
                    )
                )
            else:
                QgsMessageLog.logMessage(
                    f"WMS successfully created: {wms_url} and added to Mapbender application : {slug}", TAG,
                    level=Qgis.MessageLevel.Info)

                link = f"{server_config.mb_basis_url}/application/{slug}"
                show_success_link_box(
                    self.tr("Success report"),
                    self.tr("""
                    WMS successfully created
                    <br><br>
                    Link to Capabilities:
                    <br><br>
                    <a href="{wms_url}" style="color:black;">{wms_url}</a>
                    <br><br>
                    Link to Mapbender application:
                    <br><br>
                    <a href="{link}" style="color:black;">{link}</a>
                    """).format(
                        wms_url=wms_url,
                        link=link
                    )
                )
            #self.close()
        except Exception as e:
            show_fail_box(self.tr("Failed"), f"An error occurred during Mapbender publish: {e}")
            QgsMessageLog.logMessage(f"Error in mb_publish: {e}", TAG, level=Qgis.MessageLevel.Critical)
        return


    def mb_update(self, server_config: ServerConfig, api_request: ApiRequest, wms_url: str)-> None:
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
                show_fail_box(self.tr("Failed"), f"No source to update. WMS {wms_url} is not an existing source in Mapbender.")
                QgsMessageLog.logMessage(f"FAILED mb_update: No source to update. WMS {wms_url} is not an existing source in Mapbender.", TAG, level=Qgis.MessageLevel.Info)
                return
            else:
                source_ids_msg = ", ".join(map(str, source_ids))
                QgsMessageLog.logMessage(
                    f"WMS successfully updated and successfully updated in Mapbender source(s): {source_ids_msg}!", TAG,
                    level=Qgis.MessageLevel.Info)
                name_source = ', '.join(f'#{i}' for i in source_ids if i)
                show_success_link_box(
                    self.tr("Success report"),
                    self.tr("""
                    WMS successfully updated in QGIS Server and successfully updated in Mapbender source(s): {name_source}
                    <br><br>
                    Link to Capabilities:
                    <br><br>
                    <a href="{wms_url}" style="color:black;">{wms_url}</a>
                    """).format(
                        name_source=name_source,
                        wms_url=wms_url
                    )
                )

        except Exception as e:
            show_fail_box(self.tr("Failed"), f"An error occurred during Mapbender update: {e}")
            QgsMessageLog.logMessage(f"Error in mb_update: {e}", TAG, level=Qgis.MessageLevel.Critical)
        return