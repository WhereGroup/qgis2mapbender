import requests
from typing import Optional, Tuple
import re
from html import unescape

from qgis.core import QgsMessageLog, Qgis

from .settings import TAG, REQUEST_TIMEOUT_API, MAX_API_ERROR_MESSAGE_LENGTH
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

        response_json = self._parse_json_response(response, endpoint)
        if response.status_code != 200 or response_json is None:
            error_message = self._response_error_message(response, response_json)
            QgsMessageLog.logMessage(f"{ERROR_MSG_TITLE}: {error_message}", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box(ERROR_MSG_TITLE, error_message)
            return None

        self.token = response_json.get("token")
        if not self.token:
            error_message = self._response_error_message(
                response,
                response_json,
                "The server response did not contain an authentication token."
            )
            QgsMessageLog.logMessage(f"{ERROR_MSG_TITLE}: {error_message}", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box(ERROR_MSG_TITLE, error_message)
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
            response = self.session.request(method=method.upper(), url=url, headers= self.headers, timeout=REQUEST_TIMEOUT_API, **kwargs)
            return response
        except requests.exceptions.HTTPError as http_err:
            QgsMessageLog.logMessage(str(http_err), TAG, level=Qgis.MessageLevel.Critical)
        except requests.exceptions.Timeout as timeout_err:
            QgsMessageLog.logMessage(str(timeout_err), TAG, level=Qgis.MessageLevel.Critical)
        except requests.exceptions.RequestException as req_err:
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
                if response is None:
                    error_upload_zip = "No response received from server."
                    QgsMessageLog.logMessage(
                        f"Upload to QGIS server failed: {error_upload_zip}",
                        TAG,
                        level=Qgis.MessageLevel.Critical
                    )
                    show_fail_box(
                        "Upload failed",
                        "Upload to QGIS Server failed.\n\n"
                        f"{error_upload_zip}\n\n"
                        "See the QGIS2Mapbender log for details."
                    )
                    return status_code, upload_dir, error_upload_zip

                status_code = response.status_code
                response_json = self._parse_json_response(response, endpoint)
                if status_code != 200 or response_json is None:
                    error_upload_zip = self._response_error_message(response, response_json)
                else:
                    upload_dir = response_json.get("upload_dir")
                    if not upload_dir:
                        error_upload_zip = self._response_error_message(
                            response,
                            response_json,
                            "The server response did not contain an upload directory."
                        )

                if error_upload_zip:
                    if status_code == 200 and response_json is not None:
                        self._log_response_summary(endpoint, response, error_upload_zip)
                    QgsMessageLog.logMessage(
                        f"Upload to QGIS server failed. HTTP {status_code}: {error_upload_zip}",
                        TAG,
                        level=Qgis.MessageLevel.Critical
                    )
                    show_fail_box(
                        "Upload failed",
                        f"Upload to QGIS Server failed (HTTP {status_code}).\n\n"
                        f"{error_upload_zip}\n\n"
                        "See the QGIS2Mapbender log for technical details."
                    )
                else:
                    QgsMessageLog.logMessage(
                        f"Server response {status_code}: Zip file uploaded and extracted "
                        f"successfully in upload_dir {upload_dir}.",
                        TAG,
                        level=Qgis.MessageLevel.Info
                    )
        except FileNotFoundError:
            QgsMessageLog.logMessage(f"Zip file with qgis project created but not found: {file_path}", TAG, level=Qgis.MessageLevel.Critical)
        return status_code, upload_dir, error_upload_zip


    @staticmethod
    def _response_error_message(response: requests.Response, response_json: Optional[dict] = None,
                                default_message: str = "The server returned an empty response.") -> str:
        """
        Returns the most useful error detail available from an API response.

        JSON error or message fields take precedence. For non-JSON responses, a concise detail
        is extracted from the response.
        """
        if response_json:
            for key in ("error", "message"):
                message = response_json.get(key)
                if message:
                    formatted_message = ApiRequest._format_response_message(str(message))
                    if formatted_message:
                        return formatted_message

        response_text = response.text.strip()
        if response_text and response_json is None:
            extracted_message = ApiRequest._extract_response_message(response_text)
            if extracted_message:
                return extracted_message
        return default_message

    @staticmethod
    def _format_response_message(message: str) -> str:
        """
        Converts a response detail into text suitable for a message box.

        Server-side HTML and long diagnostic messages are kept in the QGIS log; only a
        concise, readable detail is returned to the caller.
        """
        cleaned_message = ApiRequest._strip_markup(message)
        cleaned_message = re.sub(
            r"\s*\(\d{3}\s+[^)]*\)\s*$",
            "",
            cleaned_message
        )
        cleaned_message = re.sub(
            r'The\s+""\s+file',
            "The uploaded file",
            cleaned_message,
            flags=re.IGNORECASE
        )
        if cleaned_message.lower() in {
            "an error occurred: internal server error",
            "oops! an error occurred"
        }:
            cleaned_message = "The server reported an internal error."

        if len(cleaned_message) > MAX_API_ERROR_MESSAGE_LENGTH:
            message_end = MAX_API_ERROR_MESSAGE_LENGTH - len("...")
            return f"{cleaned_message[:message_end].rstrip()}..."
        return cleaned_message

    @staticmethod
    def _strip_markup(text: str) -> str:
        """Removes HTML markup and collapses whitespace in a response detail."""
        text_without_scripts = re.sub(
            r"(?is)<(script|style)\b[^>]*>.*?</\1>",
            " ",
            text
        )
        text_without_tags = re.sub(r"(?s)<[^>]+>", " ", text_without_scripts)
        return " ".join(unescape(text_without_tags).split())

    @classmethod
    def _extract_response_message(cls, response_text: str) -> str:
        """Extracts a short message from an HTML or plain-text server response."""
        for pattern in (
            r"(?is)<title\b[^>]*>(.*?)</title>",
            r"(?is)<h1\b[^>]*>(.*?)</h1>",
            r"(?is)<h2\b[^>]*>(.*?)</h2>"
        ):
            match = re.search(pattern, response_text)
            if match:
                message = cls._format_response_message(match.group(1))
                if message:
                    return message
        return cls._format_response_message(response_text)

    @staticmethod
    def _log_response_summary(endpoint: str, response: requests.Response, detail: str) -> None:
        """Writes concise response metadata and the server detail to the QGIS message log."""
        QgsMessageLog.logMessage(
            f"API response from endpoint {endpoint}: "
            f"HTTP {response.status_code}; "
            f"Content-Type: {response.headers.get('Content-Type', '<unknown>')}; "
            f"Server message: {detail}",
            TAG,
            level=Qgis.MessageLevel.Critical
        )

    def _parse_json_response(self, response: requests.Response, endpoint: str) -> Optional[dict]:
        """
        Parses a JSON response when available without requiring a specific content type.

        Args:
            response: The HTTP response object.
            endpoint (str): The API endpoint for logging context.

        Returns:
            Optional[dict]: Parsed JSON, or None if parsing fails.
        """
        if response is None:
            return None

        try:
            response_json = response.json()
        except ValueError:
            detail = self._extract_response_message(response.text) or "The response was not valid JSON."
            self._log_response_summary(endpoint, response, detail)
            return None

        if not isinstance(response_json, dict):
            self._log_response_summary(
                endpoint,
                response,
                "The JSON response has an unsupported structure."
            )
            return None

        if response.status_code != 200:
            self._log_response_summary(
                endpoint,
                response,
                self._response_error_message(response, response_json)
            )

        return response_json

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
        if response is None:
            return 0, None, "No response received from server"

        response_json = self._parse_json_response(response, endpoint)
        if response.status_code != 200 or response_json is None:
            error_msg = self._response_error_message(response, response_json)
            QgsMessageLog.logMessage(
                f"WMS information request failed. HTTP {response.status_code}: {error_msg}",
                TAG,
                level=Qgis.MessageLevel.Critical
            )
            return response.status_code, None, error_msg

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
        if response is None:
            return 0, None, "No response received from server"

        status_code = response.status_code
        response_json = self._parse_json_response(response, endpoint)

        if status_code != 200 or response_json is None:
            error_wms_add = self._response_error_message(response, response_json)
            QgsMessageLog.logMessage(
                f"WMS could not be added to Mapbender. HTTP {status_code}: {error_wms_add}",
                TAG,
                level=Qgis.MessageLevel.Critical
            )
            return status_code, None, error_wms_add

        if status_code == 200:
            match = re.search(r"#(\d+)", response_json.get("message", ""))
            if match:
                added_source_id = match.group(1)
                QgsMessageLog.logMessage(f"New source added with ID: {added_source_id}", TAG,
                                         level=Qgis.MessageLevel.Info)
            else:
                error_wms_add = self._response_error_message(
                    response,
                    response_json,
                    "The server response did not contain a source ID."
                )
                QgsMessageLog.logMessage(
                    f"WMS could not be added to Mapbender. HTTP {status_code}: {error_wms_add}",
                    TAG,
                    level=Qgis.MessageLevel.Critical
                )
        else:
            error_wms_add = response_json.get("error", "Unknown error")
            QgsMessageLog.logMessage(f"WMS could not be added to Mapbender. Reason: {error_wms_add}", TAG,
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
        if response is None:
            return 0, {"error": "No response received from server"}

        response_json = self._parse_json_response(response, endpoint)
        if response_json is None:
            return response.status_code, {"error": self._response_error_message(response)}

        return response.status_code, response_json

    def wms_assign(self, application: str, source: int, layer_set: Optional[str]) -> tuple[int, Optional[dict]]:
        """
        Assigns a WMS source to a Mapbender application.

        Args:
            application (str): The slug of the application to assign the WMS source to.
            source (int): The ID of the WMS source.
            layer_set (Optional[str]): Optional layerset to assign.

        Returns:
            Tuple[int, Optional[dict]]:
                - status code
                - JSON response from the API (if successful)
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
        if response is None:
            return 0, {"error": "No response received from server"}

        response_json = self._parse_json_response(response, endpoint)
        if response_json is None:
            return response.status_code, {"error": self._response_error_message(response)}

        return response.status_code, response_json

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
        if response is None:
            error_message = "No response received from server"
            QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
            return 0, None

        status_code = response.status_code
        response_json = self._parse_json_response(response, endpoint)

        if response_json is not None:
            return status_code, response_json

        error_message = self._response_error_message(response)
        QgsMessageLog.logMessage(
            f"Failed to clone application. HTTP {status_code}: {error_message}",
            TAG,
            level=Qgis.MessageLevel.Critical
        )
        return status_code, {"error": error_message}

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