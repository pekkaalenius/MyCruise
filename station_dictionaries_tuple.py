import urllib.request
import zipfile
from collections import namedtuple
import sea_area_tuples as sa

Aranda_station = namedtuple("Aranda_station", \
    "name position depth country sea_area type visits first_year years")
ICES_station = namedtuple("ICESstation", \
    "name country position lat_range lon_range")

def read_station_dictionary(filename):
    """The Aranda station list is read from a local file, that
       has been done with make_station_list_from_Sumppu
    """
    with open(filename, 'r') as f:
        s = f.read().split('\n')
    stations = []
    for r in s:
        n, la, lo, d, c, s, t, v, y, a = r.split(';')
        stations.append(\
            Aranda_station(n, sa.Gp(float(lo), float(la)), int(d), \
                int(c), int(s), t, int(v), int(y), int(a)))
    return stations

def read_Aranda_stations_to_namedtuples(fname):
    """ Reads Aranda stations from a txt-file to an array of named tuples.

        In the Station namedtuple the latitude and longitude are joined to
        namedtuple position (lon, lat) for compatibility with sea_area_tuples.
        Position lon and lat: station.position.lat station.position.lon
    """
    stations = []
    with open(fname, "r") as f:
        fr = f.read().split('\n')
        i = 0
        j = len(fr)
        if 'name' in fr[0]:
            i = 1
        if fr[-1] == '':
            j = -1
        fr = fr[i:j]

        for row in fr:
            r = row.split(';')
            try:
                stations.append(
                    Aranda_station(
                        r[0], sa.Gp(float(r[2]), float(r[1])), \
                        float(r[3]), int(r[4]), int(r[5]), r[6], \
                        int(r[7]), int(r[8]), int(r[9])))
            except:
                return False
    return stations

def get_station_dictionary():
    """ This reads the Aranda station list from github (pekkaalenius).
        Note that the list may be old and does not contain all new stations.
    """
    import requests

    url = 'https://raw.githubusercontent.com/pekkaalenius/MyCruise/main/stations.txt'
    result = requests.get(url, allow_redirects=True)
    rd = result.text.split('\n')[1:-1]
    stations = []
    for r in rd:
        n, la, lo, d, c, s, t, v, a, y = r.split(';')
        stations.append(
            Aranda_station(\
                n, sa.Gp(float(lo), float(la)), float(d), \
                int(c), int(s), t, int(v), int(a), int(y)))    
    return stations

def get_station_dictionary_from_Sumppu(ahost, auser, apassword):
    """ This generates a new Aranda station list from Sumppu. 
        Connection to Sumppu has to be available.
    """
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
            stations.append(
                Aranda_station(x[0], sa.Gp(lon, lat), int(x[3]), \
                country, area, 'S1', int(x[4]), int(x[5]), int(x[6])))

    sumppu_cursor.close()
    sumppu.close()

    return stations

def make_station_list_from_Sumppu(host, user, password, file_to_save):
    """ This makes the Aranda station list from Sumppu by using
        get_station_dictionary_from_Sumppu.
        The result is stored into a local file file_to_save
    """
    stations = get_station_dictionary_from_Sumppu(host, user, password)
    if file_to_save != '':
        ofile = open(file_to_save, 'w')
        ofile.write(
            "name;lat;lon;depth;country;sea_area;type;visits;first_year;years\n")
        for s in stations:
            ofile.write(
                f"{s.name};{s.position.lat:9.6f};{s.position.lon:10.6f};"\
                f"{s.depth};{s.country};{s.area};{s.type};"\
                f"{s.visits};{s.year};{s.years}\n")
        ofile.close()

def get_BalticSea_ices_stations():
    """ This routine downloads ICES StationDictionary.zip,
        reads the Station_yyyy-mm-dd-hh-mm.tab file,
        takes from there stations that belong to Baltic Sea countries
        ['DK', 'DE', 'FI', 'EE', 'LV', 'LT', 'PL', 'RU', 'SE']
        and are inside the Baltic Sea.
        It returns a list of namedtuples ICES_station:
    """
    url = 'https://www.ices.dk/data/Documents/ENV/StationDictionary.zip'

    # The following could be used to extract the files to a local directory
    # extract_dir = "example"
    # zip_path, _ = urllib.request.urlretrieve(url)
    # with zipfile.ZipFile(zip_path, "r") as f:
    #     f.extractall(extract_dir)

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

        countries = ['DK', 'DE', 'FI', 'EE', 'LV', 'LT', 'PL', 'RU', 'SE']
        stations = []
        for d in data[1:]:
            if 'Relation' in d:
                break
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
                    stations.append(
                        ICES_station(name, country, sa.Gp(lon, lat),
                                     lat_range, lon_range))

    return stations
