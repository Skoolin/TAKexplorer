#!/usr/bin/env python3

import os
from datetime import timedelta
import time
import sqlite3

import requests
from flask import Flask, jsonify
from flask_apscheduler import APScheduler

import symmetry_normalisator
from symmetry_normalisator import TpsSymmetry
import db_extractor
import ptn_parser
from position_db import PositionDataBase

ANALYZED_OPENINGS_DB_FILE = 'data/openings_s6_1200.db'
MAX_GAME_EXAMPLES = 4
MAX_SUGGESTED_MOVES = 20

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


# import dayly update of playtak database
@scheduler.task('cron', id='import_playtak_games', hour='5', misfire_grace_time=900)
def import_playtak_games():

    playtak_games_db = 'data/games_anon.db'

    ptn_file = 'data/games.ptn'

    url = 'https://www.playtak.com/games_anon.db'
    if (
        not os.path.exists(playtak_games_db)
        or (time.time() - os.stat(playtak_games_db).st_mtime) > timedelta(hours=10).seconds
    ):
        print("Fetching latest playtak games DB...")
        try:
            with requests.get(url) as request, open(playtak_games_db,'wb') as output_file:
                output_file.write(request.content)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print("Cannot reach playtak server.")
            if not os.path.exists(playtak_games_db):
                print("no saved games database. exiting.")
                raise Exception("Failed to download playtak games database") from exc # pylint: disable=broad-exception-raised
            print("Using potentially outdated save of games database.")

    with PositionDataBase(ANALYZED_OPENINGS_DB_FILE) as db:
        print("extracting games...")
        db_extractor.main(
            db_file=playtak_games_db,
            target_file=ptn_file,
            num_plies=12,
            num_games=10000,
            min_rating=1200,
            player_black=None,
            player_white=None,
            start_id=db.max_id
        )

        print("building opening table...")
        ptn_parser.main(ptn_file, db)

        db.conn.commit()

        print("done! now serving requests")

@app.route('/')
def hello():
    return "hello"

@app.route('/api/v1/game/<game_id>', methods=['get'])
def getgame(game_id):
    print(f'requested game with id: {game_id}')

    select_game_sql = "SELECT * FROM games WHERE playtak_id=:game_id;"

    with sqlite3.connect(ANALYZED_OPENINGS_DB_FILE) as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute(select_game_sql, { "game_id": game_id })

        row = dict(cur.fetchone())
        cur.close()

    response = jsonify(row)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route('/api/v1/opening/<path:tps>', methods=['GET'])
def get_position(tps):
    print(f'requested position with tps: {tps}')
    # we don't care about move number:
    sym_tps, symmetry = to_symmetric_tps(tps)

    select_results_sql = "SELECT * FROM positions WHERE tps=:sym_tps;"

    with sqlite3.connect(ANALYZED_OPENINGS_DB_FILE) as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor() # with closing(db.cursor()) as cur:
        cur.execute(select_results_sql, { 'sym_tps': sym_tps })

        row = cur.fetchone()
        if row is None:
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
        moves_list.sort(key=lambda x: int(x[2]), reverse=True)

        result = {}
        result['white'] = row['wwins']
        result['black'] = row['bwins']

        real_positions = []
        moves = []

        for [move, move_id, _game_count] in moves_list:
            if len(real_positions) >= MAX_SUGGESTED_MOVES:
                break

            if move_id in real_positions:
                continue
            select_results_sql = "SELECT * FROM positions WHERE id=:move_id;"

            cur.execute(select_results_sql, { 'move_id': move_id })
            exe_res = cur.fetchone()
            if exe_res is None:
                continue
            next_row = dict(exe_res)
            real_positions.append(move_id)

            move = symmetry_normalisator.transposed_transform_move(move, symmetry)

            moves.append({"ptn": move, "white": next_row['wwins'], "black": next_row['bwins']})

        result['moves'] = moves

        # get top games
        select_games_sql = """
                SELECT games.id, games.playtak_id, games.white, games.black, games.result, games.rating_white, games.rating_black,
                    game_position_xref.game_id, game_position_xref.position_id,
                    positions.id, positions.tps, (games.rating_white+games.rating_black)/2 AS avg_rating
                FROM game_position_xref, games, positions
                WHERE game_position_xref.position_id=positions.id
                    AND games.id = game_position_xref.game_id
                    AND positions.tps = :sym_tps
                ORDER BY AVG_rating DESC
                LIMIT :limit;"""
        cur.execute(select_games_sql, { 'sym_tps': sym_tps, 'limit': MAX_GAME_EXAMPLES })
        game_examples = list(map(dict, cur.fetchall()))

        result['games'] = []

        for game in game_examples:
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


try:
    print("creating data directory...")
    os.mkdir("data")
except FileExistsError as e:
    print("data directory already exists")

# import games first time
import_playtak_games()
