from dataclasses import dataclass

from qgis.core import QgsSettings, QgsApplication, QgsAuthMethodConfig, QgsMessageLog, Qgis

from .settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG


@dataclass
class ServerConfig:
    name: str
    url: str
    username: str
    password: str
    projects_path: str
    qgis_server_protocol: str
    qgis_server_path: str
    mb_app_path: str
    mb_protocol: str
    mb_basis_url: str
    authcfg: str
    windows_pk_path: str
    bin_console_command: str


    def save(self, encrypted: bool):
        s = QgsSettings()
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/url", self.url)
        if encrypted:
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/username", '')
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/password", '')
            authCfgId = ServerConfig.saveBasicToAuthDb(self.name, self.username, self.password, self.authcfg)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/authcfg", authCfgId)
        else:
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/username", self.username)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/password", self.password)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/authcfg", '')

        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/projects_path", self.projects_path)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/qgis_server_protocol",
                   self.qgis_server_protocol)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/qgis_server_path",
                   self.qgis_server_path)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/mb_app_path", self.mb_app_path)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/mb_protocol", self.mb_protocol)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/mb_basis_url", self.mb_basis_url)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/windows_pk_path", self.windows_pk_path)
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{self.name}/bin_console_command",
                   self.bin_console_command)

    @staticmethod
    def saveBasicToAuthDb(server_name, username, password, authCfgId):
        """
        Saves the password securely in the qgis-auth.db file.

        Args:
            server_name (str): Name of the server or connection.
            username (str): User's username.
            password (str): User's password.
            authCfgId (str): existing auth config ID saved in settings.
        """
        auth_manager = QgsApplication.authManager()
        conf = QgsAuthMethodConfig()
        # if authCfgId already available on the stored keys, it will only be updated. Otherwise, it will be created!
        auth_manager.loadAuthenticationConfig(authCfgId, conf, True)
        conf.setMethod("Basic")
        conf.setName(server_name)
        conf.setConfig("username", username)
        conf.setConfig("password", password)

        # Register data in authdb returning the ``authcfg`` of the stored configuration
        auth_manager.storeAuthenticationConfig(conf, overwrite=True)
        return conf.id()

    @staticmethod
    def getParamsFromSettings(name: str):
        s = QgsSettings()
        url = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/url")
        projects_path = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/projects_path")
        username = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/username")
        password = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/password")
        qgis_server_path = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/qgis_server_path")
        qgis_server_protocol = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/qgis_server_protocol")
        mb_app_path = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/mb_app_path")
        mb_protocol = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/mb_protocol")
        mb_basis_url = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/mb_basis_url")
        authcfg = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/authcfg")
        windows_pk_path = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/windows_pk_path")
        bin_console_command = s.value(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/connection/{name}/bin_console_command")
        if authcfg:
            username, password = ServerConfig.get_username_and_password_from_auth_db(authcfg)

        return ServerConfig(name, url, username, password, projects_path, qgis_server_protocol, qgis_server_path,
                            mb_app_path, mb_protocol, mb_basis_url, authcfg, windows_pk_path, bin_console_command)

    @staticmethod
    def get_username_and_password_from_auth_db(authcfg):
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
