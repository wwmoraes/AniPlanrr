# Here we define our query as a multi-line string
import time
import requests
import json
import os
from dotenv import load_dotenv
import re

# Set all Variables to None initially
SONARRURL = None
SONARRAPIKEY = None
RADARRURL = None
RADARRAPIKEY = None
ANILIST_USERNAME = None
MONITOR = None
RETRY = None
LOGGING = None
AUTO_FILL_MAPPING = None

#check if there is a .env file
if os.path.exists('.env'):
    load_dotenv()
    SONARRURL = os.getenv('SONARRURL')
    SONARRAPIKEY = os.getenv('SONARRAPIKEY')
    ANILIST_USERNAME = os.getenv('ANILIST_USERNAME')
    MONITOR = os.getenv('MONITOR')
    RETRY = os.getenv('RETRY')
    AUTO_FILL_MAPPING = os.getenv('AUTO_FILL_MAPPING')
    LOGGING = os.getenv('LOGGING')
    RADARRURL = os.getenv('RADARRURL')
    RADARRAPIKEY = os.getenv('RADARRAPIKEY')
else:
    if 'SONARRURL' in os.environ: SONARRURL = os.environ['SONARRURL']
    if 'SONARRAPIKEY' in os.environ: SONARRAPIKEY = os.environ['SONARRAPIKEY']
    if 'RADARRURL' in os.environ: RADARRURL = os.environ['RADARRURL']
    if 'RADARRAPIKEY' in os.environ: RADARRAPIKEY = os.environ['RADARRAPIKEY']
    if 'LOGGING' in os.environ: LOGGING=os.environ['LOGGING']
    if 'AUTO_FILL_MAPPING' in os.environ: AUTO_FILL_MAPPING=os.environ['AUTO_FILL_MAPPING']
    ANILIST_USERNAME = os.environ['ANILIST_USERNAME']
    MONITOR = os.environ['MONITOR']
    RETRY = os.environ['RETRY']

#if logging is true
if LOGGING is not None:
    print("Logging is enabled")
else:
    print("Logging is disabled")

# Create list of titles - year objects from ignorelist.txt if it exists
ignoreList = []
if os.path.exists('ignore.csv'):
    with open('ignore.csv', 'r') as f:
        for line in f:
            arr = line.strip().split(';')
            ignoreList.append(int(arr[1]))

#import custom mapping array from mapping.csv if it exists
mapping = []
if os.path.exists('mapping.csv'):
    with open('mapping.csv', 'r') as f:
        for line in f:
            arr = line.strip().split(';')
            mapping.append([arr[0],int(arr[1]),int(arr[2]),int(arr[3])])

def addToIgnoreList(title, id):
    #if id isn't already in ignorelist
    if id not in ignoreList:
        #add id to ignorelist
        print("Adding " + title + " to ignore list")
        with open('ignore.csv', 'a') as f:
        # if file is not empty, add newline
            if os.stat('ignore.csv').st_size != 0:
                f.write('\n')
            f.write(title + ';' + str(id))
    else:
        print(title + " is already in ignore list")

def cleanText(string):
    return re.sub(r'[^\w\s]', '', str(string)).lower()

def getAniList(username):
    query = query = """
                query ($username: String) {
                MediaListCollection(userName: $username, type: ANIME) {
                    lists {
                    name
                    entries {
                        media{
                        id
                        format
                        startDate {
                            year
                        }
                        endDate {
                            year
                        }
                        title {
                            romaji
                            english
                        }
                        }
                    }
                    }
                }
                }
    """

    # Define our query variables and values that will be used in the query request
    variables = {
        'username': username
    }
    url = 'https://graphql.anilist.co'
    # Make the HTTP Api request
    response = requests.post(url, json={'query': query, 'variables': variables})
    # find id of list with name "planned"
    planned_id = next((index for (index, d) in enumerate(response.json()['data']['MediaListCollection']['lists']) if d["name"] == "Planning"), None)
    entries = response.json()['data']['MediaListCollection']['lists'][planned_id];
    
    #if name is not Planned, throw error
    if entries['name'] != "Planning":
        print("Error: List name is not Planning")
        return
    # Create list of titles - year objects
    titleYearListTV = []
    titleYearListMovies = []
    for entry in entries['entries']:
        if entry['media']['format'] == "TV":
            if entry['media']['title']['english'] is not None:
                titleYearListTV.append([cleanText(entry['media']['title']['english']), entry['media']['startDate']['year'],entry['media']['id']])
            else:
                titleYearListTV.append([cleanText(entry['media']['title']['romaji']), entry['media']['startDate']['year'],entry['media']['id']])
        if entry['media']['format'] == "MOVIE":
            if entry['media']['title']['english'] is not None:
                titleYearListMovies.append([cleanText(entry['media']['title']['english']), entry['media']['startDate']['year'],entry['media']['id']])
            else:
                titleYearListMovies.append([cleanText(entry['media']['title']['romaji']), entry['media']['startDate']['year'],entry['media']['id']])
    return [titleYearListTV,titleYearListMovies]

