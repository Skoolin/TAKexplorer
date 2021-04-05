# TAKexplorer
A tak opening DB generator and explorer (Currently only supports games with board size 6)

To run you need to supply an opening database to explore:  
`TAKexplorer.py explore <database file name>`

If you want to stare at a red progress bar for two hours, you can generate the database by yourself as well:  
`TAKexplorer extract -i <database file> -o <output file> [ -p <minimum plies> ] [ -n <maximum games> ] [ -r <minimum rating> ]` 

Yes, I know, it should not take that long and both my python code and my SQL queries are ugly, deal with it xD

I already have generated a database with all players rating 1200+ if you want to use it instead of generating your own. You can download it by going to [actions](https://github.com/Skoolin/TAKexplorer/actions). There you can click on the latest green workflow run and scroll down to artifacts. The file you are looking for is called positions_s6_1200.db (~65mb).

You need to have pillow and tqdm installed:  
`pip install pillow tqdm`

Also, you need grupplers wonderful TPStoPNG tool:  
https://github.com/gruppler/TPS-Ninja
