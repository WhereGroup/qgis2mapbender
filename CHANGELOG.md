## v1.1.0

### Features:
* Added german, spanish and italian translations ([#PR28]([https://github.com/WhereGroup/qgis2mapbender/pull/27](https://github.com/WhereGroup/qgis2mapbender/pull/28)))

### Bugfixes:
* Server configuration name with "/" in name deletes whole server configuration ([#PR27](https://github.com/WhereGroup/qgis2mapbender/pull/27))
* Fix import contextmanager and clean imports (PyQt5, _core) [#PR26]((https://github.com/WhereGroup/qgis2mapbender/pull/26))

## v1.0.0

### Features:
* Connection to QGIS Server and Mapbender via Mapbender API
* Direct SSH connection is not used anymore. Any reference to Fabric2 library was removed
* Plugin sets the GetMap format to image/png by default
* Plugin sets the GetFeatureInfo format text/html by default
* Plugin sets the layer ordering to reverse (QGIS) by default
* Improved README
* Simplified server configuration 
* Success dialog provides the link to the QGIS Server service and Mapbender application


## v0.9.2

### Features:
* Add CONTRIBUTE.md, LICENSE, rename resources.
* Reorganisation of the folder structure.
* Add a button to the "Server Configuration Manager" tab to test the SSH connection and verify access to the Mapbender and QGIS server URLs.

### Fixes:
* Fix error in Windows that occurs when the Python console is closed.

## v0.9.1

### Features:
* QGIS Server and Mapbender can also be run as Docker containers.
* Rename dialogs in plugins.
* In the "Server Configuration Manager" tab, add a button to test the SSH connection and verify access to the Mapbender and QGIS server URLs.

