# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Evacu8DockWidget
                                 A QGIS plugin
 Evacuation Plugin
                             -------------------
        begin                : 2017-12-13
        git sha              : $Format:%H$
        copyright            : (C) 2017 by group3
        email                : bouzasbasilis@hotmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal
from qgis._core import QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint
from qgis.utils import iface
from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Evacu8_dockwidget_base.ui'))




class Evacu8DockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(Evacu8DockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        #define globals
        self.iface = iface

        # set up GUI operation signals
        # data
        self.load_scen.clicked.connect(self.openScenario)
        self.set_pt.clicked.connect(self.AttackPoint)


    ##Functions##
    #Data Functions#
    #Open Scenario
    def openScenario(self,filename=""):
        scenario_open = False
        scenario_file = os.path.join(u'/Users/jorge/github/GEO1005', 'sample_data', 'time_test.qgs')
        # check if file exists
        if os.path.isfile(scenario_file):
            self.iface.addProject(scenario_file)
            scenario_open = True
        else:
            last_dir = uf.getLastDir("data")
            new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
            if new_file:
                self.iface.addProject(unicode(new_file))
                scenario_open = True


    def AttackPoint(self, event):
        # Specify the geometry type
        layer = QgsVectorLayer('Point?crs=epsg:28992', 'Attack Point', 'memory')

        # Set the provider to accept the data source
        prov = layer.dataProvider()
        point = QgsPoint(85000, 447000)

        # Add a new feature and assign the geometry
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPoint(point))
        prov.addFeatures([feat])

        # Update extent of the layer
        layer.updateExtents()

        # Add the layer to the Layers panel
        QgsMapLayerRegistry.instance().addMapLayers([layer])


    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()