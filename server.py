#!/usr/bin/env python3

import os
import sqlite3
import time
import traceback
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Union

import requests
from flask import Flask, json, jsonify, request
from flask_apscheduler import APScheduler
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, InternalServerError, NotFound

import ptn_parser
import symmetry_normalisator
from db_extractor import get_games_from_db, get_ptn
from position_db import PositionDataBase
from base_types import BoardSize, NormalizedTpsString, TpsString, TpsSymmetry

DATA_DIR = 'data'
PLAYTAK_GAMES_DB = os.path.join(DATA_DIR, 'games_anon.db')
MAX_GAME_EXAMPLES = 4
MAX_SUGGESTED_MOVES = 20
MAX_PLIES = 30
NUM_PLIES = 12
NUM_GAMES = 20_000
MIN_RATING = 1200

@dataclass
class OpeningsDbConfig:
    min_rating: int
    include_bot_games: bool
    size: BoardSize = BoardSize(6)

    @property
    def db_file_name(self):
        bots_text = "bots" if self.include_bot_games else "nobots"
        file_name = f"openings_s{self.size}_{self.min_rating}_{bots_text}.db"
        return os.path.join(DATA_DIR, file_name)

@dataclass
class PlayerInfo:
    name: str
    rating: int

@dataclass
class GameInfo:
    playtak_id: str
    result: str
    white: PlayerInfo
    black: PlayerInfo
    date: str # isoformat utc
    komi: float
    tournament: bool

@dataclass
class AnalysisSettings:
    white: Optional[Union[str, list[str]]] = None
    black: Optional[Union[str, list[str]]] = None
    min_rating: int = 0
    max_suggested_moves: int = MAX_SUGGESTED_MOVES
    include_bot_games: bool = False
    komi: Optional[Union[float, list[float]]] = None
    min_date: Optional[str] = None  # ISO-format
    max_date: Optional[str] = None  # ISO-format
    tournament: Optional[bool] = None


@dataclass
class PositionAnalysis:
    config: OpeningsDbConfig # used DB configuration
    settings: AnalysisSettings
    white: int = 0# total white wins,
    black: int = 0# total black wins
    draw: int = 0# total draws,
    moves: list[PlayerInfo] = field(default_factory=list) # explored moves,
    games: list[GameInfo] = field(default_factory=list) # top games


openings_db_configs = [
    OpeningsDbConfig(min_rating=MIN_RATING, include_bot_games=False, size=BoardSize(6)),
    OpeningsDbConfig(min_rating=1700, include_bot_games=True, size=BoardSize(6)),
    OpeningsDbConfig(min_rating=1200, include_bot_games=True, size=BoardSize(7)),
]

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['JSON_SORT_KEYS'] = False
app.config['SCHEDULER_API_ENABLED'] = True

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def datetime_from(isoformat: str):
    return datetime.fromisoformat(isoformat)

def playtak_timestamp_from(isoformat: str) -> int:
    return round(datetime_from(isoformat).timestamp() * 1000, None)

def isoformat_from(playtak_timestamp: int) -> str:
    return datetime.utcfromtimestamp(playtak_timestamp / 1000).isoformat()

def to_symmetric_tps(tps: TpsString) -> tuple[NormalizedTpsString, TpsSymmetry]:
    tps_l = tps.split(' ')
    tps_l[2] = '1'
    tps = ' '.join(tps_l) # type: ignore
    return symmetry_normalisator.get_tps_orientation(tps)


def download_playtak_db(url: str, destination: str):
    playtak_db_min_age = timedelta(hours=10)
    if (
        os.path.exists(destination)
        and (time.time() - os.stat(destination).st_mtime) <= playtak_db_min_age.seconds
    ):
        print(f"Playtak database already exists and is less than {playtak_db_min_age} old")
        return

    print("Fetching latest playtak games DB...")
    try:
        with requests.get(url, timeout=None) as requ, open(destination,'wb') as output_file:
            output_file.write(requ.content)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print("Cannot reach playtak server")
        if not os.path.exists(destination):
            print("No saved games database. exiting.")
            raise Exception("Failed to download playtak games database") from exc # pylint: disable=broad-exception-raised
        print("Using potentially outdated save of games database.")

