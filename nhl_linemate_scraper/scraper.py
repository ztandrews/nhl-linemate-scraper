#################################### NHL Linemate Scraper #########################################
#                                                                                                 #
#                                                                                                 #
#                              Author: Zach Andrews - @StatsByZach                                #
#                             Version: 0.0.1                                                      #
#                               About: The NHL Shift data is structured poorly                    #
#                                      if you'd like to do analysis on forward                    #
#                                      lines, defensive pairs, or match ups. This                 #
#                                      scraper aims to fix that problem by returning              #
#                                      3 Pandas Data Frames: One with every player on             #
#                                      the ice at every second of the game, one with              #
#                                      a report of 5v5 forward line combo TOI's, and              #
#                                      one with a report of 5v5 defensemen pair combo TOI's.      #
#                              License: MIT                                                       #
#                                                                                                 #
#                                                                                                 #
#                                                                                                 #
###################################################################################################

####################################### Import Packages ###########################################
import pandas as pd
import numpy as np
import requests
from itertools import combinations
from bs4 import BeautifulSoup
####################################### Main Functions ############################################
def scrape_game(game_id):
    '''
    scrape_game - Scrapes an NHL game and returns a df of 
    parameters - game_id - A Game ID as provided by the NHL API
    '''
    print("Scraping shifts from game {}...".format(game_id))
    # Fetch game info from API
    game_info= fetch_game_info(game_id)
    # Create the shift_data df. Need to extract it via bs4
    shift_data = create_shift_data(game_id,game_info)
    # Main function. Creates the df of whos on the ice at every second of the game
    linemate_data = create_linemate_data(shift_data,game_info)
    # Create report of 5v5 linemates and defensive pairs
    forward_5v5_report,defender_5v5_report= create_5v5_linemate_report(linemate_data,game_info)
    print("Game {} completed.".format(game_id))
    # Returns a dict of each df
    return {"linemate_data":linemate_data,"forward_5v5_report":forward_5v5_report,"defender_5v5_report":defender_5v5_report}

