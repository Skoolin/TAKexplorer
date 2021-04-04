import sys

from tqdm import tqdm

from position_db import PositionDataBase
from tak import GameState


def add_ptn(ptn, db: PositionDataBase, max_plies=sys.maxsize):

    spl = ptn.split("\n\n")
    headers = spl[0]
    moves = spl[1]

    # parse headers
    spl = headers.split("\n")
    white_name = spl[2][10:-2]
    black_name = spl[3][10:-2]
    result = spl[4][9:12]
    size = int(spl[5][7])
    rating_white = int(spl[6][10:-2])
    rating_black = int(spl[7][10:-2])

    # parse moves
    spl = moves.split("\n")
    all_moves = []
    for row in spl:
        two_ply = row.split(" ")
        all_moves.append(two_ply[1])
        if len(two_ply) > 2:
            all_moves.append(two_ply[2])

    # apply upper bound of ply depth
    all_moves = all_moves[0:min(len(all_moves), max_plies)]

    # create board
    tak = GameState(size)

    # add game to database
    game_id = db.add_game(size, white_name, black_name, ptn, result, rating_white, rating_black)

    symmetry = db.add_position(game_id, all_moves[0], result, tak.get_tps())
    # make all moves
    for i in range(0, len(all_moves) - 1):
        tak.move(all_moves[i])
        symmetry = db.add_position(game_id, all_moves[i + 1], result, tak.get_tps())
    tak.move(all_moves[-1])
    db.add_position(game_id, None, result, tak.get_tps())


def main(ptn_file, db_file):

    max_plies = 24

    db = PositionDataBase()
    db.create(db_file)

    ptn = ''

    f = open(ptn_file)
    count = f.read().count('[Site')
    f.close()

    with tqdm(total=count) as progress:
        with open(ptn_file) as f:
            line = f.readline()
            ptn += line
            line = f.readline()
            while line:
                if line.startswith("[Site"):
                    add_ptn(ptn, db, max_plies)
                    progress.update()
                    ptn = ''
                ptn += line
                line = f.readline()

    db.conn.commit()
