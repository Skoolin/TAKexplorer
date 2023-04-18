import sys

from tqdm import tqdm

from position_processor import PositionProcessor
from tak import GameState


def add_ptn(ptn, dp: PositionProcessor, max_plies=sys.maxsize):

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

    playtak_id = int(spl[8].split(' ')[1][1:-2])

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
    game_id = dp.add_game(size, playtak_id, white_name, black_name, ptn, result, rating_white, rating_black)

    # make all moves
    for move in all_moves:
        last_tps = tak.get_tps()
        tak.move(move)
        last_move = move
        dp.add_position(game_id, last_move, result, last_tps, tak.get_tps(), tak)
    dp.add_position(game_id, None, result, tak.get_tps(), None, tak)


def main(ptn_file, dp: PositionProcessor):

    max_plies = 30

    ptn = ''

    with open(ptn_file, encoding="UTF-8") as f:
        count = f.read().count('[Site')

    with tqdm(total=count, mininterval=10.0, maxinterval=50.0) as progress:
        with open(ptn_file, encoding="UTF-8") as f:
            line = f.readline()
            ptn += line
            line = f.readline()
            while line:
                if line.startswith("[Site"):
                    add_ptn(ptn, dp, max_plies)
                    progress.update()
                    ptn = ''
                ptn += line
                line = f.readline()
