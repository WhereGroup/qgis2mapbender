# Only no editable configurations

# General
PLUGIN_SETTINGS_SERVER_CONFIG_KEY = 'QGIS2Mapbender'
TAG = 'QGIS2Mapbender'

# Timeout settings for HTTP requests
REQUEST_TIMEOUT_SIMPLE = 30
REQUEST_TIMEOUT_API = (10, 300)

# Maximum length of server error details shown in a message box
MAX_API_ERROR_MESSAGE_LENGTH = 500

# QGIS project storage types
PROJECT_STORAGE_LOCAL = 'local'
PROJECT_STORAGE_DATABASE = 'database'
PROJECT_STORAGE_UNSUPPORTED = 'unsupported'
PROJECT_STORAGE_UNSAVED = 'unsaved'
DATABASE_PROJECT_STORAGE_BACKENDS = frozenset({'geopackage', 'postgresql'})
