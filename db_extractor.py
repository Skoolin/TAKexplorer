import sqlite3
from typing import Optional
from datetime import datetime, timedelta

BOTLIST = [
    'WilemBot',
    'TopazBot',
    'Tiltak_Bot',
    'TakticianBot',
    'TakticianBotDev',
    'TakkenBot',
    'kriTakBot',
    'robot',
    'AaaarghBot',
    'TakkerusBot',
    'CrumBot',
    'SlateBot',
    'alphatak_bot',
    'alphabot',
    'IntuitionBot',
    'Geust93',
    'ShlktBot',
    'Taik',
    'VerekaiBot1',
    'CobbleBot',
    'AlphaTakBot_5x5',
    'takkybot',
    'BloodlessBot',
    'TakkerBot',
    'BeginnerBot',
    'cutak_bot',
    'FriendlyBot',
    'antakonistbot',
    'sTAKbot1',
    'sTAKbot2',
    'FPABot',
    'DoubleStackBot',
    'FlashBot',
    'CairnBot'
]
BOTNAMES = '("' + '","'.join(BOTLIST) + '")'

def get_header(key: str, val: str):
    return f'[{key} "{val}"]\n'


def convert_move(move: str):
    spl = move.split(' ')
    move_type_char = spl[0]
    if move_type_char == 'P':
        # check whether it is a flat or special (C, W) stone
        res = (spl[2].replace('W', 'S') if len(spl) > 2 else '')
        return res + spl[1].lower()
    if move_type_char == 'M':
        spl[3] = ''.join(spl[3:])
        # get the number of stones picked up
        res = str(sum(map(int, spl[3])))
        # get the starting position
        res += spl[1].lower()

        # get the move direction:
        if spl[1][0] == spl[2][0]:  # move up or down
            res += ('+' if spl[1][1] < spl[2][1] else '-')
        else:                       # move left or right
            res += ('>' if spl[1][0] < spl[2][0] else '<')

        # get the stones dropped each square
        return res + spl[3]
    return ''


def get_moves(notation: str):
    moves = ''
    count = 0
    for move in notation.split(','):
        if count%2 == 0:
            moves += f'\n{int(count/2+1)}.'
        moves += ' '
        moves += convert_move(move)
        count += 1
    return moves


def get_ptn(game) -> str:
    ptn = ''

    white_name = 'Anon' if game['date'] < 1461430800000 else game['player_white']
    black_name = 'Anon' if game['date'] < 1461430800000 else game['player_black']

    ptn += get_header('Site', 'PlayTak.com')
    ptn += get_header('Event', 'Online Play')

    ptn += get_header('Player1', white_name)
    ptn += get_header('Player2', black_name)

    ptn += get_header('Result', game['result'])
    ptn += get_header('Size', game['size'])

    # rating header
    ptn += get_header('Rating1', game['rating_white'])
    ptn += get_header('Rating2', game['rating_black'])

    ptn += get_header('playtak_id', game['id'])

    # date and time headers
    dt = datetime.utcfromtimestamp((game['date'] / 1000))
    ptn += get_header('Date', dt.strftime("%Y.%m.%d"))
    ptn += get_header('Time', dt.strftime("%H:%M:%S"))

    def format_clock(timertime_seconds: int, timerinc_seconds: int):
        """Format `minutes:seconds +incrementseconds` e.g. `3:0 +5"""
        timertime = timedelta(seconds=timertime_seconds)
        timerinc = timedelta(seconds=timerinc_seconds)
        return f"{timertime.seconds // 60}:{timertime.seconds % 60} +{timerinc.seconds}"

    ptn += get_header('Clock', format_clock(game['timertime'], game['timerinc']))

    ptn += get_moves(game['notation'])
    ptn += '\n\n\n'

    return ptn


def extract_ptn(
    db_file: str,
    num_plies: int,
    num_games: int,
    min_rating: int,
    player_white: Optional[str] = None,
    player_black: Optional[str] = None,
    start_id = 0,
    exclude_bots: bool = False,
):
    with sqlite3.connect(db_file) as db:
        db.row_factory = sqlite3.Row

        conditions = [
            f"numplies>{num_plies}",
            f"rating_white >= {min_rating}",
            f"rating_black >= {min_rating}",
            f"id > {start_id}",
            "size = 6",
        ]
        if player_white is not None:
            conditions.append(f"player_white = {player_white}")
        elif exclude_bots:
            conditions.append(f"player_white NOT IN {BOTNAMES}")

        if player_black is not None:
            conditions.append(f"player_black = {player_black}")
        elif exclude_bots:
            conditions.append(f"player_black NOT IN {BOTNAMES}")

        games_query = f"""
            SELECT *, LENGTH(notation) - LENGTH(REPLACE(notation,',','')) - 1 AS numplies
            FROM games
            WHERE
                {' AND '.join(conditions)}
            LIMIT {num_games}
        ;"""
        cursor = db.execute(games_query)
        games = cursor.fetchall()
        cursor.close()
        return list(map(lambda game: (dict(game), get_ptn(game)), games))
