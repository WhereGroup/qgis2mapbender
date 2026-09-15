"""
/***************************************************************************
 QGIS2Mapbender
 A plugin to publish QGIS Projects via a Mapbender server instance.
                             -------------------
        begin                : 2024-02-12
        copyright            : (C) 2024 by WhereGroup GmbH
        email                : carmen.viesca@wheregroup.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    from .plugin import Qgis2Mapbender
    return Qgis2Mapbender(iface)

