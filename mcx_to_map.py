'''
Tämä tekee Arandan matkasuunnitelman mcx-tiedostosta kartan.
Karttatiedoston muoto valitaan vaihtoehdoista:
- interaktiivinen Leaflet-kartta (html-tiedosto)
- pyGMT-skripti, jolla voi piirtää kartan GML:llä
- ODV:n gob-tiedosto, jolla saa reitin ja pisteet ODV-kartalle
- kml-tiedosto, joplla saa pisteet Google Earth:iin

Tämän kanssa samassa hakemistossa tulee olla seuraavat tiedostot:
- mcxFile.py
'''
import os
import sys
import mcxFile as mcx


outputtypes = ['L', 'P', 'O', 'I', 'S', 'K']
f_names = []
outputtype = ''
topodir = ''

for a in sys.argv[1:]:
    if '-h' or 'help' or '-help' in a:
        print('\nUsage:')
        print('mcx_to_map           - input parameters are asked')
        print('mcx_to_map directory - finds all mcx and mkx files')
        print('                       in directory and asks rest of the parameters')
        print('mcx_to_map filename  - uses the given file')
        print('                       and asks rest of the parameters')
        print('mcx_to_map with command line parameters:')
        print('    input=filename|directory')
        print('    outputtype=L|P|O|I|S|K, small letters can also be used')
        print('               L - Leaflet html-file')
        print('               P - pyGMT script to plot the map with GMT')
        print('               O - ODV gob-file with line and points')
        print('               I - ODV gob-file, line only')
        print('               S - ODV gob-file, points only')
        print('               K - Google Earth kml-file')
        print('    topodir=directory')
        print('            used only with outputtype P to plot topography')
        print('            using Baltic_Sea_topo.nc and Baltic_Sea_topo.cpt')
        print('            from directory, otherwise the sea color is navy')
        print('\nexample:')
        print('mcx_to_map input=VRT_2020_syksy.mcx outputtype=L topodir=/Users/pekka/GMTomat\n')
        sys.exit(2)

    if 'input' in a:
        f_name = a.split('=')[1]
        if not '.MCX' in f_name.upper() and not '.MKX' in f_name.upper():
            f_names = [i for i in os.listdir(f_name) if i.upper().endswith('.MCX') or i.upper().endswith('.MKX')]
        else:
            f_names.append(f_name) 
    if 'outputtype' in a:
        outputtype = a.split('=')[1].upper()
    if 'topodir' in a:
        topodir = a.split('=')[1]

# Choose files to print
if len(f_names) == 0:
    if len(sys.argv) > 1:
        f_name = sys.argv[1] 
        if not '.MCX' in f_name.upper() and not '.MKX' in f_name.upper():
            f_names = [i for i in os.listdir(f_name) if i.upper().endswith('.MCX') or i.upper().endswith('.MKX')]
        else:
            f_names.append(f_name) 
    else:
        f_name = input('Anna matka: ')
        f_names.append(f_name)

# Choose output-type
if outputtype == '':
    if len(sys.argv) > 2:
        outputtype = sys.argv[2].upper()[0]
    else:
        outputtype = input('Anna tulostustyyppi '+
            '(pieni kirjain käy myös)\n L = Leaflet,\n P = pyGMT,\n '+
            'O = ODV gob line with points,\n I = ODV gob line,\n '+
            'S = ODV gob points,\n K = Google kml:\n ')
        if outputtype == '':
            outputtype = 'L'
        else:
            outputtype = outputtype.upper()[0]

if outputtype not in outputtypes:
    outputtype = 'L'

if outputtype == 'P':
    if topodir == '':
        topodir = input('If you have files\n'+
            'Baltic_Sea_topo.nc and Baltic_Sea_topo.cpt,\n'+
            'give their directory to get topography on the map, or push enter ')
    if topodir != '' and topodir[-1] != '/':
        topodir = topodir + '/'
    
# Print chosen files in chosen output type
for f in f_names:
    if '.MCX' in f.upper():
        acruise = mcx.MCXfile(f)
    else:
        acruise = mcx.MKXfile(f)
    
    if outputtype == 'L':
        acruise.leaflethtml()
    elif outputtype == 'P':
        if topodir == '':
            acruise.to_gmtscript()
        else:
            acruise.to_gmtscript(topodir)
    elif outputtype == 'O':
        acruise.to_ODV_gob()
    elif outputtype == 'I':
        acruise.to_ODV_GOBline()
    elif outputtype == 'S':
        acruise.to_ODV_GOBsymbols()
    elif outputtype == 'K':
        acruise.to_KML()

print('Output file(s) are ready!')


