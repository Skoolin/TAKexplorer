import sqlite3

import os
import tkinter
import tkinter.font as font
import tkinter.scrolledtext
from PIL import Image, ImageTk

import symmetry_normalisator
from tak import GameState


class TAKexplorer:

    def __init__(self, db_file):
        self.db = sqlite3.connect(db_file)
        self.db.row_factory = sqlite3.Row

        self.top = tkinter.Tk()
        self.top.title("TAK Explorer")

        os.system(f'TPStoPNG "x6/x6/x6/x6/x6/x6 2 2" name=tak opening=no-swap')
        img_load = Image.open("tak.png")
        render = ImageTk.PhotoImage(img_load)

        self.move_option_frame = tkinter.LabelFrame(self.top, text="all moves:", width=400, height=900)
        self.move_option_frame.pack(side="right", fill="both", expand="yes")

        self.board_image = tkinter.Label(self.top, image=render)
        self.board_image.image = render
        self.board_image.place(x=0, y=0)
        self.board_image.pack(side="top")

        self.tps = tkinter.StringVar()
        self.tps_label = tkinter.Label(self.top, textvariable=self.tps)
        self.tps_label.pack(side="left")

        self.win_rate = tkinter.StringVar()
        self.win_rate_label = tkinter.Label(self.top, textvariable=self.win_rate)
        self.win_rate_label.pack(side="left")

        self.back = tkinter.Button(self.top, text='<', command=lambda: self.take_move())
        self.back.pack(side="right")
        self.reset = tkinter.Button(self.top, text="reset", command=lambda: (self.game.reset(), self.collect()))
        self.reset.pack()
        self.game_list = tkinter.Button(self.top, text="all games", command=lambda: self.print_all_games())
        self.game_list.pack()

        self.game = GameState(6)
        self.game_stack = []
        self.moves = self.collect()

    def print_all_games(self):
        tps = self.game.get_tps()
        tps = symmetry_normalisator.transform_tps(tps, symmetry_normalisator.get_tps_orientation(tps))

        games_sql = f"""
        SELECT games.id, games.ptn, games.rating_white, games.rating_black,
            game_position_xref.game_id, game_position_xref.position_id,
            positions.id, positions.tps,
            CASE WHEN games.rating_white < games.rating_black THEN games.rating_white
                ELSE games.rating_black
                END AS min_rating
        FROM game_position_xref, games, positions
        WHERE game_position_xref.position_id=positions.id
            AND games.id = game_position_xref.game_id
            AND positions.tps = '{tps}'
        ORDER BY min_rating DESC;"""

        cur = self.db.cursor()
        cur.execute(games_sql)
        row = cur.fetchall()

        all_games = ''

        for r in row:
            all_games += dict(r)['ptn']

        games_window = tkinter.Toplevel(self.top)
        games_window.title = 'all games ptn'
        ptn_text = tkinter.scrolledtext.ScrolledText(games_window, height=40)
        ptn_text.pack()
        ptn_text.insert('1.0', all_games)

    def collect(self):
        cur = self.db.cursor()

        tps = self.game.get_tps()

        symmetry = symmetry_normalisator.get_tps_orientation(tps)
        sym_tps = symmetry_normalisator.transform_tps(tps, symmetry)

        os.system(f'TPStoPNG "{tps} 1 1" name=tak opening=no-swap')
        img_load = Image.open("tak.png")
        render = ImageTk.PhotoImage(img_load)

        self.board_image.configure(image=render)
        self.board_image.image = render
        self.tps.set(tps)

        select_results_sql = f"SELECT * FROM positions WHERE tps='{sym_tps}';"

        cur.execute(select_results_sql)
        row = dict(cur.fetchone())

        pos_id = row['id']

        textvar = f"white <- {row['wwins']}  :  {row['bwins']} -> black"
        self.win_rate.set(textvar)

        select_moves_sql = f"SELECT * FROM moves_map WHERE position_id={pos_id} ORDER BY times_played DESC;"

        cur.execute(select_moves_sql)
        rows = cur.fetchall()

        result = []

        for child in self.move_option_frame.winfo_children():
            child.destroy()

        real_positions = []

        m_i = 0
        for i, r in enumerate(rows):
            if len(real_positions) >= 20:
                break

            row = dict(r)

            cloned_game = self.game.clone()

            move = row['ptn']
            move = symmetry_normalisator.transposed_transform_move(move, symmetry)

            cloned_game.move(move)
            tps = cloned_game.get_tps()
            tps = symmetry_normalisator.transform_tps(tps, symmetry_normalisator.get_tps_orientation(tps))

            select_results_sql = f"SELECT * FROM positions WHERE tps='{tps}';"

            cur.execute(select_results_sql)
            exe_res = cur.fetchone()
            if exe_res is None:
                continue
            next_row = dict(exe_res)

            move_id = next_row['id']
            if move_id in real_positions:
                continue
            real_positions.append(move_id)

            times_played = next_row['bwins'] + next_row['wwins']

            button_text = f"{m_i + 1}:".rjust(3) + f"{move} - ".rjust(8) + f"{times_played} games - ".rjust(14)\
                          + f"w {next_row['wwins']}".ljust(7) + "|" + f"{next_row['bwins']} b".rjust(7)

            result.append(move)
            b = tkinter.Button(self.move_option_frame, text=button_text,
                               command=lambda m=move: self.make_move(m),
                               width=40, anchor='w')

            b['font'] = font.Font(family='Courier', size=10, weight='bold')

            b.pack()
            m_i += 1

        return result

    def make_move(self, m):
        self.game_stack.append(self.game)
        self.game = self.game.clone()
        self.game.move(m)
        self.collect()

    def take_move(self):
        if len(self.game_stack) > 0:
            self.game = self.game_stack.pop()
            self.collect()


def collector_main(db_file):
    expl = TAKexplorer(db_file)

    expl.top.mainloop()
