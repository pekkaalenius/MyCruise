''' 
MCX-file unit

This unit contains MCXfile and MKXfile object classes
that can read and manipulate respective MyCruise files.

Up to now the classes read the files and can
produce several different types of files for e.g.
- Leaflet HTML file to show the cruise route on map with options
- GMT script to show the cruise of PyGMT
- ODV gob-files to show the cruise route and/or station points on ODV
- KML file to show the cruise route of Google Earth
- list of stations in ascii

The unit includes a routine to download the
Aranda station register from github

'''
from pathlib import Path
import math
from datetime import datetime
import re
import xml.etree.ElementTree as ET
import strutils_pa as strpa
import sea_areas as sarea


def mon2num(mon):
#================
# changes three (or more) letter month name mon to it's two digit
# presentation 01...12
# The function is not case sensitive
    return str(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'].index(mon.upper(
                )[0:3]) + 1).rjust(2, '0')

def child_node_text(node, what):
    # ==========================
    child = node.find(what)
    if child is not None:
        r = child.text
    else:
        r = ''
    return r

def get_station_dictionary():
#============================
    import requests
    url = 'https://raw.githubusercontent.com/pekkaalenius/MyCruise/main/asemat.txt'
    result = requests.get(url, allow_redirects=True)
    rd = result.text.split('\n')[:-2]
    station = []
    for r in rd:
        n, la, lo, d, c, s, t, v, y, a = r.split(';')
        station.append({'name': n, 'lat': float(la), 'lon': float(lo), 'depth': int(d), 'country': int(c), 'area': int(s), 'type': t, 'visits': int(v), 'year': int(y), 'years': int(a)})
 
    return station

def get_station_dictionary_from_Sumppu(ahost, auser, apassword, **kwargs):
#=========================================================================
    import mysql.connector

    sumppu = mysql.connector.connect(
        host=ahost,
        user=auser,
        passwd=apassword,
        database="sumppu"
    )
    sumppu_cursor = sumppu.cursor()

    sqlQuery =\
        "select s.name,s.latitude,s.longitude,if(s.bottom_depth is NULL,-9,s.bottom_depth),v.nv,b.ym,a.ny "\
        "from station s, "\
        "(select station_id id,count(id) nv "\
        "from visit group by `station_id`) v, "\
        "(select id,count(y) ny "\
        "from (select distinct station_id id,year(date_visited) y "\
        "from visit order by station_id) d "\
        "group by id) a, "\
        "(select station_id id,year(min(date_visited)) ym "\
        "from visit group by station_id) b "\
        "where a.id=v.id and b.id=v.id and v.id=s.id order by s.name"
    sumppu_cursor.execute(sqlQuery)
    result = sumppu_cursor.fetchall()
    stations = []
    if len(result) > 0:
        for x in result:
            lat = float(x[1])
            lon = float(x[2])
            country = sarea.getMyCruiseCountryCode([lon, lat])
            area = sarea.getMyCruiseHelcomAreaCode([lon, lat])
            stations.append({'name': x[0], 'lat': lat, 'lon': lon, 'depth': int(x[3]), 'country': country, 'area': area, 'type': 'S1', 'visits': int(x[4]), 'year': int(x[5]), 'years': int(x[6])})
    
    sumppu_cursor.close()
    sumppu.close()

    return stations

def make_station_list_from_Sumppu(**kwargs):
#===========================================
# kwargs: savefile
    import getpass
    import mysql.connector

    hst = input('Give host for Sumppu ')
    if hst == '':
        hst = "tonnisto.fimr.fi"
    usr = getpass.getpass('Give Sumppu username: ')
    psw = getpass.getpass(f'Give Sumppu password for {usr} in {hst}: ')
    sumppu = mysql.connector.connect(
        host=hst,
        user=usr,
        passwd=psw,
        database="sumppu"
    )
    sumppu_cursor = sumppu.cursor()

#   print('Haetaan sumpusta tiedot ja varmistetaan maa- ja merialuekoodit')
    sqlQuery =\
        "select s.name,s.latitude,s.longitude,if(s.bottom_depth is NULL,-9,s.bottom_depth),v.nv,b.ym,a.ny "\
        "from station s, "\
        "(select station_id id,count(id) nv "\
        "from visit group by `station_id`) v, "\
        "(select id,count(y) ny "\
        "from (select distinct station_id id,year(date_visited) y "\
        "from visit order by station_id) d "\
        "group by id) a, "\
        "(select station_id id,year(min(date_visited)) ym "\
        "from visit group by station_id) b "\
        "where a.id=v.id and b.id=v.id and v.id=s.id"
    sumppu_cursor.execute(sqlQuery)
#   print('Stations queried. Check the country and sea-area codes for them.')
    result = sumppu_cursor.fetchall()
    stations = []
    if len(result) > 0:
        for x in result:
            lat = float(x[1])
            lon = float(x[2])
            country = sarea.getMyCruiseCountryCode([lon, lat])
            area = sarea.getMyCruiseHelcomAreaCode([lon, lat])
            stations.append(f"{x[0]};{x[1]};{x[2]};{x[3]};{country};{area};S1;{x[4]};{x[5]};{x[6]}")
    stations.sort()

    savefile = kwargs.get('savefile', False)
    if savefile:
        ofile = open(savefile, 'w')
        for s in stations:
            ofile.write(s + '\n')
        ofile.close()
#   print(f'Stations printed in file {savefile}')

    sumppu_cursor.close()
    sumppu.close()
#   print(f'Ready!')
    return stations

