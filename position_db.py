import os

import sqlite3

import symmetry_normalisator


class PositionDataBase:

    def __init__(self):
        self.conn = None

    def create(self, db_file: str):
        create_tables_sql = ["""
        CREATE TABLE IF NOT EXISTS games (
            id integer PRIMARY KEY,
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
            wwins integer
        );
        """,
                             """
        CREATE TABLE IF NOT EXISTS moves_map (
            id integer PRIMARY KEY,
            times_played integer,
            position_id integer NOT NULL,
            ptn text NOT NULL,
            FOREIGN KEY (position_id) REFERENCES positions(id)
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

    def add_position(self, game_id: int, move, result: str, tps: str) -> int:

        # normalize for symmetries
        own_symmetry = symmetry_normalisator.get_tps_orientation(tps)
        tps = symmetry_normalisator.transform_tps(tps, own_symmetry)

        select_position_row_sql = f"""
            SELECT * 
            FROM positions 
            WHERE tps = '{tps}'
            ;
        """

        curr = self.conn.cursor()
        curr.execute(select_position_row_sql)
        row = curr.fetchone()

        # if this position does not exist, create it
        if row is None:
            self.create_position_entry(tps)
            curr.execute(select_position_row_sql)
            row = curr.fetchone()

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
            select_move_row_sql = f"""
                SELECT *
                FROM moves_map
                WHERE position_id = {position_id}
                    AND ptn = '{move}'
                ;
            """
            curr.execute(select_move_row_sql)
            row = curr.fetchone()

            # if this move does not exist, create it
            if row is None:
                self.create_move_entry(position_id, move)
                curr.execute(select_move_row_sql)
                row = curr.fetchone()

            # update move count
            row_dict = dict(row)
            move_id = row_dict['id']
            curr.execute(f"""UPDATE moves_map SET times_played=times_played+1 WHERE id={move_id}""")

            return own_symmetry

    def dump(self):
        for line in self.conn.iterdump():
            print(line)

    def add_game(self, size: int, white_name: str, black_name: str, ptn: str, result: str, rating_white: int, rating_black: int) -> int:
        insert_game_data_sql = f"""
        INSERT INTO games (size, white, black, result, ptn, rating_white, rating_black)
        VALUES ('{size}', '{white_name}', '{black_name}', '{result}', '{ptn}', {rating_white}, {rating_black});
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
        INSERT INTO positions (tps, wwins, bwins)
        VALUES ('{tps}', 0, 0);
        """
        curr = self.conn.cursor()
        curr.execute(insert_position_data_sql)

    def create_move_entry(self, pos_id: int, move: str):
        insert_move_data_sql = f"""
        INSERT INTO moves_map (position_id, times_played, ptn)
        VALUES ({pos_id}, 0, '{move}');
        """
        curr = self.conn.cursor()
        curr.execute(insert_move_data_sql)
