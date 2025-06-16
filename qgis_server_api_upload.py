import os
import shutil
from typing import Optional

from qgis.core import QgsMessageLog, Qgis

from .helpers import waitCursor, get_size_and_unit
from .server_config import ServerConfig
from .settings import TAG


class QgisServerApiUpload:
    """
        Handles the process of zipping, uploading, and cleaning up QGIS project files for QGIS Server API integration.
    """
    def __init__(self, api_request, paths) -> None:
        """
            Initializes the QgisServerApiUpload object with necessary paths and API request handler.

            Args:
                api_request: The API request handler for uploading the project.
                paths: An object containing paths related to the QGIS project.
            Returns:
                None
        """
        self.source_project_dir_path = paths.source_project_dir_path
        self.source_project_dir_name = paths.source_project_dir_name
        self.source_project_file_name = paths.source_project_file_name
        self.source_project_zip_file_path = paths.source_project_zip_file_path
        self.api_request = api_request

    def get_wms_url(self, server_config: ServerConfig, upload_dir: str) -> str:
        """
            Constructs the WMS URL for the uploaded project.

            Args:
                server_config: The server configuration object.
                upload_dir: The directory where the project is uploaded.

            Returns:
                str: The WMS URL.
        """
        wms_service_version_request = "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities&map="
        server_project_dir = self.source_project_file_name.split('.')[0]
        wms_url = (f'{server_config.qgis_server_path}'
                   f'{wms_service_version_request}{upload_dir}{server_project_dir}/'
                   f'{self.source_project_file_name}')
        QgsMessageLog.logMessage(f"WMS URL: {wms_url}", TAG, level=Qgis.MessageLevel.Info)
        return wms_url

    def process_and_upload_project(self) -> Optional[tuple[str, Optional[str]]]:
        """
            Executes the steps to zip the project, upload it, and delete the ZIP file.

            Returns:
                Optional[str]: status code
        """
        status_code = None
        upload_dir = None
        # Step 1: Create a ZIP of the local project directory
        if not self._zip_local_project_dir():
            QgsMessageLog.logMessage(f"Failed to create ZIP file for the project.", TAG,
                                     level=Qgis.MessageLevel.Critical)

        # Step 2: Upload the ZIP file
        elif not os.path.isfile(self.source_project_zip_file_path):
            QgsMessageLog.logMessage(f"File not found: {self.source_project_zip_file_path}", TAG,
                                     level=Qgis.MessageLevel.Critical)

        elif self.api_request.token:
            status_code, upload_dir, error_upload_dir = self.api_request.uploadZip(self.source_project_zip_file_path)

            # Step 3: Delete the local ZIP file
            self._delete_local_project_zip_file()

        return status_code, upload_dir

    def _zip_local_project_dir(self) -> bool:
        """
            Zips the local project directory, excluding unwanted files.

            Returns:
                bool: True if the ZIP file was created successfully, False otherwise.
        """
        try:
            temp_dir_path = f'{self.source_project_dir_path}_copy_tmp'
            if os.path.isdir(temp_dir_path):
                shutil.rmtree(temp_dir_path)
            os.makedirs(temp_dir_path)

            shutil.copytree(self.source_project_dir_path, temp_dir_path + "/" + self.source_project_file_name.split('.')[0])
            for folder_name, subfolders, filenames in os.walk(temp_dir_path):
                for filename in filenames:
                    file_path = os.path.join(folder_name, filename)
                    if filename.split(".")[-1] in ('gpkg-wal', 'gpkg-shm'):
                        os.remove(file_path)
            self._create_archive_with_folder(temp_dir_path)
            shutil.rmtree(temp_dir_path)

            if os.path.isfile(self.source_project_zip_file_path):
                if os.access(self.source_project_zip_file_path, os.R_OK):
                    file_size = os.path.getsize(self.source_project_zip_file_path)
                    file_size_unit, unit = get_size_and_unit(file_size)
                    QgsMessageLog.logMessage(f"Zip-project folder successfully created. File is readable. File size: {file_size_unit} {unit}", TAG, level=Qgis.MessageLevel.Info)
                    return True
                else:
                    QgsMessageLog.logMessage(f"Zip-project folder successfully created, but file is not readable.", TAG, level=Qgis.MessageLevel.Warning)
                    return False
            else:
                return False
        except Exception as e:
            QgsMessageLog.logMessage(f"Error while zipping project directory: {e}", TAG, level=Qgis.MessageLevel.Critical)
            return False

    def _create_archive_with_folder(self, source) -> None:
        """
            Creates an archive (zip) containing the specified folder.

            Args:
                source (str): the folder you want to archive.

            Returns:
                None
        """
        try:
            base = os.path.basename(self.source_project_zip_file_path)
            zip_name = base.split('.')[0]
            zip_type = base.split('.')[1]
            archive_to = os.path.dirname(self.source_project_zip_file_path)
            shutil.make_archive(os.path.join(str(archive_to), zip_name), zip_type, source)
        except Exception as e:
            QgsMessageLog.logMessage(f"An error occurred during archiving: {e}", TAG, level=Qgis.MessageLevel.Critical)

    def _delete_local_project_zip_file(self) -> None:
        """
            Deletes the local ZIP file of the project.

            Returns:
                    None
        """
        with waitCursor():
            try:
                if os.path.isfile(self.source_project_zip_file_path):
                    os.remove(self.source_project_zip_file_path)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error while deleting ZIP file: {e}", TAG, level=Qgis.MessageLevel.Critical)