def update_openings_db(playtak_db: str, config: OpeningsDbConfig):
    print(f"extracting games from {playtak_db} to {config.db_file_name}")
    with PositionDataBase(config.db_file_name) as pos_db:
        games = get_games_from_db(
            db_file=PLAYTAK_GAMES_DB,
            board_size=config.size,
            num_plies=NUM_PLIES,
            num_games=NUM_GAMES,
            min_rating=config.min_rating,
            player_white=None,
            player_black=None,
            start_id=pos_db.max_id,
            exclude_bots=not config.include_bot_games,
        )

        print("building opening table...")
        ptn_parser.add_games_to_db(games, pos_db, max_plies=MAX_PLIES)
        pos_db.commit()

        print("...done!")

# import dayly update of playtak database
@scheduler.task('cron', id='import_playtak_games', hour='17', minute="10", misfire_grace_time=900)
def import_playtak_games():
    download_playtak_db('https://www.playtak.com/games_anon.db', PLAYTAK_GAMES_DB)

    for config in openings_db_configs:
        update_openings_db(PLAYTAK_GAMES_DB, config)
    print(f"updated {len(openings_db_configs)} opening dbs")


@app.errorhandler(HTTPException)  # type: ignore
def handle_httpexception(exc: HTTPException):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = exc.get_response()

    # replace the body with JSON
    response.data = json.dumps({  # type: ignore
        "code": exc.code,
        "name": exc.name,
        "description": exc.description,
    })

    response.content_type = "application/json"
    return response


@app.errorhandler(Exception)
def handle_exception(exc: Exception):
    """Transform any exception thrown during a request to a 500 with an explanation"""
    print(traceback.format_exc())
    err = InternalServerError(original_exception=exc, description=str(exc))
    return handle_httpexception(err)


@app.route('/', methods=['GET'])
def hello():
    return "hello"

@app.route('/api/v1/databases', methods=['GET'])
def options():
    return jsonify(openings_db_configs)

@app.route('/api/v1/game/<game_id>', methods=['get'])
def get_game(game_id):
    select_game_sql = "SELECT * FROM games WHERE id=:game_id;"
    with closing(sqlite3.connect(PLAYTAK_GAMES_DB)) as db:
        db.row_factory = sqlite3.Row
        with closing(db.cursor()) as cur:
            cur.execute(select_game_sql, { "game_id": game_id })

            game = dict(cur.fetchone())
            game['ptn'] = get_ptn(game)
            komi = float(game['komi'] or 0) / 2 # correct komi
            game['komi'] = komi

    return jsonify(game)

