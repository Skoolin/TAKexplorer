# TAKexplorer
A tak opening DB generator and explorer that serves via an API.

Currently only supports games with board size of 6.


## Opening theory
In the Wiki I started to write up an index of popular openings: https://github.com/Skoolin/TAKexplorer/wiki
Feel free to discuss, analyse and add to them!

They can also be found [in the Tak wiki](http://tak-studies.wikidot.com/wiki:opening-catalogue).

## API
Please check `./server.py` for details

## Setup
### Requirements
- Python `>= 3.9`
- pip
- sqlite `>=3.35` (for [`RETURNING`](https://www.sqlite.org/lang_returning.html))
### Install dependencies
```sh
pip install pipenv
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
pipenv shell # enter environment
pip install hupper
hupper -m waitress --listen HOST:PORT wsgi:app # automatically restarts server on filechange
```
