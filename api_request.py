import requests
from typing import Optional
import re

from qgis._core import QgsMessageLog, Qgis

from .settings import TAG
from .helpers import handle_error


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
        # should this be as per server config: mapbender application path (first release) or it remains always server url/mapbender/api?
        self.api_url = f"{self.server_config.mb_protocol}{self.server_config.url}/mapbender/api"
        self.headers = {}
        self.token = None
        QgsMessageLog.logMessage("Initializing ApiRequest with server configuration.", TAG, level=Qgis.Info)
        # self.response_json = None
        # self.status_code_login = None
        self._initialize_authentication()

    def _initialize_authentication(self) -> None:
        """
        Authenticates and sets the token in the headers if successful.
        """
        try:
            self.token = self._authenticate()
            if self.token:
                self.headers["Authorization"] = f"Bearer {self.token}"
        except ValueError as e:
            handle_error(e, "Authentication error: Please check your credentials.")
        except ConnectionError as e:
            handle_error(e, "Connection error: Please check your network connection.")

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
        try:
            QgsMessageLog.logMessage(f"Sending authentication request to endpoint: {endpoint}", TAG, level=Qgis.Info)
            response = self._send_request(endpoint, "post", json=credentials)
            if response and response.status_code == 200:
                QgsMessageLog.logMessage("Authentication request successful.", TAG, level=Qgis.Info)
                return response.json().get("token")
            elif response and response.status_code == 404:
                QgsMessageLog.logMessage("Invalid URL during authentication.", TAG, level=Qgis.Warning)
                raise ValueError("Invalid URL. Please check the server configuration (URL is valid?).")
            else:
                QgsMessageLog.logMessage("Invalid credentials provided.", TAG, level=Qgis.Warning)
                raise ValueError("Invalid credentials. Please verify your username and password.")
        except requests.RequestException as e:
            QgsMessageLog.logMessage(f"Request exception during authentication: {e}", TAG, level=Qgis.Critical)
            raise ConnectionError(f"Error authenticating with the API: {e}")

    def _ensure_token(self) -> None:
        """
        Ensures that a valid token is available. If the token is missing or invalid, it re-authenticates.
        """
        if not self._token_is_available():
            self.token = self._authenticate()
            if self.token:
                self.headers["Authorization"] = f"Bearer {self.token}"
            else:
                raise ValueError("Failed to authenticate and obtain a valid token.")

    def _token_is_available(self) -> bool:
        """
        Checks if the token is available and valid.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        return self.token is not None

    def _send_request(self, endpoint: str, method: str, **kwargs) -> Optional[requests.Response]:
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
        QgsMessageLog.logMessage(f"DEBUGGING Sending request to URL: {url} with method: {method}", TAG, level=Qgis.Info)
        QgsMessageLog.logMessage(f"DEBUGGING Request kwargs: {kwargs}", TAG, level=Qgis.Info)

        try:
            response = self.session.request(method=method.upper(), url=url, headers= self.headers, **kwargs)
            QgsMessageLog.logMessage(f"DEBUGGING Response status code: {response.status_code}", TAG, level=Qgis.Info)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response
        except requests.HTTPError as http_err:
            QgsMessageLog.logMessage(f"DEBUGGING HTTP error: {http_err}", TAG, level=Qgis.Critical)
            handle_error(http_err, f"HTTP error occurred: {http_err}")
        except requests.RequestException as req_err:
            QgsMessageLog.logMessage(f"DEBUGGING Request exception: {req_err}", TAG, level=Qgis.Critical)
            handle_error(req_err, f"Request error occurred: {req_err}")
        return None

    def upload_zip(self, file_path: str) -> tuple[int, Optional[dict]]:
        """
        Uploads a ZIP file to the server and handles the response.
        The endpoint api/upload/zip uploads a ZIP file to the server and extracts its contents into the upload
        directory, which is configured using the 'api_upload_dir' parameter. Users must have the 'access api' and
        'upload files' permissions

        Args:
            file_path (str): Path to the ZIP file.

        Returns:
            tuple[int, Optional[dict]]: Status code and JSON response from the API.
        """

        endpoint = "/upload/zip"
        try:
            with open(file_path, "rb") as file:
                files = {"file": file}
                response = self._send_request(endpoint, "post", files=files)
                if response:
                    return response.status_code, response.json()
                return 500, {"error": "Failed to receive a valid response from the server."}
        except FileNotFoundError:
            return 400, {"error": f"File not found: {file_path}"}
        except requests.RequestException as e:  # generic error
            return 500, {"error": f"Error during the request: {e}"}

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
        #params = {"id": ''} # for tests
        self._ensure_token()

        response = self._send_request(endpoint, "get", params=params)
        if response:
            try:
                data = response.json()
                QgsMessageLog.logMessage(f"DEBUGGING wms/show response: {data}", TAG, level=Qgis.Info)
                return response.status_code, data
            except ValueError as e:
                QgsMessageLog.logMessage(f"Error while processing the response:  {e}", TAG, level=Qgis.Warning)
                return 500, None
        else:
            QgsMessageLog.logMessage("No valid response from API endpoint wms/show.", TAG, level=Qgis.Critical)
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
        response = self._send_request(endpoint, "get", params=params)
        if response:
            try:
                response_json = response.json()
                QgsMessageLog.logMessage(f"DEBUGGING Full API response as JSON: {response_json}", TAG, level=Qgis.Info)

                # extract id:
                message = response_json.get("message", "")
                match = re.search(r"#(\d+)", message)
                added_source_id = match.group(1) if match else None

                if added_source_id:
                    QgsMessageLog.logMessage(
                        f"DEBUGGING Response: status={response.status_code}, added_source_id={added_source_id}, error=None", TAG,
                        level=Qgis.Info)
                    return response.status_code, added_source_id, None
                else:
                    error_message = "Added source ID not readable from API-answer."
                    QgsMessageLog.logMessage(f"CRITICAL WMS could not be added to Mapbender. Reason: {error_message}",
                                             TAG, level=Qgis.Critical)
                    return response.status_code, None, error_message
            except ValueError as e:
                error_message = f"Response from the server cannot be processed. Details: {e}"
                QgsMessageLog.logMessage(f"CRITICAL WMS could not be added to Mapbender. Reason: {error_message}", TAG,
                                         level=Qgis.Critical)
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
        response = self._send_request(endpoint, "get", params=params)
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
        response = self._send_request(endpoint, "get", params=params)
        QgsMessageLog.logMessage(f"DEBUGGING WMS ASSIGN RESPONSE: {response}", TAG,
                                 level=Qgis.Critical)
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
            response = self._send_request(endpoint, "get", params=params)
            if response:
                try:
                    response_json = response.json()
                    return response.status_code, response_json, None
                except ValueError as e:
                    error_message = f"Fehler beim Parsen der Antwort: {e}"
                    QgsMessageLog.logMessage(error_message, TAG, level=Qgis.Critical)
                    return 500, None, error_message
            else:
                error_message = "Keine gültige Antwort vom Server erhalten."
                QgsMessageLog.logMessage(error_message, TAG, level=Qgis.Critical)
                return 500, None, error_message
        except requests.RequestException as e:
            error_message = f"Fehler bei der Anfrage: {e}"
            QgsMessageLog.logMessage(error_message, TAG, level=Qgis.Critical)
            return 500, None, error_message