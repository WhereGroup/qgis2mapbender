from typing import Optional

from qgis.core import QgsMessageLog, Qgis

from .helpers import show_fail_box
from .settings import TAG


class MapbenderApiUpload:
    """
        Handles the upload, reload, and assignment of WMS sources to Mapbender applications via API.
    """
    def __init__(self, server_config, api_request, wms_url):
        """
            Initializes the MapbenderApiUpload object.

            Args:
                server_config: The server configuration object.
                api_request: The API request handler.
                wms_url: The WMS GetCapabilities URL.
        """
        self.server_config = server_config
        self.wms_url = wms_url
        self.api_request = api_request

    def mb_upload(self) -> tuple[int, Optional[list[int]], bool]:
        """
            Uploads a WMS to Mapbender or reloads it if it already exists.

            Returns:
                tuple[int, Optional[list[int]], bool]:
                    - Exit status (0 = success, 1 = failure)
                    - List of source IDs or None
                    - True if reloaded, False otherwise
        """
        is_reloaded = False
        status_code_wms_show, source_ids, error_wms_show = self.api_request.wms_show(self.wms_url)

        if status_code_wms_show != 200:
            show_fail_box("Failed",
                             f"WMS layer information on Mapbender could not be displayed. Error: {error_wms_show}.\n\n"
                             f"WMS was successfully created/updated but Mapbender upload will be interrupted.\n\n"
                             f"Link to Capabilities: \n{self.wms_url}")
            return 1, None, is_reloaded

        if source_ids: # wms already exists as a Mapbender source and will be reloaded
            is_reloaded = True
            exit_status_reload, reloaded_source_ids = self._reload_sources(source_ids, self.wms_url)
            if exit_status_reload != 0:
                return 1, reloaded_source_ids, is_reloaded
            return 0, reloaded_source_ids, is_reloaded
        else: #wms does not exist as a source and will be added to mapbender as a source
            status_code_add_wms, new_source_id, error_wms_add = self.api_request.wms_add(self.wms_url)
            if status_code_add_wms == 200:
                return 0, [new_source_id], is_reloaded
            show_fail_box("Failed",
                             f"WMS was successfully created but Mapbender upload will be interrupted:\n\n"
                             f"Failed to add WMS source. Error: {error_wms_add}.\n\nLink to Capabilities: \n{self.wms_url}")
            return 1, [new_source_id], is_reloaded


    def mb_reload(self) -> tuple[int, Optional[list[int]]]:
        """
            Reloads existing WMS sources in Mapbender.

            Returns:
                tuple[int, Optional[list[int]]]:
                    - Exit status (0 = success, 1 = failure)
                    - List of reloaded source IDs or None
        """
        try:
            exit_status_wms_show, source_ids, error_wms_show = self.api_request.wms_show(self.wms_url)
            if exit_status_wms_show != 200:
                show_fail_box("Failed",
                                 f"WMS was successfully updated on the server but Mapbender upload will be interrupted:\n\n"
                                 f"WMS layer information on Mapbender could not be displayed. Error: {error_wms_show}.\n\n "
                             f"Link to Capabilities: \n{self.wms_url}")
                return 1, None

            if source_ids:
                exit_status_reload, reloaded_source_ids = self._reload_sources(source_ids, self.wms_url)
                if exit_status_reload != 0:
                    return 1, []
                return 0, reloaded_source_ids
            else:
                    return 1, []
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in mb_upload: {e}", TAG, level=Qgis.MessageLevel.Critical)
            return 1, []


    def _reload_sources(self, source_ids: list[int], wms_url: str) -> tuple[int, Optional[list[int]]]:
        """
            Reloads the specified WMS sources in Mapbender.

            Args:
                source_ids (list[int]): A list of source IDs to reload.
                wms_url (str): The WMS URL associated with the sources.

            Returns:
                tuple[int, list[int]]: A tuple containing:
                    - An exit status (0 = success, 1 = failure).
                    - A list of successfully reloaded source IDs.
        """
        status_code_list = []
        reloaded_source_ids = []

        for source_id in source_ids:
            exit_status_reload_wms, response_json  = self.api_request.wms_reload(source_id, wms_url)
            status_code_list.append(exit_status_reload_wms)
            if exit_status_reload_wms != 200:
                error_wms_reload = response_json.get("error", "Unknown error")
                msg = f"WMS was succesfully updated on the server.\n\nFailed to reload WMS with source id #{source_id} in Mapbender. Error: {error_wms_reload}"
                QgsMessageLog.logMessage(msg, TAG, level=Qgis.MessageLevel.Critical)
                show_fail_box("Failed", msg)
                return 1, None
            else:
                reloaded_source_ids.append(source_id)

        if not all(status == 200 for status in status_code_list):
            msg = f"Reloaded sources: {reloaded_source_ids}. WMS could not be reloaded in (all sources) in Mapbender."
            QgsMessageLog.logMessage(msg, TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box("Failed", msg)
            return 1, reloaded_source_ids

        QgsMessageLog.logMessage(f"All sources (with IDs : {reloaded_source_ids}) reloaded successfully.", TAG, level=Qgis.MessageLevel.Info)
        return 0, reloaded_source_ids


    def clone_app_and_get_slug(self, template_slug: str) -> tuple[int, Optional[str]]:
        """
            Clones a Mapbender app template and retrieves its slug.

            Args:
                template_slug (str): The slug of the template to clone.

            Returns:
                tuple[int, Optional[str]]: A tuple containing:
                    - An exit status (0 = success, 1 = failure).
                    - The slug of the cloned app if successful, None otherwise.
        """
        exit_status, response_json =  self.api_request.app_clone(template_slug)
        slug = None
        msg_error_box = (f"WMS was successfully created/updated but Mapbender publish failed:\n\nFailed to clone application "
                         f"'{template_slug}'. Error: ")
        if exit_status == 200 and response_json:
            if "message" in response_json:
                message = response_json["message"]
                try:
                    slug = (message.split("slug", 1)[1]).split(",")[0].strip()
                except IndexError:
                    QgsMessageLog.logMessage("Failed to parse slug from message.", TAG, level=Qgis.MessageLevel.Warning)
            else:
                QgsMessageLog.logMessage("No valid message in response_json.", TAG, level=Qgis.MessageLevel.Warning)
        elif exit_status != 200 and response_json:
            error_message_wms_clone = response_json.get("error", "Unknown error")
            show_fail_box("Failed",
                             f"{msg_error_box}{error_message_wms_clone}.\n\n"
                             f"Link to Capabilities: \n{self.wms_url}")
        else:
            show_fail_box("Failed",f"{msg_error_box}{exit_status}.\n\n"
                          f"Link to Capabilities: \n{self.wms_url}")
        return exit_status, slug

    def assign_wms_to_source(self, slug: str, source_id: int, layer_set: str) -> int:
        """
            Assigns a WMS source to a Mapbender application.

            Args:
                slug (str): The application slug.
                source_id (int): The WMS source ID.
                layer_set (str): The layer set name.

            Returns:
                int: HTTP status code (200 = success, otherwise failure)
        """
        status_code, response_json = self.api_request.wms_assign(slug, source_id, layer_set)
        msg_error_log = f"Failed to assign source #{source_id} to application '{slug}'. Error: "
        msg_error_box = (f"WMS successfully created/updated and uploaded/reloaded to Mapbender as source #{source_id}."
                         f"\n\nFailed to assign source #{source_id}  to application '{slug}'. Error:")
        if status_code == 200 and response_json:
            QgsMessageLog.logMessage(f"WMS with source #{source_id} successfully assigned to application '{slug}'.", TAG, level=Qgis.MessageLevel.Info)
        elif response_json:
            error_assign_wms = response_json.get("error", "Unknown error")
            QgsMessageLog.logMessage(f"{msg_error_log}{error_assign_wms}", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box("Failed",
                             f"{msg_error_box} {error_assign_wms}.\n\nLink to Capabilities: \n{self.wms_url}")
        else:
            QgsMessageLog.logMessage(f"{msg_error_log}{status_code}", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box("Failed",
                          f"{msg_error_box} {status_code}.\n\nLink to Capabilities: \n{self.wms_url}")
        return status_code