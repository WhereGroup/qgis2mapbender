import requests
from typing import Optional
import re

from qgis.core import QgsMessageLog, Qgis

from .settings import TAG, MAPBENDER_API
from .helpers import error_logging_and_user_message, show_fail_box_ok


class ApiRequest:
    """
        Handles API requests, authentication, and interactions with the server.
    """

    def __init__(self, server_config):
        """
        Initializes the ApiRequest instance with server configuration.

        Args:
            server_config: Configuration object containing server details.
        """
        self.server_config = server_config
        self.session = requests.Session()
        self.api_url = f"{self.server_config.mb_protocol}{self.server_config.url}{MAPBENDER_API}"
        QgsMessageLog.logMessage(f"Configuring API requests to URL: {self.api_url}", TAG, level=Qgis.MessageLevel.Info)
        self.headers = {}
        self.token = None
        self._initialize_authentication()

    def _initialize_authentication(self) -> None:
        """
        Authenticates and sets the token in the headers if successful.
        """
        self.token = self._authenticate()
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"


    def _authenticate(self) -> Optional[str]:
        """
         Authenticates against the API to obtain an access token.

         Returns:
             Optional[str]: The authentication token, or None if authentication fails.
         """
        endpoint = "/login_check"
        credentials = {
            "username": self.server_config.username,
            "password": self.server_config.password
        }
        ERROR_MSG_404 = "Authentication failed: 404 invalid URL. Please check the server configuration (Is the URL valid?)"
        ERROR_MSG_401 = "Authentication failed: 401. Please check username and password"
        ERROR_MSG_OTHER = "Authentication failed. Please see logs under QGIS2Mapbender for more information."
        ERROR_MSG_TITLE = "Failed to obtain a valid token. Authentication failed"

        response = self._sendRequest(endpoint, "post", json=credentials)
        if response == None:
            show_fail_box_ok(ERROR_MSG_TITLE, ERROR_MSG_OTHER)
            return self.token
        if response.status_code:
            if response.status_code == 200:
                self.token = response.json().get("token")
            else:
                msg_str = ERROR_MSG_404 if response.status_code == 404 else ERROR_MSG_401 if response.status_code == 401 else ERROR_MSG_OTHER
                QgsMessageLog.logMessage(f"{ERROR_MSG_TITLE} with status code: {response.status_code}", TAG,
                                         level=Qgis.MessageLevel.Critical)
                show_fail_box_ok(ERROR_MSG_TITLE, msg_str)
        return self.token


    def _ensure_token(self) -> None:
        """
        Ensures that a valid token is available. If the token is missing or invalid, it re-authenticates.
        """
        if not self._token_is_available():
            self.token = self._authenticate()
            if self.token:
                self.headers["Authorization"] = f"Bearer {self.token}"

    def _token_is_available(self) -> bool:
        """
        Checks if the token is available and valid.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        return self.token is not None

    def _sendRequest(self, endpoint: str, method: str, **kwargs) -> Optional[requests.Response]:
        """
        Sends a request to the API with the specified method and parameters.

        Args:
            endpoint (str): The API endpoint (e.g., "/upload/zip").
            method (str): The HTTP method ("GET", "POST".).
            kwargs: Additional arguments for the request (json,etc.).

        Returns:
            Optional[requests.Response]: The response object, or None if an error occurs.
        """
        url = f"{self.api_url}{endpoint}"
        # if endpoint != "/login_check" and endpoint !="/upload/zip":
        if endpoint != "/login_check":
            QgsMessageLog.logMessage(f"Sending request to endpoint {endpoint} with kwargs: {kwargs}", TAG, level=Qgis.MessageLevel.Info)

        try:
            response = self.session.request(method=method.upper(), url=url, headers= self.headers, **kwargs)
            return response
        except requests.HTTPError as http_err:
            error_logging_and_user_message(http_err)
        except requests.RequestException as req_err:
            error_logging_and_user_message(req_err)
        return None

    def uploadZip(self, file_path: str) -> Optional[int]:
        """
        Uploads a ZIP file to the server and handles the response.
        The endpoint api/upload/zip uploads a ZIP file to the server and extracts its contents into the upload
        directory, which is configured using the 'api_upload_dir' parameter. Users must have the 'access api' and
        'upload files' permissions

        Args:
            file_path (str): Path to the ZIP file.

        Returns:
            Optional[int]: status code
        """

        endpoint = "/upload/zip"
        status_code = None
        ERROR_MSG_400 = ("Error 400 Invalid request: No file uploaded or wrong file type. Please check the variables "
                         "upload_max_filesize, post_max_size and max_file_uploads in the apache configuration")
        ERROR_MSG_403 = "Error 403: user has unsufficient rights."
        ERROR_MSG_500 = "Error 500, Server error: Failed to move or extract the file."

        try:
            with open(file_path, "rb") as file:
                files = {"file": file}
                response = self._sendRequest(endpoint, "post", files=files)
                status_code  = response.status_code
                if status_code == 200:
                    QgsMessageLog.logMessage("Zip file uploaded and extracted successfully.", TAG,
                                             level=Qgis.MessageLevel.Info)
                else:
                    msg_str = ERROR_MSG_400 if status_code == 400 else ERROR_MSG_500 if status_code == 500 else ERROR_MSG_403 if status_code == 403 else "Error: "+ str(
                        status_code)
                    QgsMessageLog.logMessage(msg_str, TAG, level=Qgis.MessageLevel.Critical)
                    show_fail_box_ok("Failed",
                        f"Upload to QGIS server failed. {msg_str}")
        except FileNotFoundError:
            QgsMessageLog.logMessage(f"File not found: {file_path}", TAG, level=Qgis.MessageLevel.Warning)
        return status_code


    def wms_show(self, wms_url: str) -> tuple[int, Optional[dict]]:
        """
        Displays a WMS layer using the provided WMS URL.

        Args:
            wms_url (str): The WMS URL to display.

        Returns:
            tuple[int, Optional[dict]]: Status code and JSON response from the API.
        """
        endpoint = "/wms/show"
        params = {"id": wms_url, "json": True}
        self._ensure_token()

        response = self._sendRequest(endpoint, "get", params=params)
        if response:
            try:
                data = response.json()
                return response.status_code, data
            except ValueError as e:
                QgsMessageLog.logMessage(f"Error while processing the response:  {e}", TAG, level=Qgis.MessageLevel.Warning)
                return 500, None
        else:
            QgsMessageLog.logMessage("No valid response from API endpoint wms/show.", TAG, level=Qgis.MessageLevel.Critical)
            return 500, None

    def wms_add(self, wms_url: str) -> tuple[int, Optional[dict]]:
        """
        Adds a WMS layer using the provided WMS URL.

        Args:
            wms_url (str): The WMS URL to add.

        Returns:
            tuple[int, Optional[dict]]: Status code and JSON response from the API.
        """
        endpoint = "/wms/add"
        params = {"serviceUrl": wms_url}

        self._ensure_token()
        response = self._sendRequest(endpoint, "get", params=params)
        if response:
            try:
                response_json = response.json()
                QgsMessageLog.logMessage(f"DEBUGGING Full API response as JSON: {response_json}", TAG, level=Qgis.MessageLevel.Info)

                # extract id:
                message = response_json.get("message", "")
                match = re.search(r"#(\d+)", message)
                added_source_id = match.group(1) if match else None

                if added_source_id:
                    QgsMessageLog.logMessage(
                        f"DEBUGGING Response: status={response.status_code}, added_source_id={added_source_id}, error=None", TAG,
                        level=Qgis.MessageLevel.Info)
                    return response.status_code, added_source_id, None
                else:
                    error_message = "Added source ID not readable from API-answer."
                    QgsMessageLog.logMessage(f"WMS could not be added to Mapbender. Reason: {error_message}",
                                             TAG, level=Qgis.MessageLevel.Critical)
                    return response.status_code, None, error_message
            except ValueError as e:
                error_message = f"Response from the server cannot be processed. Details: {e}"
                QgsMessageLog.logMessage(f"WMS could not be added to Mapbender. Reason: {error_message}", TAG,
                                         level=Qgis.MessageLevel.Critical)
                return 500, None, error_message
            else:
                return 500, None, "Failed to receive a valid response from the server."

    def wms_reload(self, source_id: str, wms_url: str) -> tuple[int, Optional[dict], Optional[str]]:
        """
        Reloads a WMS layer using the provided source ID and WMS URL.

        Args:
            source_id (str): The source ID of the WMS layer.
            wms_url (str): The WMS URL to reload.

        Returns:
            tuple[int, Optional[dict]]: Status code and JSON response from the API.
        """
        endpoint = "/wms/reload"
        params = {"id": source_id, "serviceUrl": wms_url}
        self._ensure_token()
        response = self._sendRequest(endpoint, "get", params=params)
        if response:
            try:
                return response.status_code, response.json(), None
            except ValueError as e:
                return 500, None, f"Error by parsing the response: {e}"
        return 500, None, {"error": "Failed to receive a valid response from the server."}

    def wms_assign(self, application: str, source: int, layer_set: Optional[str]) -> tuple[int, str, Optional[str]]:
        """
        Assigns a WMS layer using the provided source ID and layer ID.

        Args:
            application (str): The source ID of the WMS layer.
            source (str): The layer ID to assign.

        Returns:
            tuple[int, Optional[dict]]: Status code and JSON response from the API.
        """
        endpoint = "/wms/assign"
        params = {"application": application, "source": source}
        if layer_set:
            params["layerset"] = layer_set
        self._ensure_token()
        response = self._sendRequest(endpoint, "get", params=params)
        if response:
            return response.status_code, response.json(), None
        return 500, {"error": "Failed to receive a valid response from the server."}, None

    def app_clone(self, template_slug: str) -> tuple[int, Optional[dict], Optional[str]]:
        """
        Clones an application using the provided template slug.

        Args:
            template_slug (str): The slug of the template application to clone.

        Returns:
            tuple[int, Optional[dict]]: Status code and JSON response from the API.
        """
        endpoint = "/application/clone"
        params = {"slug": template_slug}
        self._ensure_token()
        try:
            response = self._sendRequest(endpoint, "get", params=params)
            if response:
                try:
                    response_json = response.json()
                    return response.status_code, response_json, None
                except ValueError as e:
                    error_message = f"Error parsing the response: {e}"
                    QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
                    return 500, None, error_message
            else:
                error_message = "No valid answer"
                QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
                return 500, None, error_message
        except requests.RequestException as e:
            error_message = f"Request error: {e}"
            QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
            return 500, None, error_message