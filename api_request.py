import logging

import requests
from typing import Any, Dict, Optional

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
        try:
            response = self.session.request(method=method.upper(), url=url, headers= self.headers, **kwargs)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response
        except requests.HTTPError as http_err:
            handle_error(http_err, f"HTTP error occurred: {http_err}")
        except requests.RequestException as req_err:
            handle_error(req_err, f"Request error occurred: {req_err}")
        return None

    def upload_zip(self, file_path: str) -> tuple[int, Optional[dict]]:
        """
        Uploads a ZIP file to the server and handles the response.

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
        except requests.RequestException as e:
            return 500, {"error": f"Error during the request: {e}"}

