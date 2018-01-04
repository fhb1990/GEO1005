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
import os.path

from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal
from qgis._core import QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint
from qgis._gui import QgsMapToolEmitPoint
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
        self.emitPoint = QgsMapToolEmitPoint(self.canvas)

        # set up GUI operation signals
        # data
        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.iface.legendInterface().itemRemoved.connect(self.updateLayers)
        self.iface.legendInterface().itemAdded.connect(self.updateLayers)
        self.load_scen.clicked.connect(self.openScenario)
        self.set_pt.clicked.connect(self.enterPoi)
        self.emitPoint.canvasClicked.connect(self.getPoint)
        self.set_rad.clicked.connect(self.calculateBuffer)
        self.selectLayerCombo.activated.connect(self.setSelectedLayer)
        self.selectAttributeCombo.activated.connect(self.setSelectedAttribute)
        self.set_danger.clicked.connect(self.DangerZone)

        # analysis
        self.selectBufferButton.clicked.connect(self.POI_selection)

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

    # Attack Point
    def enterPoi(self):
        # remember currently selected tool
        self.userTool = self.canvas.mapTool()
        # activate coordinate capture tool
        self.canvas.setMapTool(self.emitPoint)

    def getPoint(self, mapPoint, mouseButton):
        # change tool so you don't get more than one POI
        self.canvas.unsetMapTool(self.emitPoint)
        self.canvas.setMapTool(self.userTool)
        # Get the click
        if mapPoint:
            # Specify the geometry type
            layer = QgsVectorLayer('Point?crs=epsg:28992', 'Attack Point', 'memory')

            # Set the provider to accept the data source
            prov = layer.dataProvider()

            # Add a new feature and assign the geometry
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPoint(mapPoint))
            prov.addFeatures([feat])

            # Update extent of the layer
            layer.updateExtents()

            # Add the layer to the Layers panel
            QgsMapLayerRegistry.instance().addMapLayers([layer])



    # buffer functions#
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


    #Set danger polygon#
    def DangerZone(self):
        # Specify the geometry type
        layer = QgsVectorLayer('Polygon?crs=epsg:28992', 'Danger Zone', "memory")

        # Set the provider to accept the data source
        pr = layer.dataProvider()
        poly = QgsGeometry.fromPolygon(
            [[QgsPoint(84900, 446900), QgsPoint(84900, 447100), QgsPoint(85100, 447100), QgsPoint(85100, 446900)]])

        # Add a new feature and assign the geometry
        feat = QgsFeature()
        feat.setGeometry(poly)
        pr.addFeatures([feat])

        # Update extent of the layer
        layer.updateExtents()

        # Add the layer to the Layers panel
        QgsMapLayerRegistry.instance().addMapLayers([layer])



    #POI selection#
    def POI_selection(self):
        layer = self.getSelectedLayer()
        buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
        if buffer_layer and layer:
            points = uf.getFeaturesIntersections(layer, buffer_layer)
            new_layer = QgsVectorLayer('Point?crs=epsg:28992', 'POIs in', 'memory')
            prov = new_layer.dataProvider()
            for point in points:
                feat = QgsFeature()
                feat.setGeometry(point)
                prov.addFeatures([feat])
            new_layer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayers([new_layer])

            points2 = uf.getFeaturesDifference(layer, buffer_layer)
            new_layer2 = QgsVectorLayer('Point?crs=epsg:28992', 'POIs out', 'memory')
            prov2 = new_layer2.dataProvider()
            for point in points2:
                feat = QgsFeature()
                feat.setGeometry(point)
                prov2.addFeatures([feat])
            new_layer2.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayers([new_layer2])


    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()


    # report window functions
    def updateReport(self,report):
        self.reportList.clear()
        self.reportList.addItems(report)

    def insertReport(self,item):
        self.reportList.insertItem(0, item)

    def clearReport(self):
        self.reportList.clear()