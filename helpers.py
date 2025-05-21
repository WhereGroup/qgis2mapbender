import logging
import re
from typing import Optional
from urllib.parse import urlparse

from PyQt5.QtWidgets import QApplication
from qgis.PyQt.QtCore import Qt
from decorator import contextmanager

from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QMessageBox
from qgis._core import QgsMessageLog, Qgis
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

def check_if_qgis_project_is_dirty_and_save() -> bool:
    if QgsProject.instance().isDirty():
        msgBox = QMessageBox()
        msgBox.setWindowTitle("")
        msgBox.setText("There are unsaved changes.")
        msgBox.setInformativeText("Do you want to save your changes before continuing?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
        msgBox.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msgBox.exec()
        if ret == QMessageBox.StandardButton.Save:
            QgsProject.instance().write()
            return True
        elif ret == QMessageBox.StandardButton.Cancel:
            return False
    return True


def qgis_project_is_saved() -> bool:
    """
    Checks if the current QGIS project is saved.

    If the project is not saved, display a message box to inform the user.

    Returns:
        bool: True if the project is saved, False otherwise.
    """
    source_project_file_path = QgsProject.instance().fileName()
    if not source_project_file_path:
        show_fail_box_ok('Failed', "Please use the QGIS2Mapbender from a saved QGIS-Project")
        return False
    return True


def create_fail_box(title: str, text: str) -> QMessageBox:
    """
    Creates a QMessageBox with a failure icon.

    Args:
        title (str): The title of the message box.
        text (str): The text to display in the message box.

    Returns:
        QMessageBox: The created message box.
    """
    failBox = QMessageBox()
    failBox.setIconPixmap(QPixmap(':/images/themes/default/mIconWarning.svg'))
    failBox.setWindowTitle(title)
    failBox.setText(text)
    return failBox


def show_fail_box_ok(title: str, text: str) -> int:
    """
    Displays a failure message box with an OK button.

    Args:
        title (str): The title of the message box.
        text (str): The text to display in the message box.

    Returns:
        int: The button clicked by the user.
    """
    QApplication.restoreOverrideCursor()
    failBox = create_fail_box(title, text)
    failBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    return failBox.exec()


# def show_fail_box_yes_no(title: str, text: str) -> int:
#     """
#     Displays a failure message box with Yes and No buttons.
#
#     Args:
#         title (str): The title of the message box.
#         text (str): The text to display in the message box.
#
#     Returns:
#         int: The button clicked by the user.
#     """
#     QApplication.restoreOverrideCursor()
#     failBox = create_fail_box(title, text)
#     failBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
#     return failBox.exec()


def show_succes_box_ok(title: str, text: str) -> int:
    """
    Displays a success message box with an OK button.

    Args:
        title (str): The title of the message box.
        text (str): The text to display in the message box.

    Returns:
        int: The button clicked by the user.
    """
    QApplication.restoreOverrideCursor()
    successBox = QMessageBox()
    successBox.setIconPixmap(QPixmap(':/images/themes/default/mIconSuccess.svg'))
    successBox.setWindowTitle(title)
    successBox.setText(text)
    successBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    return successBox.exec()


def show_question_box(text: str) -> int:
    """
    Displays a question message box with Yes and No buttons.

    Args:
        text (str): The question to display in the message box.

    Returns:
        int: The button clicked by the user.
    """
    questionBox = QMessageBox()
    questionBox.setIcon(QMessageBox.Icon.Question)
    questionBox.setText(text)
    questionBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return questionBox.exec()


def list_qgs_settings_child_groups(key: str) -> list:
    """
    Lists the child groups of a given key in QGIS settings.

    Args:
        key (str): The key to search for child groups.

    Returns:
        list: A list of child group names.
    """
    s = QgsSettings()
    s.beginGroup(key)
    subkeys = s.childGroups()
    s.endGroup
    return subkeys


@contextmanager
def waitCursor():
    """
    A context manager to set the cursor to a wait state during a long-running operation.
    """
    try:
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        yield
    except Exception as ex:
        raise ex
    finally:
        QgsApplication.restoreOverrideCursor()


def validate_no_spaces(*variables: str) -> bool:
    """
    Validates that none of the provided variables contain spaces.

    Args:
        *variables (str): The variables to validate.

    Returns:
        bool: True if none of the variables contain spaces, False otherwise.
    """
    for var in variables:
        if " " in var:
            return False
    return True


def update_mb_slug_in_settings(mb_slug: str, is_mb_slug: bool) -> None:
    """
    Updates the Mapbender slug in QGIS settings.

    Args:
        mb_slug (str): The Mapbender slug to update.
        is_mb_slug (bool): Whether to add or remove the slug.
    """
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
    """
    Validates a URL to check if it is well-formed.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is well-formed, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def starts_with_single_slash_or_colon(s: str) -> bool:
    """
    Checks if a string starts with a single slash or a colon.

    Args:
        s (str): The string to check.

    Returns:
        bool: True if the string starts with a single slash or a colon, False otherwise.
    """
    pattern = r"^(/[^/]|:)"
    return bool(re.match(pattern, s))


def ends_with_single_slash(s: str) -> bool:
    """
    Checks if a string ends with a single slash.

    Args:
        s (str): The string to check.

    Returns:
        bool: True if the string ends with a single slash, False otherwise.
    """
    pattern = r"[^/]/$"
    return bool(re.search(pattern, s))


def error_logging_and_user_message(error: Exception, user_message: Optional[str] = None) -> None:
    """
    Handles errors by logging them and optionally displaying a user-friendly message.

    Args:
        error (Exception): The exception to handle.
        user_message (Optional[str]): A user-friendly message to display (optional).
    """
    QgsMessageLog.logMessage(str(error), TAG, level=Qgis.MessageLevel.Critical)
    if user_message:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(user_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()