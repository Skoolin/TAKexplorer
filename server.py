#!/usr/bin/env python3

"""See flask.palletsprojects.com.  This used Flask 1.1.1.  Run with:

FLASK_APP=server.py flask run -h 127.0.0.1
"""

import sqlite3
from flask import Flask, request
import sys

import symmetry_normalisator
from tak import GameState

from collections import OrderedDict

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route('/')
def hello():
    return "hello"

@app.route('/api/v1/opening/<tps>', methods=['GET'])
def getposition(tps):
    tps = tps.replace('A', '/')
    print(tps)
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

    return result