def getSonarrSeries(SONARRURL, SONARRAPIKEY):
    response = requests.get(
    SONARRURL + "series?apikey=" + SONARRAPIKEY)
    #create list from response title and id
    seriesList = []
    #for each object in response
    for i in response.json():
        #if seriesType=anime
        if i['seriesType'] == "anime":
            seriesList.append([cleanText(i['title']), i['year'],i['tvdbId'],i['id'],i['path'],i['seasons']])
    return seriesList

def getRadarrMovies(RADARRURL, RADARRAPIKEY):
    response = requests.get(
    RADARRURL + "v3/movie?apikey=" + RADARRAPIKEY)
    #create list from response title and id
    movieList = []
    #write response to file
    with open('movies.json', 'w') as f:
        json.dump(response.json(), f)
    for i in response.json():
        movieList.append([cleanText(i['title']),i['year'],i['tmdbId']])
    return movieList

def getListDifference(list1, list2):
    #ignore third element of every object
    list1_strip = [i[:2] for i in list1]
    list2_strip = [i[:2] for i in list2]
    #Get index of every object in list1 that is not in list2
    diff=[]
    for i in list1_strip:
        if i not in list2_strip:
            diff.append(list1_strip.index(i))
    
    #return list of objects in list1 that are not in list2
    return [list1[i] for i in diff]
    

def add_show_to_sonarr(title,tvdb_id,tag,anidb_id,season=None):
    print("Adding " + title + " to Sonarr")
    params = {
        'tvdbId': tvdb_id,
        'title': title,
        'profileId': 1,
        'seriesType': 'Anime',
        'path': '/tv/Anime/' + title,
        'seasonFolder': 'true',
        'tags': [tag]
    }
    if season is not None:
        print("adding unmonitored, season will be updated later")
        params['seasons'] = [{
        'seasonNumber': season,
        'monitored': 'true'
    }]
        params['addOptions']= {'monitor': 'none', "searchForMissingEpisodes": 'true'}
    else:
        params['addOptions']= {'monitor': MONITOR, "searchForMissingEpisodes": 'true'}

    #write params to file
    with open('params.json', 'w') as outfile:
            json.dump(params, outfile)
    response = requests.post(SONARRURL + 'series?apikey=' + SONARRAPIKEY, data=str(params).encode('utf-8'))
    # If resposne is 201, print success
    if response.status_code == 201:
        print(title + " was added to Sonarr")
        entry=response.json()
        if season is not None:
            #wait for 10 seconds
            time.sleep(4)
            updateSonarrSeason(entry['id'],season,tag,anidb_id)
            
        else:
            if AUTO_FILL_MAPPING:
                writing=entry['title'] + ";" + str(anidb_id) + ";" + str(entry['tvdbId']) + ";1"
                #write title, anidb_id, tvdbID to mapping.csv
                #if text is not already one of the lines in mappings.csv
                if not any(writing in s for s in open('mapping.csv')):
                    print("Auto-Fill Turned on, Writing " + writing + " to mapping.csv")
                    #if not the first line in mapping.csv, add a new line
                    if os.stat('mapping.csv').st_size != 0:
                        with open('mapping.csv', 'a') as f:
                            f.write("\r")
                    with open('mapping.csv', 'a') as f:
                        f.write(entry['title'] + ";" + str(anidb_id) + ";" + str(entry['tvdbId']) + ";1")
    else:
        print("ERRROR: " + title + " could not be added to Sonarr")
        #write response to file
        with open('response.json', 'w') as outfile:
            json.dump(response.json(), outfile)
        #print response.errorMessage

def add_movie_to_radarr(title,tmdb_id,tag,anidb_id):
    print("Adding " + title + " to Radarr")
    #print variables

    params = {
        'tmdbId': tmdb_id,
        'title': title,
        'qualityProfileId': 1,
        'path': '/movies/Anime/' + title,
        'minimumAvailability': 'released',
        'tags': [tag],
        'monitored': True,
        'addOptions': {'monitor': 'movieOnly', "searchForMovie": True}
    }
    #write params to file
    with open('params.json', 'w') as outfile:
            json.dump(params, outfile)
    response = requests.post(RADARRURL + 'v3/movie?apikey=' + RADARRAPIKEY, json=params)
    # If resposne is 201, print success
    if response.status_code == 201:
        print(title + " was added to Radarr")
        if AUTO_FILL_MAPPING:
            #write title, anidb_id, tvdbID to mapping.csv\
            writing = title + ";" + str(anidb_id) + ";" + str(tmdb_id) + ";1"
            #if text is not already one of the lines in mappings.csv
            if not any(writing in s for s in open('mapping.csv')):
                print("Auto-Fill Turned on, Writing " + writing + " to mapping.csv")
                #if not the first line in mapping.csv, add a new line
                if os.stat('mapping.csv').st_size != 0:
                    with open('mapping.csv', 'a') as f:
                        f.write("\r")
                with open('mapping.csv', 'a') as f:
                    f.write(str(title) + ";" + str(anidb_id) + ";" + str(tmdb_id) + ";1")
    else:
        print("ERRROR: " + title + " could not be added to Radarr")
        #write response to file
        with open('response.json', 'w') as outfile:
            json.dump(response.json(), outfile)
        #print response.errorMessage
        
