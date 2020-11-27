# MyCruise

This repository contains MyCruise related Python utilities.
They contain only a tiny incomplete part of the functionalities of the MyCruise software

MyCruise is a scientific cruise planning software system for planning RV Aranda cruises in the Baltic Sea.
MyCruise is Windows-software written in Delphi7 (Pascal). 
In the core of MyCruise is the cruise plan that is an xml-file. Aranda compatible version has extension mkx.
Newer version of MyCruise uses more advanced cruise plan with an extension mcx.

The mcxFile.py contain MCXfile and MKXfile classes that can read and parse respective files.
usage: acruise = MCXfile(filename)

At the moment the useful methods of the MCXfile and MKXfile classes are related to plotting maps. 
The most versatile option is to plot a Leaflet map (html-file) that can be opened with a browser.
It shows the route of the cruise with stations and some information on the stations.

The Python script mcx_to_leaflet.py makes maps from mcx or mkx file(s).
usage:
python mcx_to_leaflet.py  - asks the file(s) from which maps are saved
python mcx_to_leaflet.py filename.mcx (or filename.mkx) - saves filename as map
python mcx_to_leaflet.py directoryname - saves all mcx and mkx files in the defined directory as maps

The Python script mcx_to_map.py makes maps or route for maps. This includes
the actions of mcx_to_leaflet.py. running mcx_to_map.py -h gives the usegae with options.
The routine can produce Leaflet, GMT, ODV and KML compatible files.

