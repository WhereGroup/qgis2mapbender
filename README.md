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
- Create at least one template application in Mapbender (that will be cloned and used to publish a new WMS) or an application that will be used to publish a new WMS. These applications should have at least one layerset: 
  - layerset named "main" (default layerset for adding a new WMS to the application) OR 
  - layerset named with any other name (in this case, the name of the layerset should be specified when using the plugin)

### Docker
- QGIS Server and Mapbender can be run as Docker containers.

Here is a sample docker-compose.yml file to set up a docker for Mapbender and QGIS Server.
This configuration requires to have a folder `volumes/qgis/` that contains a QGIS project file called `/worldmap/worldmap.qgz`

```yaml
services:
  mapbender:
    image: mapbender/mapbender
    restart: always
    ports:
      - 8080:8080
    volumes:
      - ./volumes/mapbender/db:/var/mapbender/application/var/db:rw
  qgis:
    image: qgis/qgis-server:3.36.3-noble
    restart: always
    ports:
      - 80:80
    environment:
      - QGIS_PROJECT_FILE=/qgis/projects/worldmap/worldmap.qgz
    volumes:
      - ./volumes/qgis:/qgis/projects:ro
```

### Configuring the connection to the server 
The figure below shows a typical configuration of the connection to the server and its adaptation to a Docker virtualisation.
![](resources/config_qgis2mapbender_examples.png)

A few comments on a standard configuration with and without Docker:

|**Description**| **Without Docker**                                                                                                                                                                  |**With Docker**|
| :--------------------------------------- |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| :-------------------------- |
|**QGIS-Projects Path:** This is the path on the server where QGIS projects are uploaded. For Docker, it is necessary to specify the mount volume of the running container for QGIS Server. | /data/qgis-projects                                                                                                                                                                 |{path_to_docker_compose.yml}/volumes/qgis/ for the example above|
|<p>**QGIS-Server URL:** The relative path from the server address to access QGIS Server services.</p><p></p><p></p><p></p><p></p>| <p>cgi-bin/qgis\_mapserv.fcgi</p><p></p><p>example of getCapabilities:</p><p>http://mapbender-qgis.wheregroup.lan/cgi-bin/qgis\_mapserv.fcgi?SERVICE=WMS&REQUEST=GetCapabilities</p>|<p>/ows</p><p></p><p>example of getCapabilities:</p><p>http://mb-qgis-docker.wheregroup.lan/ows/?SERVICE=WMS&REQUEST=GetCapabilities </p>|
|**Mapbender Application Path:** The path to the Mapbender application. | /data/mapbender/application                                                                                                                                                         |{path_to_docker_compose.yml}|
|**Mapbender `bin/console` Command:** Mapbender's command-line tool for performing various operations (such as adding a new WMS or managing a Mapbender project). When using Docker, this command must be executed inside the running container. | bin/console                                                                                                                                                                         |docker compose exec mapbender bin/console|
|**Mapbender Base URL:** The home page of Mapbender where all applications are listed. | mapbender/                                                                                                                                                           |:8080/ |


## Support
info@wheregroup.com

## License
The plugin is licensed under the attached GNU General Public License.
