import sys, getopt
import sqlite3


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
            return res + spl[3][:-1]
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

# TODO date and time headers
#    dt = DateTime.strptime((game.date/1000).to_s, '%s').to_s
#    dt = (dt.gsub 'T', ' ').gsub '+00:00', ''
#    ptn += get_header('Date', dt.split(' ')[0].gsub('-', '.'))
#    ptn += get_header('Time', dt.split(' ')[1])

    ptn += get_header('Player1', wn)
    ptn += get_header('Player2', bn)

# TODO clock header
#    ptn += get_header('Clock', get_timer_info(game.timertime, game.timerinc))

    ptn += get_header('Result', game['result'])
    ptn += get_header('Size', game['size'])

    # rating header
    ptn += get_header('Rating1', game['rating_white'])
    ptn += get_header('Rating2', game['rating_black'])

    ptn += get_moves(game['notation'])
    ptn += '\n\n\n'

    return ptn


def extract_ptn(f: str, o: str, num_plies: int, max_i: int, min_rating: int):
    con = sqlite3.connect(f)
    con.row_factory = sqlite3.Row
    games = con.execute(f"""
        SELECT *, LENGTH(notation) - LENGTH(REPLACE(notation,',','')) - 1 AS numplies 
        FROM games 
        WHERE
            numplies>{num_plies} AND 
            (rating_white >= {min_rating} AND
            rating_black >= {min_rating}) AND 
            size = 6
        ;""")

    with open(o, 'w') as output_file:
        for i, row in enumerate(games):
            if i > max_i:
                break
            r = dict(row)
            output_file.write(get_ptn(r))


def main(argv):
    db_file = ''
    target_file = ''

    num_plies = 1
    num_games = sys.maxsize
    min_rating = 0

    try:
        opts, args = getopt.getopt(argv, "hi:o:p:n:r:", ["ifile=", "ofile=", "min_plies=", "max_games=", "min_rating="])
    except:
        print('db_extractor.py -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum games> ]')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('db_extractor.py -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum games> ]')
            sys.exit()
        elif opt in ('-i', '--ifile'):
            db_file = arg
        elif opt in ('-o', '--ofile'):
            target_file = arg
        elif opt in ('-p', '--min_plies'):
            num_plies = int(arg)
        elif opt in ('-n', '--max_games'):
            num_games = int(arg)
        elif opt in ('-r', '--min_rating'):
            min_rating = int(arg)

    # check if db file exists
    try:
        f = open(db_file)
        f.close()
    except IOError:
        print("File not accessible")
        sys.exit(2)

    if target_file == '':
        print("you need to give an input file and an output file")
        print('db_extractor.py -i <database file> -o <output file> [ -n <minimum plies> ]')
        sys.exit(2)

    extract_ptn(db_file, target_file, num_plies, num_games, min_rating)


if __name__ == '__main__':
    main(sys.argv[1:])
