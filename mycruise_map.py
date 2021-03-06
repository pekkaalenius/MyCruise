'''
This routine makes a route map from mcx- or mkx-file(s).
Output has severel options:
- interactive Leaflet-map (html-file)
- pyGMT-script, that makes the map in pyGMT
- ODV gob-file that can be read to ODV
- kml-file for plotting route in Google Earth

This needs:
- myCruisefile.py in the same directory
and optionally for pyGMT output in some directory
- Baltic_sea_topo.nc that is a gridded bottom topography
- Baltic_Sea_topo.cpt that is color scale for topography
'''
import os
import sys
import myCruisefile as mcx


outputtypes = ['L', 'P', 'O', 'I', 'S', 'K']
f_names = []
outputtype = ''
topodir = ''

for a in sys.argv[1:]:
    if a == '-h' or a == 'help' or a == '-help':
        print('\nUsage:')
        print('mycruise_map           - input parameters are asked')
        print('mycruise_map directory - finds all mcx and mkx files')
        print('                       in directory and asks rest of the parameters')
        print('mycruise_map filename  - uses the given file')
        print('                       and asks rest of the parameters')
        print('mycruise_map with command line parameters:')
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
        print('mycruise_map input=VRT_2020_syksy.mcx outputtype=L topodir=/Users/pekka/GMTomat\n')
        sys.exit(2)

    if 'input=' in a:
        f_name = a.split('=')[1]
        if not '.MCX' in f_name.upper() and not '.MKX' in f_name.upper():
            f_names = [i for i in os.listdir(f_name) if i.upper().endswith('.MCX') or i.upper().endswith('.MKX')]
        else:
            f_names.append(f_name) 
    if 'outputtype=' in a:
        outputtype = a.split('=')[1].upper()
    if 'topodir=' in a:
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
        f_name = input('Give cruise file: ')
        f_names.append(f_name)

# Choose output-type
if outputtype == '':
    if len(sys.argv) > 2:
        outputtype = sys.argv[2].upper()[0]
    else:
        outputtype = input('Give outputtype '+
            '(small letters are also accepted)\n L = Leaflet,\n P = pyGMT,\n '+
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
    acruise = mcx.mycruisefile(f)
    
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
