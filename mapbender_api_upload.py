from typing import Optional

from qgis.core import QgsMessageLog, Qgis

from .helpers import show_fail_box_ok
from .settings import TAG


class MapbenderApiUpload:
    def __init__(self, server_config, api_request, wms_url):
        self.server_config = server_config
        self.wms_url = wms_url
        self.api_request = api_request

    def mb_upload(self) -> tuple[int, list[int]]:
        status_code_wms_show, source_ids = self.api_request.wms_show(self.wms_url)
        if status_code_wms_show != 200:
            show_fail_box_ok("Failed",
                             f"WMS layer information could not be displayed. "
                             f"Mapbender upload will be interrupted.")
            return 1, []

        if source_ids:
            exit_status_reload, reloaded_source_ids = self._reload_sources(source_ids, self.wms_url)
            if exit_status_reload != 0:
                return 1, []
            return 0, reloaded_source_ids
        else:
            status_code_add_wms, new_source_id = self.api_request.wms_add(self.wms_url)
            if status_code_add_wms == 200:
                return 0, new_source_id
            return 1, []


    def mb_reload(self) -> tuple[int, list[int]]:
        try:
            exit_status_wms_show, source_ids = self.api_request.wms_show(self.wms_url)
            print("mb_reload", exit_status_wms_show)
            if exit_status_wms_show == 1:
                show_fail_box_ok("Failed",
                                 f"WMS layer information could not be displayed. "
                                 f"Mapbender upload will be interrupted.")
                return 1, []

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

    # def _add_new_source(self) -> tuple[int, Optional[int]]:
    #     """
    #     Adds a new WMS source to Mapbender.
    #
    #     :return: A tuple containing:
    #              - exit_status (0 = success, 1 = fail)
    #              - source_id (ID of the newly added source, or None if failed)
    #     """
    #     exit_status, source_id = self.api_request.wms_add(self.wms_url)
    #     print("exit_status, source_id:", exit_status, source_id)
    #     return exit_status, source_id


    def app_clone(self, template_slug: str) -> tuple[int, str]:
        """
        Clones an existing application in the Application backend. This will create a new application with
        a _imp suffix as application name.
        :param template_slug: template slug to clone
        :return: exit_status (0 = success, 1 = fail),
        :return:slug of the new clone app
        :return:error_output
        """
        exit_status, response_json =  self.api_request.app_clone(template_slug)

        if response_json and "message" in response_json:
            message = response_json["message"]
            try:
                slug = (message.split("slug", 1)[1]).split(",")[0].strip()
            except IndexError:
                slug = None
                QgsMessageLog.logMessage("Failed to parse slug from message.", TAG, level=Qgis.MessageLevel.Warning)
        else:
            slug = None
            QgsMessageLog.logMessage("No valid message in response_json.", TAG, level=Qgis.MessageLevel.Warning)
        return exit_status, slug

    def wms_assign(self, slug: str, source_id: int, layer_set: str) -> tuple[int, str, Optional[str]]:
        """
        :param slug:
        :param source_id:
        :param layer_set:
        :return: exit_status (0 = success, 1 = fail), output, error_output
        """
        exit_status, output = self.api_request.wms_assign(slug, source_id, layer_set)

        if output is None:
            output = ""
        return exit_status, output