# 🏒 NHL Linemate Scraper
### Overview
The NHL currently structures their shift data in a way that makes it hard to tell which players were on the ice at each second of the game, which makes it hard to tell which players were playing together and who they were matched up against. The NHL Linemate Scraper aims to solve this problem by giving users well structured Pandas DataFrames, making it easy to explore forward lines, defensive pairs, and matchup data. This package was developed with those who want to get insights about NHL shift data in mind, and it does so for every NHL game from 2007 and on.

### Features
- A Pandas DataFrame of who was on the ice at every moment of the game.
- Forward Line Analysis: A Pandas DataFrame report of all 5v5 combinations of 3 forwards and their time on ice (TOI).
- Defensive Pair Analysis:A Pandas DataFrame report of all 5v5 combinations of 2 defensemen and their TOI.

### How it's Made
This scraper was built entirely with Python. It scrapes data from the [NHL provided html shift reports]("https://www.nhl.com/scores/htmlreports/20232024/TH020017.HTM") using BeautifulSoup (it's not using the NHL shift API because it has way too many errors in it), and performs many functions to clean it up and transform it into useful data.

### Installation
Install nhl_linemate_scraper easily with pip:
```
pip install nhl_linemate_scraper
```
### Quick Start

After installation, you can start using the package to scrape NHL game data:

```
import nhl_linemate_scraper as nhllms

# Example: Scrape game data
game_id = 2023020001  # Use an actual game ID
data = nhllms.scrape_game(game_id)

# Atccessing the DataFrames. The scrape_game function will return a dict with these three DataFrames:
print(data["linemate_data"])  # Players on ice for every game second
print(data["forward_5v5_report"])  # 5v5 forward line TOI report
print(data["defender_5v5_report"])  # 5v5 defense pair TOI report

```

### Contributing
Contributions to the NHL Linemate Scraper are welcome! If you have suggestions for improvements or new features, feel free to fork the repository, make your changes, and submit a pull request.

### Future Releases
As of now, I only have functions to build 5v5 reports. In the future, I plan to add other strengths as well. I also am looking to make the code run a little faster, because it currently takes some time to scrape each game.

### Support and Feedback
If you encounter any issues or have suggestions, please open an issue on GitHub or contact the author via Twitter: @StatsByZach.