def fetch_game_info(game_id):
    '''
    fetch_game_info - Fetch game info from the pbp API. Need some data from here like game date, game ID, etc.
    parameters - game_id
    '''
    try:    
        req = requests.get("https://api-web.nhle.com/v1/gamecenter/{}/play-by-play".format(game_id))
        req.raise_for_status() 
    # Handle any errors
    except requests.exceptions.HTTPError as http_err:
        print(f"Play-by-Play API HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_exc:
        print(f"Play-by-Play API request failed: {req_exc}")
    except ValueError as val_err:
        print(f"Play-by-Play API Value error occurred: {val_err}")
    else:
        game_info=req.json()
        return game_info

def create_shift_data(game_id,game_info):
    '''
    create_shift_data - Function to build the df of a summary of each players shift. start time, end time, duration, etc.
    parameters - game_id, game_info - A dict containing game information
    '''
    shift_data = pd.DataFrame()
    for team in ['H','V']:
        page = fetch_shift_data(game_id,game_info,team)
        shifts = extract_shift_data(page)
        clean_shifts = clean_shift_data(shifts,game_info,team)
        shift_data = pd.concat([shift_data,clean_shifts])
    return shift_data

def fetch_shift_data(game_id,game_info,home_or_away):
    '''
    fetch_shift_data - Function to fetch the html report provided by the NHL
    parameters - game_id, game_info, home_or_away - will be either H or V. Need this for the URL
    '''
    try:    
        req = requests.get("https://www.nhl.com/scores/htmlreports/{}/T{}{}.HTM".format(game_info['season'],home_or_away,str(game_id)[4:]))
        req.raise_for_status() 
    # Handle any errors
    except requests.exceptions.HTTPError as http_err:
        print(f"Shift Report HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_exc:
        print(f"Shift Report request failed: {req_exc}")
    except ValueError as val_err:
        print(f"Shift Report Value error occured: {val_err}")
    else:
        page = req.text
        return page

def extract_shift_data(page):
    '''
    extract_shift_data - A series of bs4 functions to extract the actual shift info from the html code
    parameters - page - a string of the shift reports html code
    '''
    soup = BeautifulSoup(page, 'html.parser')
    shifts_data = []
    current_player = None
    # Iterate over each row in the HTML file
    for row in soup.find_all('tr'):
        if 'playerHeading' in str(row):
            # Extract player's name
            current_player = row.get_text(strip=True).split(' ', 1)
        else:
            cols = row.find_all('td')
            if cols and len(cols) == 6 and cols[0].get_text(strip=True).isdigit():
                # Extract shift details
                shift_details = [current_player] + [col.get_text(strip=True) for col in cols]
                shifts_data.append(shift_details)

    # Create DataFrame from extracted data
    column_headers = ['Player', 'Shift Number', 'Period', 'Start of Shift', 'End of Shift', 'Duration', 'Event']
    shifts_df = pd.DataFrame(shifts_data, columns=column_headers)
    return shifts_df

def clean_shift_data(shifts,game_info,team):
    '''
    clean_shift_data - Function to clean up the by-player shift data
    patameters - shifts - the extracted shifts df by bs4, game_info, team - home or away team
    '''
    shifts = shifts.rename(columns={"Shift Number":"shift_number","Period":"period","Start of Shift":"shift_start_time","End of Shift":"shift_end_time","Duration":"duration"})
    shifts['period'] = np.where(shifts['period']=="OT",4,shifts['period'])
    # The player column comes in as an array [player_number, player_name]. We need to split that
    shifts = split_player_column(shifts)
    shifts = convert_shift_times(shifts)
    # We need to convert the time to seconds
    convert_to_seconds_vectorized(shifts, ['shift_start_time', 'shift_end_time', 'duration'])
    period_condition = shifts['period'] != 1
    for time_col in ['shift_start_time_seconds', 'shift_end_time_seconds']:
        shifts[time_col] = np.where(period_condition, shifts[time_col] + 1200 * (shifts['period'].astype(int) - 1), shifts[time_col])
    team_name = game_info['homeTeam']['abbrev'] if team == 'H' else game_info['awayTeam']['abbrev']
    team_id = game_info['homeTeam']['id'] if team == 'H' else game_info['awayTeam']['id']
    shifts['team'] = team_name
    shifts = join_shifts_rosters(shifts,game_info,team_id)
    return shifts


def split_player_column(shifts):
    '''
    split_player_column - Function to split the 'Player' column into 'Player Number', 'Last Name', and 'First Name'
    parameters - shifts
    '''
    shifts['player_number'] = shifts['Player'].apply(lambda x: x[0] if len(x) > 0 else None)
    shifts['last_name'] = shifts['Player'].apply(lambda x: x[1].split(', ')[0] if len(x) > 1 and ', ' in x[1] else None)
    shifts['first_name'] = shifts['Player'].apply(lambda x: x[1].split(', ')[1] if len(x) > 1 and ', ' in x[1] else None)
    shifts.drop('Player', axis=1, inplace=True)
    return shifts

def convert_shift_times(shifts):
    '''
    convert_shift_times - Apply the helper function to 'Start of Shift' and 'End of Shift' columns. The shift start and end times on the html report show
    the time elapsed / time remaining for both. We only care about time elapsed
    parameters - df - A data frame of shifts
    '''
    shifts['shift_start_time'] = shifts['shift_start_time'].apply(extract_elapsed_time)
    shifts['shift_end_time'] = shifts['shift_end_time'] .apply(extract_elapsed_time)
    return shifts

def extract_elapsed_time(time_str):
        '''
        extract_elapsed_time - Helper function to extract elapsed time from the format 'elapsed / remaining'
        parameters - time_str - Time in the format elapsed / remaining (ex. 5:00/15:00)
        '''
        return time_str.split(' / ')[0] if ' / ' in time_str else time_str

def convert_to_seconds_vectorized(shifts, col_names):
    '''
    convert_to_seconds_vectorized - Function to convert the time columns to seconds
    parameters - shifts - A data frame of extracted shift data, col_names - column names to convert
    '''
    for col in col_names:
        time_parts = shifts[col].str.split(':', expand=True).astype(int)
        shifts[f'{col}_seconds'] = time_parts[0] * 60 + time_parts[1]

def join_shifts_rosters(shifts,game_info,team_id):
    '''
    join_shifts_rosters - Function to join the shifts df to the rosters from the play by play API. We need to do this because the html report doesn't
    give us lots of player data, we need each players position and playerId from here
    parameters - shifts, game_info, team_id - The numeric ID of a team as provided by the NHL API
    '''
    rosters = pd.json_normalize(game_info['rosterSpots'])
    rosters = rosters[rosters['teamId']==team_id][['playerId','sweaterNumber','positionCode','firstName.default','lastName.default']]
    rosters = rosters.rename(columns={"sweaterNumber":"player_number"})
    shifts['player_number'] = shifts['player_number'].astype(int)
    shifts = pd.merge(shifts,rosters,on="player_number",how='inner')
    pos_cats = {"R":"F","C":"F","L":"F","G":"G","D":"D"}
    shifts['position'] = shifts['positionCode'].map(pos_cats)
    shifts['full_name'] = shifts['firstName.default'] + ' ' + shifts['lastName.default']
    return shifts

def create_linemate_data(shift_data,game_info):
    '''
    create_linemate_data - Main function that takes the fully cleaned shift_data df, expands each players shifts, and finds out who was on the ice
    at every single second of the game. The output will be a df that contains each home and away player on the ice at every second, along with other info
    parameters - shift_data - The fully cleaned shift data from the html report, game_info
    '''
    home_team = game_info['homeTeam']['abbrev']
    away_team = game_info['awayTeam']['abbrev']
    date = game_info['gameDate']
    season = game_info['season']
    game_id = game_info['id']
    game_type = {1: "pre-season", 2: "regular-season", 3: "post-season"}[game_info['gameType']]
    max_seconds = shift_data['shift_end_time_seconds'].max()
    all_data=[]
    for second in range(1, max_seconds+1):
        # So  I could've either did <= and > or < and >= and I chose the latter.
        # When a shift change happens after a stoppage, there are technically different players on the ice
        # at the same given second (i.e a goal happens at second 5, then theres a line change before the faceoff,
        # which technially also happens at second 5). By choosing selecting playerso on ice this way, we include
        # players that are on the ice for events, rather than the faceoff, if that makes sense.
        on_ice = shift_data[(shift_data['shift_start_time_seconds'] < second) & (shift_data['shift_end_time_seconds'] >= second)]
        # Ensure there are no duplicate shifts
        on_ice = on_ice.drop_duplicates()
        on_ice = on_ice.sort_values(by=['position','team'])
        home_players = on_ice[on_ice['team'] == home_team]
        away_players = on_ice[on_ice['team'] == away_team]
        lenh = len(home_players)
        lena=len(away_players)
        if lenh >6:
            print("fyi - there are more than 6 home players on the ice at second {} of game {}. this is due to a too many pen penalty.".format(second,game_info['id']))
        if lena > 6:
            print("fyi - there are more than 6 away players on the ice at second {} of game {}. this is due to a too many pen penalty.".format(second,game_info['id']))
        players_on_ice = {}
        # Process home players
        home_on_ice = 0
        for i, p in enumerate(home_players.itertuples(), 1):
            players_on_ice[f"home_player_{i}_name"] = p.full_name
            players_on_ice[f"home_player_{i}_id"] = p.playerId
            players_on_ice[f"home_player_{i}_position"] = p.position
            if p.position != "G":
                home_on_ice += 1
        # Process away players
        away_on_ice = 0
        for i, p in enumerate(away_players.itertuples(), 1):
            players_on_ice[f"away_player_{i}_name"] = p.full_name
            players_on_ice[f"away_player_{i}_id"] = p.playerId
            players_on_ice[f"away_player_{i}_position"] = p.position
            if p.position != "G":
                away_on_ice += 1
        # Add in additional info
        players_on_ice['second'] = second
        players_on_ice['period'] = on_ice.iloc[0]['period']
        players_on_ice['home_skaters_on_ice'] = home_on_ice
        players_on_ice['away_skaters_on_ice'] = away_on_ice
        players_on_ice['strength'] = f"{home_on_ice}v{away_on_ice}"
        players_on_ice['strength_cat'] = np.where(home_on_ice==away_on_ice,'even',np.where(home_on_ice>away_on_ice,"home_advantage","away_advantage"))
        all_data.append(players_on_ice)

    # Create DataFrame after collecting all data
    linemate_data = pd.DataFrame(all_data)
    linemate_data['home_team'] = home_team
    linemate_data['away_team'] = away_team
    linemate_data['game_date'] = date
    linemate_data['game_season']=season
    linemate_data['game_id']=game_id
    linemate_data['game_type']=game_type
    return linemate_data

def create_5v5_linemate_report(linemate_data,game_info):
    '''
    create_5v5_linemate_report - Function to create forward and defender 5v5 reports. Just threw this in to give users an easy way to get forward line and d pair toi. Returns every combo of 3 forwards and 2 defensemen that played together
    parameters - linemate_data - complete data frame containing who was on the ice at every second, game_info
    '''
    forward_5v5_report=create_5v5_forward_report(linemate_data,game_info)
    defender_5v5_report = create_5v5_defender_report(linemate_data,game_info)
    return forward_5v5_report,defender_5v5_report

def create_5v5_forward_report(linemate_data,game_info):
    '''
    create_5v5_forward_report - Function to create the forward line 5v5 report
    parameters - linemate data, game_info
    '''
    df_5v5 = linemate_data[linemate_data['strength'] == '5v5']
    # Extracting forward lines for home and away teams
    home_forward_lines_df = extract_forward_lines(df_5v5, 'home')
    away_forward_lines_df = extract_forward_lines(df_5v5, 'away')
    # Some cleaning for each
    home_forward_lines_df['toi_mins'] = home_forward_lines_df['toi_secs']/60
    home_forward_lines_df['team'] = game_info['homeTeam']['abbrev']
    away_forward_lines_df ['toi_mins'] = away_forward_lines_df ['toi_secs']/60
    away_forward_lines_df['team'] = game_info['awayTeam']['abbrev']
    # Combine
    forward_5v5_report = pd.concat([home_forward_lines_df,away_forward_lines_df])
    # More cleaning
    forward_5v5_report['date'] = game_info['gameDate']
    forward_5v5_report['season'] = game_info['season']
    forward_5v5_report['game_id'] = game_info['id']
    forward_5v5_report['game_type'] = {1: "pre-season", 2: "regular-season", 3: "post-season"}[game_info['gameType']]
    # Celan and return
    forward_5v5_report = forward_5v5_report.sort_values(by="toi_secs",ascending=False).reset_index(drop=True)
    return forward_5v5_report

# Function to extract forward lines with individual player columns
def extract_forward_lines(df, team_prefix):
    '''
    extract_forward_lines - Function to extract combos of forwards that played together in the game. Also takes into accoutnt when more than 3 forwards are on the ice together
    parameters - df - A dataframe of every second of 5v5 play, team_prefix - whether we're running for the home or away team
    '''
    # Filter rows with at least 3 forwards
    df_forwards = df[df.apply(lambda row: row[f'{team_prefix}_skaters_on_ice'] - sum([1 for i in range(1, 6) if row[f'{team_prefix}_player_{i}_position'] == 'D']) >= 3, axis=1)]
    # Initialize a list to store forward line data
    forward_lines_data = []
    # Iterate through each row and extract forward data
    for _, row in df_forwards.iterrows():
        forwards = [
            (row[f'{team_prefix}_player_{i}_id'], row[f'{team_prefix}_player_{i}_name'])
            for i in range(1, 6) if row[f'{team_prefix}_player_{i}_position'] == 'F'
        ]
        # Generate all triplets of forwards, including if more than three are on the ice
        for triplet in combinations(forwards, 3):
            triplet_ids = sorted([int(triplet[0][0]), int(triplet[1][0]), int(triplet[2][0])])
            triplet_data = {
                'forward_line_id': '-'.join(map(str, triplet_ids)),
                'forward_1_name': triplet[0][1],
                'forward_1_id': triplet[0][0],
                'forward_2_name': triplet[1][1],
                'forward_2_id': triplet[1][0],
                'forward_3_name': triplet[2][1],
                'forward_3_id': triplet[2][0],
                'toi_secs': 1 
            }
            forward_lines_data.append(triplet_data)
    # Creating a DataFrame from the collected data
    forward_lines_df = pd.DataFrame(forward_lines_data)
    # Group by the forward line combination and sum the time on ice
    group_columns = [col for col in forward_lines_df.columns if col != 'toi_secs']
    forward_lines_df = forward_lines_df.groupby(group_columns).sum().reset_index()
    return forward_lines_df

def create_5v5_defender_report(linemate_data,game_info):
    '''
    create_5v5_defender_report - Function to create the 5v5 defensive pair report
    parameters - linemate data, game_info
    '''
    # Filter for 5v5 play
    df_5v5 = linemate_data[linemate_data['strength'] == '5v5']
    # Extracting defensemen pairs for home and away teams
    home_defensemen_pairs_df = extract_defensemen_pairs(df_5v5, 'home')
    away_defensemen_pairs_df = extract_defensemen_pairs(df_5v5, 'away')
    # Some cleaning for each
    home_defensemen_pairs_df['toi_mins'] = home_defensemen_pairs_df['toi_secs']/60
    home_defensemen_pairs_df['team'] = game_info['homeTeam']['abbrev']
    away_defensemen_pairs_df ['toi_mins'] = away_defensemen_pairs_df['toi_secs']/60
    away_defensemen_pairs_df['team'] = game_info['awayTeam']['abbrev']
    # Combine
    defender_5v5_report = pd.concat([home_defensemen_pairs_df,away_defensemen_pairs_df])
    # More cleaning
    defender_5v5_report['date'] = game_info['gameDate']
    defender_5v5_report['season'] = game_info['season']
    defender_5v5_report['game_id'] = game_info['id']
    defender_5v5_report['game_type'] = {1: "pre-season", 2: "regular-season", 3: "post-season"}[game_info['gameType']]
    defender_5v5_report = defender_5v5_report.sort_values(by="toi_secs",ascending=False).reset_index(drop=True)
    return defender_5v5_report


# Function to extract defensemen pairs with individual player columns
def extract_defensemen_pairs(df, team_prefix):
    '''
    extract_defensemen_pairs - Function to extract combos of defensemen that played together. Also takes in account when more than 2 defensemen were on the ice
    parameters - df, team_prefix
    '''
    # Filter rows with at least 2 defensemen
    df_defensemen = df[df.apply(lambda row: row[f'{team_prefix}_skaters_on_ice'] >= 2, axis=1)]
    # Initialize a list to store defensemen pair data
    defensemen_pairs_data = []
    # Iterate through each row and extract defensemen data
    for _, row in df_defensemen.iterrows():
        defensemen = [
            (row[f'{team_prefix}_player_{i}_id'], row[f'{team_prefix}_player_{i}_name'])
            for i in range(1, 6) if row[f'{team_prefix}_player_{i}_position'] == 'D'
        ]
        # Generate all pairs of defensemen, including if more than two are on the ice
        for pair in combinations(defensemen, 2):
            pair_ids = sorted([int(pair[0][0]), int(pair[1][0])])
            pair_data = {
                'defensemen_pair_id': '-'.join(map(str, pair_ids)),
                'defensemen_1_name': pair[0][1],
                'defensemen_1_id': pair[0][0],
                'defensemen_2_name': pair[1][1],
                'defensemen_2_id': pair[1][0],
                'toi_secs': 1 
            }
            defensemen_pairs_data.append(pair_data)
    # Creating a DataFrame from the collected data
    pairs_df = pd.DataFrame(defensemen_pairs_data)
    # Group by the defensemen pair combination and sum the time on ice
    group_columns = [col for col in pairs_df.columns if col != 'toi_secs']
    pairs_df = pairs_df.groupby(group_columns).sum().reset_index()
    return pairs_df