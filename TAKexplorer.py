import getopt
import sys

import data_collector
import db_extractor
import ptn_parser


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
            opts, args = getopt.getopt(argv, "hi:o:p:n:r:",
                                       ["ifile=", "ofile=", "min_plies=", "max_games=", "min_rating="])
        except:
            print(
                'TAKexplorer.py extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum '
                'games> ] [ -r <minimum rating> ]')
            sys.exit(2)

        for opt, arg in opts:
            if opt == '-h':
                print(
                    'TAKexplorer.py extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum '
                    'games> ] [ -r <minimum rating> ]')
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

        db_extractor.main(db_file, ptn_file, num_plies, num_games, min_rating)
        ptn_parser.main(ptn_file, target_file)

    elif task == 'explore':
        data_collector.collector_main(argv[0])


if __name__ == '__main__':
    main(sys.argv[1:])