def get_id_from_radarr(title, year,anidb_id):
    search_string = title.replace(' ', '%20') + '%20' + str(year)
    #print(search_string)
    response = requests.get(
        RADARRURL + 'v3/movie/lookup?apikey=' + RADARRAPIKEY + '&term=' + search_string)
    #print(response.json())
    radarrTitle=cleanText(response.json()[0]['title'])
    if radarrTitle == title.lower():
        return [response.json()[0]['title'], response.json()[0]['tmdbId'],anidb_id]
    else:
        #print the two titles
        print("TMDB ID " + str(response.json()[0]['tmdbId']) + "(" + cleanText(response.json()[0]['title']) + ") seems wrong for " + title)
        #append to error file with newline if not first line

def get_id_from_sonarr(title, year,anidb_id):
    search_string = title.replace(' ', '%20') + '%20' + str(year)
    #print(search_string)
    response = requests.get(
        SONARRURL + 'series/lookup?apikey=' + SONARRAPIKEY + '&term=' + search_string)
    sonarrTitle=cleanText(response.json()[0]['title'])
    if sonarrTitle == title.lower():
        return [response.json()[0]['title'], response.json()[0]['tvdbId'],anidb_id]
    else:
        #print the two titles
        print("TVDB ID " + str(response.json()[0]['tvdbId']) + "(" + cleanText(response.json()[0]['title']) + ") seems wrong for " + title)
        #append to error file with newline if not first line
        if RETRY == "False":
            addToIgnoreList(title, anidb_id)

def updateSonarrSeason(sonarrid,season,tag,anidb_id):
    # Print variables
    print("Updating Sonarr season")
    # Get entry from sonarr by id
    entry = requests.get(SONARRURL + 'series/' + str(sonarrid) + '?apikey=' + SONARRAPIKEY).json()
    title=entry['title']
    print("Adding " + title + " season " + str(season) + " to Sonarr")
    #change "monitored" in entry['seasons'] to true where seasonNumber = season
    for i in range(len(entry['seasons'])):
        if entry['seasons'][i]['seasonNumber'] == season:
            entry['seasons'][i]['monitored'] = 'true'
    entry['tags'].append(tag)
    response = requests.put(SONARRURL + 'series/' + str(sonarrid) + '?apikey=' + SONARRAPIKEY, json=entry)
    # If resposne is 201, print success
    if response.status_code == 202:
        print(title + " season " + str(season) + " was added to Sonarr")
        if AUTO_FILL_MAPPING:
            #write title, anidb_id, tvdbID to mappings.csv
                writing=entry['title'] + ";" + str(anidb_id) + ";" + str(entry['tvdbId']) + ";1"
                #write title, anidb_id, tvdbID to mapping.csv
                #if text is not already one of the lines in mappings.csv
                if not any(writing in s for s in open('mapping.csv')):
                    print("Auto-Fill Turned on, Writing " + writing + " to mapping.csv")
                    #if not the first line in mapping.csv, add a new line
                    if os.stat('mapping.csv').st_size != 0:
                        with open('mapping.csv', 'a') as f:
                            f.write("\r")
                    with open('mapping.csv', 'a') as f:
                        f.write(entry['title'] + ";" + str(anidb_id) + ";" + str(entry['tvdbId']) + ";"+ str(season))
                
    else:
        print("ERRROR: " + title + " season " + str(season) + " could not be added to Sonarr")
        #write response to file
        with open('response.json', 'w') as outfile:
            json.dump(response.json(), outfile)
        #print response.errorMessage

def getSonarrTagId(tag_name):
    params = {
        'label': tag_name
    }
    response = requests.get(SONARRURL + 'tag?apikey=' + SONARRAPIKEY)
    #get id of tag labeled "fronAniList"
    tag_id = None
    for i in response.json():
        if i['label'] == tag_name.lower():
            tag_id=i['id']
    # if tag_id was not found, create it
    if tag_id is None:
        response = requests.post(SONARRURL + 'tag?apikey=' + SONARRAPIKEY, data=str(params).encode('utf-8'))
        if response.status_code == 201:
            tag_id = response.json()['id']
    return tag_id