# ==============================
mcx_html_tmpl = [
    '<!DOCTYPE html>',
    '<html>',
    '  <head>',
    '    <title>OTSIKKO</title>',
    '    <meta charset="utf-8" />',
    '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.5.1/dist/leaflet.css" integrity="sha512-xwE/Az9zrjBIphAcBb3F6JVqxf46+CDLwfLMHloNu6KEQCAWi6HcDUbeOfBIptF7tcCzusKFjFw2yuvEpDL9wQ==" crossorigin=""/>',
    '',
    '    <style>',
    '      html,body {',
    '        width: 100%;',
    '        height: 100%;',
    '        margin: 2%;',
    '        padding: 0;',
    '      }',
    '      #map {',
    '        position: absolute;',
    '        bottom: 2%;',
    '        top: 2%;',
    '        width: 90%;',
    '        height: 95%;',
    '        }',
    '      .info { padding: 6px 8px; font: 14px/16px Arial, Helvetica, sans-serif; background: white; background: rgba(255,255,255,0.8); box-shadow: 0 0 15px rgba(0,0,0,0.2); border-radius: 5px; } .info h4 { margin: 0 0 5px; color: #777; }',
    '      .legend { text-align: left; line-height: 18px; color: #555; } .legend i { width: 18px; height: 18px; float: left; margin-right: 8px; opacity: 0.7; }',
    '    </style>',
    '  </head>',
    '  <body>',
    '      <div id="map"></div>',
    '      <script src="https://unpkg.com/leaflet@1.5.1/dist/leaflet.js" integrity="sha512-GffPMF3RvMeYyc1LWMHtK8EbPv0iNZ8/oTtHPx9/cc2ILxQ+u905qIwdpULaqDkyBKgOaB57QTMg7ztg8Jm2Og==" crossorigin=""></script>',
    '      <script src="https://unpkg.com/leaflet" type="text/javascript"></script>',
    '      <script src="https://unpkg.com/leaflet-ant-path" type="text/javascript"></script>',
    '      <link rel="stylesheet" href="https://ppete2.github.io/Leaflet.PolylineMeasure/Leaflet.PolylineMeasure.css"/>',
    '      <script src="https://ppete2.github.io/Leaflet.PolylineMeasure/Leaflet.PolylineMeasure.js"></script>',
    '    <script>',
    '',
    '//pisteet ja reitti',
    '',
    '//    GRID LINES',
    '      var latlongrid = L.layerGroup();',
    '      latlongrid.onAdd = function(map) {',
    '        for (var i = 50; i < 71; i++) {L.polyline([[i*1.0, -180.0],[i*1.0, 180.0]], {color: \'black\', weight: 1, opacity: 0.2}).addTo(this);}',
    '        for (var i = 0; i < 61; i++) {L.polyline([[0.0, i*1.0],[80.0, i*1.0],], {color: \'black\', weight: 1, opacity: 0.2}).addTo(this);}',
    '      }',
    '',
    '      function style(feature) {',
    '        return {',
    '          weight: 2,',
    '          opacity: 1,',
    '          color: \'white\',',
    '          dashArray: \'3\',',
    '          fillOpacity: 0.7,',
    '          fillColor: getColor(feature.properties.visits)',
    '        };',
    '      }',
    '',
    '      function highlightFeature(e) {',
    '        var layer = e.target;',
    '        layer.setStyle({',
    '          weight: 5,',
    '          color: \'#666\',',
    '          dashArray: \'\',',
    '          fillOpacity: 0.7',
    '        });',
    '        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {layer.bringToFront();}',
    '        info.update(layer.feature.properties);',
    '      }',
    '',
    '      var geojson;',
    '',
    '      function resetHighlight(e) {',
    '        geojson.resetStyle(e.target);',
    '        info.update();',
    '      }',
    '',
    '      function zoomToFeature(e) {',
    '        map.fitBounds(e.target.getBounds());',
    '      }',
    '',
    '      function onEachFeature(feature, layer) {',
    '        layer.on({',
    '          mouseover: highlightFeature,',
    '          mouseout: resetHighlight,',
    '          click: zoomToFeature',
    '        });',
    '      }',
    '',
    '//    INFO',
    '      var info = L.control();',
    '',
    '      info.onAdd = function (map) {',
    '        this._div = L.DomUtil.create(\'div\', \'info\');',
    '        this.update();',
    '        return this._div;',
    '      };',
    '',
    '      info.update = function (props) {',
    '        this._div.innerHTML = \'<h4 style="color: #0000CC;">Cruise route of</h4> <br> - \';',
    '      };',
    '',
    '//    LEGEND',
    '      var legend = L.control({position: \'bottomright\'});',
    '',
    '      legend.onAdd = function (map) {',
    '        var div = L.DomUtil.create(\'div\', \'info legend\'),',
    '            clrRed = \'red\',',
    '            clrGreen = \'green\';',
    '        div.innerHTML = \'<h4 style="color: #0000CC;">Color of stations</h4>\'+',
    '          \'<i style="background: \'+clrGreen+\'"></i> in Finnish EEZ<br>\'+',
    '          \'<i style="background: \'+clrRed+\'"></i> \' + \'outside of Finnish EEZ\';',
    '        return div;',
    '      };',
    '',
    '//    CURSOR POSITION',
    '      var cursorinfo = L.control({position: \'bottomleft\'});',
    '',
    '      cursorinfo.onAdd = function (map) {',
    '        this._div = L.DomUtil.create(\'div\', \'info info2\');',
    '        this.update();',
    '        return this._div;',
    '      };',
    '',
    '      cursorinfo.update = function (props) {',
    '        this._div.innerHTML = \'Cursor position<br/>\';',
    '      };',
    '',
    '//    MOUSE POSITION DISPLAY',
    '',
    '      L.Control.MousePosition = L.Control.extend({',
    '        options: {',
    '          position: \'bottomleft\',',
    '          separator: \'<br>\',',
    '          emptyString: \'Cursor coordinates<br>0&deg;N<br>0&deg;E\',',
    '          lngFirst: false,',
    '          numDigits: 5,',
    '          lngFormatter: function(num) {',
    '            var direction = (num < 0) ? \'W\' : \'E\';',
    '            var degzero = (num < 10) ? \'0\' : \'\';',
    '            var minzero = ((Math.abs(num)-Math.abs(Math.trunc(num)))*60 < 10) ? \'0\' : \'\';',
    '            var formatted = degzero + Math.abs(L.Util.formatNum(num, 5)) + \'&deg; \' + direction + \' = \' + degzero + Math.abs(Math.trunc(num)) + \'&deg; \' + minzero + L.Util.formatNum((Math.abs(num)-Math.abs(Math.trunc(num)))*60,2) + \'&lsquo; \' + direction;',
    '            return formatted;',
    '          },',
    '          latFormatter: function(num) {',
    '            var direction = (num < 0) ? \'S\' : \'N\';',
    '            var degzero = (num < 10) ? \'0\' : \'\';',
    '            var minzero = ((Math.abs(num)-Math.abs(Math.trunc(num)))*60 < 10) ? \'0\' : \'\';',
    '            var formatted = degzero + Math.abs(L.Util.formatNum(num, 5)) + \'&deg; \' + direction + \' = \' + degzero + Math.abs(Math.trunc(num)) + \'&deg; \' + minzero + L.Util.formatNum((Math.abs(num)-Math.abs(Math.trunc(num)))*60,2) + \'&lsquo; \' + direction;',
    '            return formatted;',
    '          },',
    '          prefix: \'<h4 style="color: #0000CC;">Cursor position</h4>\'',
    '        },',
    '',
    '        onAdd: function (map) {',
    '          this._container = L.DomUtil.create(\'div\', \'leaflet-control-mouseposition\');',
    '          L.DomEvent.disableClickPropagation(this._container);',
    '          map.on(\'mousemove\', this._onMouseMove, this);',
    '//          this._container.innerHTML=this.options.emptyString;',
    '          return this._container;',
    '        },',
    '',
    '        onRemove: function (map) {',
    '          map.off(\'mousemove\', this._onMouseMove)',
    '        },',
    '',
    '        _onMouseMove: function (e) {',
    '          var lng = this.options.lngFormatter ? this.options.lngFormatter(e.latlng.lng) : L.Util.formatNum(e.latlng.lng, this.options.numDigits);',
    '          var lat = this.options.latFormatter ? this.options.latFormatter(e.latlng.lat) : L.Util.formatNum(e.latlng.lat, this.options.numDigits);',
    '          var value = this.options.lngFirst ? lng + this.options.separator + lat : lat + this.options.separator + lng;',
    '          var prefixAndValue = this.options.prefix + value;',
    '//          this._container.innerHTML = prefixAndValue;',
    '          cursorinfo._div.innerHTML = prefixAndValue;',
    '',
    '        }',
    '      });',
    '',
    '//    MAP',
    '      var map = L.map(\'map\', {center:[60.517167, 21.280833], zoom: 5});',
    '      mapLink = \'<a href="http://openstreetmap.org">OpenStreetMap</a>\';',
    '',
    '      var strmaplayer = L.tileLayer(',
    '        \'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png\', {',
    '        attribution: \'&copy; \' + mapLink + \' Contributors\',',
    '        maxZoom: 20,',
    '      }).addTo(map);',
    '',
    '//    BASEMAPS',
    '',
    '      var positron = L.tileLayer(\'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png\', {',
    '        attribution: \'�OpenStreetMap, �CartoDB\',',
    '      });',
    '',
    '      var Esri_OceanBasemap = L.tileLayer(\'http://server.arcgisonline.com/ArcGIS/rest/services/Ocean_Basemap/MapServer/tile/{z}/{y}/{x}\', {',
    '        attribution: \'Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri\',',
    '        maxZoom: 20',
    '      });',
    '',
    '      var Esri_WorldTopoMap = L.tileLayer(\'http://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}\', {',
    '        attribution: \'Sources: Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), (c) OpenStreetMap contributors, and the GIS User Community\',',
    '        maxZoom: 20',
    '      });',
    '',
    '      var Esri_WorldStreetMap = L.tileLayer(\'http://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}\', {',
    '        attribution: \'Sources: Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, (c) OpenStreetMap contributors, and the GIS User Community\',',
    '        maxZoom: 20',
    '      });',
    '',
    '      var Esri_NatGeoWorldMap = L.tileLayer(\'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}\', {',
    '        attribution: \'Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC\',',
    '        maxZoom: 16',
    '      });',
    '',
    '      var Esri_WorldImagery = L.tileLayer(\'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}\', {',
    '        attribution: \'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community\'',
    '      });',
    '',
    '      var opentopo = L.tileLayer(\'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png\', {',
    '        attribution: \'�OpenStreetMap, �CartoDB\',',
    '      });',
    '',
    '      var GeoportailFrance_orthos = L.tileLayer(\'https://wxs.ign.fr/{apikey}/geoportail/wmts?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0&STYLE={style}&TILEMATRIXSET=PM&FORMAT={format}&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}\', {',
    '        attribution: \'<a target="_blank" href="https://www.geoportail.gouv.fr/">Geoportail France</a>\',',
    '        bounds: [[-75, -180], [81, 180]],',
    '        minZoom: 2,',
    '        maxZoom: 19,',
    '        apikey: \'choisirgeoportail\',',
    '        format: \'image/jpeg\',',
    '        style: \'normal\'',
    '      });',
    '',
    '//    OVERLAYMAPS',
    '',
    '      var bathymetryLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {',
    '        layers: \'emodnet:mean_atlas_land\',',
    '        format: \'image/png\',',
    '        transparent: true,',
    '        attribution: "Emodnet bathymetry",',
    '        opacity: 0.8',
    '      });',
    '',
    '      var coastlinesLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {',
    '        layers: \'coastlines\',',
    '        format: \'image/png\',',
    '        transparent: true,',
    '        attribution: "Emodnet bathymetry",',
    '        opacity: 0.8',
    '      });',
    '',
    '      var emodnetbathymetry = L.layerGroup([bathymetryLayer, coastlinesLayer]);',
    '',
    '      var contourLayer = L.tileLayer.wms("http://ows.emodnet-bathymetry.eu/wms", {',
    '        layers: \'emodnet:contours\',',
    '        format: \'image/png\',',
    '        transparent: true,',
    '        attribution: "Emodnet bathymetry",',
    '        opacity: 0.8',
    '      });',
    '',
    '      var emodnetdepthcontours = L.layerGroup([contourLayer]);',
    '',
    '      var fairways = new L.LayerGroup();',
    '      var fairWays =',
    '        L.tileLayer.wms(\'https://extranet.liikennevirasto.fi/inspirepalvelu/avoin/wms\', {',
    '          layers: \'vaylat,vaylaalueet\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          maxZoom: 18,',
    '          minZoom: 7,',
    '          attribution: \'CC 4.0 Liikennevirasto. Ei navigointikäyttöön. Ei täytä virallisen merikartan vaatimuksia.\',',
    '      }).addTo(fairways);',
    '',
    '      var eez = new L.LayerGroup();',
    '      var eeZ =',
    '        L.tileLayer.wms(\'http://geo.vliz.be/geoserver/MarineRegions/wms\', {',
    '          layers: \'eez_boundaries\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          attribution: \'Marineregions.org.\',',
    '      }).addTo(eez);',
    '',
    '      var internalwaters = new L.LayerGroup();',
    '      var internalWaters =',
    '        L.tileLayer.wms(\'http://geo.vliz.be/geoserver/MarineRegions/wms\', {',
    '          layers: \'eez_internal_waters\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          attribution: \'Marineregions.org.\',',
    '      }).addTo(internalwaters);',
    '',
    '      var internalwaters12 = new L.LayerGroup();',
    '      var internalWaters12 =',
    '        L.tileLayer.wms(\'http://geo.vliz.be/geoserver/MarineRegions/wms\', {',
    '          layers: \'eez_12nm\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          attribution: \'Marineregions.org.\',',
    '      }).addTo(internalwaters12);',
    '',
    '      var helcomareaboundaries = new L.LayerGroup();',
    '      var helcomAreaboundaries =',
    '        L.tileLayer.wms(\'https://maps.helcom.fi/arcgis/services/MADS/Sea_environmental_monitoring/MapServer/WmsServer\', {',
    '          layers: \'89\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          attribution: \'HELCOM.\',',
    '      }).addTo(helcomareaboundaries);',
    '',
    '      var helcomareas = new L.LayerGroup();',
    '      var helcomAreas =',
    '        L.tileLayer.wms(\'https://maps.helcom.fi/arcgis/services/MADS/Sea_environmental_monitoring/MapServer/WmsServer\', {',
    '          layers: \'88\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          attribution: \'HELCOM.\',',
    '      }).addTo(helcomareas);',
    '',
    '      var mNavAttr = \'--- Merikorttipalvelu perustuu Liikenneviraston tuottaman rasterimuotoiseen merikartta-aineistoon. Käyttölupa CC 4.0\'',
    '        +\' Lähde: Liikennevirasto. Ei navigointikäyttöön. Ei täytä virallisen merikartan vaatimuksia.\';',
    '',
    '      var navigate = new L.LayerGroup();',
    '      var Navigate     =',
    '        L.tileLayer.wms(\'https://julkinen.traficom.fi/s57/wms\', {',
    '          layers: \'cells\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          minZoom: 7,',
    '          attribution: mNavAttr',
    '      }).addTo(navigate);',
    '',
    '      var bshcwater = new L.LayerGroup();',
    '      var Bshcwater =',
    '        L.tileLayer.wms(\'http://data.bshc.pro/ogc/bsbd-0.0.4/wms\', {',
    '          layers: \'water\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          minZoom: 5,',
    '          attribution: \'BSHC\'',
    '      }).addTo(bshcwater);',
    '',
    '      var mllAttr =\' Maanmittauslaitoksen nimipalvelu\';',
    '      var nimet = new L.LayerGroup();',
    '      var Nimet =',
    '        L.tileLayer.wms(\'https://inspire-wms.maanmittauslaitos.fi/inspire-wms/GN/wms\', {',
    '          layers: \'GN.GeographicalNames\',',
    '          transparent: true,',
    '          format: \'image/png\',',
    '          minzoom: 5,',
    '          attribution: mllAttr',
    '      }).addTo(nimet);',
    '',
    '      var openseamap = new L.LayerGroup();',
    '      var openSeaMap =',
    '        L.tileLayer(\'http://tiles.openseamap.org/seamark/{z}/{x}/{y}.png\', {minZoom: 6}).addTo(openseamap);',
    '',
    '      L.Map.mergeOptions({positionControl: false});',
    '',
    '      L.Map.addInitHook(function () {',
    '        if (this.options.positionControl) {',
    '          this.positionControl = new L.Control.MousePosition();',
    '          this.addControl(this.positionControl);',
    '        }',
    '      });',
    '',
    '      L.control.mousePosition = function (options) {return new L.Control.MousePosition(options);};',
    '      L.control.mousePosition().addTo(map);',
    '',
    '//    KILOMETER SCALE'
    '',
    '      L.control.scale ({maxWidth:240, metric:true, imperial:false, position: \'bottomleft\'}).addTo (map);',
    '',
    '//    LENGTH MEASUREMENT CONTROL',
    ''
    '      let polylineMeasure = L.control.polylineMeasure ({position:\'topleft\', unit:\'metres\', showBearings:true, clearMeasurementsOnStop: false, showClearControl: true, showUnitControl: true})',
    '      polylineMeasure.addTo (map);',
    '',
    '      function debugevent(e) { console.debug(e.type, e, polylineMeasure._currentLine) }',
    '      map.on(\'polylinemeasure:toggle\', debugevent);',
    '      map.on(\'polylinemeasure:start\', debugevent);',
    '      map.on(\'polylinemeasure:resume\', debugevent);',
    '      map.on(\'polylinemeasure:finish\', debugevent);',
    '      map.on(\'polylinemeasure:clear\', debugevent);',
    '      map.on(\'polylinemeasure:add\', debugevent);',
    '      map.on(\'polylinemeasure:insert\', debugevent);',
    '      map.on(\'polylinemeasure:move\', debugevent);',
    '      map.on(\'polylinemeasure:remove\', debugevent);',
    '',
    '//    ADD INFO; CURSORINFO AND LEGEND TO THE MAP',
    '',
    '      info.addTo(map);',
    '      cursorinfo.addTo(map);',
    '      legend.addTo(map);',
    '',
    '//    STATIONS AND ROUTELINE are on the map by default, other layers not',
    '',
    '      stationPoints.addTo(map);',
    '      routeLine.addTo(map);',
    '',
    '      var baseMaps = {',
    '        "StreetMap"                : strmaplayer,',
    '        "Positron"                 : positron,',
    '        "ESRI OceanBasemap"        : Esri_OceanBasemap,',
    '        "ESRI Worl_Topo_Map"       : Esri_WorldTopoMap,',
    '        "ESRI World_Street_Map"    : Esri_WorldStreetMap,',
    '        "ESRI NatGeoWorldMap"      : Esri_NatGeoWorldMap,',
    '        "Topo"                     : opentopo,',
    '        "ESRI WorldImagery"        : Esri_WorldImagery,',
    '        "Geoportail France orthos" : GeoportailFrance_orthos}',
    '',
    '      var overlayMaps = {',
    '        "EMODnet Bathymetry"            : emodnetbathymetry,',
    '        "BSHC Baltic Sea Bathymetry"    : bshcwater,',
    '        "EMODnet depth contours"        : emodnetdepthcontours,',
    '        "EEZ"                           : eez,',
    '        "Internal waters"               : internalwaters,',
    '        "Internal waters 12 nm"         : internalwaters12,',
    '        "HELCOM areas"                  : helcomareas,',
    '        "HELCOM area boundaries"        : helcomareaboundaries,',
    '        "Open seamap"                   : openseamap,',
    '        "Finnish fairways"              : fairways,',
    '        "Finnish navigation chart"      : navigate,',
    '        "Latitude-longitude grid"       : latlongrid,',
    '        "Stations of the cruise"        : stationPoints,',
    '        "Routeline of the cruise"       : routeLine,',
    '        "Animated route of the cruise"  : antLine,',
    '        "Finnish place names"           : nimet',
    '      }',
    '',
    '      L.control.layers(baseMaps, overlayMaps).addTo(map);',
    '',
    '    </script>',
    '  </body>',
    '</html>',
    '']

