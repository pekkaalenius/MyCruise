'''
Tämä tekee Arandan matkasuunnitelman mcx-tiedostosta Leaflet-kartan (html-tiedoston)

Pohjana käytetään MyCruise_Leaflet_Routemap_template_variable_size.html-tiedostoa,
josta tehdään kopio, johon laitetaan matkaa koskevat tiedot oikeille paikoilleen.

Tämän kanssa samassa hakemistossa tulee olla seuraavat tiedostot:
- mcxFile.py
'''
import os
import sys
import mcxFile as mcx

f_names = []
if len(sys.argv) > 1:
    f_name = sys.argv[1] 
    if not '.MCX' in f_name.upper() and not '.MKX' in f_name.upper():
        f_names = [i for i in os.listdir(f_name) if i.upper().endswith('.MCX') or i.upper().endswith('.MKX')]
    else:
        f_names.append(f_name) 
else:
    f_name = input('Anna matka: ')
    f_names.append(f_name) 

for f in f_names:
#    print(f)
    if '.MCX' in f.upper():
        acruise = mcx.MCXfile(f)
    else:
        acruise = mcx.MKXfile(f)
    acruise.leaflethtml()


