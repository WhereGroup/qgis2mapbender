import os
from typing import Optional

import requests
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QRegularExpression, QSettings
from qgis.PyQt.QtGui import QIntValidator, QRegularExpressionValidator, QIcon
from qgis.PyQt.QtWidgets import QDialogButtonBox, QLineEdit, QRadioButton, QLabel, QComboBox, QPushButton
from qgis.gui import QgsFileWidget

from ..helpers import show_succes_box_ok, list_qgs_settings_child_groups, show_fail_box_ok, get_os, \
    uri_validator,  waitCursor
from ..server_config import ServerConfig
from ..settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG

from ..api_request import ApiRequest

# Dialog from .ui file
WIDGET, BASE = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/server_config_dialog.ui'))


class ServerConfigDialog(BASE, WIDGET):
    serverConfigNameLineEdit: QLineEdit
    serverAddressLineEdit: QLineEdit
    credentialsPlainTextRadioButton: QRadioButton
    credentialsAuthDbRadioButton: QRadioButton
    userNameLineEdit: QLineEdit
    passwordLineEdit: QLineEdit
    authLabel: QLabel
    protocolQgisServerCmbBox: QComboBox
    # serverConfigNameLabel1: QLabel
    qgisServerPathLineEdit: QLineEdit     # TODO: better to rename qgisServerUrlLineEdit
    qgisProjectPathLineEdit: QLineEdit
    protocolMapbenderCmbBox: QComboBox
    # serverConfigNameLabel2: QLabel
    mbBasisUrlLineEdit: QLineEdit
    mbPathLineEdit: QLineEdit
    winPKFileWidget: QgsFileWidget
    # buttons
    testButton: QPushButton
    dialogButtonBox: QDialogButtonBox

    def __init__(self, server_config_name: Optional[str] = None, mode: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.mandatoryFields = [
            self.serverConfigNameLineEdit,
            self.serverAddressLineEdit,
            self.qgisProjectPathLineEdit,
            self.qgisServerPathLineEdit,
            self.mbPathLineEdit,
            self.mbBasisUrlLineEdit,
        ]
        if get_os() == "Linux":
            self.winPKFileWidget.setEnabled(False)
        self.setupConnections()
        self.authcfg = ''
        self.selected_server_config_name = server_config_name
        self.mode = mode
        self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.testButton.setEnabled(False)
        if server_config_name:
            self.getSavedServerConfig(server_config_name, mode)
        if self.mode == 'edit':
            self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(True)
            self.testButton.setEnabled(True)

        self.serverConfigNameLineEdit.setToolTip('Custom server configuration name without blank spaces')
        self.qgisProjectPathLineEdit.setToolTip('Example: /data/qgis-projects/')
        self.qgisProjectPathLineEdit.setPlaceholderText('/data/qgis-projects/')
        self.qgisServerPathLineEdit.setToolTip('Example: [SERVER_NAME]/cgi-bin/qgis_mapserv.fcgi')
        self.mbPathLineEdit.setToolTip('Example: /data/mapbender/application/')
        self.mbPathLineEdit.setPlaceholderText('/mapbender/index_dev.php/')
        self.mbBasisUrlLineEdit.setToolTip('Example: [SERVER_NAME]/mapbender/index_dev.php/')
        self.winPKFileWidget.setToolTip('Example: C:/Users/user/Documents/ED25519-Key_private_key.ppk')

        # QLineEdit validators
        regex = QRegularExpression("[^\\s;]*")  # regex for blank spaces and semicolon
        regex_validator = QRegularExpressionValidator(regex)
        int_validator = QIntValidator()
        self.serverConfigNameLineEdit.setValidator(regex_validator)
        self.serverAddressLineEdit.setValidator(regex_validator)
        self.userNameLineEdit.setValidator(regex_validator)
        self.passwordLineEdit.setValidator(regex_validator)
        self.qgisProjectPathLineEdit.setValidator(regex_validator)
        self.qgisServerPathLineEdit.setValidator(regex_validator)
        self.mbPathLineEdit.setValidator(regex_validator)
        self.mbBasisUrlLineEdit.setValidator(regex_validator)
        self.checkedIcon = QIcon(":images/themes/default/mIconSuccess.svg")

    def setupConnections(self):
        self.dialogButtonBox.accepted.connect(self.saveServerConfig)
        self.dialogButtonBox.rejected.connect(self.reject)
        self.serverConfigNameLineEdit.textChanged.connect(self.validateFields)
        self.serverAddressLineEdit.textChanged.connect(self.onChangeServerName)
        self.credentialsPlainTextRadioButton.toggled.connect(self.onToggleCredential)
        self.qgisProjectPathLineEdit.textChanged.connect(self.validateFields)
        self.qgisServerPathLineEdit.textChanged.connect(self.validateFields)
        self.mbPathLineEdit.textChanged.connect(self.validateFields)
        self.mbBasisUrlLineEdit.textChanged.connect(self.validateFields)
        self.testButton.clicked.connect(self.execTests)

    def execTests(self) -> None:
        """
        Runs a series of tests (described in the method <execTestsImpl>). Displays a message if errors are found.
        """
        self.testButton.setIcon(QIcon())
        with waitCursor():
            errorMsg, successMsg  = self.execTestsImpl()

        if errorMsg:
            show_fail_box_ok(
                "Test Results",
                f"<b>Failed Tests:</b><ul>{''.join(f'<li>{test}</li>' for test in errorMsg.splitlines())}</ul>"
                f"<b>Successful Tests:</b><ul>{''.join(f'<li>{test}</li>' for test in successMsg.splitlines())}</ul>"
            )
        else:
            self.testButton.setIcon(self.checkedIcon)
            show_succes_box_ok(
                "Test Results",
                f"<b>All tests were successful:</b><ul>{''.join(f'<li>{test}</li>' for test in successMsg.splitlines())}</ul>"
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

        # Test 1: Server URL validation
        serverUrl = (f'{self.protocolQgisServerCmbBox.currentText()}'
                        f'{configFromForm.url}')
        if not uri_validator(serverUrl):
            failed_tests.append("The provided server URL is invalid.")
        else:
            successful_tests.append("The provided server URL is valid.")

        # Test 2: Token generation
        try:
            api_request = ApiRequest(configFromForm)
            if not api_request._token_is_available():
                failed_tests.append("Token generation failed. Please check your credentials.")
            else:
                successful_tests.extend(["Credentials are valid.","Token generation was successful."])
                # Test 3: ZIP upload
                test_zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/test_upload.zip'))
                status_code, response_upload = api_request.upload_zip(test_zip_path)
                if status_code != 200:
                    failed_tests.append(
                        f"Server upload is not validated (status code {status_code}): {response_upload.get('error')}.")
                else:
                    successful_tests.append("Server upload is validated.")
        except Exception as e:
            show_fail_box_ok("Error", f"An error occurred during API initialization: {str(e)}")

        # Test 4: QGIS server connection
        wmsServiceRequest = "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
        qgiServerUrl = (f'{self.protocolQgisServerCmbBox.currentText()}'
                        f'{configFromForm.qgis_server_path}'
                        f'{wmsServiceRequest}')
        errorStr = self.testHttpConn(qgiServerUrl, 'Qgis Server', configFromForm.qgis_server_path)
        if errorStr:
            failed_tests.append(errorStr)
        else:
            successful_tests.append("Connection to QGIS Server was successful.")

        # Test 5: Mapbender connection
        mapbenderUrl = (f'{configFromForm.mb_protocol}'
                        f'{configFromForm.mb_basis_url}')
        errorStr = self.testHttpConn(mapbenderUrl, 'Mapbender', configFromForm.mb_basis_url)
        if errorStr:
            failed_tests.append(errorStr)
        else:
            successful_tests.append("Connection to Mapbender was successful.")

        # if failed_tests:
        #     QgsMessageLog.logMessage(f"Fehlgeschlagene Tests:\n{chr(10).join(failed_tests)}", TAG, level=Qgis.Warning)
        # if successful_tests:
        #     QgsMessageLog.logMessage(f"Erfolgreiche Tests:\n{chr(10).join(successful_tests)}", TAG, level=Qgis.Info)

        return "\n".join(failed_tests) if failed_tests else None, "\n".join(
            successful_tests) if successful_tests else None

    def testHttpConn(self, url: str, serverName: str, lastPart: str) -> Optional[str]:
        # if not starts_with_single_slash_or_colon(lastPart):
        #     return f"Is the address {url} correct?"

        errorStr = f"Unable to connect to the {serverName} {url}. Is the address correct?"
        if not uri_validator(url):
            return f"The URL {url} seems not valid. Is the address correct?"

        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                return errorStr
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError) as error:
            return f"{errorStr}\n {str(error)}"

        return None

    def getSavedServerConfig(self, server_config_name: str, mode: str):
        server_config = ServerConfig.getParamsFromSettings(server_config_name)
        self.authcfg = server_config.authcfg
        if mode == 'edit':
            self.serverConfigNameLineEdit.setText(server_config_name)
        self.serverAddressLineEdit.setText(server_config.url)
        self.userNameLineEdit.setText(server_config.username)
        self.passwordLineEdit.setText(server_config.password)
        if server_config.authcfg:
            self.authLabel.setText(f'Authentication saved in database. Configuration: {server_config.authcfg}')
            self.credentialsAuthDbRadioButton.setChecked(True)
        else:
            self.authLabel.setText('')
            self.credentialsPlainTextRadioButton.setChecked(True)
        self.qgisProjectPathLineEdit.setText(server_config.projects_path)
        self.protocolQgisServerCmbBox.setCurrentText(server_config.qgis_server_protocol)
        self.qgisServerPathLineEdit.setText(server_config.qgis_server_path)
        self.mbPathLineEdit.setText(server_config.mb_app_path)
        self.protocolMapbenderCmbBox.setCurrentText(server_config.mb_protocol)
        self.mbBasisUrlLineEdit.setText(server_config.mb_basis_url)
        self.winPKFileWidget.lineEdit().setText(server_config.windows_pk_path)

    def getServerConfigFromFormular(self) -> ServerConfig:
        return ServerConfig(
            name=self.serverConfigNameLineEdit.text(),
            url=self.serverAddressLineEdit.text(),
            username=self.userNameLineEdit.text(),
            password=self.passwordLineEdit.text(),
            projects_path=self.qgisProjectPathLineEdit.text(),
            qgis_server_protocol=self.protocolQgisServerCmbBox.currentText(),
            qgis_server_path=self.qgisServerPathLineEdit.text(),
            mb_app_path=self.mbPathLineEdit.text(),
            mb_protocol=self.protocolMapbenderCmbBox.currentText(),
            mb_basis_url=self.mbBasisUrlLineEdit.text(),
            authcfg=self.authcfg,
            windows_pk_path=self.winPKFileWidget.lineEdit().text(),
        )

    def onChangeServerName(self, newValue) -> None:
        self.qgisServerPathLineEdit.setPlaceholderText(newValue + '/cgi-bin/qgis_mapserv.fcgi')
        self.mbBasisUrlLineEdit.setPlaceholderText(newValue + '/mapbender/index.php/')
        self.validateFields()

    def validateFields(self) -> None:
        self.dialogButtonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            all(field.text() for field in self.mandatoryFields))

        self.testButton.setEnabled(
            all(field.text() for field in self.mandatoryFields))

    def checkConfigName(self, config_name_from_formular) -> bool:
        saved_config_names = list_qgs_settings_child_groups(f'{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection')
        if self.mode == 'edit' and config_name_from_formular not in saved_config_names:
            s = QSettings()
            s.remove(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.selected_server_config_name}")
            return True
        if config_name_from_formular in saved_config_names and self.mode != 'edit':
            show_fail_box_ok('Failed', 'Server configuration name already exists')
            return False
        return True

    def saveServerConfig(self):
        serverConfigFromFormular = self.getServerConfigFromFormular()
        if not self.checkConfigName(serverConfigFromFormular.name):
            return
        if self.credentialsPlainTextRadioButton.isChecked():
            serverConfigFromFormular.save(encrypted=False)
        else:
            serverConfigFromFormular.save(encrypted=True)
        show_succes_box_ok('Success', 'Server configuration successfully saved')
        self.close()
        return

    def onToggleCredential(self, isChecked: bool):
        """QLabel <authLabel> is visible only if credentials are NOT saved as plain text"""
        self.authLabel.setVisible(not isChecked)