def get_position_analysis(
    config: OpeningsDbConfig,
    settings: AnalysisSettings,
    tps: TpsString,
) -> PositionAnalysis:
    print(f'requested position with white: {settings.white}, black: {settings.black}, min. min_rating: {settings.min_rating}, tps: {tps}')

    settings.min_rating = max(config.min_rating, settings.min_rating) if settings.min_rating else config.min_rating
    settings.include_bot_games = config.include_bot_games and settings.include_bot_games
    settings.min_date = datetime_from(settings.min_date).isoformat() if settings.min_date else None
    settings.max_date = datetime_from(settings.max_date).isoformat() if settings.max_date else None
    if settings.tournament in [True, False, None]:
        settings.tournament = settings.tournament
    else:
        raise ValueError(f"tournament field is '{settings.tournament}' of type '{type(settings.tournament)}' but should be bool or null")

    print("Searching with", config, settings)

    # we don't care about move number:
    sym_tps, symmetry = to_symmetric_tps(tps)

    select_results_sql = "SELECT * FROM positions WHERE tps=:sym_tps;"

    with closing(sqlite3.connect(config.db_file_name)) as db:
        db.row_factory = sqlite3.Row
        with closing(db.cursor()) as cur:
            cur.execute(select_results_sql, {"sym_tps": sym_tps})

            rows = cur.fetchone()
            if rows is None:
                return PositionAnalysis(config=config, settings=settings)

            rows = dict(rows)

            position_moves = rows['moves']
            if position_moves == '':
                position_moves = []
            else:
                position_moves = position_moves.split(';')

            moves_list: list[tuple[str, str]] = list(map(lambda x: x.split(','), position_moves))

            explored_position_ids: set[str] = set()
            moves = []

            total_wwins = 0
            total_bwins = 0
            total_draws = 0
            def build_condition(
                field_name: str,
                values: Optional[Union[list[str], list[int], list[float], int, float, str, bool]]
            ):
                """
                Returns a partial SQL condition checking that `field_name` equals or is in `values`
                """
                if values == [] or values is None or values == "":  # intentionally allow e.g. `0``
                    return "", {}

                if isinstance(values, list) and len(values) == 1:
                    values = values[0]

                if isinstance(values, list):
                    kv_map = {f'{field_name}{i}':v for i, v in enumerate(values)}
                    field_names = [f":{k}" for k in kv_map.keys()]
                    return f"AND games.{field_name} IN ({','.join(field_names)})", kv_map

                return f"AND games.{field_name} = :{field_name}", { field_name: values }

            white_str, white_vals = build_condition("white", settings.white)
            black_str, black_vals = build_condition("black", settings.black)

            # db stores komi as an integer (double of what it actually is)
            komi_raw: Optional[list[float]] = settings.komi if isinstance(settings.komi, list) \
                else [settings.komi] if settings.komi is not None \
                else None
            komi: Optional[list[int]] = [round(k * 2, None) for k in komi_raw] if komi_raw else None
            komi_str, komi_vals  = build_condition("komi", komi)
            # update `settings` because it's part of the response and thus
            # the one making the response knows, what was actually applied
            settings.komi = [k / 2 for k in komi] if komi else None

            min_date_str = "AND games.date >= :min_date" if settings.min_date else ""
            max_date_str = "AND games.date <= :max_date" if settings.max_date else ""
            tournament_str, tournament_vals = build_condition("tournament", settings.tournament)

            default_query_vars = {
                "min_rating": settings.min_rating,
                "min_date": playtak_timestamp_from(settings.min_date) if settings.min_date else None,
                "max_date": playtak_timestamp_from(settings.max_date) if settings.max_date else None,
                **white_vals,
                **black_vals,
                **komi_vals,
                **tournament_vals,
            }

            for (move, position_id) in moves_list:
                if position_id in explored_position_ids:
                    continue
                explored_position_ids.add(position_id)

                select_games_sql = f"""
                    SELECT games.result, count(games.result) AS count
                    FROM game_position_xref, games, positions
                    WHERE game_position_xref.position_id = positions.id
                        AND games.id = game_position_xref.game_id
                        AND positions.id = {position_id}
                        AND games.rating_white >= :min_rating
                        AND games.rating_black >= :min_rating
                        {tournament_str}
                        {min_date_str}
                        {max_date_str}
                        {white_str}
                        {black_str}
                        {komi_str}
                    GROUP BY games.result
                """
                cur.execute(select_games_sql, default_query_vars)
                exe_res = list(cur.fetchall())
                if len(exe_res) == 0:
                    continue

                wwins = 0
                bwins = 0
                draws = 0
                for next_row in map(dict, exe_res):
                    if next_row['result'].startswith('0-'):
                        bwins += next_row['count']
                    elif next_row['result'].endswith('-0'):
                        wwins += next_row['count']
                    elif next_row['result'] == '1/2-1/2':
                        draws += next_row['count']

                total_wwins += wwins
                total_bwins += bwins
                total_draws += draws

                move = symmetry_normalisator.transposed_transform_move(
                    move,
                    symmetry,
                    config.size,
                )

                moves.append({"ptn": move, "white": wwins, "black": bwins, "draw": draws})

            moves.sort(key=lambda x: x['white']+x['black']+x['draw'], reverse=True)

            position_analysis = PositionAnalysis(
                config = config,
                settings = settings,
                white = total_wwins,
                black = total_bwins,
                draw = total_draws,
                moves = moves[:settings.max_suggested_moves],
                games = [],
            )

            # get top games
            select_games_sql = f"""
                SELECT games.id, games.playtak_id, games.white, games.black, games.result, games.komi, games.rating_white, games.rating_black, games.date, games.tournament,
                    game_position_xref.game_id, game_position_xref.position_id,
                    positions.id, positions.tps, (games.rating_white+games.rating_black)/2 AS avg_rating
                FROM game_position_xref, games, positions
                WHERE game_position_xref.position_id=positions.id
                    AND games.id = game_position_xref.game_id
                    AND positions.tps = :sym_tps
                    AND games.rating_white >= :min_rating
                    AND games.rating_black >= :min_rating
                    {tournament_str}
                    {min_date_str}
                    {max_date_str}
                    {white_str}
                    {black_str}
                    {komi_str}
                ORDER BY AVG_rating DESC
                LIMIT {MAX_GAME_EXAMPLES};
            """
            cur.execute(select_games_sql, {
                'sym_tps': sym_tps,
                **default_query_vars,
            })
            top_games = cur.fetchall()


            # todo: normalize (rotate) game so that users aren't interrupted in their
            # exploration with suddenly rotated games
            for game in map(dict, top_games):
                position_analysis.games.append(GameInfo(
                    playtak_id = game['playtak_id'],
                    result = game['result'],
                    white = PlayerInfo(name=game['white'], rating=game['rating_white']),
                    black = PlayerInfo(name=game['black'], rating=game['rating_black']),
                    komi = float(game['komi'] or 0) / 2,
                    date = isoformat_from(game['date']),
                    tournament=bool(game['tournament']),
                ))

            return position_analysis

