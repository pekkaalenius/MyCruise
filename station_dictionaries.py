import urllib.request
import zipfile
import sea_areas as sa


def read_station_dictionary(filename):
#=====================================
# The Aranda station list an be in a local file
# Such a local file can be done with make_station_list_from_Sumppu

    with open(filename, 'r') as f:
        s = f.read().split('\n')
    stations = []
    for r in s:
        n, la, lo, d, c, s, t, v, y, a = r.split(';')
        stations.append({'name': n, 'lat': float(la), 'lon': float(lo), 'depth': int(d), 'country': int(c), 'area': int(s), 'type': t, 'visits': int(v), 'year': int(y), 'years': int(a)})
 
    return stations

def get_station_dictionary():
#============================
# This reads the Aranda station list from github (pekkaalenius)
# Note that the list may be old and does not contain all new stations

    import requests
    url = 'https://raw.githubusercontent.com/pekkaalenius/MyCruise/main/asemat.txt'
    result = requests.get(url, allow_redirects=True)
    rd = result.text.split('\n')[:-2]
    stations = []
    for r in rd:
        n, la, lo, d, c, s, t, v, y, a = r.split(';')
        stations.append({'name': n, 'lat': float(la), 'lon': float(lo), 'depth': int(d), 'country': int(c), 'area': int(s), 'type': t, 'visits': int(v), 'year': int(y), 'years': int(a)})
 
    return stations

def get_station_dictionary_from_Sumppu(ahost, auser, apassword, **kwargs):
#=========================================================================
# This generates a new Aranda station list from Sumppu. Connection to Sumppu
# has to be available.

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
            country = sa.getMyCruiseCountryCode([lon, lat])
            area = sa.getMyCruiseHelcomAreaCode([lon, lat])
            stations.append({'name': x[0], 'lat': lat, 'lon': lon, 'depth': int(x[3]), 'country': country, 'area': area, 'type': 'S1', 'visits': int(x[4]), 'year': int(x[5]), 'years': int(x[6])})
    
    sumppu_cursor.close()
    sumppu.close()

    return stations

def make_station_list_from_Sumppu(host, user, password, file_to_save):
#=====================================================================
# This makes the Aranda station list from Sumppu using the previous routine
# and stores the result into a local file

    stations = get_station_dictionary_from_Sumppu(host, user, password, savefile=file_to_save)
    if file_to_save != '':
        ofile = open(file_to_save, 'w')
        for s in stations:
            ofile.write(f"{s['name']};{s['lat']:9.6f};{s['lon']:10.6f};{s['depth']};{s['country']};{s['area']};{s['type']};{s['visits']};{s['year']};{s['years']}\n")
        ofile.close()


def get_BalticSea_ices_stations():
#=================================
# This routine downloads ICES StationDictionary.zip,
# reads the Station_yyyy-mm-dd-hh-mm.tab file,
# takes from there stations that belong to Baltic Sea countries
# ['DK', 'DE', 'FI', 'EE', 'LV', 'LT', 'PL', 'RU', 'SE']
# and are inside the Baltic Sea.
# It returns a list of dictionaries:
# [{'name': name, 'country': countrycode, 'lat': lat, 'dlat': latrange, 'lon': lon, 'dlon': lonrange}...]

    url = 'https://www.ices.dk/data/Documents/ENV/StationDictionary.zip'

#    The following lines could be used to extract the files to a local directory
#    extract_dir = "example"
#    zip_path, _ = urllib.request.urlretrieve(url)
#    with zipfile.ZipFile(zip_path, "r") as f:
#        f.extractall(extract_dir)

    filehandle, _ = urllib.request.urlretrieve(url)
    zip_file_object = zipfile.ZipFile(filehandle, 'r')
    files = zip_file_object.namelist()
    id = -1
    for i in range(len(files)):
        if 'Station_' in files[i][:8]:
            id = i
    if id > -1: 
        station_file = zip_file_object.namelist()[id]
        file = zip_file_object.open(station_file)
        content = file.read()
        c = content.decode()
        data = c.split('\r')

        i = 0
        countries = ['DK', 'DE', 'FI', 'EE', 'LV', 'LT', 'PL', 'RU', 'SE']
        stations = []
        for d in data[1:]:
            if 'Relation' in d:
                break
            i = i + 1
            s = d.split('\t')
            if s[3] in countries:
                try:
                    country = s[3]
                    name = s[4]
                    lat = float(s[11])
                    lat_range = float(s[12])
                    lon = float(s[13])
                    lon_range = float(s[14])
                except:
                    lat = float(s[12])
                    lat_range = float(s[13])
                    lon = float(s[14])
                    lon_range = float(s[15])

                if sa.gsw_Baltic(lon, lat):
                    stations.append({'name': name, 'country': country, 'lat': lat, 'dlat': lat_range, 'lon': lon, 'dlo': lon_range})
    return stations

