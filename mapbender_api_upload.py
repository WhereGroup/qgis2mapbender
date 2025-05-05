from qgis.core import QgsMessageLog, Qgis
from typing import Optional

from .api_request import ApiRequest
from .helpers import show_fail_box_ok
from .settings import TAG


class MapbenderApiUpload:
    def __init__(self, server_config, wms_url):
        self.server_config = server_config
        self.wms_url = wms_url
        self.api_request = ApiRequest(self.server_config)
        QgsMessageLog.logMessage(f"Initializing MapbenderApiUpload...", TAG, level=Qgis.Info)

    def mb_upload(self) -> tuple[int, list[int]]:
        try:
            exit_status_wms_show, source_ids = self.wms_show()
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
                exit_status_add, new_source_ids = self._add_new_source()
                if exit_status_add != 0:
                    return 1, []
                return 0, new_source_ids

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in mb_upload: {e}", TAG, level=Qgis.Critical)
            return 1, []

    def mb_reload(self) -> tuple[int, list[int]]:
        try:
            exit_status_wms_show, source_ids = self.wms_show()
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
            QgsMessageLog.logMessage(f"Error in mb_upload: {e}", TAG, level=Qgis.Critical)
            return 1, []

    def wms_show(self) -> tuple[int, list[int]]:
        """
        Displays layer information of a persisted WMS source.
        Parses the url of the WMS Source to get the information.
        :param url: url of the WMS Source
        :return: exit_status (0 = success, 1 = fail),
        :return: sources_ids (list with sources ids if available)
        """
        # check if source already exists in Mapbender as a source (with endpoint wms/show)
        exit_status, output = self.api_request.wms_show(self.wms_url)

        if exit_status != 200 or not isinstance(output, dict):
            QgsMessageLog.logMessage(f"Response error from wms/show: {output}", TAG, level=Qgis.Warning)
            return exit_status, []

        if not output.get("success", False):
            QgsMessageLog.logMessage("Request to wms/show not successful.", TAG, level=Qgis.Warning)
            return exit_status, []

        source_ids = [item['id'] for item in output.get('message', []) if isinstance(item, dict) and 'id' in item]
        QgsMessageLog.logMessage(f"DEBUGGING Raw output: {output}", TAG, level=Qgis.Info)
        QgsMessageLog.logMessage(f"WMS' source-IDs in Mapbender: {source_ids}", TAG, level=Qgis.Info)
        return exit_status, source_ids

    def _reload_sources(self, source_ids: list[int], wms_url: str) -> int:
        exit_status_list = []
        reloaded_source_ids = []

        for source_id in source_ids:
            QgsMessageLog.logMessage(f"DEBUGGING Sending reload request for source_id: {source_id}, wms_url: {wms_url}",
                                     TAG, level=Qgis.Info)

            exit_status, response_json, error  = self.api_request.wms_reload(source_id, wms_url)
            QgsMessageLog.logMessage(f"DEBUGGING Exit status reload {exit_status}.", TAG, level=Qgis.Critical)
            exit_status_list.append(exit_status)
        if exit_status == 200:
            reloaded_source_ids.append(source_id)

        QgsMessageLog.logMessage(f"DEBUGGING Exit status reload LIST {exit_status_list}.", TAG, level=Qgis.Critical)

        if not all(status == 200 for status in exit_status_list):
            QgsMessageLog.logMessage(f"WMS could not be reloaded in Mapbender.", TAG, level=Qgis.Critical)
            show_fail_box_ok("Failed",
                             f"WMS could not be reloaded in Mapbender.")
            return 1, reloaded_source_ids

        QgsMessageLog.logMessage("All sources reloaded successfully.", TAG, level=Qgis.Info)
        return 0, reloaded_source_ids

    def _add_new_source(self) -> int:
        QgsMessageLog.logMessage(f"DEBUGGING Adding new source with URL: {self.wms_url}", TAG, level=Qgis.Info)
        exit_status, source_id, error = self.api_request.wms_add(self.wms_url)
        QgsMessageLog.logMessage(f"DEBUGGING Response in MapbenderApiUpload: status={exit_status}, source_id={source_id}, error={error}", TAG,
                                 level=Qgis.Info)

        if exit_status != 200 or not source_id:
            QgsMessageLog.logMessage(f"WMS could not be added to Mapbender. Reason: {error}", TAG, level=Qgis.Critical)
            show_fail_box_ok("Failed",
                             f"WMS could not be added to Mapbender. Reason: {error}")
            return 1, []

        QgsMessageLog.logMessage(f"New source added with ID: {source_id}", TAG, level=Qgis.Info)
        return 0, [source_id]

    def app_clone(self, template_slug: str) -> tuple[int, str, Optional[str]]:
        """
        Clones an existing application in the Application backend. This will create a new application with
        a _imp suffix as application name.
        :param template_slug: template slug to clone
        :return: exit_status (0 = success, 1 = fail),
        :return:slug of the new clone app
        :return:error_output
        """
        QgsMessageLog.logMessage(f"Sending request application/clone '{template_slug}'", TAG, level=Qgis.Info)
        exit_status, response_json, error_output =  self.api_request.app_clone(template_slug)
        QgsMessageLog.logMessage(f"DEBUGGING '{exit_status, response_json, error_output}'", TAG, level=Qgis.Info)

        if response_json and "message" in response_json:
            # Extrahiere den Slug aus der Nachricht
            message = response_json["message"]
            try:
                slug = (message.split("slug", 1)[1]).split(",")[0].strip()
            except IndexError:
                slug = None
                QgsMessageLog.logMessage("Failed to parse slug from message.", TAG, level=Qgis.Warning)
        else:
            slug = None
            QgsMessageLog.logMessage("No valid message in response_json.", TAG, level=Qgis.Warning)
        return exit_status, slug, error_output

    def wms_assign(self, slug: str, source_id: int, layer_set: str) -> tuple[int, str, Optional[str]]:
        """
        :param slug:
        :param source_id:
        :param layer_set:
        :return: exit_status (0 = success, 1 = fail), output, error_output
        """
        QgsMessageLog.logMessage(f"Sending request wms/assign '{slug}' '{source_id}' '{layer_set}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = self.api_request.wms_assign(slug, source_id, layer_set)

        if output is None:
            output = ""
        if error_output is None:
            error_output = ""

        QgsMessageLog.logMessage(f"Exit status {exit_status}, output: {output}, error: {error_output}", TAG,
                                 level=Qgis.Info)
        return exit_status, output, error_output