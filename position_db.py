import os

import sqlite3
from typing import Union

import symmetry_normalisator
from position_processor import PositionProcessor
from tak import GameState


class PositionDataBase(PositionProcessor):

    def __init__(self):
        self.conn = None

    def create(self, db_file: str):
        create_tables_sql = ["""
        CREATE TABLE IF NOT EXISTS games (
            id integer PRIMARY KEY,
            playtak_id integer,
            size integer,
            white text NOT NULL,
            black text NOT NULL,
            result text NOT NULL,
            ptn text NOT NULL,
            rating_white integer DEFAULT 1000,
            rating_black integer DEFAULT 1000
        );
        """,
                             """
        CREATE TABLE IF NOT EXISTS positions (
            id integer PRIMARY KEY,
            tps text UNIQUE,
            bwins integer,
            wwins integer,
            moves text
        );
        """,
                             """
        CREATE TABLE IF NOT EXISTS game_position_xref (
            id integer PRIMARY KEY,
            game_id integer,
            position_id integer,
            FOREIGN KEY (game_id) REFERENCES games(id),
            FOREIGN KEY (position_id) REFERENCES positions(id)
        );
        """]

        try:
            try:
                os.remove(db_file)
            except FileNotFoundError:
                a = ''
            self.conn = sqlite3.connect(db_file)
            self.conn.row_factory = sqlite3.Row
            for q in create_tables_sql:
                self.conn.execute(q)
        except sqlite3.Error as e:
            print(e)

    def connect(self, db_file: str):
        try:
            self.conn = sqlite3.connect(db_file)
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(e)

    def add_position(self, game_id: int, move, result: str, tps: str, next_tps: Union[str, None], tak: GameState) -> int:
        curr = self.conn.cursor()

        # normalize for symmetries
        own_symmetry = symmetry_normalisator.get_tps_orientation(tps)
        tps = symmetry_normalisator.transform_tps(tps, own_symmetry)

        if next_tps is not None:
            next_symmetry = symmetry_normalisator.get_tps_orientation(next_tps)
            next_tps = symmetry_normalisator.transform_tps(next_tps, next_symmetry)

        select_position_row_sql = f"""
            SELECT *
            FROM positions
            WHERE tps = '{tps}'
            ;
        """

        curr.execute(select_position_row_sql)
        row = curr.fetchone()

        # if this position does not exist, create it
        if row is None:
            self.create_position_entry(tps)
            curr.execute(select_position_row_sql)
            row = curr.fetchone()

        if next_tps is not None:
            select_next_position_row_sql = f"""
                SELECT *
                FROM positions
                WHERE tps = '{next_tps}'
                ;
            """
            curr.execute(select_next_position_row_sql)
            next_pos = curr.fetchone()

            # if next position does not exist, create it
            if next_pos is None:
                self.create_position_entry(next_tps)
                curr.execute(select_next_position_row_sql)
                next_pos = curr.fetchone()

            next_pos_id = dict(next_pos)['id']

        # update win counts of either player:
        row_dict = dict(row)
        position_id = row_dict['id']

        if result[0] != '0':  # white win!
            curr.execute(f"UPDATE positions SET wwins=wwins+1 WHERE id={position_id};")
        if result[2] != '0':  # black win!
            curr.execute(f"UPDATE positions SET bwins=bwins+1 WHERE id={position_id};")

        # update the game-move crossreference table
        curr.execute(f"""
            INSERT INTO game_position_xref (game_id, position_id)
            VALUES ({game_id}, {position_id});
        """)

        # if a move is given also update the move table
        if move is not None:
            # orient move to previous symmetry
            move = symmetry_normalisator.transform_move(move, own_symmetry)
            position_moves = row_dict['moves']
            if position_moves != '':
                position_moves = row_dict['moves'].split(';')
            else:
                position_moves = []
            moves_list = list(map(lambda x: x.split(','), position_moves))

            # if move is in moves_list, update count
            move_found = False
            for moves in moves_list:
                if moves[0] == move:
                    move_found = True
                    moves[2] = str(int(moves[2]) + 1) # increment times played
                    break

            if not move_found:
                # append new move to moves_list
                moves_list.append([move, str(next_pos_id), '1'])

            # transform moves_list into db string format
            position_moves = ';'.join(list(map(lambda x: ','.join(x), moves_list)))

            curr.execute(f"""UPDATE positions SET moves='{position_moves}' WHERE id={position_id}""")

        return own_symmetry

    def dump(self):
        for line in self.conn.iterdump():
            print(line)

    def add_game(self, size: int, playtak_id: int, white_name: str, black_name: str, ptn: str, result: str, rating_white: int, rating_black: int) -> int:
        insert_game_data_sql = f"""
        INSERT INTO games (playtak_id, size, white, black, result, ptn, rating_white, rating_black)
        VALUES ('{playtak_id}', '{size}', '{white_name}', '{black_name}', '{result}', '{ptn}', {rating_white}, {rating_black});
        """
        get_game_idx_sql = f"""
        SELECT id FROM games WHERE ptn = '{ptn}';
        """
        curr = self.conn.cursor()
        curr.execute(insert_game_data_sql)
        curr.execute(get_game_idx_sql)
        res = dict(curr.fetchone())['id']
        return res

    def create_position_entry(self, tps: str):
        insert_position_data_sql = f"""
        INSERT INTO positions (tps, wwins, bwins, moves)
        VALUES ('{tps}', 0, 0, '');
        """
        curr = self.conn.cursor()
        curr.execute(insert_position_data_sql)
