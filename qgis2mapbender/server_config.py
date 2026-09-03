from dataclasses import dataclass
import re

from qgis.core import QgsSettings, QgsApplication, QgsAuthMethodConfig, QgsMessageLog, Qgis

from .settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG


@dataclass
class ServerConfig:
    """
        Stores the configuration for a QGIS Server and Mapbender connection.
    """
    name: str # original name, as entered by the user
    username: str
    password: str
    qgis_server_path: str
    mb_basis_url: str
    authcfg: str
    cleaned_name: str = ""

    @staticmethod
    def clean_name_for_storage(name: str) -> str:
        """
        Removes "/" and "\" from the name before saving.
        This ensures that the backend does not store problematic characters.
        """
        return re.sub(r'[\\/]', '', name)

    def save(self, encrypted: bool) -> None:
        """
            Saves the server configuration to QGIS settings.

            Args:
                encrypted (bool): If True, credentials are stored in the QGIS authentication database.
                                  If False, credentials are stored in plain text in the settings.

            Returns:
                None
        """
        s = QgsSettings()
        # Clean the name to remove "/" and "\" for storage purposes
        clean_name = ServerConfig.clean_name_for_storage(self.name)
        # Store the original name for UI/display purposes
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/original_name", self.name)
        if encrypted:
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/username", '')
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/password", '')
            authCfgId = ServerConfig.saveBasicToAuthDb(clean_name, self.username, self.password, self.authcfg)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/authcfg", authCfgId)
        else:
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/username", self.username)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/password", self.password)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/authcfg", '')

        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/qgis_server_path",
                   self.qgis_server_path)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/mb_basis_url", self.mb_basis_url)

    @staticmethod
    def saveBasicToAuthDb(server_name, username, password, authCfgId) -> str:
        """
             Saves the username and password securely in the QGIS authentication database.

             Args:
                 server_name (str): Name of the server or connection.
                 username (str): User's username.
                 password (str): User's password.
                 authCfgId (str): Existing authentication config ID.

             Returns:
                 str: The authentication config ID used or created.
         """
        auth_manager = QgsApplication.authManager()
        conf = QgsAuthMethodConfig()
        # if authCfgId already available on the stored keys, it will only be updated. Otherwise, it will be created!
        auth_manager.loadAuthenticationConfig(authCfgId, conf, True)
        conf.setMethod("Basic")
        conf.setName(server_name)
        conf.setConfig("username", username)
        conf.setConfig("password", password)

        # Register test_upload in authdb returning the ``authcfg`` of the stored configuration
        auth_manager.storeAuthenticationConfig(conf, overwrite=True)
        return conf.id()

    @staticmethod
    def getParamsFromSettings(name: str) -> 'ServerConfig':
        """
            Loads the server configuration from QGIS settings.

            Args:
                name (str): The name of the server configuration.

            Returns:
                ServerConfig: The loaded server configuration object.
        """
        s = QgsSettings()
        # Clean the name for storage retrieval
        clean_name = ServerConfig.clean_name_for_storage(name)
        original_name = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/original_name",
                                clean_name)
        username = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/username")
        password = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/password")
        qgis_server_path = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/qgis_server_path")
        mb_basis_url = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/mb_basis_url")
        authcfg = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{clean_name}/authcfg")
        if authcfg:
            username, password = ServerConfig.get_username_and_password_from_auth_db(authcfg)
        return ServerConfig(original_name, username, password, qgis_server_path,
                        mb_basis_url, authcfg)

    @staticmethod
    def get_username_and_password_from_auth_db(authcfg) -> tuple[str, str]:
        """
            Retrieves the username and password from the QGIS authentication database using the provided authcfg.

            Args:
                authcfg (str): The authentication configuration ID.

            Returns:
                tuple[str, str]: A tuple containing the username and password.
        """
        auth_manager = QgsApplication.authManager()
        conf = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(authcfg, conf, True)
        if conf.id():
            username = conf.config('username', '')
            password = conf.config('password', '')
            return username, password
        else:
            username = ''
            password = ''
            QgsMessageLog.logMessage("No config id...", TAG, level=Qgis.MessageLevel.Warning)
            return username, password
