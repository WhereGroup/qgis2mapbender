from typing import Optional
from urllib.parse import urlparse
from xml.etree import ElementTree

import requests

from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtCore import QCoreApplication, Qt
from contextlib import contextmanager

from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsProject, QgsSettings

from .settings import (
    PLUGIN_SETTINGS_SERVER_CONFIG_KEY,
    PROJECT_STORAGE_LOCAL,
    PROJECT_STORAGE_UNSAVED,
    QGIS_SERVER_POSTGRESQL_WRAPPER_PATH,
    REQUEST_TIMEOUT_SIMPLE,
    TAG,
    WMS_CAPABILITIES_ROOT_ELEMENTS,
)

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QSizePolicy,
)


def translate(text: str) -> str:
    """Translate text that is shared by dialogs and message boxes."""
    return QCoreApplication.translate("QGIS2Mapbender", text)


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
            bool: True if the project is saved or has no changes, False if cancelled or saving failed.
    """
    project = QgsProject.instance()
    if project.isDirty():
        msgBox = QMessageBox()
        msgBox.setWindowTitle("")
        msgBox.setText(translate("There are unsaved changes."))
        msgBox.setInformativeText(translate("Do you want to save your changes before continuing?"))
        msgBox.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
        msgBox.button(QMessageBox.StandardButton.Save).setText(translate("Save"))
        msgBox.button(QMessageBox.StandardButton.Cancel).setText(translate("Cancel"))
        msgBox.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msgBox.exec()
        if ret == QMessageBox.StandardButton.Save:
            if project.write():
                return True

            error_message = project.error()
            QgsMessageLog.logMessage(
                f"Failed to save QGIS project: {error_message}",
                TAG,
                level=Qgis.MessageLevel.Critical,
            )
            show_fail_box(
                translate("Save failed"),
                translate("Could not save the QGIS project.\n\n{error_message}").format(
                    error_message=error_message
                ),
            )
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
        show_fail_box(
            translate("Failed"),
            translate(
                "The QGIS project has not been saved. Please save the project before publishing or updating."
            ),
        )
        return False
    return True


def get_qgis_project_storage_type(project=None) -> str:
    """
    Returns the storage type of a QGIS project.

    QGIS does not expose a project storage object for projects stored on the
    local filesystem. Database-backed projects expose their backend through
    ``QgsProjectStorage.type()``.

    Args:
        project: Optional QGIS project. The current project is used by default.

    Returns:
        str: One of the project storage type constants from ``settings.py``.
    """
    qgis_project = project if project is not None else QgsProject.instance()
    if not qgis_project.fileName():
        project_storage_type = PROJECT_STORAGE_UNSAVED
    else:
        project_storage = qgis_project.projectStorage()
        if project_storage is None:
            project_storage_type = PROJECT_STORAGE_LOCAL
        else:
            project_storage_backend = project_storage.type()
            project_storage_type = str(project_storage_backend).lower()

    return project_storage_type


def append_query_to_url(url: str, query: str) -> str:
    """Appends a separator-free query string without duplicating the separator."""
    if not query:
        return url
    if url.endswith(('?', '&')):
        separator = ''
    elif '?' in url:
        separator = '&'
    else:
        separator = '?'
    return f'{url}{separator}{query}'


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
    failBox.button(QMessageBox.StandardButton.Ok).setText(translate("OK"))
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
    successBox.button(QMessageBox.StandardButton.Ok).setText(translate("OK"))
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
    icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    layout.addWidget(icon_label)

    message_label = QLabel()
    message_label.setTextFormat(Qt.TextFormat.RichText)
    message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    message_label.setOpenExternalLinks(True)
    message_label.setWordWrap(True)
    message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    available_width = QApplication.primaryScreen().availableGeometry().width()
    margins = layout.contentsMargins()
    message_label.setMaximumWidth(
        available_width // 2 - margins.left() - margins.right()
    )
    message_label.setText(text)
    layout.addWidget(message_label)

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    button_box.button(QDialogButtonBox.StandardButton.Ok).setText(translate("OK"))
    button_box.accepted.connect(dialog.accept)
    layout.addWidget(button_box)

    dialog.adjustSize()
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
    questionBox.button(QMessageBox.StandardButton.Yes).setText(translate("Yes"))
    questionBox.button(QMessageBox.StandardButton.No).setText(translate("No"))
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


def check_wms_url(url: str) -> Optional[str]:
    """Checks that a generated URL returns a valid WMS capabilities document."""
    if not uri_validator(url):
        return translate("The generated WMS URL is invalid.")

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SIMPLE)
    except requests.exceptions.RequestException as error:
        QgsMessageLog.logMessage(
            f"Failed to validate WMS URL: {error}",
            TAG,
            level=Qgis.MessageLevel.Critical,
        )
        return translate(
            "The generated WMS URL could not be reached. "
            "Please see the QGIS2Mapbender log for more information."
        )

    if response.status_code != 200:
        return translate(
            "The generated WMS URL returned HTTP status {status_code}."
        ).format(status_code=response.status_code)

    try:
        capabilities = ElementTree.fromstring(response.content)
    except (ElementTree.ParseError, TypeError):
        return translate(
            "The server response is not a valid WMS capabilities document."
        )

    root_name = capabilities.tag.rsplit("}", 1)[-1]
    if root_name not in WMS_CAPABILITIES_ROOT_ELEMENTS:
        return translate(
            "The server response is not a valid WMS capabilities document."
        )

    return None


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