def mycruise_leaflet_map(filename):
    # ==================================
    if '.MKX' in filename.upper():
        acruise = MKXfile(filename)
    else:
        acruise = MCXfile(filename)

    [lo1, la1, lo2, la2] = acruise.get_boundingbox()

    tmpl = mcx_html_tmpl

    for I in range(len(tmpl)):
        if '<title>' in tmpl[I]:
            tmpl[I] = f'    <title>Routemap of {acruise.name_en}</title>'

        if 'var map = L.map' in tmpl[I]:
            tmpl[I] = f"      var map = L.map('map', {{center:["\
                f"{((la1+la2)/2):10.6f}, {((lo1+lo2)/2):11.6f}]"\
                f", zoom: 5}});"

        if 'Cruise route of' in tmpl[I]:
            #        tmpl[I] = tmpl[I].split('</h4>')[0] \
            tmpl[I] = '        this._div.innerHTML = \'<h4 style="color: #0000CC;">Cruise route of' \
                + ' the ' \
                + acruise.platform_name \
                + ' cruise ' \
                + acruise.nro \
                + '/' \
                + str(acruise.year) \
                + '</h4>' \
                + acruise.name_en \
                + '<br>' \
                + acruise.departure_time.split('T')[0] \
                + ' - ' \
                + acruise.arrival_time.split('T')[0] \
                + '\';'
        if '//pisteet ja reitti' in tmpl[I]:
            I1 = I
            I2 = I+1

    olist = []

    for I in range(0, I1):
        olist.append(tmpl[I])

    olist.append('')
    olist.append('      var stationPoints = L.layerGroup();')
    olist.append('')

    for I in range(len(acruise.route)):
        if acruise.route[I].name == 'P':
            continue
        nameandtime = str(I)+': '+acruise.route[I].name+', '+acruise.route[I].entry + \
            ', '+'{:5.1f} {}'.format(acruise.route[I].distance, 'nmi')

        if acruise.route[I].country == 'Finland':
            pColor = 'green'
        else:
            pColor = 'red'

        r = f'      L.circle([{acruise.route[I].lat:9.6f}, '\
            f"{acruise.route[I].lon:11.6f}], 500, "\
            f"{{color: '{pColor}', fillColor: '{pColor}',fillOpacity: 0.5}})"\
            f'.addTo(stationPoints).bindTooltip("{nameandtime}");'
        olist.append(r)

    olist.append(' ')
    olist.append('      var routeLine = L.layerGroup();')
    olist.append('      var antLine   = L.layerGroup();')
    olist.append('')

    rLine = '      route = ['
    for I in range(len(acruise.route)-1):
        rLine = rLine + f'[{acruise.route[I].lat:9.5f}, '\
            f'{acruise.route[I].lon:10.5f}],'
    rLine = rLine +\
        f'[{acruise.route[-1].lat:9.5f}, {acruise.route[-1].lon:10.5f}]]'

    olist.append(rLine)
    olist.append(
        '      L.polyline(route, {color: \'blue\', weight: 1}).addTo(routeLine);')
    olist.append(' ')
    olist.append('      antroute = L.polyline.antPath(route, {')
    olist.append('          "delay": 1000,')
    olist.append('          "dashArray": [10,10],')
    olist.append('          "weight": 3,')
    olist.append('          "color": "#0000FF",')
    olist.append('          "pulseColor": "#FFFFFF",')
    olist.append('          "paused": false ,')
    olist.append('          "reverse": false ,')
    olist.append('          "hardwareAccelerated": true')
    olist.append('      }).addTo(antLine)')
    olist.append(' ')

    for I in range(I2, len(tmpl)):
        olist.append(tmpl[I])

    o_name = filename.split('.')[0] + '.html'
    o_file = open(o_name, 'w')
    for i in range(len(olist)):
        o_file.write(olist[i] + '\n')
    o_file.close()
    print('Valmis! Tulostettu tiedosto '+o_name)
