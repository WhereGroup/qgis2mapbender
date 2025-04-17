import json

from qgis.core import QgsMessageLog, Qgis

from .helpers import waitCursor
from .settings import TAG


class MapbenderApiUpload:
    def __init__(self, connection, server_config, wms_url):
        self.server_config = server_config
        self.wms_url = wms_url
        self.connection = connection



    def wms_show(self):
        """
        Displays layer information of a persisted WMS source.
        Parses the url of the WMS Source to get the information.
        :param url: url of the WMS Source
        :return: exit_status (0 = success, 1 = fail),
        :return: sources_ids (list with sources ids if available)
        """
        QgsMessageLog.logMessage(f"Executing wms:show --json '{self.wms_url}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = self.run_mapbender_command(f"wms:show --json '{self.wms_url}'")
        #     if options:
        #         options_string = " ".join(("--{option}" for option in options))
        #     ... = run_app_console_mapbender_command(f"wms:parse:url {options_string if options_string else ''} {wms_id} {file_path}")
        #     ...
        if exit_status == 0:
            parsed_json = json.loads(output)
            sources_ids = [obj["id"] for obj in parsed_json]
            QgsMessageLog.logMessage(f"Exit status {exit_status}, source(s) ID(s): {sources_ids}'", TAG,
                                     level=Qgis.Info)
        else:
            sources_ids = []
            QgsMessageLog.logMessage(f"Exit status {exit_status}, source(s) ID(s): {sources_ids}'", TAG,
                                     level=Qgis.Info)
        return exit_status, sources_ids

    def wms_add(self):
        """
        Adds a new WMS Source to your Mapbender Service repository.
        :param url: url of the WMS Source
        :return: exit_status (0 = success, 1 = fail),
        :return: source_id (id of the new added source)
        """
        QgsMessageLog.logMessage(f"Executing wms:add '{self.wms_url}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = self.run_mapbender_command(f"wms:add '{self.wms_url}'")
        if exit_status == 0 and output:
            spl = 'Saved new source #'
            source_id = output.split(spl, 1)[1]
            QgsMessageLog.logMessage(f"Exit status {exit_status}, new source ID: {source_id}'", TAG, level=Qgis.Info)
        else:
            source_id = ''
            QgsMessageLog.logMessage(f"Exit status: {exit_status}, failed, no new source ID {source_id}'", TAG,
                                     level=Qgis.Info)
        return exit_status, source_id, error_output

    def wms_reload(self, id):
        """
        Reloads (updates) a WMS source from given url.
        :param id: existing source id
        :param url: url of the WMS Source
        :return: exit_status (0 = success, 1 = fail)
        """
        QgsMessageLog.logMessage(f"Executing wms:reload:url {id} '{self.wms_url}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = self.run_mapbender_command(f"wms:reload:url {id} '{self.wms_url}'")
        QgsMessageLog.logMessage(f"Exit status: {exit_status}, output: {output}, error: {error_output}'", TAG,
                                 level=Qgis.Info)
        return exit_status, output, error_output

    def app_clone(self, template_slug):
        """
        Clones an existing application in the Application backend. This will create a new application with
        a _imp suffix as application name.
        :param template_slug: template slug to clone
        :return: exit_status (0 = success, 1 = fail),
        :return:slug of the new clone app
        :return:error_output
        """
        QgsMessageLog.logMessage(f"Executing application:clone '{template_slug}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = self.run_mapbender_command(f"application:clone '{template_slug}'")
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
        QgsMessageLog.logMessage(f"Executing wms:assign '{slug}' '{source_id}' '{layer_set}'", TAG, level=Qgis.Info)
        exit_status, output, error_output = (
            self.run_mapbender_command(f"wms:assign '{slug}' '{source_id}' '{layer_set}'"))
        QgsMessageLog.logMessage(f"Exit status {exit_status}, output: {output}, error: {error_output}'", TAG,
                                 level=Qgis.Info)
        return exit_status, output, error_output
