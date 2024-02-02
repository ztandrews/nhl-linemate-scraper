################### examples.py ###################
#                                                 #
#            Quick program to provide             #
#            Examples of the scraper in use.      #
#            Run in project's root dir, using     #
#            python -m examples.epy               #
#                                                 #
###################################################


import sys
from pathlib import Path

# Add the scraper directory to sys.path
project_root = Path(__file__).parent.parent  # Adjusts depending on your project structure
scraper_dir = project_root / 'nhl_linemate_scraper'
print(scraper_dir)
sys.path.append(str(scraper_dir))

# Import the scraper
import scraper as nhllms

# Scrape a single game
game_id = 2023020350
single_game_data = nhllms.scrape_game(game_id)
# Access the linemate data Data Frame. This is the df that contains who was on the ice at each game second
linemate_data = single_game_data['linemate_data']
print("Linemate Data Data Frame:\n",linemate_data.head())
# Access the forward 5v5 report Data Frame. This is the df of every combo of 3 forwards that played at least 1 second together
forward_5v5_report = single_game_data['forward_5v5_report']
print("Linemate Data Data Frame:\n",forward_5v5_report.head())
# Access the defender 5v5 report Data Frame. This is the df of every combo of 2 defensemen that played at least 1 second together
defender_5v5_report = single_game_data['defender_5v5_report']
print("Linemate Data Data Frame:\n",defender_5v5_report.head())