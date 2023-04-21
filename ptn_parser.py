import sys
import typing

from tqdm import tqdm

from position_processor import PositionProcessor
from tak import GameState
from db_extractor import get_moves_array


def add_game(game: dict, dp: PositionProcessor, max_plies=sys.maxsize):
    ptn_array = get_moves_array(game['notation'])
    all_moves = ptn_array[0:min(len(ptn_array), max_plies)]

    # create board
    tak = GameState(game['size'])

    # add game to database
    result = game['result']
    komi = int(game['komi'] or 0)

    game_id = dp.add_game(
        size=game['size'],
        playtak_id=game['id'],
        white_name=game['player_white'],
        black_name=game['player_black'],
        result=game['result'],
        komi=komi,
        rating_white=game['rating_white'],
        rating_black=game['rating_black'],
        date=game['date'],
    )

    # make all moves
    last_tps = tak.get_tps()
    for move in all_moves:
        tak.move(move)
        current_tps = tak.get_tps()  # we want to calculate the TPS only once per game state
        dp.add_position(game_id, move, result, last_tps, current_tps, tak)
        last_tps = current_tps

    dp.add_position(game_id, None, result, last_tps, None, tak)


def add_games_to_db(games: typing.Iterable[dict], dp: PositionProcessor, max_plies=30):
    games = list(games)

    with tqdm(total=len(games), mininterval=0.5, maxinterval=2.0) as progress:
        for game in games:
            add_game(game, dp, max_plies)
            progress.update()
