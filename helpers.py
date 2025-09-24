from urllib.parse import urlparse

from PyQt5.QtWidgets import QApplication
from qgis.PyQt.QtCore import Qt
from contextlib import contextmanager

from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsApplication, QgsProject, QgsSettings

from .settings import PLUGIN_SETTINGS_SERVER_CONFIG_KEY, TAG

from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox




def get_project_layer_names() -> list:
    """
        Returns a list of all layer names in the current QGIS project.

        Returns:
            list: List of layer names.
    """
    return [layer.name() for layer in QgsProject.instance().mapLayers().values()]

def check_if_qgis_project_is_dirty_and_save() -> bool:
    """
        Checks if the current QGIS project has unsaved changes and prompts the user to save.

        Returns:
            bool: True if the project is saved or user chose to continue, False if cancelled.
    """
    if QgsProject.instance().isDirty():
        msgBox = QMessageBox()
        msgBox.setWindowTitle("")
        msgBox.setText("There are unsaved changes.")
        msgBox.setInformativeText("Do you want to save your changes before continuing?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
        msgBox.button(QMessageBox.Save).setText("Save")
        msgBox.button(QMessageBox.Cancel).setText("Cancel")
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
        show_fail_box('Failed', "Please use the QGIS2Mapbender from a saved QGIS-Project")
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


def show_fail_box(title: str, text: str) -> int:
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

def show_success_box(title: str, text: str) -> int:
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

def show_success_link_box(title: str, text: str) -> int:
    """
    Displays a success message box with a clickable link and an OK button.

    Args:
        title (str): The title of the message box.
        text (str): The text to display in the message box, which can include a link.

    Returns:
        int: The button clicked by the user.
    """

    QApplication.restoreOverrideCursor()

    dialog = QDialog()
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)

    icon_label = QLabel()
    icon_label.setPixmap(QPixmap(':/images/themes/default/mIconSuccess.svg'))
    layout.addWidget(icon_label)

    message_label = QLabel()
    message_label.setTextFormat(Qt.TextFormat.RichText)
    message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    message_label.setOpenExternalLinks(True)
    message_label.setWordWrap(True)
    message_label.setText(text)
    layout.addWidget(message_label)

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    button_box.accepted.connect(dialog.accept)
    layout.addWidget(button_box)

    return dialog.exec()


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
    questionBox.button(QMessageBox.Yes).setText("Yes")
    questionBox.button(QMessageBox.No).setText("No")
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
def waitCursor() -> None:
    """
        A context manager to set the cursor to a wait state during a long-running operation.

        Returns:
            None
    """
    try:
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        yield
    except Exception as ex:
        raise ex
    finally:
        QgsApplication.restoreOverrideCursor()

def update_mb_slug_in_settings(mb_slug: str, is_mb_slug: bool) -> None:
    """
        Updates the Mapbender slug in QGIS settings.

        Args:
            mb_slug (str): The Mapbender slug to update.
            is_mb_slug (bool): Whether to add or remove the slug.

        Returns:
            None
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


def get_size_and_unit(bytes_size) -> tuple:
    """
       Converts a byte size to a human-readable value and unit.

       Args:
           bytes_size (int or float): Size in bytes.

       Returns:
           tuple: (size, unit) where size is float/int and unit is str.
    """
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_size)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    # Round to two decimals for units KB and above, no decimals for bytes
    if unit_index == 0:
        size = int(size)
    else:
        size = round(size, 2)

    return size, units[unit_index]