def getRadarrTagId(tag_name):
    params = {
        'label': tag_name
    }
    response = requests.get(RADARRURL + 'v3/tag?apikey=' + RADARRAPIKEY)
    tag_id = None
    #get id of tag labeled "fronAniList"
    #find id in response.json() where label = tag_name
    for i in response.json():
        if i['label'] == tag_name.lower():
            tag_id=i['id']
    # if tag_id was not found, create it
    if tag_id is None:
        response = requests.post(RADARRURL + 'v3/tag?apikey=' + RADARRAPIKEY, json=params)
        if response.status_code == 201:
            tag_id = response.json()['id']
    return tag_id

def sendToRadarr(newMovies,mapping,radarrTag,radarrList):
    moviedblist = []
    for movie in newMovies:
        if LOGGING:
            print("Looking for ID for " + movie[0])
        if movie[2] in [i[1] for i in mapping]:
            map=mapping[[i[1] for i in mapping].index(movie[2])]
            print(movie[0] + " is mapped to " + str(map[2]))
            moviedblist.append([map[0],map[2],map[1]])

        else:
            tmp = get_id_from_radarr(movie[0], movie[1], movie[2])
            if tmp is not None:
                print("ID received from radarr " + movie[0])
                moviedblist.append(tmp)

    for movie in moviedblist:
        if movie[1] in [i[2] for i in radarrList]:
            print(movie[0] + " is already in Radarr, skipping")
        else:
            add_movie_to_radarr(movie[0],movie[1],radarrTag,movie[2])

def sendToSonarr(newShows,mapping,sonarrTag,sonarrlist):
    tvdblist = []
    for show in newShows:
        if LOGGING:
            print("Looking for ID for " + show[0])
        if show[2] in [i[1] for i in mapping]:
            map=mapping[[i[1] for i in mapping].index(show[2])]
            print(show[0] + " is mapped to " + str(map[2]) + " season " + str(map[3]))
            tvdblist.append([map[0],map[2],map[3],map[1]])
        else:
            tmp = get_id_from_sonarr(show[0], show[1], show[2])
            if tmp is not None:
                print("ID received from sonarr " + show[0])
                tvdblist.append(tmp)
    #if id is in sonarrlist's third object, add to ignorelist
    for show in tvdblist:
        if show[1] in [i[2] for i in sonarrlist]:
            print(show[0] + " is already in Sonarr, checking season")
            i=sonarrlist[[i[2] for i in sonarrlist].index(show[1])]
            if str(show[2]) not in [str(season["seasonNumber"]) for season in i[5] if season["monitored"]]:
                print("Adding season " + str(show[2]) + " to " + show[0])
                updateSonarrSeason(i[3],show[2],sonarrTag,show[3])
            else:
                print("Season " + str(show[2]) + " is already monitored for " + show[0] +", skipping")
            tvdblist= [x for x in tvdblist if not x==show]
    #send each item in tvdblist to add_show_to_sonarr
    for show in tvdblist:
        #if show length is 3
        if len(show) == 4:
            add_show_to_sonarr(show[0],show[1],sonarrTag,show[2],show[3])
        else:
            add_show_to_sonarr(show[0],show[1],sonarrTag,show[2])
            
if os.path.exists('.env'):
    print("Found .env file, loading variables")
else:
    print("No .env file found, loading variables from environment")
    
def main():
    if LOGGING: print("Getting AniList for " + ANILIST_USERNAME)
    [anilist,animovielist] = getAniList(str(ANILIST_USERNAME));
    #filter anilist if anilist[2] is in ignorelist
    anilist = [x for x in anilist if x[2] not in ignoreList]
    animovielist = [x for x in animovielist if x[2] not in ignoreList]
    if SONARRURL:
        if LOGGING: print("Getting Sonarr List")
        sonarrlist = getSonarrSeries(SONARRURL, SONARRAPIKEY);
        newShows = getListDifference(anilist, sonarrlist);
        sonarrTag=getSonarrTagId("fromanilist")
        if LOGGING: print("Found " + str(len(newShows)) + " new shows to add to Sonarr")
        #send each item in newShows to get_id_from_sonarr
        sendToSonarr(newShows,mapping,sonarrTag,sonarrlist)
    if RADARRURL:
        if LOGGING: print("Getting Radarr List")
        radarrlist = getRadarrMovies(RADARRURL, RADARRAPIKEY);
        newMovies = getListDifference(animovielist, radarrlist);
        if LOGGING: print("Found " + str(len(newMovies)) + " new movies to add to Radarr")
        radarrTag=getRadarrTagId("fromanilist")
        sendToRadarr(newMovies,mapping,radarrTag,radarrlist)

if __name__ == "__main__":
    main()
    print("Sync Completed")