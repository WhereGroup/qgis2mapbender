import os
from dataclasses import dataclass

from qgis.core import QgsProject


@dataclass
class Paths:
    """
        Stores and manages paths for the current QGIS project.
    """
    source_project_dir_path: str
    source_project_dir_name: str
    source_project_file_name: str
    source_project_zip_file_path: str

    @staticmethod
    def get_paths() -> 'Paths':
        """
            Creates and returns a `Paths` object with the relevant project paths.

            Returns:
                Paths: An object containing the project directory path, directory name,
                project file name, and the path to the ZIP archive of the project.
        """
        source_project_dir_path = QgsProject.instance().absolutePath()
        source_project_dir_name = os.path.basename(source_project_dir_path)
        source_project_file_name = os.path.basename(QgsProject.instance().fileName())
        source_project_zip_file_path = source_project_dir_path + '.zip'
        return Paths(source_project_dir_path, source_project_dir_name, source_project_file_name,
                 source_project_zip_file_path)
