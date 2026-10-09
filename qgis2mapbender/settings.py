# Only no editable configurations

# General
PLUGIN_SETTINGS_SERVER_CONFIG_KEY = 'QGIS2Mapbender'
TAG = 'QGIS2Mapbender'

# Timeout settings for HTTP requests
REQUEST_TIMEOUT_SIMPLE = (10, 30)
REQUEST_TIMEOUT_API = (10, 60) # (connect timeout, read timeout)
# Uploads may spend longer sending and processing large project ZIP files.
REQUEST_TIMEOUT_UPLOAD = (900, 900)

# Accepted root elements of a WMS GetCapabilities response
WMS_CAPABILITIES_ROOT_ELEMENTS = frozenset((
    "WMS_Capabilities",
))

# Maximum length of server error details shown in a message box
MAX_API_ERROR_MESSAGE_LENGTH = 500

# QGIS project storage types
PROJECT_STORAGE_LOCAL = 'local'
PROJECT_STORAGE_GEOPACKAGE = 'geopackage'
PROJECT_STORAGE_POSTGRESQL = 'postgresql'
PROJECT_STORAGE_UNSAVED = 'unsaved'
QGIS_SERVER_POSTGRESQL_WRAPPER_PATH = '/qgis/'
