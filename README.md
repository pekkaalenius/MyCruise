# MyCruise

# mcxFile.py

This repository contains some MyCruise related Python units.
They contain only a small fraction of the functionalities of the MyCruise software

MyCruise is a scientific cruise planning software system for planning RV Aranda cruises in the Baltic Sea.
MyCruise is Windows-software written in Delphi7 (Pascal). 
In the core of MyCruise is the cruise plan that is an xml-file. Aranda compatible version has extension mkx.
Newer version of MyCruise uses more advanced cruise plan with an extension mcx.

mcxFile.py contains mcx- and mkx-file classess for reading those files.
myCruisefile.py is older version of the mcxFile.
usage: 
import mcxFile as mcx
acruise = mcx.mcxFile(filename)

The most useful methods of the class are related to plotting route maps. 

mycruise_map.py is a Python script that can output routemap or files that can be used to
plot the route on a map with some other programs.
Running mycruise_map.py -h gives the usege with options.
The routine can produce Leaflet, GMT, ODV and KML compatible files.

# sea_areas.py

This is a unit that contains lsits of dictionaries for geographical sea areas of the Baltic Sea.
It also contains rough EEZ's, territorial waters and baselines.
There are routines to find in which particular area a lon,lat point is.

# station_dictionaries.py

This unit contains routines to make station lists for use with other routines.
There are option to read local files that contain dictionaries and routines to generate
dictionaries from ICES station dictionary (publicly available) and from FMI database (in-house only).

# strutils_pa.py

This unit contains some string handling that is used in other routines included.
