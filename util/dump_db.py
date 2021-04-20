import csv
import sqlite3

con = sqlite3.connect('data/openings_s6_1200.db')
con.row_factory = sqlite3.Row

cur = con.cursor()

# dump positions
cur.execute("SELECT * FROM positions;")
with open("positions.csv", "w") as csv_file:
    csv_writer = csv.writer(csv_file, delimiter="\t")
    csv_writer.writerow([i[0] for i in cur.description])
    csv_writer.writerows(cur)

# dump moves
cur.execute("""
SELECT moves_map.*, positions.bwins, positions.wwins
FROM moves_map, positions
WHERE positions.id = moves_map.next_position_id
ORDER BY position_id;
""")
with open("moves.csv", "w") as csv_file:
    csv_writer = csv.writer(csv_file, delimiter="\t")
    csv_writer.writerow([i[0] for i in cur.description])
    csv_writer.writerows(cur)

# dump games
cur.execute("SELECT * FROM games;")
with open("games.csv", "w") as csv_file:
    csv_writer = csv.writer(csv_file, delimiter="\t")
    csv_writer.writerow([i[0] for i in cur.description])
    csv_writer.writerows(cur)

# dump reference table for games and positions
cur.execute("SELECT * FROM game_position_xref ORDER BY position_id;")
with open("game_references.csv", "w") as csv_file:
    csv_writer = csv.writer(csv_file, delimiter="\t")
    csv_writer.writerow([i[0] for i in cur.description])
    csv_writer.writerows(cur)

# done!
con.close()

total = ""

with open("positions.csv") as t:
    total += t.read() + "\nTABLE\n"
with open("games.csv") as t:
    total += t.read() + "\nTABLE\n"
with open("moves.csv") as t:
    total += t.read() + "\nTABLE\n"
with open("game_references.csv") as t:
    total += t.read()

with open("db_dump", "w") as t:
    t.write(total)
