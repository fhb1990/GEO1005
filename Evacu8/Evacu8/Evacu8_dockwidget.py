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
        self.canvas = self.iface.mapCanvas()

        # set up GUI operation signals
        # data
        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.iface.legendInterface().itemRemoved.connect(self.updateLayers)
        self.iface.legendInterface().itemAdded.connect(self.updateLayers)
        self.load_scen.clicked.connect(self.openScenario)
        self.set_pt.clicked.connect(self.AttackPoint)
        self.set_rad.clicked.connect(self.calculateBuffer)
        self.selectLayerCombo.activated.connect(self.setSelectedLayer)
        self.selectAttributeCombo.activated.connect(self.setSelectedAttribute)


    def closeEvent(self, event):
        # disconnect interface signals
        try:
            self.iface.projectRead.disconnect(self.updateLayers)
            self.iface.newProjectCreated.disconnect(self.updateLayers)
            self.iface.legendInterface().itemRemoved.disconnect(self.updateLayers)
            self.iface.legendInterface().itemAdded.disconnect(self.updateLayers)
        except:
            pass

        self.closingPlugin.emit()
        event.accept()

    ##Functions##
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
        if scenario_open:
            self.updateLayers()

    # Data Functions#
    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
        else:
            self.selectAttributeCombo.clear()
            self.clearChart()


    def setSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        self.updateAttributes(layer)

    def getSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def updateAttributes(self, layer):
        self.selectAttributeCombo.clear()
        if layer:
            self.clearReport()
            self.clearChart()
            fields = uf.getFieldNames(layer)
            if fields:
                self.selectAttributeCombo.addItems(fields)
                self.setSelectedAttribute()
                # send list to the report list window
                self.updateReport(fields)


    def setSelectedAttribute(self):
        field_name = self.selectAttributeCombo.currentText()
        self.updateAttribute.emit(field_name)

    def getSelectedAttribute(self):
        field_name = self.selectAttributeCombo.currentText()
        return field_name

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

    # buffer functions
    def getBufferCutoff(self):
        buffer = self.buff_area.text()
        if uf.isNumeric(buffer):
            return uf.convertNumeric(buffer)
        else:
            return 0

    def calculateBuffer(self):
        origins = self.getSelectedLayer().selectedFeatures()
        layer = self.getSelectedLayer()
        if origins > 0:
            cutoff_distance = self.getBufferCutoff()
            buffers = {}
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance,12).asPolygon()
            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QtCore.QVariant.String, QtCore.QVariant.Double]
                buffer_layer = uf.createTempLayer('Buffers','POLYGON',layer.crs().postgisSrid(), attribs, types)
                uf.loadTempLayer(buffer_layer)
                buffer_layer.setLayerName('Buffers')
            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0],cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.refreshCanvas(buffer_layer)

    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()
