import os
import sqlite3


con = sqlite3.connect('../data/openings_s6_1200.db')
con.row_factory = sqlite3.Row

query = '''
SELECT *, wwins+bwins AS num_games
FROM positions
WHERE length(tps) > 35
ORDER BY num_games DESC
'''

cur = con.cursor()

cur.execute(query)
rows = cur.fetchmany(100)

try:
    os.removedirs('drawn_games')
except Exception as e:
    print(e)
try:
    os.makedirs('drawn_games')
except Exception as e:
    print(e)

for i, r in enumerate(rows):
    row = dict(r)
    tps = row['tps']
    cnt = row['num_games']
    os.system(f'TPStoPNG "{tps} 1 1" name=drawn_games/position_{i}_{cnt} opening=no-swap')