# =================


class Participant:
    first_name = ''
    last_name = ''
    nationality = ''
    institute = ''
    isquest = False
    tt = False
    isboss = False
    role = ''
    projects = []
    cabin_no = ''
    lab_no = ''
    cabin_phone = ''
    boarding_time = ''
    exit_time = ''
    boarding_harbour = ''
    exit_harbour = ''
    isboardingwithcruise = True
    isleavingwithcruise = True

    def __init__(self, first_name, family_name):
        self.first_name = first_name
        self.family_name = family_name


class Sciencecrew:
    participants = []


class Routepoint:
    name = ''
    lat = 0.0
    lon = 0.0
    depth = 0.0
    point_type = ''
    arrival_time = ''
    departure_time = ''
    duration = 0.0
    observations = []
    isvisited = False
    baseindex = 0
    speedfrom = 10.0
    selected = False
    isarrivalgiven = False
    isspeedcalculated = False
    mapsymbol = 0
    mapsymbol_size = 0
    mapsymbol_color = 0
    comment = ''
    SDN_P02_parameters = ''
    SDN_C77_data = ''
    mooring = False
    mooring_function = ''
    country = ''
    sea_area = ''

    def __init__(self, name, lat, lon):
        self.name = name
        self.lat = lat
        self.lon = lon


class Cruiseroute:
    default_speed_knots = 10.0
    default_duration_hours = 0.5
    default_observations = []
    routepoints = []
    language = ''
    default_mapsymbol = 0
    default_mapsymbol_size = 0
    default_mapsymbol_color = 0
    routeline_color = 0
    isscheduled = False
    default_SDN_P02_parameters = []
    default_SDN_C77_data = []


