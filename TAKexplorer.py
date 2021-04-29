import getopt
import sys

import data_collector
import db_extractor
import ptn_parser
from position_db import PositionDataBase
from statistics_generator import StatisticsGenerator


def main(args):
    task = args[0]
    argv = args[1:]

    if task == 'extract':
        db_file = ''
        target_file = ''
        ptn_file = 'data/games.ptn'

        num_plies = 1
        num_games = sys.maxsize
        min_rating = 0

        try:
            opts, args = getopt.getopt(argv, "hi:o:p:n:r:b:w:",
                                       ["ifile=", "ofile=",
                                        "min_plies=", "max_games=", "min_rating=",
                                        "black=", "white="])
        except getopt.GetoptError:
            print(
                'TAKexplorer.py extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum '
                'games> ] [ -r <minimum rating> ] [ -b <black player> ] [ -w <white player>]')
            sys.exit(2)

        player_black = None
        player_white = None

        for opt, arg in opts:
            if opt == '-h':
                print(
                    'TAKexplorer.py extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum '
                    'games> ] [ -r <minimum rating> ] [ -b <black player> ] [ -w <white player>]')
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
            elif opt in ('-w', '--white'):
                player_white = arg
            elif opt in ('-b', '--black'):
                player_black = arg

        db_extractor.main(db_file, ptn_file, num_plies, num_games, min_rating, player_black, player_white)

        db = PositionDataBase()
        db.create(target_file)

        ptn_parser.main(ptn_file, db)

        db.conn.commit()

    elif task == 'explore':
        data_collector.collector_main(argv[0])

    elif task == 'stats':
        db_file = ''
        target_file = ''
        ptn_file = 'data/games.ptn'

        num_plies = 1
        num_games = sys.maxsize
        min_rating = 0

        try:
            opts, args = getopt.getopt(argv, "hi:o:p:n:r:b:w:",
                                       ["ifile=", "ofile=",
                                        "min_plies=", "max_games=", "min_rating=",
                                        "black=", "white="])
        except getopt.GetoptError:
            print(
                'TAKexplorer.py extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum '
                'games> ] [ -r <minimum rating> ] [ -b <black player> ] [ -w <white player>]')
            sys.exit(2)

        player_black = None
        player_white = None

        for opt, arg in opts:
            if opt == '-h':
                print(
                    'TAKexplorer.py extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum '
                    'games> ] [ -r <minimum rating> ] [ -b <black player> ] [ -w <white player>]')
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
            elif opt in ('-w', '--white'):
                player_white = arg
            elif opt in ('-b', '--black'):
                player_black = arg

        db_extractor.main(db_file, ptn_file, num_plies, num_games, min_rating, player_black, player_white)

        sg = StatisticsGenerator(target_file)
        ptn_parser.main(ptn_file, sg)
        sg.print_results()


if __name__ == '__main__':
    main(sys.argv[1:])
