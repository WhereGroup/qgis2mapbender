import logging
import os
import platform
import re
from typing import Optional
from urllib.parse import urlparse
from fabric2 import Connection
from qgis.PyQt.QtCore import Qt
from decorator import contextmanager

from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsApplication, QgsProject, QgsSettings

from .settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG


def get_os():
    os = platform.system()
    if os == "Windows":
        return "Windows"
    elif os == "Linux":
        return "Linux"
    return "Unknown OS"
def get_plugin_dir() -> str:
    return os.path.dirname(__file__)


def get_project_layer_names() -> list:
    return [layer.name() for layer in QgsProject.instance().mapLayers().values()]

def check_if_qgis_project_is_dirty_and_save() -> None:
    if QgsProject.instance().isDirty():
        msgBox = QMessageBox()
        msgBox.setWindowTitle("")
        msgBox.setText("The project has been modified.")
        msgBox.setInformativeText("Do you want to save your changes?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        msgBox.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msgBox.exec()
        if ret == QMessageBox.StandardButton.Save:
            QgsProject.instance().write()
        return ret

def qgis_project_is_saved() -> bool:
    # Get and check .qgz project path
    #source_project_dir_path = QgsProject.instance().readPath("./")
    source_project_file_path = QgsProject.instance().fileName()
    #if source_project_dir_path == "./" or source_project_file_path == "":
    if not source_project_file_path:
        show_fail_box_ok('Failed',
                         "Please use the QGIS2Mapbender from a saved QGIS-Project")
        return False
    return True


def create_fail_box(title, text):
    failBox = QMessageBox()
    failBox.setIconPixmap(QPixmap(':/images/themes/default/mIconWarning.svg'))
    failBox.setWindowTitle(title)
    failBox.setText(text)
    return failBox


def show_fail_box_ok(title, text):
    failBox = create_fail_box(title, text)
    failBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    return failBox.exec()


def show_fail_box_yes_no(title, text):
    failBox = create_fail_box(title, text)
    failBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return failBox.exec()


def show_succes_box_ok(title: object, text: object) -> int:
    successBox = QMessageBox()
    successBox.setIconPixmap(QPixmap(':/images/themes/default/mIconSuccess.svg'))
    successBox.setWindowTitle(title)
    successBox.setText(text)
    successBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    return successBox.exec()


def show_question_box(text):
    questionBox = QMessageBox()
    questionBox.setIcon(QMessageBox.Icon.Question)
    questionBox.setText(text)
    questionBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return questionBox.exec()


def list_qgs_settings_child_groups(key):
    s = QgsSettings()
    s.beginGroup(key)
    subkeys = s.childGroups()
    s.endGroup
    return subkeys

@contextmanager
def waitCursor():
    try:
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        yield
    except Exception as ex:
        raise ex
    finally:
        QgsApplication.restoreOverrideCursor()


def validate_no_spaces(*variables):
    for var in variables:
        if " " in var:
            return False
    return True


def update_mb_slug_in_settings(mb_slug, is_mb_slug) -> None:
    s = QgsSettings()
    if s.contains(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/mb_templates"):
        s.beginGroup(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/")
        mb_slugs = s.value('mb_templates')
        s.endGroup()
        if isinstance(mb_slugs, str) and mb_slugs != '':
            mb_slugs_list = mb_slugs.split(", ")
        elif isinstance(mb_slugs, str) and mb_slugs == '':
            mb_slugs_list = []
        elif isinstance(mb_slugs, list):
            mb_slugs_list = mb_slugs

        if is_mb_slug and mb_slug not in mb_slugs_list:
            mb_slugs_list.append(mb_slug)
            updated_mb_slugs = ", ".join(mb_slugs_list)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/mb_templates", updated_mb_slugs)
        if not is_mb_slug and mb_slug in mb_slugs_list:
            mb_slugs_list.remove(mb_slug)
            updated_mb_slugs = ", ".join(mb_slugs_list)
            s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/mb_templates", updated_mb_slugs)

    elif is_mb_slug:
        s.setValue(f"{PLUGIN_SETTINGS_SERVER_CONFIG_KEY}/mb_templates", mb_slug)


def uri_validator(url: str) -> bool:
    """Validating a URL in Python.
    It only checks if the URL is malformed and does not check the response of the http request."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def starts_with_single_slash_or_colon(s) -> bool:
    """To check if a string starts with only one '/' or with a column using regular expressions (regex)"""
    # Regex pattern to check if string starts with exactly one "/"
    pattern = r"^(/[^/]|:)"
    return bool(re.match(pattern, s))


def ends_with_single_slash(s) -> bool:
    """To check if a string ends with only one '/' using regular expressions (regex)"""
    # Regex pattern to check if string starts with exactly one "/"
    pattern = r"[^/]/$"
    return bool(re.search(pattern, s))


def check_if_project_folder_exists_on_server(conn: Connection, path: str) -> bool:
    if conn.run(f'test -d {path}', warn=True).failed:
       return False
    return True

def handle_error(error: Exception, user_message: Optional[str] = None) -> None:
    """
    Handles errors by logging them and optionally displaying a user-friendly message.

    Args:
        error (Exception): The exception to handle.
        user_message (Optional[str]): A user-friendly message to display (optional).
    """
    logging.error(f"{TAG} - {str(error)}")
    if user_message:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(user_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