class MCXfile:
    name_fi = ''
    name_en = ''
    ship_name = ''
    ship_code = ''
    ship_master = ''
    nro = 0
    year = 0
    organiser = ''
    scientific_crew = []
    route = []
    status = ''
    plandatetime = ''
    timezonediff = 0
    letterid = ''
    aim_fi = []
    aim_en = []
    project = ''
    ctdname = ''
    language = ''
    softwareversion = ''
    departure_time = ''
    departure_timezone = ''
    departure_port = ''
    arrival_time = ''
    arrival_timezone = ''
    arrival_port = ''
    header_errors = []

    def __init__(self, fname):
        self.fname = fname
        self.name = ''
        self.organiser = ''
        self.nro = 0
        self.year = 0
        self.status = ''
        self.plandatetime = ''
        self.timezonediff = 0
        self.letterid = ''
        self.name_fi = ''
        self.name_en = ''
        self.aim_fi = ''
        self.aim_en = ''
        self.project = ''
        self.ctd_name = ''
        self.scientific_crew = []
        self.route = []
        self.language = ''
        self.software_version = ''
        self.master = ''
        self.ship_name = ''
        self.ship_code = ''
        self.ship_master = ''
        self.departure_time = ''
        self.departure_timezone = ''
        self.departure_port = ''
        self.arrival_time = ''
        self.arrival_timezone = ''
        self.arrival_port = ''

        my_file = Path(fname)
        if my_file.is_file():
            self.read()
            self.OK = True
        else:
            self.OK = False
            print('\nNOTE! File '+fname+' not found!')

    def read(self):
        # read the mcx-file into mcx-object
        cruise = ET.parse(self.fname).getroot()

        cruise_attributes = cruise.attrib
        self.organiser = cruise_attributes['organiser']
        self.name_fi = cruise_attributes['name']
        self.name_en = cruise_attributes['nameEN']
        self.nro = cruise_attributes['nro']
        self.platform_name = cruise_attributes['platformname']
        self.collate_center = cruise_attributes['collateCenter']
        self.platform_code = cruise_attributes['platformcode']
        self.platform_class = cruise_attributes['platform_class']
        self.project = cruise_attributes['project']
        self.plan_status = cruise_attributes['status']
        self.plan_datetime = cruise_attributes['planDateTime']
        self.plan_language = cruise_attributes['language']

        self.software_version = cruise.find("software").get('version')

        ship = cruise.find("ship")
        self.ship_name = ship.get('name')
        self.ship_code = ship.get('platformcode')
        self.ship_master = ship.get('master')

        departure = cruise.find('departure')
        self.departure_time = departure.get('dateTime')
        self.departure_timezone = departure.get('timeZone')
        self.departure_port = departure.get('harbour')

        arrival = cruise.find('arrival')
        self.arrival_time = arrival.get('dateTime')
        self.arrival_timezone = arrival.get('timeZone')
        self.arrival_port = arrival.get('harbour')

        self.purpose = cruise.find('purpose').text

        # Description of the cruise in English and in Finnish
        description_en = cruise.find('description')
        description_fi = cruise.find('descriptionFIN')
        self.aim_en = []
        for row in description_en.findall('dr'):
            self.aim_en.append(row.text)
        self.aim_fi = []
        for row in description_fi.findall('drf'):
            self.aim_fi.append(row.text)

        self.year = 0
        self.timezonediff = 0
        self.letterid = ''
        self.ctd_name = ''

        # get scientific crew
        self.scientific_crew = []
        staff = cruise.find("staff")
        for person in staff.findall("person"):
            member = Participant(
                person.attrib['firstName'], person.attrib['familyName'])
            member.organisation = person.attrib['organisation']
            member.infixed = person.attrib['inFixed']
            member.indate = person.attrib['inDate']
            member.outfixed = person.attrib['outFixed']
            member.outdate = person.attrib['outDate']
            if person.find('role') is not None:
                member.role = person.find('role').text
            if person.find('project') is not None:
                member.project = person.find('project').text
            cabin = person.find('cabin').attrib
            member.cabin_no = cabin['nro']
            member.cabin_phone = cabin['phone']
            lab = person.find('lab').attrib
            member.lab_no = lab['nro']
            member.lab_phone = lab['phone']

            self.scientific_crew.append(member)

        # Get cruise route
        croute = cruise.find("route")

        defaults = croute.find('defaults')
        self.default_speed_knots = float(defaults.find('speed').text)

        hm = defaults.find('duration').text[1:]
        if 'H' in hm and 'M' in hm:
            h = float(hm.split('H')[0]) + \
                float(hm.split('H')[1].split('M')[0])/60
        elif 'H' in hm:
            h = float(hm.split('H')[0])
        elif 'M' in hm:
            h = float(hm.split('M')[0])/60
        else:
            h = 1.0
        self.default_duration_hours = h

        if defaults.find('observations') is not None:
            ocode = defaults.find('observations')
            if ocode.find('obscode') is not None:
                self.default_observations = ocode.find('obscode').text

        self.default_mapsymbol = defaults.find('mapsymbol').attrib

        # Get routepoints
        stations = croute.find("points")
        for station in stations.findall("point"):
            la = station.find('lat').text.split('D')
            lat = float(la[0]) + float(la[1].split('M')[0])/60
            lo = station.find('lon').text.split('D')
            lon = float(lo[0]) + float(lo[1].split('M')[0])/60

            rpoint = Routepoint(station.find('name').text, lat, lon)

            rpoint.nro = station.attrib['nro']
            rpoint.type = station.attrib['type']
            rpoint.status = station.attrib['status']
            rpoint.index = station.attrib['index']

            rpoint.depth = float(station.find('depth').text)
            rpoint.distance = float(station.find('distance').text)
            rpoint.entry = station.find('entry').attrib['dateTime']
            rpoint.entry_status = station.find('entry').attrib['status']
            dur = station.find('duration').text[1:]
            rpoint.duration = dur
            rpoint.exit = station.find('exit').attrib['dateTime']
            rpoint.exit_status = station.find('exit').attrib['status']
            rpoint.speed = float(station.find('speed').text)
            rpoint.speed_status = station.find('speed').attrib['status']

            if station.find('observations') is not None:
                ocode = station.find('observations')
                if ocode.find('obscode') is not None:
                    rpoint.observations = ocode.find('obscode').text

            if station.find('SDN_P02_parameters') is not None:
                rpoint.SDN_P02_parameters = station.find(
                    'SDN_P02_parameters').text

            if station.find('SDN_C77_data') is not None:
                rpoint.SDN_C77_data = station.find('SDN_C77_data').text

            rpoint.country = station.find('Country').text
            rpoint.sea_area = station.find('SeaArea').text
            rpoint.mooring = child_node_text(station, 'isMooring')
            rpoint.mapsymbol = station.find('mapsymbol').attrib
            rpoint.comments = child_node_text(station, 'comments')

            self.route.append(rpoint)

        if cruise.find('acquisitionInfo') is not None:
            # jotain
            self.acquisitionInfo = cruise.find('acquisitionInfo').text

        if cruise.find('accesPolicies') is not None:
            self.accessPolicies = cruise.find('accesPolicies').text

        if cruise.find('dataPaths') is not None:
            datapaths = cruise.find('dataPaths')
            if datapaths.find('MKXsave') is not None:
                if datapaths.find('MKXsave').attrib['value'] == 'false':
                    self.mkxsave = False
                else:
                    self.mkxsave = True

        self.mapfiles = []
        for mf in cruise.findall('mapfiles'):
            if mf is not None:
                self.mapfiles.append(mf.text)

        if self.name_en == '':
            self.name_en = self.name_fi

    def get_persons_in_role(self, a_role):
        result = []
        for person in self.scientific_crew:
            if a_role in person.role:
                result.append(f'{person.family_name} {person.first_name}')
        return result

    def who_is(self, a_role):
        result = 'none'
        for person in self.scientific_crew:
            if a_role in person.role:
                result = f'{person.family_name} {person.first_name}'
        return result

    def get_chief_scientist(self):
        result = self.who_is('chief scientist')
        return result

    def get_chief_chemist(self):
        result = self.who_is('chief chemist')
        return result

    def get_IT_chief(self):
        result = self.who_is('IT-chief')
        return result

    def get_lat(self):
        lat = []
        for station in self.route:
            lat.append(station.lat)
        return lat

    def get_boundingbox(self):
        result = [180.0, 90, -180.0, -90.0]
        lat = []
        lon = []
        for station in self.route:
            lat.append(station.lat)
            lon.append(station.lon)
        result = [min(lon), min(lat), max(lon), max(lat)]
        return result

    def get_duration_to(self):
        result = [f'Cruise departure: {self.route[0].entry}']
        result.append('')
        result.append('Nro Station          arrival to            duration to')
        result.append(' ')
        start = datetime.fromisoformat(self.route[0].entry)
        for i, station in enumerate(self.route):
            dur = (datetime.fromisoformat(station.entry) - start).total_seconds()
            dh = math.floor(dur/3600)
            dm = math.floor((dur - dh*3600)/60)
            dd = math.floor(dur/86400)
            hh = math.floor((dur - dd*86400)/3600)
            mm = math.floor((dur - dd*86400 - hh*3600)/60)

            result.append(f"{i:3d} {station.name:16} {station.entry[:10]} {station.entry[11:]} {dh:4d} h {dm:2d} min  = {dd:3d} d {hh:2d} h {mm:2} min")
        return result

    def leaflethtml(self):
        # =====================
        [lo1, la1, lo2, la2] = self.get_boundingbox()
        llhtml = mcx_html_tmpl.copy()
        for I in range(len(llhtml)):
            if '<title>' in llhtml[I]:
                llhtml[I] = f'    <title>Routemap of {self.name_en}</title>'

            if 'var map = L.map' in llhtml[I]:
                llhtml[I] = f"      var map = L.map('map', {{center:["\
                    f'{((la1+la2)/2):10.6f}, {((lo1+lo2)/2):11.6f}],'\
                    f' zoom: 5}});'

            if 'Cruise route of' in llhtml[I]:
                llhtml[I] = '        this._div.innerHTML = \'<h4 style="color: #0000CC;">Cruise route of' \
                    + ' the ' \
                    + self.platform_name \
                    + ' cruise ' \
                    + self.nro \
                    + '/' \
                    + str(self.year) \
                    + '</h4>' \
                    + self.name_en \
                    + '<br>' \
                    + self.departure_time.split('T')[0] \
                    + ' - ' \
                    + self.arrival_time.split('T')[0] \
                    + '\';'
            if '//pisteet ja reitti' in llhtml[I]:
                I1 = I
                I2 = I+1

        olist = []

        for I in range(0, I1):
            olist.append(llhtml[I])

        olist.append('')
        olist.append('      var stationPoints = L.layerGroup();')
        olist.append('')

        for I in range(len(self.route)):
            if self.route[I].name == 'P':
                continue
            nameandtime = f"{I}: {self.route[I].name}, {self.route[I].entry}, "\
                f"{self.route[I].distance:5.1f} nmi"

            if self.route[I].country == 'Finland':
                pColor = 'green'
            else:
                pColor = 'red'

            r = '      L.circle('\
                f"[{self.route[I].lat:9.6f}, {self.route[I].lon:11.6f}], "\
                f"500, {{color: '{pColor}',fillColor: '{pColor}',"\
                f"fillOpacity: 0.5"\
                f'}}).addTo(stationPoints).bindTooltip("{nameandtime}");'
            olist.append(r)

        olist.append(' ')
        olist.append('      var routeLine = L.layerGroup();')
        olist.append('      var antLine   = L.layerGroup();')
        olist.append('')

        rLine = '      route = ['
        for I in range(len(self.route)-1):
            rLine = rLine + \
                f'[{self.route[I].lat:9.5f}, {self.route[I].lon:10.5f}], '
        rLine = rLine + \
            f'[{self.route[-1].lat:9.5f}, {self.route[-1].lon:10.5f}]]'

        olist.append(rLine)
        olist.append(
            '      L.polyline(route, {color: \'blue\', weight: 1}).addTo(routeLine);')
        olist.append(' ')
        olist.append('      antroute = L.polyline.antPath(route, {')
        olist.append('          "delay": 1000,')
        olist.append('          "dashArray": [10,10],')
        olist.append('          "weight": 3,')
        olist.append('          "color": "#0000FF",')
        olist.append('          "pulseColor": "#FFFFFF",')
        olist.append('          "paused": false ,')
        olist.append('          "reverse": false ,')
        olist.append('          "hardwareAccelerated": true')
        olist.append('      }).addTo(antLine)')
        olist.append(' ')

        for I in range(I2, len(llhtml)):
            olist.append(llhtml[I])

        o_name = f"{self.fname.split('.')[0]}.html"
        o_file = open(o_name, 'w')
        for i in range(len(olist)):
            o_file.write(olist[i] + '\n')
        o_file.close()
        print('Valmis! Tulostettu tiedosto '+o_name)
        return

    def to_gmtscript(self,topodir=None):
        o_name = f"{self.fname.split('.')[0]}_gmt.txt"
        [lo1, la1, lo2, la2] = self.get_boundingbox()
        reg = [float(math.trunc(lo1-1)), float(math.trunc(lo2+2)), float(math.trunc(la1)), float(math.trunc(la2+1))]
        olist = []
        olist.append('import pygmt')
        olist.append(' ')
        olist.append('fig = pygmt.Figure()')
        olist.append(' ')
        olist.append('# mapregion [minlon, maxlon, minlat, maxlat]')
        olist.append(f'fig.basemap(region=[{reg[0]:.{7}}, {reg[1]:.{7}}, {reg[2]:.{7}}, {reg[3]:.{7}}], projection="M8i", frame=True)')
        if topodir:
            topodat = f'{topodir}Baltic_Sea_topo.nc'
            topoclr = f'{topodir}Baltic_Sea_topo.cpt' 
            olist.append('# plot bottom topography')
            olist.append(f'fig.grdimage("{topodat}", cmap="{topoclr}")')
            olist.append('# plot land')
            olist.append('fig.coast(land="darkgreen")')
            penclr = 'black'
        else:
            olist.append('# plot land')
            olist.append('fig.coast(land="darkgreen", water="navy")')
            penclr = 'white'

        xs = ', '.join([f'{p.lon:.{7}}' for p in self.route])
        ys = ', '.join([f'{p.lat:.{7}}' for p in self.route])
        s = f'fig.plot(x=[{xs}], y=[{ys}]'
        olist.append('# plot routeline ')
        olist.append(s + f', pen="1,{penclr}")')
        olist.append('# plot station marks')
        olist.append(s + ', pen="3,red", S="c0.1")')
        # Plot cruise name
        namestr = f'Cruise {self.name}, {self.departure_time.split("T")[0]} - {self.arrival_time.split("T")[0]}'
        olist.append('# plot title ')
        olist.append(f'fig.text(text="{namestr}", x={reg[0]+(reg[1]-reg[0])/25}, y={reg[3]-(reg[3]-reg[2])/25}, justify="LM", font="16p,Helvetica-Bold,{penclr}")')
        olist.append(' ')
        olist.append('fig.show()')

        ofile = open(o_name, 'w')
        for r in olist:
            ofile.write(r+'\n')
        ofile.close()

    def to_ODV_GOBline(self):
        olist = []
        olist.append('%GOB1.04 graphics objects')
        olist.append('')
        olist.append(':POLYLINE')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=0')
        olist.append('doSmooth=0')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=1')
        olist.append('FillColor=-1')
        olist.append('SymbolTypeAtStart=-1')
        olist.append('SymbolSizeAtStart=3')
        olist.append('SymbolTypeAtEnd=-1')
        olist.append('SymbolSizeAtEnd=3')
        olist.append(f'nPts={len(self.route)}')
        olist.append(f'nStrokePts={len(self.route)}')
        for p in self.route:
            olist.append('{:10.5f}'.format(p.lon).strip() + ' ' + '{:9.5f}'.format(p.lat).strip())

        ofile = open(f"{self.fname.split('.')[0]}_ODV_line.gob", 'w')
        for r in olist:
            ofile.write(r + '\n')
        ofile.close()

    def to_ODV_GOBsymbols(self):
        stations = [str(p.lon) + ' ' + str(p.lat) for p in self.route if p.type == 's']
        olist = []
        olist.append('%GOB1.04 graphics objects')
        olist.append('')
        olist.append(':SYMBOLSET')
        olist.append(f'Text={self.name_en}')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=1')
        olist.append('addToLegends=1')
        olist.append('symbolNo=1')
        olist.append('symbolSize=2.5')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=-1')
        olist.append('FillColor=12')
        olist.append('BorderColor=0')
        olist.append('BorderWidth=1')
        olist.append(f'nPts={len(stations)}')

        for p in self.route:
            if p.type == 's':
                olist.append('{:10.5f}'.format(p.lon).strip() + ' ' + '{:9.5f}'.format(p.lat).strip())

        ofile = open(self.fname.split('.')[0]+'_ODV_points.gob', 'w')
        for r in olist:
            ofile.write(r+'\n')
        ofile.close()

    def to_ODV_gob(self):
        olist = []
        olist.append('%GOB1.04 graphics objects')
        olist.append('')
        olist.append(':POLYLINE')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=0')
        olist.append('doSmooth=0')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=1')
        olist.append('FillColor=-1')
        olist.append('SymbolTypeAtStart=-1')
        olist.append('SymbolSizeAtStart=3')
        olist.append('SymbolTypeAtEnd=-1')
        olist.append('SymbolSizeAtEnd=3')
        olist.append(f'nPts={len(self.route)}')
        olist.append(f'nStrokePts={len(self.route)}')
        for p in self.route:
            olist.append(f'{p.lon:.5f} {p.lat:.5f}')

        stations = [str(p.lon) + ' ' + str(p.lat) for p in self.route if p.type == 's']
        olist.append('')
        olist.append(':SYMBOLSET')
        olist.append(f'Text={self.name_en}')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=1')
        olist.append('addToLegends=1')
        olist.append('symbolNo=1')
        olist.append('symbolSize=2.5')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=-1')
        olist.append('FillColor=12')
        olist.append('BorderColor=0')
        olist.append('BorderWidth=1')
        olist.append(f'nPts={len(stations)}')

        for p in self.route:
            if p.type == 's':
                olist.append(f'{p.lon:.5f} {p.lat:.5f}')

        ofile = open(f"{self.fname.split('.')[0]}_ODV.gob", 'w')
        for r in olist:
            ofile.write(r + '\n')
        ofile.close()

    def to_KML(self):
        olist = []
        olist.append('<?xml version="1.0" encoding="UTF-8"?>')
        olist.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">')
        olist.append('<Document>')
        olist.append(f'  <name>{self.name_en}</name>')
        olist.append('  <open>1</open>')
        olist.append('  <description>Cruise route</description>')
        olist.append('  <Style id="sn_placemark_circle">')
        olist.append('    <IconStyle>')
        olist.append('      <color>802e19fc</color>')
        olist.append('      <scale>0.6</scale>')
        olist.append('      <Icon>')
        olist.append('        <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>')
        olist.append('      </Icon>')
        olist.append('    </IconStyle>')
        olist.append('    <LabelStyle>')
        olist.append('      <color>1affffff</color>')
        olist.append('      <scale>0.3</scale>')
        olist.append('    </LabelStyle>')
        olist.append('    <ListStyle>')
        olist.append('    </ListStyle>')
        olist.append('  </Style>')
        olist.append('  <StyleMap id="msn_placemark_circle">')
        olist.append('    <Pair>')
        olist.append('      <key>normal</key>')
        olist.append('      <styleUrl>#sn_placemark_circle</styleUrl>')
        olist.append('    </Pair>')
        olist.append('    <Pair>')
        olist.append('      <key>highlight</key>')
        olist.append('      <styleUrl>#sh_placemark_circle_highlight</styleUrl>')
        olist.append('    </Pair>')
        olist.append('  </StyleMap>')
        olist.append('  <Style id="sh_placemark_circle_highlight">')
        olist.append('    <IconStyle>')
        olist.append('      <color>802e19fc</color>')
        olist.append('      <scale>0.6</scale>')
        olist.append('      <Icon>')
        olist.append('        <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle_highlight.png</href>')
        olist.append('      </Icon>')
        olist.append('    </IconStyle>')
        olist.append('    <LabelStyle>')
        olist.append('      <color>1affffff</color>')
        olist.append('      <scale>0.3</scale>')
        olist.append('    </LabelStyle>')
        olist.append('    <ListStyle>')
        olist.append('    </ListStyle>')
        olist.append('  </Style>')
        olist.append('  <Placemark>')
        olist.append('    <name>Route</name>')
        olist.append('    <LineString>')
        olist.append('      <tessellate>1</tessellate>')
        olist.append('      <coordinates>')
        for p in self.route:
            olist.append(f'        {p.lon:.5f},{p.lat:.5f},0')
        olist.append('      </coordinates>')
        olist.append('    </LineString>')
        olist.append('  </Placemark>')
        olist.append('  <Folder>')
        olist.append('    <name>Points</name>')
        olist.append('    <open>1</open>')
        olist.append('    <description>These are the observation stations</description>')
        olist.append('    <LookAt>')
        lons = [p.lon for p in self.route]
        lats = [p.lat for p in self.route]
        clon = (min(lons) + max(lons))/2
        clat = (min(lats) + max(lats))/2
        olist.append(f'      <longitude>{clon:10.5f}</longitude>')
        olist.append(f'      <latitude>{clat:9.5}</latitude>')
        olist.append('      <altitude>0</altitude>')
        olist.append('      <heading>0</heading>')
        olist.append('      <tilt>0</tilt>')
        olist.append('      <range>500000</range>')
        olist.append('    </LookAt>')
        for p in self.route:
            if p.name != 'P':
                olist.append('    <Placemark>')
                olist.append(f'      <name>{p.name}</name>')
                olist.append('      <Snippet maxLines="0"></Snippet>')
                olist.append(f'      <description><![CDATA[{self.name_en}')
                olist.append(f'        <p>Longitude: {p.lon:10.5f}<br>Latitude: {p.lat:9.5f}<br>]]></description>')
                olist.append('      <styleUrl>#msn_placemark_circle</styleUrl>')
                olist.append('      <Point>')
                olist.append(f'        <coordinates>{p.lon:10.5f},{p.lat:9.5f},0</coordinates>')
                olist.append('      </Point>')
                olist.append('    </Placemark>')
        olist.append('    </Folder>')
        olist.append('  </Document>')
        olist.append('</kml>')

        ofile = open(f"{self.fname.split('.')[0]}.kml", 'w')
        for r in olist:
            ofile.write(r + '\n')
        ofile.close()

    def to_python_list(self):
        olist = []
        for p in self.route:
            if p.name != 'P': 
                olist.append(f'[{p.lon:10.5f}, {p.lat:9.5f}, {p.name}]')

        ofile = open(f"{self.fname.split('.')[0]}_python_list.txt", 'w')
        ofile.write('[')
        for r in olist[:-2]:
            ofile.write(r + ',\n')
        ofile.write(f'{olist[-1]}]')
        ofile.close()

