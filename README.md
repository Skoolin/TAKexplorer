# TAKexplorer
A tak opening DB generator and explorer (Currently only supports games with board size 6)

To run you need to supply an opening database to explore:  
`TAKexplorer.py explore <database file name>`

If you want to stare at a red progress bar for two hours, you can generate the database by yourself as well:  
`TAKexplorer extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum games> ] [ -r <minimum rating> ]` 

Yes, I know, it should not take that long and both my python code and my SQL queries are ugly, deal with it xD

I already have generated a database with all players rating 1200+ if you want to use it instead of generating your own.

You need to have sqlite3 installed:  
`pip install sqlite3`

Also, you need grupplers wonderful TPStoPNG tool:  
https://github.com/gruppler/TPS-Ninja
