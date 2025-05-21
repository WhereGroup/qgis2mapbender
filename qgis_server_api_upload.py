import os
import shutil
from typing import Optional

from qgis.core import QgsMessageLog, Qgis

from .api_request import ApiRequest
from .helpers import waitCursor
from .server_config import ServerConfig
from .settings import TAG


class QgisServerApiUpload:
    def __init__(self, api_request, paths):
        self.source_project_dir_path = paths.source_project_dir_path
        self.source_project_dir_name = paths.source_project_dir_name
        self.source_project_file_name = paths.source_project_file_name
        self.source_project_zip_file_path = paths.source_project_zip_file_path
        self.server_project_parent_dir_path = paths.server_project_parent_dir_path
        self.api_request = api_request

    def get_wms_url(self, server_config: ServerConfig) -> str:
        """
        Constructs the WMS URL for the uploaded project.

        Args:
            server_config: The server configuration object.

        Returns:
            str: The WMS URL.
        """
        wms_service_version_request = "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities&map="
        server_project_dir = self.source_project_file_name.split('.')[0]
        wms_url = (f'{server_config.qgis_server_protocol}{server_config.qgis_server_path}'
                   f'{wms_service_version_request}{server_config.projects_path}{server_project_dir}/'
                   f'{self.source_project_file_name}')
        QgsMessageLog.logMessage(f"WMS URL: {wms_url}", TAG, level=Qgis.MessageLevel.Info)
        return wms_url

    def zip_local_project_dir(self) -> bool:
        """
        Zips the local project directory, excluding unwanted files.

        Returns:
            bool: True if the ZIP file was created successfully, False otherwise.
        """
        try:
            temp_dir = f'{self.source_project_dir_path}_copy_tmp'
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            shutil.copytree(self.source_project_dir_path, temp_dir + "/" + self.source_project_file_name.split('.')[0])

            for folder_name, subfolders, filenames in os.walk(temp_dir):
                for filename in filenames:
                    file_path = os.path.join(folder_name, filename)
                    if filename.split(".")[-1] in ('gpkg-wal', 'gpkg-shm'):
                        os.remove(file_path)
            self._create_archive_with_folder(temp_dir)
            shutil.rmtree(temp_dir)

            if os.path.isfile(self.source_project_zip_file_path):
                QgsMessageLog.logMessage("Zip-project folder successfully created", TAG, level=Qgis.MessageLevel.Info)
                return True
            else:
                return False
        except Exception as e:
            QgsMessageLog.logMessage(f"Error while zipping project directory: {e}", TAG, level=Qgis.MessageLevel.Critical)
            return False

    def _create_archive_with_folder(self, source):
        """
        Creates an archive (zip) containing the specified folder.

        Args:
            source (str): the folder you want to archive.
        """
        try:
            base = os.path.basename(self.source_project_zip_file_path)
            zip_name = base.split('.')[0]
            zip_type = base.split('.')[1]
            archive_to = os.path.dirname(self.source_project_zip_file_path)
            shutil.make_archive(os.path.join(str(archive_to), zip_name), zip_type, source)
        except Exception as e:
            QgsMessageLog.logMessage(f"An error occurred during archiving: {e}", TAG, level=Qgis.MessageLevel.Critical)

    def delete_local_project_zip_file(self) -> None:
        """
        Deletes the local ZIP file of the project.
        """
        with waitCursor():
            try:
                if os.path.isfile(self.source_project_zip_file_path):
                    os.remove(self.source_project_zip_file_path)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error while deleting ZIP file: {e}", TAG, level=Qgis.MessageLevel.Critical)

    # def api_upload(self, file_path: str, api_request, server_config: ServerConfig) -> Optional[str]:
    #     """
    #     Uploads and extracts the ZIP file to the server using the ApiRequest class.
    #
    #     Args:
    #         file_path (str): Path to the ZIP file.
    #         server_config (ServerConfig): Server configuration object.
    #
    #     Returns:
    #         Optional[str]: Error message if the upload fails, None otherwise.
    #     """
    #     try:
    #         if not os.path.isfile(file_path):
    #             QgsMessageLog.logMessage(f"File not found: {file_path}", TAG, level=Qgis.MessageLevel.Critical)
    #             return f"Error: File not found at {file_path}"
    #
    #         # TODO: Upload does not work if zip file is too big! Mapbender API returns:
    #         # "Bad Request for url: http://mapbender-qgis.wheregroup.lan/mapbender/api/upload/zip"
    #         # without explain what it is wrong!
    #         # api_request = ApiRequest(server_config)
    #         if api_request.token:
    #             status_code, response_json = api_request.uploadZip(file_path)
    #             # QgsMessageLog.logMessage(f" DEBUGGING uploadZip: {status_code, response_json}", TAG, level=Qgis.MessageLevel.Warning)
    #             # if status_code == 200:
    #             #     QgsMessageLog.logMessage("Project ZIP file successfully uploaded and unzipped on QGIS server",
    #             #                              TAG, level=Qgis.MessageLevel.Info)
    #             #     return None
    #             # elif status_code == 400:
    #             #     error_message = (f"Error {status_code}: Invalid request. "
    #             #                      f"Message: {response_json.get('error')}.")
    #             #     QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Warning)
    #             #     return error_message
    #             # elif status_code == 401:
    #             #     error_message = (f"Error {status_code}: Unauthorized. "
    #             #                      f"Message: {response_json.get('error')}.")
    #             #     QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Warning)
    #             #     return error_message
    #             # elif status_code == 403:
    #             #     error_message = (f"Error {status_code}: Access Denied. "
    #             #                      f"Error: {response_json.get('error')}.")
    #             #     QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Warning)
    #             #     return error_message
    #             # elif status_code == 500:
    #             #     error_message = (f"Error {status_code}: Server error. "
    #             #                      f"Message json: {response_json.get('error')}. Message raw {response_json}.")
    #             #     QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Critical)
    #             #     return error_message
    #             # else:
    #             #     error_message = f"Unexpected error with status code {status_code}."
    #             #     QgsMessageLog.logMessage(error_message, TAG, level=Qgis.MessageLevel.Warning)
    #             #     return error_message
    #     except Exception as e:
    #         QgsMessageLog.logMessage(f"Error during file upload: {e}", TAG, level=Qgis.MessageLevel.Critical)
    #         return f"Error during file upload: {e}"

    def process_and_upload_project(self, server_config: ServerConfig, api_request: ApiRequest) -> Optional[int]:
        """
        Executes the steps to zip the project, upload it, and delete the ZIP file.

        Args:
            server_config (ServerConfig): Server configuration.


        Returns:
            Optional[str]: status code
        """
        status_code = None
        # Step 1: Create a ZIP of the local project directory
        if not self.zip_local_project_dir():
            QgsMessageLog.logMessage(f"Failed to create ZIP file for the project.", TAG,
                                     level=Qgis.MessageLevel.Critical)

        # Step 2: Upload the ZIP file
        elif not os.path.isfile(self.source_project_zip_file_path):
            QgsMessageLog.logMessage(f"File not found: {self.source_project_zip_file_path}", TAG,
                                     level=Qgis.MessageLevel.Critical)

        elif api_request.token:
            status_code= api_request.uploadZip(self.source_project_zip_file_path)

            # Step 3: Delete the local ZIP file
            self.delete_local_project_zip_file()

        return status_code
