from contextlib import closing
import csv
import sqlite3

with closing(sqlite3.connect('data/openings_s6_1200.db')) as con:
    con.row_factory = sqlite3.Row

    with closing(con.cursor()) as cur:
        # dump positions
        cur.execute("SELECT * FROM positions;")
        with open("positions.csv", "w", encoding="UTF-8") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter="\t")
            csv_writer.writerow([i[0] for i in cur.description])
            csv_writer.writerows(cur)

        # dump games
        cur.execute("SELECT * FROM games;")
        with open("games.csv", "w", encoding="UTF-8") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter="\t")
            csv_writer.writerow([i[0] for i in cur.description])
            csv_writer.writerows(cur)

        # dump reference table for games and positions
        cur.execute("SELECT * FROM game_position_xref ORDER BY position_id;")
        with open("game_references.csv", "w", encoding="UTF-8") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter="\t")
            csv_writer.writerow([i[0] for i in cur.description])
            csv_writer.writerows(cur)

total: str = ""

with open("positions.csv", encoding="UTF-8") as t:
    total += t.read() + "\nTABLE\n"
with open("games.csv", encoding="UTF-8") as t:
    total += t.read() + "\nTABLE\n"
with open("game_references.csv", encoding="UTF-8") as t:
    total += t.read()

with open("db_dump", "w", encoding="UTF-8") as t:
    t.write(total)
