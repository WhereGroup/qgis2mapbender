import os
import shutil
import requests

from qgis.core import QgsMessageLog, Qgis

from .api_request import ApiRequest
from .helpers import show_fail_box_ok, waitCursor
from .server_config import ServerConfig
from .settings import TAG

class QgisServerApiUpload:
    def __init__(self, paths):
        self.source_project_dir_path = paths.source_project_dir_path
        self.source_project_dir_name = paths.source_project_dir_name
        self.source_project_file_name = paths.source_project_file_name
        self.source_project_zip_file_path = paths.source_project_zip_file_path
        self.server_project_parent_dir_path = paths.server_project_parent_dir_path

    def get_wms_url(self, server_config: ServerConfig) -> str:
        wms_service_version_request = "?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities&map="
        wms_url = (f'{server_config.qgis_server_protocol}{server_config.qgis_server_path}'
                   f'{wms_service_version_request}{server_config.projects_path}{self.source_project_dir_name}/'
                   f'{self.source_project_file_name}')
        return wms_url

    def zip_local_project_dir(self) -> bool:
        # Copy source directory and remove unwanted files
        if os.path.isdir(f'{self.source_project_dir_path}_copy_tmp'):
            shutil.rmtree(f'{self.source_project_dir_path}_copy_tmp')
        os.mkdir(f'{self.source_project_dir_path}_copy_tmp')
        shutil.copytree(self.source_project_dir_path, f'{self.source_project_dir_path}_copy_tmp/'
                                                      f'{self.source_project_dir_name}')
        for folder_name, subfolders, filenames in os.walk(f'{self.source_project_dir_path}_copy_tmp'):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                if filename.split(".")[-1] in ('gpkg-wal', 'gpkg-shm'):
                    os.remove(file_path)
        # Compress tmp copy of project folder
        shutil.make_archive(self.source_project_dir_path, 'zip', f'{self.source_project_dir_path}_copy_tmp')
        # Remove temporary copy of source directory
        shutil.rmtree(f'{self.source_project_dir_path}_copy_tmp')
        # Check
        if os.path.isfile(self.source_project_zip_file_path):
            QgsMessageLog.logMessage("Zip-project folder successfully created", TAG, level=Qgis.Info)
            return True
        else:
            return False

    def delete_local_project_zip_file(self) -> None:
        with waitCursor():
            if os.path.isfile(self.source_project_zip_file_path):
                os.remove(self.source_project_zip_file_path)

    @staticmethod
    def api_upload(file_path):
        try:
            with open(file_path, 'rb') as file:
                print('open')
                file = {'file': file}
                #response_upload = requests.post(api_url + "/upload/zip" , files=files, headers=header)
                status_code, response_json = ApiRequest.upload_zip(file)
                print(status_code, response_json)
                print(f"success: {response_json.get('success')}, "
                  f"error: {response_json.get('error')}")

            if status_code == 200:
                print('ZIP file uploaded and extracted successfully')
            elif status_code == 400:
                return (f"Error {status_code}: Invalid request, e.g., no file uploaded or wrong file type.\n"
                        f"Message: {response_json.get('message')}.\n")
            elif status_code == 401: #JWT Tocken not found
                return (f"Error {status_code}: Unauthorized.\n"
                        f"Message: {response_json.get('message')}.")
            elif status_code == 403:
                return (f"Error {status_code}: Unauthorized.\n"
                        f"Error: {response_json.get('error')}. Access Denied: Missing permissions - Upload Files.\n")
            elif status_code == 500: # Warning: mkdir(): Permission denied (500 Internal Server Error
                # (user: carmen, root)
                return (f"Error {status_code}: Server error, e.g., failed to move or extract the file.\n"
                        f"Message: {response_json.get('message')}.\n")
            else:
                return f"Error {status_code}"
        except FileNotFoundError:
            return f"Error: File not found at {file_path}"
