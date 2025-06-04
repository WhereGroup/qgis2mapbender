from typing import Optional

from qgis.core import QgsMessageLog, Qgis

from .helpers import show_fail_box_ok
from .settings import TAG


class MapbenderApiUpload:
    def __init__(self, server_config, api_request, wms_url):
        self.server_config = server_config
        self.wms_url = wms_url
        self.api_request = api_request

    def mb_upload(self) -> tuple[int, Optional[list[int]], bool]:
        is_reloaded = False
        status_code_wms_show, source_ids = self.api_request.wms_show(self.wms_url)

        if status_code_wms_show != 200:
            show_fail_box_ok("Failed",
                             f"WMS layer information could not be displayed. "
                             f"Mapbender upload will be interrupted.")
            return 1, None, is_reloaded

        if source_ids: # wms already exists as a Mapbender source and will be reloaded
            is_reloaded = True
            exit_status_reload, reloaded_source_ids = self._reload_sources(source_ids, self.wms_url)
            if exit_status_reload != 0:
                return 1, reloaded_source_ids, is_reloaded
            return 0, reloaded_source_ids, is_reloaded
        else: #wms does not exist as a source and will be added to mapbender as a source
            status_code_add_wms, new_source_id = self.api_request.wms_add(self.wms_url)
            if status_code_add_wms == 200:
                return 0, [new_source_id], is_reloaded
            return 1, [new_source_id], is_reloaded


    def mb_reload(self) -> tuple[int, Optional[list[int]]]:
        try:
            exit_status_wms_show, source_ids = self.api_request.wms_show(self.wms_url)
            if exit_status_wms_show != 200:
                show_fail_box_ok("Failed",
                                 f"WMS layer information could not be displayed. "
                                 f"Mapbender upload will be interrupted.")
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


    def _reload_sources(self, source_ids: list[int], wms_url: str) -> tuple[int, list[int]]:
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
            if exit_status_reload_wms == 200:
                reloaded_source_ids.append(source_id)

        if not all(status == 200 for status in status_code_list):
            QgsMessageLog.logMessage(f"Reloaded sources: {reloaded_source_ids}. WMS could not be reloaded in (all sources) in Mapbender.", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box_ok("Failed",
                             f"Reloaded sources: {reloaded_source_ids}. WMS could not be reloaded in (all sources) in Mapbender.")
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
        if response_json and "message" in response_json:
            message = response_json["message"]
            try:
                slug = (message.split("slug", 1)[1]).split(",")[0].strip()
            except IndexError:
                QgsMessageLog.logMessage("Failed to parse slug from message.", TAG, level=Qgis.MessageLevel.Warning)
        else:
            QgsMessageLog.logMessage("No valid message in response_json.", TAG, level=Qgis.MessageLevel.Warning)
        return exit_status, slug

    def assign_wms_to_source(self, slug: str, source_id: int, layer_set: str) -> int:
        exit_status = self.api_request.wms_assign(slug, source_id, layer_set)
        if exit_status == 404:
            msg = (f"WMS {self.wms_url} was successfully created and uploaded to Mapbender, but not assigned to an "
                   f"application. \n\nApplication '{slug}' does not exists. Please choose a different application.")
            QgsMessageLog.logMessage(msg, TAG, level=Qgis.MessageLevel.Warning)
            show_fail_box_ok("Failed",msg)
            return exit_status
        elif exit_status == 200:
            QgsMessageLog.logMessage(f"WMS with source id {source_id} successfully assigned to slug {slug}.", TAG, level=Qgis.MessageLevel.Info)
        elif exit_status == 500:
            QgsMessageLog.logMessage(f"Failed to assign WMS with source id {source_id} to slug {slug}. Please "
                                     f"check if the application has at least one layerset.", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box_ok("Failed",
                             f"WMS {self.wms_url} successfully created and uploaded to Mapbender. \n\nFailed to "
                             f"assign WMS with source id {source_id} to slug {slug}.\n\nPlease check if the application "
                             f"has at least one layerset or if the given layerset exists. \n\n**Requirements:** \nThe Mapbender applications should "
                             f"have at least one layerset named 'main' or any other name. \n\nThe input parameter layerset (optional) in QGSI2Mapbender "
                             f"defaults to 'main' (if exists) or the first layerset in the application")
        else:
            QgsMessageLog.logMessage(f"Failed to assign WMS with source id {source_id} to slug {slug}.", TAG, level=Qgis.MessageLevel.Critical)
            show_fail_box_ok("Failed",
                             f"WMS {self.wms_url} successfully created and uploaded to Mapbender. \n\nFailed to "
                             f"assign WMS with source id {source_id} to slug {slug}.")
        return exit_status