# QGIS2Mapbender

## Description
QGIS plugin to transfer your QGIS Server project on your server and publish your QGIS Server WMS in Mapbender.

## Installation and Requirements
### Installing the plugin
Installation is possible directly from the QGIS plugin repository.
Alternatively, a release can be downloaded here and the zipped folder can be installed manually as a QGIS extension. There are no further dependencies.

### Requirements on your local system
- The QGIS project must be saved in the same folder as the data.

### Requirements on your server
- QGIS Server is installed on your server.
- Mapbender is installed on your server.

### Requirements on your Mapbender instance

**Apache**
- Configure Apache authorisation and upload directory (see https://doc.mapbender.org/en/customization/api.html)

**PHP**
- Configure the following parameters in php.ini to match the characteristics of the projects you plan to upload to the server. Remember that the folder containing your project and data will be zipped for uploading to the server.

  - **upload_max_filesize** - the maximum size of an uploaded file. 
  - **post_max_size** - maximum size of all data sent via a POST request, its value should be equal to or greater than upload_max_filesize
  - **max_execution_tine** - this sets the maximum time in seconds a script is allowed to parse input data.


**Mapbender**

- Application: Create at least one template application in Mapbender (that can be copied and can be used to publish a new WMS) or an application that will be used directly to publish a new WMS. 

- The applications should have at least one instance of a map and one layerset.
  
 Note: The field "layerset" in QGIS2Mapbender is the id or name of the layerset to use. Defaults are "main" or the first layerset in the application.

- User/Groups: All Mapbender users that should be authorized to use QGIS2Mapbender need special rights. There is only one exception and this is the Mapbender super user with the id 1, where this permission is automatically granted. 

  - User/group needs to have the global permission **access_api** and **upload_files** in order to perform any operation on the API and to be able to upload files.
  - User/group needs the global permission **create_applications** 
  - User/group needs the global permission **sources_view**  
  - User/group need to have **read** rights on the template application 


### Configuring the connection to the server 

The figure below shows a typical configuration of the connection to the server.

![QGIS2Mapbender server configuration](resources/img_server_config_readme.png)

A few comments on a standard configuration:

| **Parameter**          | **Description**                                           | **Example**                          |
|------------------------|-----------------------------------------------------------|-----------------------------------------------|
| **Mapbender base URL** | Link to your Mapbender landing page (application overview) | http://localhost/mapbender/  |                                                                                                                                  |
| **QGIS Server URL**   | URL to access your QGIS Server              | http://localhost/cgi-bin/qgis_mapserv.fcgi   |


## Support
info@wheregroup.com

## License
The plugin is licensed under the attached GNU General Public License.