# for access of specific DB
# not implemented because we use only one DB currently
@app.route('/api/v1/opening/<int:db_id>/<path:tps>', methods=['GET', 'POST'])
def get_position_with_db_id(db_id: int, tps: str):

    if request.is_json and (json_data:=request.json):
        print("json", json_data)
        settings = AnalysisSettings(**json_data)
    else:
        print("no json")
        settings = AnalysisSettings()
    print("SETTINGS", settings)

    if db_id >= len(openings_db_configs):
        raise NotFound("database index out of range, query api/v1/databases for options")
    tps_string: TpsString = tps # type: ignore
    analysis = get_position_analysis(openings_db_configs[db_id], settings, tps_string)
    return jsonify(analysis)

@app.route('/api/v1/opening/<path:tps>', methods=['POST', 'GET'])
def get_position(tps: str):
    return  get_position_with_db_id(0, tps)


@app.route('/api/v1/players', methods=['GET'])
def get_player_names():
    """
    Returns the list of `white` and `black` player names whose games appear in
    any of the `openings_db_configs`
    """
    white_names = set()
    black_names = set()
    for config in openings_db_configs:
        with closing(sqlite3.connect(config.db_file_name)) as db:
            db.row_factory = sqlite3.Row
            with closing(db.cursor()) as cur:

                cur.execute("SELECT DISTINCT white AS name from games")
                white_names.update(map(lambda x: x['name'], cur.fetchall()))

                cur.execute("SELECT DISTINCT black AS name from games")
                black_names.update(map(lambda x: x['name'], cur.fetchall()))

    return jsonify({
        'white': sorted(white_names),
        'black': sorted(black_names),
    })

print("sqlite3 version", sqlite3.sqlite_version)

try:
    print("creating data directory...")
    os.mkdir(DATA_DIR)
except FileExistsError as e:
    print("data directory already exists")

# import new games if necessary (or do the initial import) asynchronously
scheduler.add_job("initial_import", import_playtak_games)
