import requests
from typing import Any, Dict, Optional

class ApiRequest:
    def __init__(self, server_config):
        self.server_config = server_config
        self.session = requests.Session()
        self.api_url = f"{self.server_config.mb_protocol}{self.server_config.url}/mapbender/api"
        self.headers = {}
        self.token = self._authenticate()
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _authenticate(self) -> Optional[str]:
        """
        Authenticates against the API to obtain an access token.
        """
        endpoint = "/login_check"
        credentials = {
            "username": self.server_config.username,
            "password": self.server_config.password
        }
        try:
            response = self._send_request(endpoint, "post", json=credentials)
            if response and response.status_code == 200:
                return response.json().get("token")
            elif response and response.status_code == 404:
                raise ValueError("Invalid URL. Please check the server configuration (URL is valid?).")
            else:
                raise ValueError("Invalid credentials. Please verify your username and password.")
        except requests.RequestException as e:
            raise ConnectionError(f"Error authenticating with the API: {e}")

    def _send_request(self, endpoint: str, method: str, **kwargs) -> Optional[requests.Response]:
        """
        Sends a request to the API with the specified method and parameters.

        Args:
            endpoint (str): The API endpoint (e.g., "/upload/zip").
            method (str): The HTTP method ("GET", "POST".).
            kwargs: Additional arguments for the request (json,etc.).

        Returns:
            Response: The API's response object.
        """
        url = f"{self.api_url}{endpoint}"
        try:
            response = self.session.request(method=method.upper(), url=url, headers= self.headers, **kwargs)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
        return None

    def upload_zip(self, file_path: str) -> tuple[int, Optional[dict]]:
        """
        Uploads a ZIP file to the server and handles the response.

        Args:
            file_path (str): Path to the ZIP file.

        Returns:
            Dict[str, Any]: JSON response from the API if the upload was successful.
        """
        endpoint = "/upload/zip"
        try:
            with open(file_path, "rb") as file:
                files = {"file": file}
                response = self._send_request(endpoint, "post", files=files)
                if response:
                    return response.status_code, response.json()
                else:
                    return 500, {"error": "Failed to receive a valid response from the server."}
        except FileNotFoundError:
            return 400, {"error": f"File not found: {file_path}"}
        except requests.RequestException as e:
            return 500, {"error": f"Error during the request: {e}"}