class MKXfile:
    name = ''
    name_en = ''
    ship_name = ''
    ship_code = ''
    ship_master = ''
    nro = 0
    year = 0
    organiser = ''
    scientific_crew = []
    route = []
    status = ''
    plandatetime = ''
    timezonediff = 0
    letterid = ''
    aim_fi = []
    aim_en = []
    project = ''
    ctdname = ''
    language = ''
    softwareversion = ''
    departure_time = ''
    departure_timezone = ''
    departure_port = ''
    arrival_time = ''
    arrival_timezone = ''
    arrival_port = ''
    header_errors = []

    def __init__(self, fname):
        self.fname = fname
        self.name = ''
        self.organiser = ''
        self.nro = 0
        self.year = 0
        self.status = ''
        self.plandatetime = ''
        self.timezonediff = 0
        self.letterid = ''
        self.name_fi = ''
        self.name_en = ''
        self.aim_fi = ''
        self.aim_en = ''
        self.project = ''
        self.ctd_name = ''
        self.scientific_crew = []
        self.route = []
        self.language = ''
        self.software_version = ''
        self.master = ''
        self.platform_name = ''
        self.platform_code = ''
        self.ship_name = ''
        self.ship_code = ''
        self.ship_master = ''
        self.departure_time = ''
        self.departure_timezone = ''
        self.departure_port = ''
        self.arrival_time = ''
        self.arrival_timezone = ''
        self.arrival_port = ''

        my_file = Path(fname)
        if my_file.is_file():
            self.read()
            self.OK = True
        else:
            self.OK = False

    def read(self):
        # read the mcx-file into mcx-object
        cruise = ET.parse(self.fname).getroot()

        cruise_attributes = cruise.attrib
        self.organiser = cruise_attributes['organiser']
        self.name_fi = cruise_attributes['name']
        self.name_en = cruise_attributes['nameEN']
        self.nro = cruise_attributes['nro']
#        self.platform_name = cruise_attributes['platformname']
#        self.collate_center = cruise_attributes['collateCenter']
#        self.platform_code = cruise_attributes['platformcode']
#        self.platform_class = cruise_attributes['platform_class']
        self.project = cruise_attributes['project']
        self.plan_status = cruise_attributes['status']
        self.plan_datetime = cruise_attributes['planDateTime']
        self.plan_language = cruise_attributes['language']

        self.software_version = cruise.find("software").get('version')

        ship = cruise.find("ship")
        self.ship_name = ship.get('name')
        self.ship_code = ship.get('platformcode')
        self.ship_master = ship.get('master')

        departure = cruise.find('departure')
        self.departure_time = departure.get('dateTime')
        self.departure_timezone = departure.get('timeZone')
        self.departure_port = departure.get('harbour')

        arrival = cruise.find('arrival')
        self.arrival_time = arrival.get('dateTime')
        self.arrival_timezone = arrival.get('timeZone')
        self.arrival_port = arrival.get('harbour')

        # Description of the cruise in English and in Finnish
        description_en = cruise.find('description')
        description_fi = cruise.find('descriptionFIN')
        self.aim_en = []
        for row in description_en.findall('dr'):
            self.aim_en.append(row.text)
        self.aim_fi = []
        for row in description_fi.findall('drf'):
            self.aim_fi.append(row.text)

        self.year = 0
        self.timezonediff = 0
        self.letterid = ''
        self.ctd_name = ''

        # get scientific crew
        self.scientific_crew = []
        staff = cruise.find("staff")
        for person in staff.findall("person"):
            member = Participant(
                person.attrib['firstName'], person.attrib['familyName'])
            member.organisation = person.attrib['institute']
            member.infixed = person.attrib['inFixed']
            member.indate = person.attrib['inDate']
            member.outfixed = person.attrib['outFixed']
