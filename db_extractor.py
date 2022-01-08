import sys

import sqlite3
from xmlrpc.client import DateTime


def get_header(key: str, val: str):
    return f'[{key} "{val}"]\n'


def convert_move(move: str):
        spl = move.split(' ')
        t = spl[0]
        if t == 'P':
            # check whether it is a flat or special (C, W) stone
            res = (spl[2].replace('W', 'S') if len(spl) > 2 else '')
            return res + spl[1].lower()
        elif t == 'M':
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

    wn = 'Anon' if game['date'] < 1461430800000 else game['player_white']
    bn = 'Anon' if game['date'] < 1461430800000 else game['player_black']

    ptn += get_header('Site', 'PlayTak.com')
    ptn += get_header('Event', 'Online Play')

    ptn += get_header('Player1', wn)
    ptn += get_header('Player2', bn)

    ptn += get_header('Result', game['result'])
    ptn += get_header('Size', game['size'])

    # rating header
    ptn += get_header('Rating1', game['rating_white'])
    ptn += get_header('Rating2', game['rating_black'])

    ptn += get_header('playtak_id', game['id'])

    # date and time headers
    dt = str(DateTime((game['date'] / 1000)))
    dt_d = dt.split('T')[0]
    dt_d = ''+dt_d[6:8]+'.'+dt_d[4:6]+'.'+dt_d[0:4]
    ptn += get_header('Date', dt_d)
    ptn += get_header('Time', dt.split('T')[1])

    # TODO clock header
    #    ptn += get_header('Clock', get_timer_info(game.timertime, game.timerinc))

    ptn += get_moves(game['notation'])
    ptn += '\n\n\n'

    return ptn


def extract_ptn(f: str, o: str, num_plies: int, max_i: int, min_rating: int, player_white: str = None, player_black: str = None, start_id = 0):
    con = sqlite3.connect(f)
    con.row_factory = sqlite3.Row
    botlist = [
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
    botlist = '("' + '","'.join(botlist) + '")'

    games_query = f"""
        SELECT *, LENGTH(notation) - LENGTH(REPLACE(notation,',','')) - 1 AS numplies
        FROM games
        WHERE
            numplies>{num_plies} AND
            rating_white >= {min_rating} AND
            rating_black >= {min_rating} AND
            id > {start_id} AND
            player_white {f'NOT IN {botlist}' if player_white is None else f'= "{player_white}"'} AND
            player_black {f'NOT IN {botlist}' if player_black is None else f'= "{player_black}"'} AND
            size = 6
        ;"""
    games = con.execute(games_query)

    with open(o, 'w') as output_file:
        for i, row in enumerate(games):
            if i > max_i:
                break
            r = dict(row)
            output_file.write(get_ptn(r))


def main(db_file, target_file, num_plies, num_games, min_rating, player_black=None, player_white=None, start_id=0):

    # check if db file exists
    try:
        f = open(db_file)
        f.close()
    except IOError:
        print("File not accessible")
        sys.exit(2)

    extract_ptn(db_file, target_file, num_plies, num_games, min_rating, player_white, player_black, start_id)
