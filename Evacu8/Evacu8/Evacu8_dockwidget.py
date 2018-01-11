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
from PyQt4.QtCore import pyqtSignal, Qt, QVariant
from PyQt4.QtGui import QColor
from qgis._core import QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint, QgsSpatialIndex, QGis, \
    QgsDistanceArea, QgsTolerance, QgsRectangle
from qgis._gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.utils import iface

import random

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
        self.emitEvac = QgsMapToolEmitPoint(self.canvas)
        self.emitShel = QgsMapToolEmitPoint(self.canvas)

        # set up GUI operation signals
        # data
        self.load_scen.clicked.connect(self.openScenario)
        self.set_pt.clicked.connect(self.enterPoi)
        self.emitPoint.canvasClicked.connect(self.getPoint)
        self.set_rad.clicked.connect(self.calculateBuffer)
        # self.set_rad.clicked.connect(self.POI_selection)
        self.set_danger.clicked.connect(self.setDangerZone)
        self.get_danger.clicked.connect(self.getDangerZone)

        # set images and icons
        self.logo.setPixmap(QtGui.QPixmap(':images\Logo.jpeg'))
        self.legend.setPixmap(QtGui.QPixmap(':images\Legend.png'))

        # analysis
        self.evac = None
        self.evacId = int()
        self.shel = None
        self.shelId = int()

        self.evac_layer = None
        self.evac_feat = None
        self.shel_layer = None
        self.shel_feat = None

        self.select_POI.clicked.connect(self.enterEvac)
        self.emitEvac.canvasClicked.connect(self.getEvac)
        self.desel_POI.clicked.connect(self.deleteEvac)
        self.select_shelter.clicked.connect(self.enterShel)
        self.emitShel.canvasClicked.connect(self.getShel)
        self.shortestRouteButton.clicked.connect(self.buildNetwork)
        self.shortestRouteButton.clicked.connect(self.calculateRoute)
        self.tied_points = []
        self.to_evac_info.setVerticalHeaderLabels(["Type", "Name", "Adr.", "Pop.","Dist."])
        self.shelter_info.setVerticalHeaderLabels(["Type", "Name", "Adr.", "Cap.","Route"])

    def closeEvent(self, event):
        # disconnect interface signa
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
            self.atk_pt = QgsPoint(mapPoint)
            self.distance()
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


    def distance(self):
        layers = ["Schools points", "Hospitals points", "Nursery Homes points"]
        for layer in layers:
            vl = uf.getLegendLayerByName(self.iface, layer)
            uf.addFields(vl, ['distance'], [QVariant.Double])
            index = vl.fieldNameIndex('distance')

            feats = vl.getFeatures()
            dist = QgsDistanceArea()
            vl.startEditing()
            for feat in feats:
                geom = feat.geometry()
                pt = geom.asPoint()
                m = dist.measureLine(self.atk_pt, pt)
                vl.changeAttributeValue(feat.id(), index, m)
            vl.commitChanges()


    # buffer functions
    def getBufferCutoff(self):
        buffer = self.buff_area.text()
        if uf.isNumeric(buffer):
            return uf.convertNumeric(buffer)
        else:
            return 0

    def calculateBuffer(self):
        layer = uf.getLegendLayerByName(self.iface, "Attack Point")
        origins = layer.getFeatures()
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
                buffer_layer = uf.createTempLayer('Buffers','POLYGON',layer.crs().postgisSrid(), attribs, types, 70)
                uf.loadTempLayer(buffer_layer)
                buffer_layer.setLayerName('Buffers')
                symbols = buffer_layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor.fromRgb(220, 220, 0))
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

            extent = buffer_layer.extent()
            self.canvas.setExtent(extent)

        layers = ["Schools points", "Hospitals points", "Nursery Homes points", "road_net"]
        for layer in layers:
            vl = uf.getLegendLayerByName(self.iface, layer)
            iface.legendInterface().setLayerVisible(vl, True)


    # Set danger polygon
    def setDangerZone(self):
        self.canvas.setMapTool(self.toolPoly)

    def getDangerZone(self):
        self.canvas.unsetMapTool(self.toolPoly)


    #POI selection#
    # def POI_selection(self, mapPoint):
    #     init_layers = ["Schools points", "Hospitals points", "Nursery Homes points"]
    #     layers_in = ['Schools in', 'Hospitals in', 'Nursery Homes in']
    #     layers_out = ['Schools out', 'Hospitals out', 'Nursery Homes out']
    #
    #     buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
    #     if len(QgsMapLayerRegistry.instance().mapLayersByName('Schools in')) == 0:
    #         for init_layer, layer_in, layer_out in zip(init_layers, layers_in, layers_out):
    #             layer = uf.getLegendLayerByName(self.iface, init_layer)
    #             if buffer_layer and layer:
    #                 points = uf.getFeaturesIntersections(layer, buffer_layer)
    #                 new_layer = QgsVectorLayer('Point?crs=epsg:28992', layer_in, 'memory')
    #                 prov = new_layer.dataProvider()
    #                 for point in points:
    #                     feat = QgsFeature()
    #                     feat.setGeometry(point)
    #                     prov.addFeatures([feat])
    #                 new_layer.updateExtents()
    #                 QgsMapLayerRegistry.instance().addMapLayers([new_layer])
    #                 iface.legendInterface().setLayerVisible(new_layer, False)
    #                 uf.addFields(new_layer, ['distance'], [QVariant.String])
    #                 uf.updateField(new_layer, 'distance', '3')
    #
    #                 points2 = uf.getFeaturesDifference(layer, buffer_layer)
    #                 new_layer2 = QgsVectorLayer('Point?crs=epsg:28992', layer_out, 'memory')
    #                 prov2 = new_layer2.dataProvider()
    #                 for point in points2:
    #                     feat = QgsFeature()
    #                     feat.setGeometry(point)
    #                     prov2.addFeatures([feat])
    #                 new_layer2.updateExtents()
    #                 QgsMapLayerRegistry.instance().addMapLayers([new_layer2])
    #                 iface.legendInterface().setLayerVisible(new_layer2, False)
    #                 uf.addFields(new_layer2, ['distance'], [QVariant.String])
    #                 uf.updateField(new_layer2, 'distance', '3')


    # picking
    def enterEvac(self):
        self.canvas.setMapTool(self.emitEvac)

    def getEvac(self, evac):
        self.canvas.unsetMapTool(self.emitEvac)

        if evac:
            lineLayer = uf.getLegendLayerByName(iface, "road_net")
            provider = lineLayer.dataProvider()

            spIndex = QgsSpatialIndex()  # create spatial index object

            feat = QgsFeature()
            fit = provider.getFeatures()  # gets all features in layer

            # insert features to index
            while fit.nextFeature(feat):
                spIndex.insertFeature(feat)

            self.evac = QgsPoint(evac)

            # QgsSpatialIndex.nearestNeighbor (QgsPoint point, int neighbors)
            nearestIds = spIndex.nearestNeighbor(self.evac, 1)  # we need only one neighbour
            self.evacId = nearestIds[0]
            lineLayer.select(self.evacId)

            self.evac_layer, self.evac_feat = self.select(self.evac)
            self.to_evac_table()

    def select(self, point):
        layers = ["Schools points", "Hospitals points", "Nursery Homes points"]

        min_dist = QgsDistanceArea()
        min_layer = QgsVectorLayer()
        for layer in layers:
            vl = uf.getLegendLayerByName(self.iface, layer)

            feats = vl.getFeatures()
            for feat in feats:
                geom = feat.geometry()
                pt = geom.asPoint()
                dist = QgsDistanceArea().measureLine(point, pt)
                if dist < min_dist:
                    min_dist = dist
                    min_feat = feat
                    min_id = feat.id()
                    min_layer = vl

        min_layer.select(min_id)
        self.canvas.setSelectionColor(QColor("red"))
        self.canvas.refresh()

        return min_layer, min_feat

    def deleteEvac(self):
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        if routes_layer:
            QgsMapLayerRegistry.instance().removeMapLayer(routes_layer.id())
        lineLayer = uf.getLegendLayerByName(iface, "road_net")
        lineLayer.removeSelection()
        self.evac_layer.removeSelection()
        self.refreshCanvas(lineLayer)

    def enterShel(self):
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        if routes_layer:
            QgsMapLayerRegistry.instance().removeMapLayer(routes_layer.id())
        if self.shel_layer:
            self.shel_layer.deselect(self.shel_feat.id())
        lineLayer = uf.getLegendLayerByName(iface, "road_net")
        lineLayer.deselect(self.shelId)
        self.canvas.setMapTool(self.emitShel)

    def getShel(self, shel):
        self.canvas.unsetMapTool(self.emitShel)

        if shel:
            lineLayer = uf.getLegendLayerByName(iface, "road_net")
            provider = lineLayer.dataProvider()

            spIndex = QgsSpatialIndex()  # create spatial index object

            feat = QgsFeature()
            fit = provider.getFeatures()  # gets all features in layer

            # insert features to index
            while fit.nextFeature(feat):
                spIndex.insertFeature(feat)

            self.shel = QgsPoint(shel)

            # QgsSpatialIndex.nearestNeighbor (QgsPoint point, int neighbors)
            nearestIds = spIndex.nearestNeighbor(self.shel, 1)  # we need only one neighbour
            self.shelId = nearestIds[0]
            lineLayer.select(self.shelId)

            self.shel_layer, self.shel_feat = self.select(self.shel)
            self.shelter_table()


    # route functions
    def getNetwork(self):
        roads_layer = uf.getLegendLayerByName(self.iface, "road_net")
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Danger Zones")
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
            selected_sources = uf.getLegendLayerByName(self.iface, "road_net").selectedFeatures()
            source_points = [feature.geometry().centroid().asPoint() for feature in selected_sources]
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
                # the tied points are the new source_points on the graph
                if self.graph and self.tied_points:
                    text = "network is built for %s points" % len(self.tied_points)

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
            self.refreshCanvas(routes_layer)

            lineLayer = uf.getLegendLayerByName(iface, "road_net")
            lineLayer.deselect(self.shelId)
            self.refreshCanvas(lineLayer)

    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

    # Displaying information
    def to_evac_table(self):
        tent_values = self.evac_feat.attributes()
        indices = [2,3,7,8,9]
        values = [tent_values[i] for i in indices]
        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        for i, item in enumerate(values):
            # i is the table row, items must be added as QTableWidgetItems
            self.to_evac_info.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))

    def shelter_table(self):
        if len(QgsMapLayerRegistry.instance().mapLayersByName('Routes')) == 0:
            return
        layer = uf.getLegendLayerByName(self.iface, "Schools points")
        feat = layer.selectedFeatures()
        tent_values = feat[0].attributes()
        indices = [2, 3, 7, 8]
        values = [tent_values[i] for i in indices]
        route = uf.getLegendLayerByName(self.iface, "Routes")
        feat = route.getFeatures()

        # values.append[ROUTE LENGTH]
        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        for i, item in enumerate(values):
            # i is the table row, items must tbe added as QTableWidgetItems
            self.shelter_info.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))



class PolyMapTool(QgsMapToolEmitPoint):

    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubberband = QgsRubberBand(self.canvas, QGis.Polygon)
        self.point = None
        self.points = []
        attribs = ['id']
        types = [QtCore.QVariant.String]
        self.layer = uf.createTempLayer('Danger Zones', 'POLYGON', '28992', attribs, types, 50)
        self.symbols = self.layer.rendererV2().symbols()
        self.symbol = self.symbols[0]
        self.symbol.setColor(QColor.fromRgb(160, 160, 160))

    def canvasPressEvent(self, e):
        self.point = self.toMapCoordinates(e.pos())
        self.points.append(self.point)
        self.showPoly(e)

    def showPoly(self, e):
        self.rubberband.reset(QGis.Polygon)
        for point in self.points[:-1]:
            self.rubberband.addPoint(point, False)
        self.rubberband.addPoint(self.points[-1], True)
        if e.button() == Qt.RightButton:
            self.poly()
            self.point = None
            self.points = []
            self.rubberband.reset(QGis.Polygon)

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
        self.refreshCanvas(self.layer)
        
        # Add the layer to the Layers panel
        QgsMapLayerRegistry.instance().addMapLayers([self.layer])

    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()