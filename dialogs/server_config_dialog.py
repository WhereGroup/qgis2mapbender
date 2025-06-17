import os
from typing import Optional

import requests
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QRegularExpression, QSettings
from qgis.PyQt.QtGui import QRegularExpressionValidator, QIcon
from qgis.PyQt.QtWidgets import QDialogButtonBox, QLineEdit, QRadioButton, QLabel, QPushButton
from qgis.core import QgsMessageLog, Qgis

from ..api_request import ApiRequest
from ..helpers import show_success_box, list_qgs_settings_child_groups, show_fail_box, uri_validator, waitCursor
from ..server_config import ServerConfig
from ..settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG

# Dialog from .ui file
WIDGET, BASE = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/server_config_dialog.ui'))


class ServerConfigDialog(BASE, WIDGET):
    """
        Dialog for creating, editing, and testing QGIS server and Mapbender server configurations.

        Allows users to input server URLs, credentials, and test connectivity and authentication.
    """
    serverConfigNameLineEdit: QLineEdit
    credentialsPlainTextRadioButton: QRadioButton
    credentialsAuthDbRadioButton: QRadioButton
    userNameLineEdit: QLineEdit
    passwordLineEdit: QLineEdit
    authLabel: QLabel
    qgisServerUrlLineEdit: QLineEdit
    mbBasisUrlLineEdit: QLineEdit
    testButton: QPushButton
    dialogButtonBox: QDialogButtonBox

    def __init__(self, server_config_name: Optional[str] = None, mode: Optional[str] = None, parent=None) -> None:
        """
            Initializes the server configuration dialog and sets up the UI.

            Args:
                server_config_name (Optional[str]): Name of the server config to edit or duplicate.
                mode (Optional[str]): Dialog mode ('edit', 'duplicate', or None for new).
                parent: Optional parent widget.
            Returns:
                None
        """
        super().__init__(parent)
        self.setupUi(self)
        self.mandatoryFields = [
            self.serverConfigNameLineEdit,
            self.qgisServerUrlLineEdit,
            self.mbBasisUrlLineEdit,
        ]
        self.setupConnections()
        self.authcfg = ''
        self.selected_server_config_name = server_config_name
        self.mode = mode
        self.credentialsPlainTextRadioButton.setChecked(True)
        self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.testButton.setEnabled(False)
        if server_config_name:
            self.getSavedServerConfig(server_config_name, mode)
        if self.mode == 'edit':
            self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(True)
            self.testButton.setEnabled(True)

        button_save = self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save)
        button_save.setText(self.tr('Save'))

        self.serverConfigNameLineEdit.setToolTip('Custom server configuration name without blank spaces')
        self.qgisServerUrlLineEdit.setToolTip('Example: [SERVER_NAME]/cgi-bin/qgis_mapserv.fcgi')
        self.mbBasisUrlLineEdit.setToolTip('Example: [SERVER_NAME]/mapbender/index_dev.php/')

        # QLineEdit validators
        regex = QRegularExpression("[^\\s;]*")  # regex for blank spaces and semicolon
        #regex_username = QRegularExpression("^(?!\\s)[^;/\\\\]*$")

        regex_validator = QRegularExpressionValidator(regex)
        #regex_username_validator = QRegularExpressionValidator(regex_username)
        self.serverConfigNameLineEdit.setValidator(regex_validator)
        self.userNameLineEdit.setValidator(regex_validator)
        self.passwordLineEdit.setValidator(regex_validator)
        self.qgisServerUrlLineEdit.setValidator(regex_validator)
        self.mbBasisUrlLineEdit.setValidator(regex_validator)
        self.checkedIcon = QIcon(":images/themes/default/mIconSuccess.svg")

    def setupConnections(self) -> None:
        """
            Connects UI signals to their respective slots for user interaction.

            Returns:
                None
        """
        self.dialogButtonBox.accepted.connect(self.saveServerConfig)
        self.dialogButtonBox.rejected.connect(self.reject)
        self.serverConfigNameLineEdit.textChanged.connect(self.validateFields)
        self.credentialsPlainTextRadioButton.toggled.connect(self.onToggleCredential)
        self.qgisServerUrlLineEdit.textChanged.connect(self.validateFields)
        self.mbBasisUrlLineEdit.textChanged.connect(self.validateFields)
        self.testButton.clicked.connect(self.execTests)

        button_cancel = self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Cancel)
        button_cancel.setText(self.tr('Cancel'))

    def execTests(self) -> None:
        """
            Runs a series of tests (described in the method <execTestsImpl>). Displays a message if errors are found.

            Returns:
                None
        """
        self.testButton.setIcon(QIcon())
        with waitCursor():
            errorMsg, successMsg  = self.execTestsImpl()

        if errorMsg and successMsg:
            errors = ''.join(f'<li>{test}</li>' for test in errorMsg.splitlines())
            successes = ''.join(f'<li>{test}</li>' for test in successMsg.splitlines())

            show_fail_box(
                self.tr("Test Results"),
                self.tr("<b>Failed Tests:</b><ul>{errors}</ul>"
                "<b>Successful Tests:</b><ul>{successes}</ul>").format(
                    errors=errors,
                    successes=successes
                )
            )
        elif errorMsg:
            errors = ''.join(f'<li>{test}</li>' for test in errorMsg.splitlines())

            show_fail_box(
                self.tr("Test Results"),
                self.tr("<b>Failed Tests:</b><ul>{errors}</ul>").format(
                    errors=errors
                )
            )

        elif successMsg:
            successes = ''.join(f'<li>{test}</li>' for test in successMsg.splitlines())

            self.testButton.setIcon(self.checkedIcon)
            show_success_box(
                self.tr("Test Results"),
                self.tr("<b>All tests were successful:</b><ul>{successes}</ul>").format(
                    successes=successes
                )
            )


    def execTestsImpl(self) -> tuple[Optional[str], Optional[str]]:
        """
            Runs a series of tests and returns a messages with:
            -  failed tests.
            -  successful tests.

            Returns:
                tuple: (Error message, Success message)
        """

        configFromForm = self.getServerConfigFromFormular()
        failed_tests = []
        successful_tests = []

        # Test 1: QGIS Servre-URL
        wmsServiceRequest = "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
        qgisServerUrl = (f'{configFromForm.qgis_server_path}{wmsServiceRequest}')
        errorStr = self.testHttpConn(qgisServerUrl, 'QGIS Servre')
        if errorStr:
            failed_tests.append(errorStr)
        else:
            successful_tests.append(self.tr("Connection to QGIS Servre was successful."))

        # Test 2: Mapbender-URL
        mapbenderUrl = configFromForm.mb_basis_url
        errorStr = self.testHttpConn(mapbenderUrl, 'Mapbender')
        if errorStr:
            failed_tests.append(errorStr)
        else:
            successful_tests.append(self.tr("Connection to Mapbender was successful."))

        # Test 3: Token generation
            try:
                api_request = ApiRequest(configFromForm)
                if not api_request._token_is_available():
                    failed_tests.append(self.tr("Token generation failed. Please check your credentials."))
                else:
                    successful_tests.extend([self.tr("Credentials are valid.","Token generation was successful.")])
                    # Test 4: ZIP upload
                    test_zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../resources/test_upload/test_upload.zip'))
                    status_code, upload_dir, error_zip_upload = api_request.uploadZip(test_zip_path)
                    if status_code != 200:
                        failed_tests.append(
                            self.tr("Server upload is not validated (status code {status_code}: {error_zip_upload}).").format(
                            status_code=status_code,
                            error_zip_upload=error_zip_upload
                        ))
                    else:
                        successful_tests.append(self.tr("Server upload is validated. Upload directory on server: {upload_dir}.").format(
                            upload_dir=upload_dir
                        ))
            except Exception as e:
                show_fail_box(self.tr("Error"), self.tr("An error occurred during API initialization: {e}.\nAPI tests "
                                          "(token generation, upload to server, etc.) could not be executed").format(
                    e=str(e)
                ))

        return "\n".join(failed_tests) if failed_tests else None, "\n".join(
            successful_tests) if successful_tests else None

    def testHttpConn(self, url: str, serverName: str) -> Optional[str]:
        """
            Tests HTTP connectivity to a given server URL.

            Args:
                url (str): The URL to test.
                serverName (str): The name of the server (for error messages).

            Returns:
                Optional[str]: Error message if connection fails, otherwise None.
        """
        errorStr = (self.tr("Unable to connect to the {serverName}. Is the address correct and is the schema supplied (http)? "
                    "Please see QGIS2Mapbender logs for more information.")).format(
            serverName=serverName
        )
        if not uri_validator(url):
            return errorStr
        try:
            resp = requests.get(url)
            if serverName != "Mapbender":
                if resp.status_code != 200:
                    content_type = resp.headers.get('Content-Type', '')
                    if 'text/xml' not in content_type:
                        return errorStr
            else:
                if resp.status_code != 200:
                    return errorStr
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError) as error:
            QgsMessageLog.logMessage(f"Connection error: {error}", TAG, level=Qgis.MessageLevel.Critical)
            return f"{errorStr}"

        return None

    def getSavedServerConfig(self, server_config_name: str, mode: str) -> None:
        """
            Loads a saved server configuration and populates the dialog fields.

            Args:
                server_config_name (str): The name of the saved configuration.
                mode (str): The dialog mode ('edit' or 'duplicate').
            Returns:
                None
        """
        server_config = ServerConfig.getParamsFromSettings(server_config_name)
        self.authcfg = server_config.authcfg
        if mode == 'edit':
            self.serverConfigNameLineEdit.setText(server_config_name)
        self.userNameLineEdit.setText(server_config.username)
        self.passwordLineEdit.setText(server_config.password)
        if server_config.authcfg:
            self.authLabel.setText(f'Authentication saved in database. Configuration: {server_config.authcfg}')
            self.credentialsAuthDbRadioButton.setChecked(True)
        else:
            self.authLabel.setText('')
            self.credentialsPlainTextRadioButton.setChecked(True)
        self.qgisServerUrlLineEdit.setText(server_config.qgis_server_path)
        self.mbBasisUrlLineEdit.setText(server_config.mb_basis_url)

    def getServerConfigFromFormular(self) -> ServerConfig:
        """
            Collects the current form values and returns a ServerConfig object.

            Returns:
                ServerConfig: The server configuration from the form.
        """
        return ServerConfig(
            name=self.serverConfigNameLineEdit.text(),
            username=self.userNameLineEdit.text(),
            password=self.passwordLineEdit.text(),
            qgis_server_path=self.qgisServerUrlLineEdit.text(),
            mb_basis_url=self.mbBasisUrlLineEdit.text(),
            authcfg=self.authcfg,
        )

    def onChangeServerName(self, newValue) -> None:
        """
            Updates placeholder texts for server URL fields based on the server name.

            Args:
                newValue: The new server name.

            Returns:
                None
        """
        self.qgisServerUrlLineEdit.setPlaceholderText(newValue + '/cgi-bin/qgis_mapserv.fcgi')
        self.mbBasisUrlLineEdit.setPlaceholderText(newValue + '/mapbender/index.php/')
        self.validateFields()

    def validateFields(self) -> None:
        """
            Enables or disables the Save and Test buttons based on mandatory field completion.

            Returns:
                None
        """
        self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            all(field.text() for field in self.mandatoryFields))

        self.testButton.setEnabled(
            all(field.text() for field in self.mandatoryFields))

    def checkConfigName(self, config_name_from_formular) -> bool:
        """
        Checks if the server configuration name is unique or valid for editing.

        Args:
            config_name_from_formular: The configuration name from the form.

        Returns:
            bool: True if the name is valid, False otherwise.
        """
        saved_config_names = list_qgs_settings_child_groups(f'{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection')
        if self.mode == 'edit' and config_name_from_formular not in saved_config_names:
            s = QSettings()
            s.remove(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.selected_server_config_name}")
            return True
        if config_name_from_formular in saved_config_names and self.mode != 'edit':
            show_fail_box('Failed', 'Server configuration name already exists')
            return False
        return True

    def saveServerConfig(self) -> None:
        """
            Saves the current server configuration, either encrypted or plain text, and closes the dialog.

            Returns:
                None
        """
        serverConfigFromFormular = self.getServerConfigFromFormular()
        if not self.checkConfigName(serverConfigFromFormular.name):
            return
        if self.credentialsPlainTextRadioButton.isChecked():
            serverConfigFromFormular.save(encrypted=False)
        else:
            serverConfigFromFormular.save(encrypted=True)
        show_success_box('Success', 'Server configuration successfully saved')
        self.close()
        return

    def onToggleCredential(self, isChecked: bool) -> None:
        """
             Shows or hides the authentication label depending on credential storage mode.

             Args:
                 isChecked (bool): True if plain text credentials are selected.
            Returns:
                None
         """
        self.authLabel.setVisible(not isChecked)