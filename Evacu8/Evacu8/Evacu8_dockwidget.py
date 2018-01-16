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
import webbrowser
from time import localtime, strftime

from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal, Qt, QVariant, QSize, QTimer
from PyQt4.QtGui import QColor
from qgis._core import QgsVectorLayer, QgsMapLayerRegistry, QgsFeature, QgsGeometry, QgsPoint, QGis, \
    QgsDistanceArea
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
        self.plugin_dir = os.path.dirname(__file__)
        self.emitPoint = QgsMapToolEmitPoint(self.canvas)
        self.toolPoly = PolyMapTool(self.canvas)
        self.emitEvac = QgsMapToolEmitPoint(self.canvas)
        self.emitShel = QgsMapToolEmitPoint(self.canvas)
        self.emitDel = QgsMapToolEmitPoint(self.canvas)
        self.input_template = self.scen_info.toHtml()

        # set up GUI operation signals
        # data
        self.load_scen.clicked.connect(self.openScenario)
        self.tabs.setTabEnabled(1, False)
        self.set_pt.clicked.connect(self.enterPoi)
        self.emitPoint.canvasClicked.connect(self.getPoint)
        self.set_rad.clicked.connect(self.calculateBuffer)
        self.set_rad.setEnabled(False)
        self.send_notes.clicked.connect(self.sendNotes)
        # self.set_rad.clicked.connect(self.POI_selection)
        self.set_danger.clicked.connect(self.setDangerZone)
        self.get_danger.clicked.connect(self.getDangerZone)
        self.del_danger.clicked.connect(self.delDangerZone)
        self.emitDel.canvasClicked.connect(self.get_del)

        # set images and icons
        self.logo.setPixmap(QtGui.QPixmap(':images\Logosmall.jpeg'))
        self.load_scen.setIcon(QtGui.QIcon(':images\Open.png'))
        self.load_scen.setIconSize(QSize(25, 25))
        self.set_danger.setIcon(QtGui.QIcon(':images\Draw1.svg'))
        self.set_danger.setIconSize(QSize(25, 25))
        self.get_danger.setIcon(QtGui.QIcon(':images\Check.png'))
        self.get_danger.setIconSize(QSize(25, 25))
        self.del_danger.setIcon(QtGui.QIcon(':images\Delete.png'))
        self.del_danger.setIconSize(QSize(30, 30))
        self.shortestRouteButton.setIcon(QtGui.QIcon(':images\Route.png'))
        self.shortestRouteButton.setIconSize(QSize(25, 25))
        self.to_wiki1.setIcon(QtGui.QIcon(':images\Info.png'))
        self.to_wiki1.setIconSize(QSize(20, 20))
        # self.to_wiki2.setIcon(QtGui.QIcon(':images\Info.png'))
        # self.to_wiki2.setIconSize(QSize(20, 20))

        # analysis
        self.evac = QgsPoint()
        self.evacId = int()
        self.shel = QgsPoint()
        self.shelId = int()

        self.evac_layer = QgsVectorLayer()
        self.evac_feat = QgsFeature()
        self.shel_layer = QgsVectorLayer()
        self.shel_feat = QgsFeature()

        self.select_POI.clicked.connect(self.enterEvac)
        self.emitEvac.canvasClicked.connect(self.getEvac)
        self.desel_POI.clicked.connect(self.deleteEvac)
        self.select_shelter.setEnabled(False)
        self.select_shelter.clicked.connect(self.enterShel)
        self.emitShel.canvasClicked.connect(self.getShel)
        self.shortestRouteButton.setEnabled(False)
        self.shortestRouteButton.clicked.connect(self.buildNetwork)
        self.shortestRouteButton.clicked.connect(self.calculateRoute)
        self.network_layer = QgsVectorLayer()
        self.tied_points = []
        self.to_evac_info.setVerticalHeaderLabels(["Type", "Name", "Address", "Population","Dist from Attack(m)"])
        self.shelter_info.setVerticalHeaderLabels(["Type", "Name", "Address", "Capacity","Route distance (m)"])
        # self.scen_details.setVerticalHeaderLabels(["Time", "Type", "Adr.", "Level"])
        # self.scen_list.addItems(["Bomb Threat","Shooting"])
        # self.scen_list.itemClicked.connect(self.show_scen_details1)
        # self.scen_list.itemClicked.connect(self.show_scen_details2)

        # Open wiki
        self.to_wiki1.clicked.connect(self.open_wiki)
        #self.to_wiki2.clicked.connect(self.open_wiki)

        self.big_button.clicked.connect(self.evacuateThis)
        self.savelog.clicked.connect(self.saveLog)

        self.big_button.setEnabled(False)
        self.warning_msg.setVisible(False)

        self.show_selected.clicked.connect(self.showSelected)
        self.hide_selected.clicked.connect(self.hideSelected)
        self.save_map.clicked.connect(self.saveMap)

        self.savelog.clicked.connect(self.timerMessage)
        self.save_map.clicked.connect(self.timerMessage)
        self.saved_msg.setVisible(False)

        self.sent_msg.setVisible(False)

    def closeEvent(self, event):
        # disconnect interface signa
        self.closingPlugin.emit()
        event.accept()


    ##Functions##
    #Open Scenario
    def openScenario(self,filename=""):
        self.iface.addProject(unicode(self.plugin_dir+"/data/Evacu8_dataset_new.qgs"))
        self.set_rad.setEnabled(False)
        self.tabs.setTabEnabled(1, False)
        self.scen_info.clear()
        self.scen_info.insertHtml(self.input_template)
        self.buildings.clear()
        # scenario_open = False
        # scenario_file = os.path.join(u'/Users/jorge/github/GEO1005', 'sample_data', 'time_test.qgs')
        # # check if file exists
        # if os.path.isfile(scenario_file):
        #     self.iface.addProject(scenario_file)
        #     scenario_open = True
        # else:
        #     last_dir = uf.getLastDir("data")
        #     new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
        #     if new_file:
        #         self.iface.addProject(unicode(new_file))
        #         scenario_open = True


    # Attack Point
    def enterPoi(self):
        if not(QgsMapLayerRegistry.instance().mapLayersByName('Attack Point')):
            # remember currently selected tool
            self.userTool = self.canvas.mapTool()
            # activate coordinate capture tool
            self.canvas.setMapTool(self.emitPoint)

    def getPoint(self, mapPoint):
        self.set_rad.setEnabled(True)
        # change tool so you don't get more than one POI
        self.canvas.unsetMapTool(self.emitPoint)
        self.canvas.setMapTool(self.userTool)
        # Get the click
        if mapPoint:
            self.atk_pt = QgsPoint(mapPoint)
            self.distance()
            # Specify the geometry type
            layer = QgsVectorLayer('Point?crs=epsg:28992', 'Attack Point', 'memory')

            style = "style_attack.qml"
            qml_path = self.plugin_dir + "/data/" + style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()

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
        layers = ["POI_Evacu8"]
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
                m = dist.measureLine(self.atk_pt, pt)//1
                vl.changeAttributeValue(feat.id(), index, m)
            vl.commitChanges()

    # DUPLICATE POI LAYER
    def dup_layer(self, crs, names):
        for name in names:
            layer = uf.getLegendLayerByName(self.iface, "POI_Evacu8")
            layer_type = {'0': 'Point', '1': 'LineString', '2': 'Polygon'}
            mem_layer = QgsVectorLayer(layer_type[str(layer.geometryType())] + "?crs=epsg:" + str(crs), name,
                                       "memory")
            feats = [feat for feat in layer.getFeatures()]
            mem_layer_data = mem_layer.dataProvider()
            attr = layer.dataProvider().fields().toList()
            mem_layer_data.addAttributes(attr)
            mem_layer.updateFields()
            mem_layer_data.addFeatures(feats)
            QgsMapLayerRegistry.instance().addMapLayer(mem_layer)

    # LOAD STYLE
    def load_style(self, names, styles):
        for name, style in zip(names, styles):
            layer = uf.getLegendLayerByName(self.iface, name)
            qml_path = self.plugin_dir + "/data/" + style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()

    # SELECT AND DELETE
    def intersectANDdelete(self):
        lay1 = uf.getLegendLayerByName(self.iface, "Perimeter")
        lay2 = uf.getLegendLayerByName(self.iface, "Shelters")
        lay3 = uf.getLegendLayerByName(self.iface, "Buildings to evacuate")
        if lay1 and lay2:
            to_delete = uf.getFeaturesByIntersection(lay2, lay1, True)

            lay2.startEditing()
            for feat in to_delete:
                lay2.deleteFeature(feat.id())
            lay2.commitChanges()

        if lay1 and lay3:
            to_delete2 = uf.getFeaturesByIntersection(lay3, lay1, False)

            lay3.startEditing()
            for feat in to_delete2:
                lay3.deleteFeature(feat.id())
            lay3.commitChanges()

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
            if cutoff_distance:
                if (QgsMapLayerRegistry.instance().mapLayersByName("Perimeter")):
                    buffer_layer =  uf.getLegendLayerByName(self.iface, "Perimeter")
                    QgsMapLayerRegistry.instance().removeMapLayer(buffer_layer.id())
                buffers = {}
                for point in origins:
                    geom = point.geometry()
                    buffers[point.id()] = geom.buffer(cutoff_distance,12).asPolygon()
                # store the buffer results in temporary layer called "Perimeter"
                buffer_layer = uf.getLegendLayerByName(self.iface, "Perimeter")
                # create one if it doesn't exist
                if not buffer_layer:
                    attribs = ['id', 'distance']
                    types = [QtCore.QVariant.String, QtCore.QVariant.Double]
                    buffer_layer = uf.createTempLayer('Perimeter','POLYGON',layer.crs().postgisSrid(), attribs, types, 70)
                    uf.loadTempLayer(buffer_layer)
                    buffer_layer.setLayerName('Perimeter')
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

                layers = ["road_net"]
                for layer in layers:
                    vl = uf.getLegendLayerByName(self.iface, layer)
                    iface.legendInterface().setLayerVisible(vl, True)

                # Make half transparent Open Street Map
                rlayer = uf.getLegendLayerByName(self.iface, "OpenStreetMap")
                rlayer.renderer().setOpacity(0.5)  # 0.5 = 50%; 0.1 = 90%...
                rlayer.triggerRepaint()

                #jump to tab 2
                self.tabs.setTabEnabled(1, True)
                self.tabs.setCurrentIndex(1)
                self.scrollArea.verticalScrollBar().setValue(0)

                # If POIs in and out already exist, remove them
                check_layer = uf.getLegendLayerByName(self.iface, "Buildings to evacuate")
                check_layer2 = uf.getLegendLayerByName(self.iface, "Shelters")
                if check_layer:
                    QgsMapLayerRegistry.instance().removeMapLayer(check_layer.id())
                    QgsMapLayerRegistry.instance().removeMapLayer(check_layer2.id())
                    self.buildings.clear()
                if buffer_layer:
                    names = ["Buildings to evacuate", "Shelters"]
                    styles = ["style.qml", "style2.qml"]
                    self.dup_layer(28992, names)
                    self.load_style(names, styles)
                    self.intersectANDdelete()

                    build = uf.getLegendLayerByName(iface, "Buildings to evacuate")
                    feats = build.getFeatures()
                    n = 0
                    for feat in feats:
                        if feat.attributes()[2] != 'police' and feat.attributes()[2] != 'fire_station':
                            n += 1
                    self.buildings.append('%s'%n)

    # Making notes and sending to livechat
    def getNotes(self):
        notes = self.scen_info.toHtml()
        return notes

    def sendNotes(self):
        input_data = self.getNotes()
        if len(input_data) == 1042:
             return
        time = strftime("%d-%m-%Y %H:%M:%S", localtime())
        new_notes = time + ": " + input_data + "\n"
        old_notes = self.live_chat.toHtml()
        self.live_chat.clear()
        self.live_chat.insertHtml(new_notes)
        self.live_chat.append("\n")
        self.live_chat.insertHtml(old_notes)
        self.live_chat.moveCursor(QtGui.QTextCursor.Start)

    # Set danger polygon
    def setDangerZone(self):
        self.canvas.setMapTool(self.toolPoly)

    def getDangerZone(self):
        self.canvas.unsetMapTool(self.toolPoly)

    def delDangerZone(self):
        self.canvas.unsetMapTool(self.toolPoly)
        self.canvas.setMapTool(self.emitDel)

    def get_del(self, delete):
        self.canvas.unsetMapTool(self.emitDel)

        if delete:
            layer = "Danger Zones"

            min_dist = QgsDistanceArea()
            vl = uf.getLegendLayerByName(self.iface, layer)
            point = QgsPoint(delete)
            feats = vl.getFeatures()
            for feat in feats:
                geom = feat.geometry()
                pt = geom.centroid().asPoint()
                dist = QgsDistanceArea().measureLine(point, pt)
                if dist < min_dist:
                    min_dist = dist
                    fid = feat.id()

            vl.startEditing()
            vl.deleteFeature(fid)
            vl.commitChanges()

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
        self.select_POI.setEnabled(False)
        self.select_shelter.setEnabled(True)

        if evac:
            self.evac = QgsPoint(evac)
            self.evac_layer, self.evac_feat = self.select(self.evac)
            self.to_evac_table()

    def select(self, point):
        layers = ["Buildings to evacuate", "Shelters"]

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

        layers = ["Buildings to evacuate", "Shelters"]
        for layer in layers:
            uf.getLegendLayerByName(self.iface, layer).removeSelection()
        self.refreshCanvas(lineLayer)

        item = ''
        for i in range(5):
            # i is the table row, items must be added as QTableWidgetItems
            self.to_evac_info.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))
            self.shelter_info.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))

        self.select_POI.setEnabled(True)
        self.select_shelter.setEnabled(False)
        self.shortestRouteButton.setEnabled(False)
        self.warning_msg.setVisible(False)
        self.big_button.setEnabled(False)


    def enterShel(self):
        self.shortestRouteButton.setEnabled(False)
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
            self.shel = QgsPoint(shel)
            self.shel_layer, self.shel_feat = self.select(self.shel)
            self.shelter_table()
        if self.evac and self.shel:
            self.shortestRouteButton.setEnabled(True)


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
            source_points = [self.evac, self.shel]
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

                style = "style_red_routes.qml"
                qml_path = self.plugin_dir + "/data/" + style
                routes_layer.loadNamedStyle(qml_path)
                routes_layer.triggerRepaint()

                uf.loadTempLayer(routes_layer)
            # calculate route length
            d = 0
            for i in range(len(path)-1):
                pt1 = path[i]
                pt2 = path[i+1]
                dx = pt2[0] - pt1[0]
                dy = pt2[1] - pt1[1]
                d += ((dx**2 + dy**2)**0.5)//1
            uf.insertTempFeatures(routes_layer, [path], [['testing']])
            self.refreshCanvas(routes_layer)
            self.shelter_info.setItem(4, 0, QtGui.QTableWidgetItem(unicode(d)))

            lineLayer = uf.getLegendLayerByName(iface, "road_net")
            lineLayer.deselect(self.shelId)
            self.refreshCanvas(lineLayer)
            self.big_button.setEnabled(True)

            # Set ROUTE text color Red
            self.shelter_info.item(4, 0).setTextColor(QColor(255, 0, 0))

    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

    # Displaying information

    # def show_scen_details1(self,item):
    #     if str(item.text()) == "Bomb Threat":
    #         values = ["11:34","Bomb Threat","Rotterdam Centraal","3"]
    #         for i, item in enumerate(values):
    #             # i is the table row, items must be added as QTableWidgetItems
    #             self.scen_details.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))
    #
    # def show_scen_details2(self,item):
    #     # if str(item.text()) == "Shooting":
    #         values = ["11:55","Shooting","Lijnbaan 5, Rotterdam","5"]
    #         for i, item in enumerate(values):
    #             # i is the table row, items must be added as QTableWidgetItems
    #             self.scen_details.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))


    def to_evac_table(self):
        tent_values = self.evac_feat.attributes()
        indices = [2,3,7,8,9]
        values = [tent_values[i] for i in indices]
        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        for i, item in enumerate(values):
            # i is the table row, items must be added as QTableWidgetItems
            self.to_evac_info.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))

    def shelter_table(self):
        tent_values = self.shel_feat.attributes()
        indices = [2,3,7,8]
        values = [tent_values[i] for i in indices]

        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        for i, item in enumerate(values):
            # i is the table row, items must tbe added as QTableWidgetItems
            self.shelter_info.setItem(i, 0, QtGui.QTableWidgetItem(unicode(item)))
        cap = values[3]
        pop = int(self.to_evac_info.item(3,0).text())
        if cap - pop < 0:
            self.warning_msg.setVisible(True)
        else:
            self.warning_msg.setVisible(False)


    # Open the wiki
    def open_wiki(self):
        webbrowser.open('https://github.com/fhb1990/GEO1005_2017-18_group3/wiki')

    # Combine toEvacuate building and shelter
    def evacuateThis(self):
        # Write to log
        time = strftime("%d-%m-%Y %H:%M:%S", localtime())
        evac_type = self.to_evac_info.item(0, 0).text()
        to_evac = self.to_evac_info.item(1, 0).text()
        adr = self.to_evac_info.item(2, 0).text()
        pop = int(self.to_evac_info.item(3, 0).text())
        log_str = time + ":" + "\nBuilding selected for evacuation." \
                               "\nType:\t%s\nName:\t%s\nAddress:\t%s\nPredicted pop:\t%d\n" %(evac_type, to_evac, adr, pop)
        self.log.append(log_str)

        evac_type = self.shelter_info.item(0, 0).text()
        to_evac = self.shelter_info.item(1, 0).text()
        adr = self.shelter_info.item(2, 0).text()
        log_str = "Evacuate to:\nType:\t%s\nName:\t%s\nAddress:\t%s\n" %(evac_type, to_evac, adr)
        self.log.append(log_str)

        # Mark things as DONE
        if not(uf.getLegendLayerByName(self.iface, "Done")):
            done = QgsVectorLayer('Point?crs=epsg:28992', 'Done', 'memory')
            QgsMapLayerRegistry.instance().addMapLayers([done])
            style = "style for green marks.qml"
            qml_path = self.plugin_dir + "/data/" + style
            done.loadNamedStyle(qml_path)
            done.triggerRepaint()
        prov = uf.getLegendLayerByName(self.iface, "Done").dataProvider()
        prov.addFeatures([self.evac_feat])
        self.refreshCanvas(uf.getLegendLayerByName(self.iface, "Done"))

        # Store Selected Routes
        lay1 = uf.getLegendLayerByName(self.iface, "Selected Routes")
        if not (lay1):
            selected = QgsVectorLayer('LINESTRING?crs=epsg:28992', 'Selected Routes', 'memory')
            QgsMapLayerRegistry.instance().addMapLayers([selected])
            style = "style_blue_routes.qml"
            qml_path = self.plugin_dir + "/data/" + style
            selected.loadNamedStyle(qml_path)
            selected.triggerRepaint()
            iface.legendInterface().setLayerVisible(selected, False)
        prov = uf.getLegendLayerByName(self.iface, "Selected Routes").dataProvider()
        if uf.getLegendLayerByName(self.iface, "Routes"):
            route_layer = uf.getLegendLayerByName(self.iface, "Routes")
            feats = route_layer.getFeatures()
        for feat in feats:
            prov.addFeatures([feat])
        self.refreshCanvas(uf.getLegendLayerByName(self.iface, "Selected Routes"))

        uf.addFields(lay1, ['number'], [QVariant.Int])
        uf.updateField(lay1, 'number', 'rand(1,100)')

        # Lower capacity of shelter
        layer = uf.getLegendLayerByName(self.iface, "Shelters" )
        layer.startEditing()
        cap = int(self.shelter_info.item(3, 0).text())
        m = cap - pop
        if m > 0:
            layer.changeAttributeValue(self.shel_feat.id(), 8, cap - pop)
        else:
            layer.changeAttributeValue(self.shel_feat.id(), 8, 0)
        layer.commitChanges()

        # Change Number of Buildings to Evacuate
        build = uf.getLegendLayerByName(iface, "Buildings to evacuate")
        buildings = build.getFeatures()
        n =  0
        for building in buildings:
            if building.attributes()[2] != 'police' and building.attributes()[2] != 'fire_station':
                n += 1

        ev = uf.getLegendLayerByName(iface, "Selected Routes")
        evacs = ev.getFeatures()
        m = 0
        for evac in evacs:
            m += 1

        self.buildings.clear()
        if n-m > 0:
            self.buildings.append('%s'%(n-m))
        else:
            self.buildings.append('0')

        # Display confirmation message
        self.sent_msg.setVisible(True)
        QTimer.singleShot(3000, lambda: (self.sent_msg.setVisible(False)))

        # Clear selections to start picking new targets
        self.deleteEvac()

    def saveLog(self):
        log_text = self.log.toPlainText()
        path = 'C:/Users/'+os.getenv('USERNAME')+'/Desktop/Evacu8_log.txt'
        with open(path,"w") as fh:
            fh.write("%s" %(log_text))

    def showSelected(self):
        selected = uf.getLegendLayerByName(self.iface, "Selected Routes")
        if selected:
            iface.legendInterface().setLayerVisible(selected, True)

    def hideSelected(self):
        selected = uf.getLegendLayerByName(self.iface, "Selected Routes")
        if selected:
            iface.legendInterface().setLayerVisible(selected, False)

    def saveMap(self):
        filename = 'C:/Users/' + os.getenv('USERNAME') + '/Desktop/Evacu8_log.png'
        if filename != '':
            self.canvas.saveAsImage(filename, None, "PNG")

    def timerMessage(self):
        self.saved_msg.setVisible(True)
        QTimer.singleShot(2000, lambda: (self.saved_msg.setVisible(False)))

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