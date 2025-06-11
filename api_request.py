import requests
from typing import Optional, Tuple
import re

from qgis.core import QgsMessageLog, Qgis

from .settings import TAG
from .helpers import show_fail_box


class ApiRequest:
    """
    Handles API requests, authentication, and server interactions for the QGIS2Mapbender plugin.
    """

    def __init__(self, server_config):
        """
        Initializes the ApiRequest instance with server configuration.

        Args:
            server_config: Configuration object containing server details (URLs, credentials, etc.).
        """
        self.server_config = server_config
        self.session = requests.Session()
        if self.server_config.mb_basis_url.endswith("/"):
            self.server_config.mb_basis_url = self.server_config.mb_basis_url.rstrip("/")
        self.api_url = f"{self.server_config.mb_basis_url}/api"
        QgsMessageLog.logMessage(f"Configuring API requests to URL: {self.api_url}", TAG, level=Qgis.MessageLevel.Info)
        self.headers = {}
        self.token = None
        self._initialize_authentication()

    def _initialize_authentication(self) -> None:
        """
            Authenticates and sets the token in the request headers if successful.

            Returns:
                None
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
        ERROR_MSG_OTHER = "Authentication failed. Please see logs under QGIS2Mapbender for more information."
        ERROR_MSG_TITLE = "Failed to obtain a valid token. Authentication failed"

        response = self._sendRequest(endpoint, "post", json=credentials)
        if response == None:
            show_fail_box(ERROR_MSG_TITLE, ERROR_MSG_OTHER)
            return self.token
        if response.status_code:
            if response.status_code == 200:
                self.token = response.json().get("token")
            else:
                try:
                    response_json = response.json()
                    error_message = response_json.get("error", "Unknown error")
                    QgsMessageLog.logMessage(f"{ERROR_MSG_TITLE}: {error_message}", TAG, level=Qgis.MessageLevel.Critical)
                    show_fail_box(ERROR_MSG_TITLE, error_message)
                except ValueError as e:
                    QgsMessageLog.logMessage(f"Error parsing the response from endpoint {endpoint}: {e}", TAG, level=Qgis.MessageLevel.Critical)
                    show_fail_box(ERROR_MSG_TITLE, ERROR_MSG_OTHER)
                    return None
        return self.token

    def _ensure_token(self) -> None:
        """
            Ensures that a valid token is available. If the token is missing or invalid, it re-authenticates.

            Returns:
                None
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
        Sends an HTTP request to the API with the specified method and parameters.

        Args:
            endpoint (str): The API endpoint (e.g., "/upload/zip").
            method (str): The HTTP method ("GET", "POST".).
            **kwargs: Additional arguments for the request (json,etc.).

        Returns:
            Optional[requests.Response]: The response object, or None if an error occurs.
        """
        url = f"{self.api_url}{endpoint}"

        if endpoint != "/login_check" and endpoint != "/upload/zip":
            QgsMessageLog.logMessage(f"Sending request to endpoint {endpoint} with kwargs: {kwargs}", TAG, level=Qgis.MessageLevel.Info)
        try:
            response = self.session.request(method=method.upper(), url=url, headers= self.headers, **kwargs)
            return response
        except requests.HTTPError as http_err:
            QgsMessageLog.logMessage(str(http_err), TAG, level=Qgis.MessageLevel.Critical)
        except requests.RequestException as req_err:
            QgsMessageLog.logMessage(str(req_err), TAG, level=Qgis.MessageLevel.Critical)
        return None

    def uploadZip(self, file_path: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Uploads a ZIP file to the server and handles the response.

        Args:
            file_path (str): Path to the ZIP file.

        Returns:
            Tuple[Optional[int], Optional[str], Optional[str]]:
                - status code
                - upload directory on the server (if successful)
                - error message (if any)
        """

        endpoint = "/upload/zip"
        status_code = None
        upload_dir = None
        error_upload_zip = None
        self._ensure_token()

        try:
            with open(file_path, "rb") as file:
                files = {
                    "file": (file_path, file, "application/zip")}
                file_log = file.name if hasattr(file, "name") else str(file)
                QgsMessageLog.logMessage(
                    f"Sending request to endpoint {endpoint} with file: {file_log}", TAG, level=Qgis.MessageLevel.Info)
                response = self._sendRequest(endpoint, "post", files=files)
                try:
                    response_json = response.json()
                    status_code = response.status_code
                    if status_code == 200:
                        upload_dir = response.json().get("upload_dir", None)
                        QgsMessageLog.logMessage(f"Server response {status_code}: Zip file uploaded and extracted "
                                                 f"successfully in upload_dir {upload_dir}.", TAG,
                                                 level=Qgis.MessageLevel.Info)
                    else:
                        error_upload_zip = response_json.get('error', None)
                        QgsMessageLog.logMessage(f"Error: {status_code}:  {error_upload_zip}", TAG,
                                                 level=Qgis.MessageLevel.Critical)
                        show_fail_box("Failed",
                                         f"Upload to QGIS server failed. \n\nError {status_code}: {error_upload_zip}")
                except ValueError as e:
                    QgsMessageLog.logMessage(f"Error while processing the response from endpoint upload/zip:  {e}", TAG,
                                             level=Qgis.MessageLevel.Critical)
        except FileNotFoundError:
            QgsMessageLog.logMessage(f"Zip file with qgis project created but not found: {file_path}", TAG, level=Qgis.MessageLevel.Critical)
        return status_code, upload_dir, error_upload_zip


    def wms_show(self, wms_url: str) -> tuple[int, Optional[list]]:
        """
        Queries the API to check if a WMS source exists in Mapbender.

        Args:
            wms_url (str): The WMS URL to display.

        Returns:
            Tuple[int, Optional[list]]:
                - status code
                - list of source IDs if found, else None
        """
        endpoint = "/wms/show"
        params = {"id": wms_url, "json": True}
        self._ensure_token()

        response = self._sendRequest(endpoint, "get", params=params)
        try:
            response_json = response.json()
            if response.status_code == 200:
                source_ids = [item['id'] for item in response_json.get('message', []) if isinstance(item, dict) and 'id' in item]
                if source_ids:
                    QgsMessageLog.logMessage(f"WMS is already a source(s) in Mapbender with ID(s): {source_ids}", TAG,
                                         level=Qgis.MessageLevel.Info)
                else:
                    QgsMessageLog.logMessage(f"WMS does not exist as a source in Mapbender yet.", TAG,
                                         level=Qgis.MessageLevel.Info)
                return response.status_code, source_ids, None
            else:
                error = response_json.get('error', None)
                QgsMessageLog.logMessage(f"Error: {error}", TAG,
                                         level=Qgis.MessageLevel.Warning)
                return response.status_code, None, error
        except ValueError as e:
            QgsMessageLog.logMessage(f"Error while processing the response from endpoint wms/show:  {e}", TAG, level=Qgis.MessageLevel.Warning)
            return response.status_code, None, None


    def wms_add(self, wms_url: str) -> Tuple[int, Optional[str], Optional[str]]:
        """
        Adds a WMS layer using the provided WMS URL.

        Args:
            wms_url (str): The WMS URL to add.

        Returns:
            Tuple[int, Optional[str], Optional[str]]:
                - status code
                - ID of the added source (if successful)
                - error message (if any)
        """
        endpoint = "/wms/add"
        params = {"serviceUrl": wms_url}
        self._ensure_token()
        error_wms_add = None
        added_source_id = None

        response = self._sendRequest(endpoint, "get", params=params)
        status_code = response.status_code

        if status_code == 200:
            response_json = response.json()
            match = re.search(r"#(\d+)", response_json.get("message", ""))
            if match:
                added_source_id = match.group(1)
                QgsMessageLog.logMessage(f"New source added with ID: {added_source_id}", TAG,
                                         level=Qgis.MessageLevel.Info)
            else:
                QgsMessageLog.logMessage(f"Status code: {status_code}. But added source ID not readable from API-answer."
                                         f" Full API response as JSON: {response_json}")
        else:
            try:
                error_wms_add = response.json().get("error", "Unknown error")
                QgsMessageLog.logMessage(f"WMS could not be added to Mapbender. Reason: {error_wms_add}", TAG,
                                         level=Qgis.MessageLevel.Critical)

            except ValueError as e:
                QgsMessageLog.logMessage(f"WMS could not be added to Mapbender. Reason: Error parsing the response: {e}", TAG,
                                         level=Qgis.MessageLevel.Critical)
        return status_code, added_source_id, error_wms_add

    def wms_reload(self, source_id: str, wms_url: str) -> tuple[int, Optional[dict]]:
        """
         Reload a WMS source in Mapbender.

        Args:
            source_id (str): The source ID of the WMS layer.
            wms_url (str): The WMS URL to reload.

        Returns:
            Tuple[int, Optional[dict]]:
                - status code
                - JSON response from the API (if successful)
        """
        endpoint = "/wms/reload"
        params = {"id": source_id, "serviceUrl": wms_url}
        self._ensure_token()

        response = self._sendRequest(endpoint, "get", params=params)
        try:
            response_json= response.json()
            return response.status_code, response_json
        except ValueError as e:
            return response.status_code, None

    def wms_assign(self, application: str, source: int, layer_set: Optional[str]) -> str:
        """
        Assigns a WMS source to a Mapbender application.

        Args:
            application (str): The slug of the application to assign the WMS source to.
            source (int): The ID of the WMS source.
            layer_set (Optional[str]): Optional layerset to assign.

        Returns:
            str: The API response.
        """
        endpoint = "/wms/assign"
        format = "image/png"
        infoformat = "text/html"
        layerorder = "reverse"
        params = {"application": application, "source": source, "format": format , "infoformat": infoformat, "layerorder": layerorder}
        if layer_set:
            params["layerset"] = layer_set
        self._ensure_token()

        response = self._sendRequest(endpoint, "get", params=params)
        return response


    def app_clone(self, template_slug: str) -> tuple[int, Optional[dict]]:
        """
        Clones a Mapbender application using the provided template slug.

        Args:
            template_slug (str): The slug of the template application to clone.

        Returns:
            Tuple[int, Optional[dict]]:
                - status code
                - JSON response from the API (if successful)
        """
        endpoint = "/application/clone"
        params = {"slug": template_slug}
        self._ensure_token()

        response = self._sendRequest(endpoint, "get", params=params)
        status_code = response.status_code
        if status_code == 200:
            try:
                response_json = response.json()
                return response.status_code, response_json
            except ValueError as e:
                error_message = f"Error parsing the response: {e}"
                QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
                return response.status_code, None
        else:
            error_message = f"Failed to clone application. Status code: {status_code}"
            QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
            return status_code, None

    def mark_api_requests_done(self) -> None:
        """
            Marks API requests as done and close the session.

            Returns:
                None
        """
        self._api_requests_done = True
        self.close()

    def close(self) -> None:
        """
            Closes the requests session to free up resources.

            Returns:
                None
        """
        if self.session is not None:
            self.session.close()
            self.session = None
            QgsMessageLog.logMessage("API session closed.", TAG, level=Qgis.MessageLevel.Info)
        else:
            QgsMessageLog.logMessage("API session already closed.", TAG, level=Qgis.MessageLevel.Info)

    def __del__(self) -> None:
        """
            Destructor: Ensure the requests session is closed when the object is deleted.

            Returns:
                None
        """
        if self.session is not None:
            self.session.close()
            QgsMessageLog.logMessage("API session closed in __del__.", TAG, level=Qgis.MessageLevel.Info)