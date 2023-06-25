from contextlib import closing
import os
import sqlite3
from typing import Optional, Union

import symmetry_normalisator
from position_processor import PositionProcessor
from tak import GameState


class PositionDataBase(PositionProcessor):

    def __init__(self, db_file_name: str):
        assert db_file_name
        self.conn: Optional[sqlite3.Connection] = None
        self.max_id = 0
        self.db_file_name = db_file_name

    def __enter__(self):
        create_tables_sql = ["""
            CREATE TABLE IF NOT EXISTS games (
                id integer PRIMARY KEY,
                playtak_id integer,
                size integer,
                white text NOT NULL,
                black text NOT NULL,
                result text NOT NULL,
                komi integer,
                rating_white integer DEFAULT 1000,
                rating_black integer DEFAULT 1000,
                date integer,
                tournament integer
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS positions (
                id integer PRIMARY KEY,
                tps text UNIQUE,
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

        create_index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_xref_game_id ON game_position_xref (game_id);",
            "CREATE INDEX IF NOT EXISTS idx_xref_position_id ON game_position_xref (position_id);",
            "CREATE INDEX IF NOT EXISTS idx_position_tps ON positions (tps);",
            "CREATE INDEX IF NOT EXISTS idx_games_white ON games (white);",
            "CREATE INDEX IF NOT EXISTS idx_games_black ON games (black);",
            "CREATE INDEX IF NOT EXISTS idx_games_rating_white ON games (rating_white);",
            "CREATE INDEX IF NOT EXISTS idx_games_rating_black ON games (rating_black);",
            "CREATE INDEX IF NOT EXISTS idx_games_komi ON games (komi);",
            "CREATE INDEX IF NOT EXISTS idx_games_date ON games (date);",
            "CREATE INDEX IF NOT EXISTS idx_games_tournament ON games (tournament);",
        ]

        try:
            if os.path.exists(self.db_file_name):
                self.conn = sqlite3.connect(self.db_file_name)

                for query in create_index_sql:
                    self.conn.execute(query)

                self.conn.row_factory = sqlite3.Row
                with closing(self.conn.cursor()) as cur:
                    get_highest_id_sql = """
                        SELECT MAX(playtak_id) AS max_id, COUNT(ALL playtak_id) AS games_count FROM games;
                    """
                    cur.execute(get_highest_id_sql)
                    row = cur.fetchone()

                    if row is not None:
                        row_dict = dict(row)
                        max_id = row_dict['max_id']
                        games_count = row_dict['games_count']
                        if max_id is not None:
                            print("max game ID in loaded DB: ", max_id)
                            print("number of games in loaded DB:", games_count)
                            self.max_id = max_id
                    return self

            self.conn = sqlite3.connect(self.db_file_name)
            self.conn.row_factory = sqlite3.Row
            for query in create_tables_sql:
                self.conn.execute(query).close()

            for query in create_index_sql:
                self.conn.execute(query).close()

            return self

        except sqlite3.Error as exc:
            print(exc)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def commit(self):
        assert self.conn is not None
        self.conn.commit()

    def add_position(
        self,
        game_id: int,
        move,
        result: str,
        tps: symmetry_normalisator.TpsString,
        next_tps: Union[symmetry_normalisator.TpsString, None],
        tak: GameState
    ) -> int:
        assert self.conn is not None
        curr = self.conn.cursor()

        # normalize for symmetries
        tps_normalized, own_symmetry = symmetry_normalisator.get_tps_orientation(tps)

        select_position_row_sql = f"""
            SELECT *
            FROM positions
            WHERE tps = '{tps_normalized}'
            ;
        """

        curr.execute(select_position_row_sql)
        row = curr.fetchone()

        # if this position does not exist, create it
        if row is None:
            self.create_position_entry(tps_normalized)
            curr.execute(select_position_row_sql)
            row = curr.fetchone()

        if next_tps is not None:
            next_tps_normalized, _next_symmetry = symmetry_normalisator.get_tps_orientation(next_tps)
            select_next_position_row_sql = f"""
                SELECT *
                FROM positions
                WHERE tps = '{next_tps_normalized}'
                ;
            """
            curr.execute(select_next_position_row_sql)
            next_pos = curr.fetchone()

            # if next position does not exist, create it
            if next_pos is None:
                self.create_position_entry(next_tps_normalized)
                curr.execute(select_next_position_row_sql)
                next_pos = curr.fetchone()

            next_pos_id = dict(next_pos)['id']

        # update the game-move crossreference table
        row_dict = dict(row)
        position_id = row_dict['id']

        curr.execute(
            "INSERT INTO game_position_xref (game_id, position_id) VALUES (:game_id, :position_id);",
            { 'game_id': game_id, 'position_id': position_id }
        )

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
                    break

            if not move_found:
                # append new move to moves_list
                moves_list.append((move, str(next_pos_id)))

                # transform moves_list into db string format
                position_moves = ';'.join(map(','.join, moves_list))

                curr.execute(
                    "UPDATE positions SET moves=:position_moves WHERE id=:position_id",
                    { 'position_moves': position_moves, 'position_id': position_id }
                )

        return own_symmetry

    def dump(self):
        assert self.conn is not None
        for line in self.conn.iterdump():
            print(line)

    def add_game(
            self,
            size: int,
            playtak_id: int,
            white_name: str,
            black_name: str,
            result: str,
            komi: int,
            rating_white: int,
            rating_black: int,
            date: int, # timestamp
            tournament: bool
    ) -> int:
        assert self.conn is not None

        insert_game_data_sql = f"""
            INSERT INTO games (playtak_id, size, white, black, result, komi, rating_white, rating_black, 'date', tournament)
            VALUES ('{playtak_id}', '{size}', '{white_name}', '{black_name}', '{result}', {komi}, {rating_white}, {rating_black}, {date}, {tournament})
            RETURNING id;
        """ # use RETURNING so that we can get the inserted id after the query

        curr = self.conn.cursor()
        curr.execute(insert_game_data_sql)
        inserted_id = curr.fetchone()[0]
        return inserted_id

    def create_position_entry(self, tps: str):
        assert self.conn is not None

        insert_position_data_sql = "INSERT INTO positions (tps, moves) VALUES (:tps, '');"
        curr = self.conn.cursor()
        curr.execute(insert_position_data_sql, { 'tps': tps })
