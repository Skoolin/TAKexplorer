#!/usr/bin/env python3

import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import requests
from flask import Flask, jsonify
from flask_apscheduler import APScheduler

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

openings_db_configs = [
    OpeningsDbConfig(min_rating=MIN_RATING, include_bot_games=False, size=6),
]

app = Flask(__name__)
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

@app.route('/')
def hello():
    return "hello"

@app.route('/api/v1/databases')
def options():
    response = jsonify(openings_db_configs)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route('/api/v1/game/<game_id>', methods=['get'])
def getgame(game_id):
    # opening_database_config = openings_db_configs[database_id]
    # print(f'requested game from {opening_database_config.db_file_name} with id: {game_id}')

    select_game_sql = "SELECT * FROM games WHERE id=:game_id;"
    with sqlite3.connect(PLAYTAK_GAMES_DB) as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute(select_game_sql, { "game_id": game_id })

        game = dict(cur.fetchone())
        game['ptn'] = get_ptn(game)

        cur.close()

    response = jsonify(game)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route('/api/v1/opening/white=<white>,black=<black>,rating=<int:rating>,tps=<path:tps>', methods=['GET'])
def getposition_parameterized(white, black, rating, tps):
    print(f'requested position with white: {white}, black: {black}, min. rating: {rating}, tps: {tps}')

    config = openings_db_configs[0] # we only use one db config right now

    # we don't care about move number:
    sym_tps, symmetry = to_symmetric_tps(tps)

    select_results_sql = "SELECT * FROM positions WHERE tps=:sym_tps;"

    with sqlite3.connect(config.db_file_name) as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute(select_results_sql, {"sym_tps": sym_tps})

        row = cur.fetchone()
        if row is None:
            cur.close()
            result = {'white': 0, 'black': 0, 'moves': [], 'games': []}
            response = jsonify(result)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response

        row = dict(row)

        position_moves = row['moves']
        if position_moves == '':
            position_moves = []
        else:
            position_moves = position_moves.split(';')

        moves_list = list(map(lambda x: x.split(','), position_moves))

        real_positions = []
        moves = []

        total_wwins = 0
        total_bwins = 0
        total_draws = 0

        white_str = "" if white == "None" else "AND games.white = :white"
        black_str = "" if black == "None" else "AND games.black = :black"

        for r in moves_list:

            move = r[0]
            move_id = r[1]
            if move_id in real_positions:
                continue
            select_games_sql = f"""
                    SELECT games.result, count(games.result) AS count
                    FROM game_position_xref, games, positions
                    WHERE game_position_xref.position_id = positions.id
                        AND games.id = game_position_xref.game_id
                        AND positions.id = {move_id}
                        AND games.rating_white >= :rating
                        AND games.rating_black >= :rating
                        {white_str}
                        {black_str}
                    GROUP BY games.result
                        """

            cur.execute(select_games_sql, {"rating": rating, "white": white, "black": black})
            exe_res = cur.fetchall()
            if len(exe_res) < 1:
                continue

            wwins = 0
            bwins = 0
            draws = 0
            for row in exe_res:
                next_row = dict(row)
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

            real_positions.append(move_id)

        moves.sort(key=lambda x: x['white']+x['black']+x['draw'], reverse=True)

        result = {
            'white': total_wwins,
            'black': total_bwins,
            'draw': total_draws,
            'config': config,
            'moves': moves[:min(20, len(moves))],
            'games': [],
        }

        # get top games
        select_games_sql = f"""
                SELECT games.id, games.playtak_id, games.white, games.black, games.result, games.rating_white, games.rating_black,
                    game_position_xref.game_id, game_position_xref.position_id,
                    positions.id, positions.tps, (games.rating_white+games.rating_black)/2 AS avg_rating
                FROM game_position_xref, games, positions
                WHERE game_position_xref.position_id=positions.id
                    AND games.id = game_position_xref.game_id
                    AND positions.tps = :sym_tps
                    AND games.rating_white >= :rating
                    AND games.rating_black >= :rating
                    {white_str}
                    {black_str}
                ORDER BY AVG_rating DESC;"""
        cur.execute(select_games_sql, { 'sym_tps': sym_tps, "rating": rating, "black": black, "white": white })
        row = cur.fetchall()

        all_games = []

        for r in row:
            all_games.append(dict(r))

        all_games = all_games[0:min(4, len(all_games))]

        for game in all_games:
            result['games'].append({
                'playtak_id': game['playtak_id'],
                'result': game['result'],
                'white': {
                    'name': game['white'],
                    'rating': game['rating_white']
                    },
                'black': {
                    'name': game['black'],
                    'rating': game['rating_black']
                    }
                })

        cur.close()

    response = jsonify(result)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# for access of specific DB
# not implemented because we use only one DB currently
@app.route('/api/v1/opening/<int:db_id>/<path:tps>', methods=['GET'])
def getposition_default_with_db_id(db_id, tps):
    return getposition_default(tps)

@app.route('/api/v1/opening/<path:tps>', methods=['GET'])
def getposition_default(tps):
    return getposition_parameterized(white="None", black="None", rating=1200, tps=tps)

try:
    print("creating data directory...")
    os.mkdir(DATA_DIR)
except FileExistsError as e:
    print("data directory already exists")

# import new games if necessary (or do the initial import) asynchronously
scheduler.add_job("initial_import", import_playtak_games)
