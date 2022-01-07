#!/usr/bin/env python3

"""See flask.palletsprojects.com.  This used Flask 1.1.1.  Run with:

FLASK_APP=server.py flask run -h 127.0.0.1
"""

import sqlite3
from flask import Flask, request, jsonify
import sys

import symmetry_normalisator
from tak import GameState

from collections import OrderedDict

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route('/')
def hello():
    return "hello"

@app.route('/api/v1/game/<game_id>', methods=['get'])
def getgame(game_id):
    print(f'requested game with id: {game_id}')

    select_game_sql = f"SELECT * FROM games WHERE playtak_id={game_id};"

    db = sqlite3.connect('data/openings_s6_1200.db')
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(select_game_sql)
    row = dict(cur.fetchone())
    cur.close()
    db.close()

    response = jsonify(row)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response



@app.route('/api/v1/opening/<tps>', methods=['GET'])
def getposition(tps):
    tps = tps.replace('A', '/')
    print(f'requested position with tps: {tps}')
    # we don't care about move number:
    tps_l = tps.split(' ')
    tps_l[2] = 1
    tps = ' '.join(tps_l)
    symmetry = symmetry_normalisator.get_tps_orientation(tps)
    sym_tps = symmetry_normalisator.transform_tps(tps, symmetry)

    select_results_sql = f"SELECT * FROM positions WHERE tps='{sym_tps}';"

    db = sqlite3.connect('data/openings_s6_1200.db')
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(select_results_sql)
    row = dict(cur.fetchone())

    pos_id = row['id']

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

    for r in moves_list:
        if len(real_positions) >= 20:
            break

        move = r[0]
        move_id = r[1]
        if move_id in real_positions:
            continue
        select_results_sql = f"SELECT * FROM positions WHERE id='{move_id}';"

        cur.execute(select_results_sql)
        exe_res = cur.fetchone()
        if exe_res is None:
            continue
        next_row = dict(exe_res)
        real_positions.append(move_id)

        move = symmetry_normalisator.transposed_transform_move(move, symmetry)
        times_played = next_row['bwins'] + next_row['wwins']

        moves.append({"ptn": move, "white": next_row['wwins'], "black": next_row['bwins']})

    result['moves'] = moves

    # get top games
    select_games_sql = f"""
            SELECT games.id, games.playtak_id, games.white, games.black, games.rating_white, games.rating_black,
                game_position_xref.game_id, game_position_xref.position_id,
                positions.id, positions.tps, (games.rating_white+games.rating_black)/2 AS avg_rating
            FROM game_position_xref, games, positions
            WHERE game_position_xref.position_id=positions.id
                AND games.id = game_position_xref.game_id
                AND positions.tps = '{sym_tps}'
            ORDER BY AVG_rating DESC;"""
    cur.execute(select_games_sql)
    row = cur.fetchall()

    all_games = []

    for r in row:
        all_games.append(dict(r))

    all_games = all_games[0:min(4, len(all_games))]

    result['games'] = []

    for game in all_games:
        result['games'].append({
            'playtak_id': game['playtak_id'],
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
    db.close()

    response = jsonify(result)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response
