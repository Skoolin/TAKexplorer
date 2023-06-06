#!/usr/bin/env python3

import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Optional
from contextlib import closing

import requests
from flask import Flask, json, jsonify, request
from flask_apscheduler import APScheduler
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, NotFound

import ptn_parser
import symmetry_normalisator
from db_extractor import get_games_from_db, get_ptn
from position_db import PositionDataBase
from symmetry_normalisator import TpsSymmetry

DATA_DIR = 'data'
PLAYTAK_GAMES_DB = os.path.join(DATA_DIR, 'games_anon.db')
MAX_GAME_EXAMPLES = 4
MAX_SUGGESTED_MOVES = 20
MAX_PLIES = 30
NUM_PLIES = 12
NUM_GAMES = 10_000
MIN_RATING = 1200

@dataclass
class OpeningsDbConfig:
    min_rating: int
    include_bot_games: bool
    size: Literal[6] = 6

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

@dataclass
class AnalysisSettings:
    white: Optional[str] = None
    black: Optional[str] = None
    min_rating: int = 0
    max_suggested_moves: int = MAX_SUGGESTED_MOVES
    include_bot_games: bool = False
    komi: Optional[float] = None

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
    OpeningsDbConfig(min_rating=MIN_RATING, include_bot_games=False, size=6),
    OpeningsDbConfig(min_rating=1700, include_bot_games=True, size=6),
]

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['JSON_SORT_KEYS'] = False
app.config['SCHEDULER_API_ENABLED'] = True

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def to_symmetric_tps(tps: str) -> tuple[str, TpsSymmetry]:
    tps_l = tps.split(' ')
    tps_l[2] = '1'
    tps = ' '.join(tps_l)
    symmetry = symmetry_normalisator.get_tps_orientation(tps)
    sym_tps = symmetry_normalisator.transform_tps(tps, symmetry)
    return sym_tps, symmetry


def download_playtak_db(url: str, destination: str):
    if (
        not os.path.exists(destination)
        or (time.time() - os.stat(destination).st_mtime) > timedelta(hours=10).seconds
    ):
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


@app.errorhandler(HTTPException)
def handle_exception(exc):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = exc.get_response()

    # replace the body with JSON
    response.data = json.dumps({
        "code": exc.code,
        "name": exc.name,
        "description": exc.description,
    })
    response.content_type = "application/json"
    return response

@app.route('/', methods=['GET'])
def hello():
    return "hello"

@app.route('/api/v1/databases', methods=['GET'])
def options():
    return jsonify(openings_db_configs)

@app.route('/api/v1/game/<game_id>', methods=['get'])
def get_game(game_id):
    # opening_database_config = openings_db_configs[database_id]
    # print(f'requested game from {opening_database_config.db_file_name} with id: {game_id}')

    select_game_sql = "SELECT * FROM games WHERE id=:game_id;"
    with sqlite3.connect(PLAYTAK_GAMES_DB) as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute(select_game_sql, { "game_id": game_id })

        game = dict(cur.fetchone())
        game['ptn'] = get_ptn(game)
        komi = float(game['komi'] or 0) / 2 # correct komi
        game['komi'] = komi

        cur.close()

    return jsonify(game)

def get_position_analysis(
    config: OpeningsDbConfig,
    settings: AnalysisSettings,
    tps: str,
) -> PositionAnalysis:
    print(f'requested position with white: {settings.white}, black: {settings.black}, min. min_rating: {settings.min_rating}, tps: {tps}')

    settings.min_rating = max(config.min_rating, settings.min_rating)
    settings.include_bot_games = config.include_bot_games and settings.include_bot_games
    print("Searching with", config, settings)

    # we don't care about move number:
    sym_tps, symmetry = to_symmetric_tps(tps)

    select_results_sql = "SELECT * FROM positions WHERE tps=:sym_tps;"

    with sqlite3.connect(config.db_file_name) as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute(select_results_sql, {"sym_tps": sym_tps})

        rows = cur.fetchone()
        if rows is None:
            cur.close()
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

        white_str = "AND games.white = :white" if settings.white else ""
        black_str = "AND games.black = :black" if settings.black else ""
        komi_str  = "AND games.komi = :komi" if settings.komi is not None else ""

        # db stores komi as an integer (double of what it actually is)
        komi: Optional[int] = round(settings.komi * 2, None) if settings.komi is not None else None

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
                        {white_str}
                        {black_str}
                        {komi_str}
                    GROUP BY games.result
                        """
            cur.execute(select_games_sql, {
                "min_rating": settings.min_rating,
                "white": settings.white,
                "black": settings.black,
                "komi": komi,
            })
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

            move = symmetry_normalisator.transposed_transform_move(move, symmetry)

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
                SELECT games.id, games.playtak_id, games.white, games.black, games.result, games.komi, games.rating_white, games.rating_black, games.date,
                    game_position_xref.game_id, game_position_xref.position_id,
                    positions.id, positions.tps, (games.rating_white+games.rating_black)/2 AS avg_rating
                FROM game_position_xref, games, positions
                WHERE game_position_xref.position_id=positions.id
                    AND games.id = game_position_xref.game_id
                    AND positions.tps = :sym_tps
                    AND games.rating_white >= :min_rating
                    AND games.rating_black >= :min_rating
                    {white_str}
                    {black_str}
                    {komi_str}
                ORDER BY AVG_rating DESC
                LIMIT {MAX_GAME_EXAMPLES};"""
        cur.execute(select_games_sql, {
            'sym_tps': sym_tps,
            "min_rating": settings.min_rating,
            "black": settings.black,
            "white": settings.white,
            "komi": komi,
        })
        top_games = cur.fetchall()

        for game in map(dict, top_games):
            position_analysis.games.append(GameInfo(
                playtak_id = game['playtak_id'],
                result = game['result'],
                white = PlayerInfo(name=game['white'], rating=game['rating_white']),
                black = PlayerInfo(name=game['black'], rating=game['rating_black']),
                komi = float(game['komi'] or 0) / 2,
                date = datetime.utcfromtimestamp(game['date']/1000).isoformat(),
            ))

        cur.close()

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

    analysis = get_position_analysis(openings_db_configs[db_id], settings, tps)
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