#            member.outdate = person.attrib['outDate']
            if person.find('role') is not None:
                member.role = person.find('role').text
            if person.find('project') is not None:
                member.project = person.find('project').text
            cabin = person.find('cabin').attrib
            member.cabin_no = cabin['nro']
            member.cabin_phone = cabin['phone']
            lab = person.find('lab').attrib
            member.lab_no = lab['nro']
            member.lab_phone = lab['phone']

            self.scientific_crew.append(member)

        # Get cruise route
        croute = cruise.find("route")

        defaults = croute.find('defaults')
        self.default_speed_knots = float(defaults.find('speed').text)

        hm = defaults.find('duration').text[1:]
        if 'H' in hm and 'M' in hm:
            h = float(hm.split('H')[0]) + \
                float(hm.split('H')[1].split('M')[0])/60
        elif 'H' in hm:
            h = float(hm.split('H')[0])
        elif 'M' in hm:
            h = float(hm.split('M')[0])/60
        else:
            h = 1.0
        self.default_duration_hours = h

        if defaults.find('observations') is not None:
            ocode = defaults.find('observations')
            if ocode.find('obscode') is not None:
                self.default_observations = ocode.find('obscode').text

        self.default_mapsymbol = defaults.find('mapsymbol').attrib

        # Get routepoints
        stations = croute.find("points")
        for station in stations.findall("point"):
            la = station.find('lat').text.split('D')
            lat = float(la[0])+float(la[1].split('M')[0])/60
            lo = station.find('long').text.split('D')
            lon = float(lo[0])+float(lo[1].split('M')[0])/60

            rpoint = Routepoint(station.find('name').text, lat, lon)

            rpoint.nro = station.attrib['nro']
            rpoint.type = station.attrib['type']
            rpoint.status = station.attrib['status']
            rpoint.index = station.attrib['index']

            rpoint.depth = float(station.find('depth').text)
            rpoint.distance = float(station.find('distance').text)
            rpoint.entry = station.find('entry').attrib['dateTime']
