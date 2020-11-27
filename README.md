# MyCruise

This repository contains MyCruise related Python utilities.
They contain only a tiny incomplete part of the functionalities of the MyCruise software

MyCruise is a scientific cruise planning software system for planning RV Aranda cruises in the Baltic Sea.
MyCruise is Windows-software written in Delphi7 (Pascal). 
In the core of MyCruise is the cruise plan that is an xml-file. Aranda compatible version has extension mkx.
Newer version of MyCruise uses more advanced cruise plan with an extension mcx.

The myCruisefile.py contains mycruisefile-class that can read MCX- and MKX-files.
usage: acruise = mycruisefile(filename)

At the moment the most useful methods of the class are related to plotting maps. 

mycruise_map.py is a Python script that can output routemap or files that can be used to
plot the route on a map with some other programs.
Running mycruise_map.py -h gives the usege with options.
The routine can produce Leaflet, GMT, ODV and KML compatible files.
