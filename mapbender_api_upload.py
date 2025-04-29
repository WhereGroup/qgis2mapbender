import json

from qgis.core import QgsMessageLog, Qgis

from .api_request import ApiRequest
from .helpers import waitCursor, show_fail_box_ok, show_succes_box_ok
from .settings import TAG


class MapbenderApiUpload:
    def __init__(self, server_config, wms_url):
        self.server_config = server_config
        self.wms_url = wms_url
        self.api_request = ApiRequest(self.server_config)
        QgsMessageLog.logMessage(f"Initializing MapbenderApiUpload...", TAG, level=Qgis.Info)

    def mb_upload(self) -> None:
        try:
            exit_status_wms_show, source_ids = self.wms_show()
            if exit_status_wms_show == 1:
                show_fail_box_ok("Failed",
                                 f"WMS layer information could not be displayed. "
                                 f"Mapbender upload will be interrupted.")
                return 1, []

            if source_ids:
                self._reload_sources(source_ids)
            else:
                self._add_new_source()

            return 0, source_ids

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
            QgsMessageLog.logMessage(f"Error from wms/show: {output}", TAG, level=Qgis.Warning)
            return exit_status, []

        if not output.get("success", False):
            QgsMessageLog.logMessage("Request to wms/show not successful.", TAG, level=Qgis.Warning)
            return exit_status, []

        source_ids = [item['id'] for item in output.get('message', []) if isinstance(item, dict) and 'id' in item]
        QgsMessageLog.logMessage(f"DEBUGGING Raw output: {output}", TAG, level=Qgis.Info)
        QgsMessageLog.logMessage(f"Extrahierte Source-IDs: {source_ids}", TAG, level=Qgis.Info)
        return exit_status, source_ids

    def _reload_sources(self, source_ids: list[int]) -> None:
        exit_status_list = []
        for source_id in source_ids:
            exit_status, _, _ = self.api_request.wms_reload(source_id, self.wms_url)
            exit_status_list.append(exit_status)

        if not all(status == 0 for status in exit_status_list):
            QgsMessageLog.logMessage(f"WMS could not be reloaded in Mapbender.", TAG, level=Qgis.Critical)
            show_fail_box_ok("Failed",
                             f"WMS could not be reloaded in  Mapbender.")
        else:
            QgsMessageLog.logMessage("All sources reloaded successfully.", TAG, level=Qgis.Info)

    def _add_new_source(self) -> None:
        exit_status, source_id, error = self.api_request.wms_add(self.wms_url)
        if exit_status != 0 or not source_id:
            QgsMessageLog.logMessage("WMS could not be added to Mapbender. Reason: {error}", TAG, level=Qgis.Critical)
            show_fail_box_ok("Failed",
                             f"WMS could not be added to Mapbender. Reason: {error}")
        else:
            QgsMessageLog.logMessage(f"New source added with ID: {source_id}", TAG, level=Qgis.Info)

    def app_clone(self, template_slug):
        """
        Clones an existing application in the Application backend. This will create a new application with
        a _imp suffix as application name.
        :param template_slug: template slug to clone
        :return: exit_status (0 = success, 1 = fail),
        :return:slug of the new clone app
        :return:error_output
        """
        QgsMessageLog.logMessage(f"Sending request application/clone '{template_slug}'", TAG, level=Qgis.Info)
        exit_status, output, error_output =  self.api_request.app_clone(template_slug)
        if output != '':
            spl = 'slug'
            slug = (output.split(spl, 1)[1]).split(',')[0].strip()
            QgsMessageLog.logMessage(f"Exit status {exit_status}, output: {output}, error: {error_output}'", TAG,
                                     level=Qgis.Info)
        else:
            slug = ''
            QgsMessageLog.logMessage(f"Exit status {exit_status}, output: {output}, error: {error_output}'", TAG,
                                     level=Qgis.Info)
        return exit_status, output, slug, error_output

    def wms_assign(self, slug, source_id, layer_set):
        """
        :param slug:
        :param source_id:
        :param layer_set:
        :return: exit_status (0 = success, 1 = fail), output, error_output
        """
        QgsMessageLog.logMessage(f"Sending request wms/assign '{slug}' '{source_id}' '{layer_set}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = self.api_request.wms_assign(source_id, layer_set)
        QgsMessageLog.logMessage(f"Exit status {exit_status}, output: {output}, error: {error_output}'", TAG,
                                 level=Qgis.Info)
        return exit_status, output, error_output
