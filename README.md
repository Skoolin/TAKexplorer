# TAKexplorer
A tak opening DB generator and explorer that serves via an API.

Support began for 6x6 but now 3x3 up to 8x8 should be possible. To support larger sizes `expand/collapse_tps_xn()` needs to be updated.

## Opening theory
In the Wiki I started to write up an index of popular openings: https://github.com/Skoolin/TAKexplorer/wiki
Feel free to discuss, analyse and add to them!

They can also be found [in the Tak wiki](http://tak-studies.wikidot.com/wiki:opening-catalogue).

## API
Please check `./server.py` for details

|endpoint|methods|description|
|-|-|-|
|`/api/v1/databases`|`GET`|Settings of queryable databases|
|`/api/v1/game/<int:game_id>`|`GET`|Game by its `playtak_id` with `PTN`|
|`/api/v1/players`|`GET`|Get all player names that appear in all opening databases|
|`/api/v1/opening/<int:db_id>/<path:tps>`|`GET` `POST`|Query database `db_id` with a position in `TPS` format. Returns moves, used search settings and best games from that position.|
|`/api/v1/opening/<path:tps>`|`GET` `POST`|Like the above but on the default (first) database|

When querying the `opening` endpoints with `POST` the results can be filtered with `class AnalysisSettings`. The values that were actually applied (which factors in which database was used) are included in the response. Example:
```json
{
    "black": [ "nitzel", "Alff" ],  // single names and multiple names possible. falsy values to disable (empty array, empty string, null)
    "white": "Simmon", // same here
    "komi": [ 1.5, 2.0 ],  // same here, just with floats/ints
    "min_rating": 1700,  // minimum value depends on the database
    "max_suggested_moves": 20,  // how many moves to return
    "include_bot_games": false,  // might not be possible, depending on the used database
    "min_date": "2023-01-01T00:00:00",  // includeo only games after this date - null to omit
    "max_date": "2023-03-30T00:00:00",  // include only games before this date - null to omit
    "tournament": true, // search for tournament-games only - null to omit
}
```


## Setup
### Requirements
- Python `>= 3.11`
- pip
- sqlite `>=3.35` (for [`RETURNING`](https://www.sqlite.org/lang_returning.html))
### Install dependencies
```sh
pip install pipenv
pipenv --rm # remove environment if python version was upgraded
pipenv install
```

### Run API server
This will automatically download the latest database from playtak.com and update the openings database accordingly.

```sh
pipenv run waitress-serve --listen HOST:PORT wsgi:app` # (e.g. `HOST:PORT`=`0.0.0.0:5000`)
```

Depending on your location and connection downloading the database may be very slow. If that's the case, consider getting it from another source.

Deriving the exploration database the first time may take a few minutes. Updates should be quick.

### Automatic reloading for development
```sh
pipenv run hupper -m waitress --listen HOST:PORT wsgi:app # automatically restarts server on filechange
```

### Unit tests
The coverage is not very good yet.

#### Running unit tests:
```sh
pipenv run hupper -m pytest --verbose # automatically reruns unit tests on filechange
```

### TQDM
If you encounter the warning `UserWarning: resource_tracker: There appear to be 1 leaked semaphore objects to clean up at shutdown` on restarts - we get that because we're using TQDM.
I'm not sure what can be done about it.
