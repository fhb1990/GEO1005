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
from PyQt4.QtGui import QColor
from qgis._core import QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint, QgsSpatialIndex, QGis
from qgis._gui import QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker
from qgis.utils import iface

import random
import processing

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
        self.toolPoly = PolyMapTool(self.canvas)

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
        self.shortestRouteButton.clicked.connect(self.buildNetwork)
        self.shortestRouteButton.clicked.connect(self.calculateRoute)
        self.select_POI.clicked.connect(self.evacWhich)
        self.tied_points = []

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

            symbols = layer.rendererV2().symbols()
            symbol = symbols[0]
            symbol.setSize(5)
            symbol.setColor(QColor.fromRgb(50, 50, 250))

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
        layer = uf.getLegendLayerByName(self.iface, "Attack Point")
        origins = layer.getFeatures()
        #origins = self.getSelectedLayer().selectedFeatures()
        #layer = self.getSelectedLayer()
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
                buffer_layer = uf.createTempLayer('Buffers','POLYGON',layer.crs().postgisSrid(), attribs, types, 30)
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
        self.canvas.setMapTool(self.toolPoly)


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



    # picking
    def evacWhich(self):
        lineLayer = uf.getLegendLayerByName(iface, "road_net")
        provider = lineLayer.dataProvider()

        spIndex = QgsSpatialIndex()  # create spatial index object

        feat = QgsFeature()
        fit = provider.getFeatures()  # gets all features in layer

        # insert features to index
        while fit.nextFeature(feat):
            spIndex.insertFeature(feat)

        pt = QgsPoint(91000, 437000)

        # QgsSpatialIndex.nearestNeighbor (QgsPoint point, int neighbors)
        nearestIds = spIndex.nearestNeighbor(pt, 1)  # we need only one neighbour
        featureId = nearestIds[0]
        lineLayer.select(featureId)


    # route functions
    def getNetwork(self):
        roads_layer = self.getSelectedLayer()
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            if obstacles_layer:
                # retrieve roads outside obstacles (inside = False)
                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
                # add these roads to a new temporary layer
                road_network = uf.createTempLayer('Temp_Network','LINESTRING',roads_layer.crs().postgisSrid(),[],[])
                road_network.dataProvider().addFeatures(features)
            else:
                road_network = roads_layer
            return road_network
        else:
            return

    def buildNetwork(self):
        self.network_layer = self.getNetwork()
        if self.network_layer:
            # get the points to be used as origin and destination
            # in this case gets the centroid of the selected features
            selected_sources = self.getSelectedLayer().selectedFeatures()
            source_points = [feature.geometry().centroid().asPoint() for feature in selected_sources]
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
                # the tied points are the new source_points on the graph
                if self.graph and self.tied_points:
                    text = "network is built for %s points" % len(self.tied_points)
                    self.insertReport(text)
        return

    def calculateRoute(self):
        # origin and destination must be in the set of tied_points
        options = len(self.tied_points)
        if options > 1:
            # origin and destination are given as an index in the tied_points list
            origin = 0
            destination = random.randint(1, options - 1)
            # calculate the shortest path for the given origin and destination
            path = uf.calculateRouteDijkstra(self.graph, self.tied_points, origin, destination)
            # store the route results in temporary layer called "Routes"
            routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
            # create one if it doesn't exist
            if not routes_layer:
                attribs = ['id']
                types = [QtCore.QVariant.String]
                routes_layer = uf.createTempLayer('Routes', 'LINESTRING', self.network_layer.crs().postgisSrid(),
                                                  attribs, types)

                symbols = routes_layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setWidth(1.5)
                symbol.setColor(QColor.fromRgb(250,50,50))

                uf.loadTempLayer(routes_layer)
            # insert route line
            for route in routes_layer.getFeatures():
                print route.id()
            uf.insertTempFeatures(routes_layer, [path], [['testing', 100.00]])
            # self.refreshCanvas(routes_layer)


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


class PolyMapTool(QgsMapToolEmitPoint):

    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubberband = QgsRubberBand(self.canvas, QGis.Polygon)
        self.rubberband.setColor(QColor(0,0,0))
        self.rubberband.setWidth(1)
        self.point = None
        self.points = []
        self.layer = QgsVectorLayer('Polygon?crs=epsg:28992', 'Danger Zone', "memory")

    def canvasPressEvent(self, e):
        self.point = self.toMapCoordinates(e.pos())
        m = QgsVertexMarker(self.canvas)
        m.setCenter(self.point)
        m.setColor(QColor(0,255,0))
        m.setIconSize(5)
        m.setIconType(QgsVertexMarker.ICON_BOX)
        m.setPenWidth(3)
        self.points.append(self.point)
        self.showPoly()

    def showPoly(self):
        self.rubberband.reset(QGis.Polygon)
        for point in self.points[:-1]:
            self.rubberband.addPoint(point, False)
        self.rubberband.addPoint(self.points[-1], True)
        self.rubberband.show()
        if len(self.points) == 4:
            self.poly()
            self.rubberband = QgsRubberBand(self.canvas, QGis.Polygon)
            self.rubberband.setColor(QColor(0, 0, 0))
            self.rubberband.setWidth(1)
            self.point = None
            self.points = []

    def poly(self):
        geom = self.rubberband.asGeometry()

        # Set the provider to accept the data source
        pr = self.layer.dataProvider()

        # Add a new feature and assign the geometry
        feat = QgsFeature()
        feat.setGeometry(geom)
        pr.addFeatures([feat])

        # Update extent of the layer
        self.layer.updateExtents()

        # Add the layer to the Layers panel
        QgsMapLayerRegistry.instance().addMapLayers([self.layer])