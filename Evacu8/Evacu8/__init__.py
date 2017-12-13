# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Evacu8
                                 A QGIS plugin
 Evacuation Plugin
                             -------------------
        begin                : 2017-12-13
        copyright            : (C) 2017 by group3
        email                : bouzasbasilis@hotmail.com
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


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Evacu8 class from file Evacu8.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .Evacu8 import Evacu8
    return Evacu8(iface)