#            rpoint.entry_status = station.find('entry').attrib['status']
            dur = station.find('duration').text[1:]
            rpoint.duration = dur
            rpoint.exit = station.find('exit').attrib['dateTime']
            rpoint.exit_status = station.find('exit').attrib['status']
            rpoint.speed = float(station.find('speed').text)
            rpoint.speed_status = station.find('speed').attrib['status']

            if station.find('observations') is not None:
                ocode = station.find('observations')
                if ocode.find('obscode') is not None:
                    rpoint.observations = ocode.find('obscode').text

            if station.find('SDN_P02_parameters') is not None:
                rpoint.SDN_P02_parameters = station.find(
                    'SDN_P02_parameters').text

            if station.find('SDN_C77_data') is not None:
                rpoint.SDN_C77_data = station.find('SDN_C77_data').text

            if station.find('Country') is not None:
                rpoint.country = station.find('Country').text
            if station.find('SeaArea') is not None:
                rpoint.sea_area = station.find('SeaArea').text
            if child_node_text(station, 'isMooring') is not None:
                rpoint.mooring = child_node_text(station, 'isMooring')
            if station.find('mapsymbol') is not None:
                rpoint.mapsymbol = station.find('mapsymbol').attrib
            if child_node_text(station, 'comments') is not None:
                rpoint.comments = child_node_text(station, 'comments')

            self.route.append(rpoint)

        if cruise.find('acquisitionInfo') is not None:
            # jotain
            self.acquisitionInfo = cruise.find('acquisitionInfo').text

        if cruise.find('accesPolicies') is not None:
            self.accessPolicies = cruise.find('accesPolicies').text

        if cruise.find('dataPaths') is not None:
            datapaths = cruise.find('dataPaths')
            if datapaths.find('MKXsave') is not None:
                if datapaths.find('MKXsave').attrib['value'] == 'false':
                    self.mkxsave = False
                else:
                    self.mkxsave = True

        self.mapfiles = []
        for mf in cruise.findall('mapfiles'):
            if mf is not None:
                self.mapfiles.append(mf.text)

        if self.name_en == '':
            self.name_en = self.name_fi

    def get_persons_in_role(self, a_role):
        result = []
        for person in self.scientific_crew:
            if a_role in person.role:
                result.append(f'{person.family_name} {person.first_name}')
        return result

    def who_is(self, a_role):
        result = 'none'
        for person in self.scientific_crew:
            if a_role in person.role:
                result = f'{person.family_name} {person.first_name}'
        return result

    def get_chief_scientist(self):
        result = self.who_is('chief scientist')
        return result

    def get_chief_chemist(self):
        result = self.who_is('chief chemist')
        return result

    def get_IT_chief(self):
        result = self.who_is('IT-chief')
        return result

    def get_lat(self):
        lat = []
        for station in self.route:
            lat.append(station.lat)
        return lat

    def get_boundingbox(self):
        result = [180.0, 90, -180.0, -90.0]
        lat = []
        lon = []
        for station in self.route:
            lat.append(station.lat)
            lon.append(station.lon)
        result = [min(lon), min(lat), max(lon), max(lat)]
        return result

    def leaflethtml(self):
        #   Prints the leaflet html into a file
        [lo1, la1, lo2, la2] = self.get_boundingbox()
        llhtml = mcx_html_tmpl.copy()
        for I in range(len(llhtml)):
            if '<title>' in llhtml[I]:
                llhtml[I] = f'    <title>Routemap of {self.name_en}</title>'

            if 'var map = L.map' in llhtml[I]:
                llhtml[I] = '      var map = L.map(\'map\', {center:[' \
                    f'{((la1+la2)/2):10.6f}, {((lo1+lo2)/2):11.6f}], '\
                    f'zoom: 5}});'

            if 'Cruise route of' in llhtml[I]:
                llhtml[I] = '        this._div.innerHTML = \'<h4 style="color: #0000CC;">Cruise route of' \
                    + ' the ' \
                    + self.platform_name \
                    + ' cruise ' \
                    + self.nro \
                    + '/' \
                    + str(self.year) \
                    + '</h4>' \
                    + self.name_en \
                    + '<br>' \
                    + self.departure_time.split('T')[0] \
                    + ' - ' \
                    + self.arrival_time.split('T')[0] \
                    + '\';'
            if '//pisteet ja reitti' in llhtml[I]:
                I1 = I
                I2 = I+1

        olist = []

        for I in range(0, I1):
            olist.append(llhtml[I])

        olist.append('')
        olist.append('      var stationPoints = L.layerGroup();')
        olist.append('')

        for I in range(len(self.route)):
            if self.route[I].name == 'P':
                continue
            nameandtime = f'{I}: {self.route[I].name}, {self.route[I].entry}'\
                f', {self.route[I].distance:5.1f} nmi'

            country = sarea.whosEconomicZone(
                [self.route[I].lon, self.route[I].lat])
            if country == 'Finland':
                pColor = 'green'
            else:
                pColor = 'red'

            r = '      L.circle(['\
                f'{self.route[I].lat:9.6f}, {self.route[I].lon:11.6f}], 500,'\
                f" {{color: '{pColor}',fillColor: '{pColor}',"\
                f"fillOpacity: 0.5"\
                f'}}).addTo(stationPoints).bindTooltip("{nameandtime}");'
            olist.append(r)

        olist.append(' ')
        olist.append('      var routeLine = L.layerGroup();')
        olist.append('      var antLine   = L.layerGroup();')
        olist.append('')

        rLine = '      route = ['
        for I in range(len(self.route)-1):
            rLine = rLine +\
                f'[{self.route[I].lat:9.5f}, {self.route[I].lon:10.5f}],'
        rLine = rLine +\
            f'[{self.route[-1].lat:9.5f}, {self.route[-1].lon:10.5f}]]'

        olist.append(rLine)
        olist.append(
            '      L.polyline(route, {color: \'blue\', weight: 1}).' +
            'addTo(routeLine);')
        olist.append(' ')
        olist.append('      antroute = L.polyline.antPath(route, {')
        olist.append('          "delay": 1000,')
        olist.append('          "dashArray": [10,10],')
        olist.append('          "weight": 3,')
        olist.append('          "color": "#0000FF",')
        olist.append('          "pulseColor": "#FFFFFF",')
        olist.append('          "paused": false ,')
        olist.append('          "reverse": false ,')
        olist.append('          "hardwareAccelerated": true')
        olist.append('      }).addTo(antLine)')
        olist.append(' ')

        for I in range(I2, len(llhtml)):
            olist.append(llhtml[I])

        o_file = open(f"{self.fname.split('.')[0]}.html", 'w')
        for i in range(len(olist)):
            o_file.write(olist[i] + '\n')
        o_file.close()

    def to_gmtscript(self,topodir=None):
        o_name = f"{self.fname.split('.')[0]}_gmt.txt"
        [lo1, la1, lo2, la2] = self.get_boundingbox()
        reg = [float(math.trunc(lo1-1)),float(math.trunc(lo2+2)), float(math.trunc(la1)), float(math.trunc(la2+1))]
        olist = []
        olist.append('import pygmt')
        olist.append(' ')
        olist.append('fig = pygmt.Figure()')
        olist.append(' ')
        olist.append('# mapregion [minlon, maxlon, minlat, maxlat]')
        olist.append(f'fig.basemap(region=[{reg[0]:.{7}}, {reg[1]:.{7}}, {reg[2]:.{7}}, {reg[3]:.{7}}], projection="M8i", frame=True)')
        if topodir:
            topodat = f'{topodir}Baltic_Sea_topo.nc'
            topoclr = f'{topodir}Baltic_Sea_topo.cpt' 
            olist.append('# plot bottom topography')
            olist.append(f'fig.grdimage("{topodat}", cmap="{topoclr}")')
            olist.append('# plot land')
            olist.append('fig.coast(land="darkgreen")')
            penclr = 'black'
        else:
            olist.append('# plot land')
            olist.append('fig.coast(land="darkgreen", water="navy")')
            penclr = 'white'

        xs = ', '.join([f'{p.lon:.{7}}' for p in self.route])
        ys = ', '.join([f'{p.lat:.{7}}' for p in self.route])
        s ='fig.plot(x=[' + xs + '], y=[' + ys + ']'
        olist.append('# plot routeline ')
        olist.append(s + f', pen="1,{penclr}")')
        olist.append('# plot station marks')
        olist.append(s + ', pen="3,red", S="c0.1")')
        # Plot cruise name
        namestr = f'Cruise {self.name}, {self.departure_time.split("T")[0]} - {self.arrival_time.split("T")[0]}'
        olist.append('# plot title ')
        olist.append(f'fig.text(text="{namestr}", x={reg[0]+(reg[1]-reg[0])/25}, y={reg[3]-(reg[3]-reg[2])/25}, justify="LM", font="16p,Helvetica-Bold,{penclr}")')
        olist.append(' ')
        olist.append('fig.show()')

        ofile = open(o_name, 'w')
        for r in olist:
            ofile.write(r+'\n')
        ofile.close()

    def to_ODV_GOBline(self):
        olist = []
        olist.append('%GOB1.04 graphics objects')
        olist.append('')
        olist.append(':POLYLINE')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=0')
        olist.append('doSmooth=0')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=1')
        olist.append('FillColor=-1')
        olist.append('SymbolTypeAtStart=-1')
        olist.append('SymbolSizeAtStart=3')
        olist.append('SymbolTypeAtEnd=-1')
        olist.append('SymbolSizeAtEnd=3')
        olist.append(f'nPts={len(self.route)}')
        olist.append(f'nStrokePts={len(self.route)}')
        for p in self.route:
            olist.append(f'{p.lon:.5f} {p.lat:.5f}')

        ofile = open(f"{self.fname.split('.')[0]}_ODV_line.gob", 'w')
        for r in olist:
            ofile.write(r+'\n')
        ofile.close()

    def to_ODV_GOBsymbols(self):
        stations = [f"{p.lon} {p.lat}" for p in self.route if p.type == 's']
        olist = []
        olist.append('%GOB1.04 graphics objects')
        olist.append('')
        olist.append(':SYMBOLSET')
        olist.append(f'Text={self.name_en}')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=1')
        olist.append('addToLegends=1')
        olist.append('symbolNo=1')
        olist.append('symbolSize=2.5')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=-1')
        olist.append('FillColor=12')
        olist.append('BorderColor=0')
        olist.append('BorderWidth=1')
        olist.append(f'nPts={len(stations)}')

        for p in self.route:
            if p.type == 's':
                olist.append(f'{p.lon:.5f} {p.lat:.5f}')

        ofile = open(f"{self.fname.split('.')[0]}_ODV_points.gob", 'w')
        for r in olist:
            ofile.write(r + '\n')
        ofile.close()

    def to_ODV_gob(self):
        olist = []
        olist.append('%GOB1.04 graphics objects')
        olist.append('')
        olist.append(':POLYLINE')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=0')
        olist.append('doSmooth=0')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=1')
        olist.append('FillColor=-1')
        olist.append('SymbolTypeAtStart=-1')
        olist.append('SymbolSizeAtStart=3')
        olist.append('SymbolTypeAtEnd=-1')
        olist.append('SymbolSizeAtEnd=3')
        olist.append(f'nPts={len(self.route)}')
        olist.append(f'nStrokePts={len(self.route)}')
        for p in self.route:
            olist.append(f'{p.lon:.5f} {p.lat:.5f}')

        stations = [f'{p.lon} {p.lat}' for p in self.route if p.type == 's']
        olist.append('')
        olist.append(':SYMBOLSET')
        olist.append(f'Text={self.name_en}')
        olist.append('coordinates=1')
        olist.append('clip=1')
        olist.append('iOrder=1')
        olist.append('isFixed=1')
        olist.append('addToLegends=1')
        olist.append('symbolNo=1')
        olist.append('symbolSize=2.5')
        olist.append('LineColor=1')
        olist.append('LineType=0')
        olist.append('LineWidth=-1')
        olist.append('FillColor=12')
        olist.append('BorderColor=0')
        olist.append('BorderWidth=1')
        olist.append(f'nPts={len(stations)}')

        for p in self.route:
            if p.type == 's':
                olist.append(f'{p.lon:.5f} {p.lat:.5f}')

        ofile = open(f"{self.fname.split('.')[0]}_ODV.gob", 'w')
        for r in olist:
            ofile.write(r + '\n')
        ofile.close()

    def to_KML(self):
        olist = []
        olist.append('<?xml version="1.0" encoding="UTF-8"?>')
        olist.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">')
        olist.append('<Document>')
        olist.append(f'  <name>{self.name_en}</name>')
        olist.append('  <open>1</open>')
        olist.append('  <description>Cruise route</description>')
        olist.append('  <Style id="sn_placemark_circle">')
        olist.append('    <IconStyle>')
        olist.append('      <color>802e19fc</color>')
        olist.append('      <scale>0.6</scale>')
        olist.append('      <Icon>')
        olist.append('        <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>')
        olist.append('      </Icon>')
        olist.append('    </IconStyle>')
        olist.append('    <LabelStyle>')
        olist.append('      <color>1affffff</color>')
        olist.append('      <scale>0.3</scale>')
        olist.append('    </LabelStyle>')
        olist.append('    <ListStyle>')
        olist.append('    </ListStyle>')
        olist.append('  </Style>')
        olist.append('  <StyleMap id="msn_placemark_circle">')
        olist.append('    <Pair>')
        olist.append('      <key>normal</key>')
        olist.append('      <styleUrl>#sn_placemark_circle</styleUrl>')
        olist.append('    </Pair>')
        olist.append('    <Pair>')
        olist.append('      <key>highlight</key>')
        olist.append('      <styleUrl>#sh_placemark_circle_highlight</styleUrl>')
        olist.append('    </Pair>')
        olist.append('  </StyleMap>')
        olist.append('  <Style id="sh_placemark_circle_highlight">')
        olist.append('    <IconStyle>')
        olist.append('      <color>802e19fc</color>')
        olist.append('      <scale>0.6</scale>')
        olist.append('      <Icon>')
        olist.append('        <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle_highlight.png</href>')
        olist.append('      </Icon>')
        olist.append('    </IconStyle>')
        olist.append('    <LabelStyle>')
        olist.append('      <color>1affffff</color>')
        olist.append('      <scale>0.3</scale>')
        olist.append('    </LabelStyle>')
        olist.append('    <ListStyle>')
        olist.append('    </ListStyle>')
        olist.append('  </Style>')
        olist.append('  <Placemark>')
        olist.append('    <name>Route</name>')
        olist.append('    <LineString>')
        olist.append('      <tessellate>1</tessellate>')
        olist.append('      <coordinates>')
        for p in self.route:
            olist.append('        ' + f'{p.lon:.5f},{p.lat:.5f},0')
        olist.append('      </coordinates>')
        olist.append('    </LineString>')
        olist.append('  </Placemark>')
        olist.append('  <Folder>')
        olist.append('    <name>Points</name>')
        olist.append('    <open>1</open>')
        olist.append('    <description>These are the observation stations</description>')
        olist.append('    <LookAt>')
        lons = [p.lon for p in self.route]
        lats = [p.lat for p in self.route]
        clon = (min(lons) + max(lons))/2
        clat = (min(lats) + max(lats))/2
        olist.append(f'      <longitude>{clon:10.5f}</longitude>')
        olist.append(f'      <latitude>{clat:9.5}</latitude>')
        olist.append('      <altitude>0</altitude>')
        olist.append('      <heading>0</heading>')
        olist.append('      <tilt>0</tilt>')
        olist.append('      <range>500000</range>')
        olist.append('    </LookAt>')
        for p in self.route:
            if p.name != 'P':
                olist.append('    <Placemark>')
                olist.append(f'      <name>{p.name}</name>')
                olist.append('      <Snippet maxLines="0"></Snippet>')
                olist.append('      <description><![CDATA[' + self.name_en)
                olist.append(f'        <p>Longitude: {p.lon:10.5f}<br>Latitude: {p.lat:9.5f}<br>]]></description>')
                olist.append('      <styleUrl>#msn_placemark_circle</styleUrl>')
                olist.append('      <Point>')
                olist.append(f'        <coordinates>{p.lon:10.5f},{p.lat:9.5f},0</coordinates>')
                olist.append('      </Point>')
                olist.append('    </Placemark>')
        olist.append('    </Folder>')
        olist.append('  </Document>')
        olist.append('</kml>')

        ofile = open(f"{self.fname.split('.')[0]}.kml", 'w')
        for r in olist:
            ofile.write(r + '\n')
        ofile.close()
