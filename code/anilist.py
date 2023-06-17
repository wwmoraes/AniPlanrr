import requests
from util import pr, dumpVar, LOGGING
from enum import StrEnum

class MediaListStatus(StrEnum):
  WATCHING = "CURRENT"
  PLANNING = "PLANNING"
  COMPLETED = "COMPLETED"
  DROPPED = "DROPPED"
  PAUSED = "PAUSED"
  REPEATING = "REPEATING"


def convertToDict(entry):
    return {
        'titles': entry['media']['title'],
        'title': list(entry['media']['title'].values())[0],
        'year': entry['media']['startDate']['year'],
        'anilistId': entry['media']['id']
    }

def mediaListStatusFrom(status) -> MediaListStatus:
    return MediaListStatus.__dict__.get(
        str(status).upper(),
        MediaListStatus.PLANNING,
    )

def getAniList(username, status):
    query = query = """
                query ($username: String, $status: MediaListStatus) {
                MediaListCollection(userName: $username, type: ANIME, status: $status) {
                    lists {
                    name
                    entries {
                        media{
                        id
                        idMal
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
        'username': username,
        'status': mediaListStatusFrom(status).value
    }
    url = 'https://graphql.anilist.co'
    # Make the HTTP Api request
    response = requests.post(
        url, json={'query': query, 'variables': variables})
    # if response is not 200, throw error
    if response.status_code != 200:
        pr("Error: AniList response is not 200")
        return
    # filter down to entries of returned list
    entries = response.json(
    )['data']['MediaListCollection']['lists'][0]

    # Create list of titles - year objects
    titleYearListTV = []
    titleYearListMovies = []
    for entry in entries['entries']:
        if entry['media']['format'] == "TV":
            titleYearListTV.append(convertToDict(entry))
        if entry['media']['format'] == "MOVIE":
            titleYearListMovies.append(convertToDict(entry))
    if LOGGING == "True":
        dumpVar('aniListTV', titleYearListTV)
        dumpVar('aniListMovies', titleYearListMovies)
    return [titleYearListTV, titleYearListMovies]
