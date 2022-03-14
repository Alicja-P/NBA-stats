import sys
import requests
from typing import List
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

# W trzecim zadaniu zapis do plików i odpowiednie printowanie w konsoli
class Data():
    def __init__(self,arg: List[str]):
        self.arg = arg
        self.num = len(arg)

    def validate(self):
        arg = self.arg
        num = self.num
        
        if num == 1 and arg[0] == "grouped-teams":
            pass
        
        elif arg[0] == "players-stats":
            if arg[1] != "--name" or num != 3:
                raise ValueError("Try: players-stats --name 'player name'")
            else:
                self.name = arg[2]
            
            # Making sure that the first letter of a name is uppercase
            if arg[2][0].islower():
                self.name = arg[2].capitalize()

        elif arg[0] == "teams-stats":
            if arg[1] == "--season" and arg[2].isdigit() and (num == 3 or num == 5):
                self.season = int(arg[2])
                self.goal = "stdout"
            else:
                raise ValueError("Try: teams-stats --season 'year in the period from 1979 to now' --output 'file format' (optional)")

            if num == 5 and arg[3] == "--output":
                if arg[4] == "csv" or arg[4] == "json" or arg[4] == "sqlite" or arg[4] == "stdout":
                    self.goal = arg[4]
                else:
                    raise ValueError("Try: teams-stats --season 'year in the period from 1979 to now' --output 'file format' (optional)")

        else:
            raise ValueError("Try again. Possible arguments: 'grouped-teams', 'players-stats' and 'teams-stats'")

    # Get all teams and group them by division
    def grouped_teams(self):
        url = "https://www.balldontlie.io/api/v1/teams"
        params = {'per_page':100,'page':1}
        
        response = requests.get(url,params).json()
        teams = list(response['data'])
        meta = response['meta']

        teams = self.pagination(url,meta,teams,params) 
        teams_df = pd.DataFrame(teams)

        division_names = teams_df['division'].tolist()
        for i in range(len(division_names)):
            division_abbreviation = teams_df['abbreviation'].loc[ teams_df['division'] == division_names[i] ].to_list()
            division_full_name    = teams_df['full_name'].loc[ teams_df['division'] == division_names[i] ].to_list()

            print("\n"+division_names[i])
            for j in range(len(division_full_name)):
                print("\t".expandtabs(4) + division_full_name[j] + " (" + division_abbreviation[j] + ")")

    # Get players with a specific name (first_name or last_name) who is the tallest 
    # and another one who weights the most (print height and weight in metric system)
    def players_stats(self):
        name = self.name
        url = "https://www.balldontlie.io/api/v1/players"
        params = {'per_page':100,"search": name}
        
        response = requests.get(url,params).json()
        players = list(response['data'])
        meta = response['meta']

        players = self.pagination(url,meta,players,params) 
        players_df = pd.DataFrame(players).dropna()

        if players_df.size == 0:
            print("The tallest player: Not found")
            print("The heaviest player: Not found")
            return
        
        # Parameter "search" returns players that HAVE this value IN first or last name - some players could have this value as a part of their name.
        # We need additional processing to receive players with a name of this exact value.
        players_df = players_df.loc[( players_df["first_name"] == name ) | ( players_df["last_name"] == name )]

        # Columns height_feet and height_inches into one column in meters 
        # Column weight_pounds into kilograms
        df_metric = [ players_df["first_name"], players_df["last_name"], round(players_df["height_feet"] * 0.3048 + players_df["height_inches"] * 0.0254,2), round(players_df["weight_pounds"] * 0.45359237,1) ]
        headers = ["first_name", "last_name", "height_meters", "weight_kilograms"]
        df_metric = pd.concat(df_metric, axis=1, keys=headers)

        player_tallest = df_metric.sort_values("height_meters",ascending=False, na_position='last').iloc[0]
        player_heaviest = df_metric.sort_values("weight_kilograms",ascending=False, na_position='last').iloc[0]

        print("The tallest player:", player_tallest["first_name"], player_tallest["last_name"], player_tallest["height_meters"], "meters")
        print("The heaviest player:", player_heaviest["first_name"], player_heaviest["last_name"], player_heaviest["weight_kilograms"], "kilograms")

    # Get statistics for a given season and optionally store it
    def teams_stats(self):
        season = self.season
        url = "https://www.balldontlie.io/api/v1/games"
        params = {'per_page':100,'page':1,'seasons[]': season}
        
        response = requests.get(url,params=params).json()
        games = list(response['data'])
        meta = response['meta']

        games = self.pagination(url,meta,games,params)      
        stats_df = self.stats_dataframe(games)
        self.stats_processing(stats_df)
        teams_ids = self.unique_ids(stats_df)
        
        # Stats for every team
        stats = []
        for team in teams_ids:
            team_name    = stats_df.loc[stats_df["home_id"]    == team, ]['home_name'].iloc[0]
            team_abb     = stats_df.loc[stats_df["home_id"]    == team, ]['home_abb'].iloc[0]
            team_name = team_name + ' (' + team_abb + ')'

            home_won     = stats_df.loc[stats_df['home_id']    == team, 'home_score'].sum()
            visitor_won  = stats_df.loc[stats_df['visitor_id'] == team, 'visitor_score'].sum()
            home_lost    = stats_df.loc[stats_df['home_id']    == team, 'home_score'].count() - home_won
            visitor_lost = stats_df.loc[stats_df['visitor_id'] == team, 'visitor_score'].count() - visitor_won

            stats.append([team_name,home_won,visitor_won,home_lost,visitor_lost])

        stats = pd.DataFrame(stats,columns=['Team name', 'Won games as home team', 'Won games as visitor team', 'Lost games as home team', 'Lost games as visitor team'])
        
        self.output(stats)

    def pagination(self,url,meta,data:list,params):
        for page in range(2,meta['total_pages']+1):
            params['page'] = page
            response = requests.get(url,params).json()
            data.extend(response['data'])
        return data

    def stats_dataframe(self,games:list):
        games_df = pd.DataFrame(games)
        games_df = games_df[['home_team', 'home_team_score', 'visitor_team', 'visitor_team_score']]
        home_team = pd.json_normalize(games_df['home_team'])
        visitor_team = pd.json_normalize(games_df['visitor_team'])
        
        # Dataframe with needed columns for team-stats
        stats_df = [ home_team['id'], home_team['abbreviation'], home_team['full_name'], games_df['home_team_score'], 
                     visitor_team['id'], visitor_team['abbreviation'], visitor_team['full_name'],games_df['visitor_team_score'] ]
        headers = ["home_id", "home_abb", "home_name", "home_score", "visitor_id", "visitor_abb", "visitor_name", "visitor_score"]
        stats_df = pd.concat(stats_df, axis=1, keys=headers)

        return stats_df

    def stats_processing(self,stats_df):
        stats_df.loc[( stats_df['home_score'] < stats_df['visitor_score'] ), 'home_score'] = 0
        stats_df.loc[( stats_df['home_score'] > stats_df['visitor_score'] ), 'home_score'] = 1
        stats_df.loc[( stats_df['home_score'] == 0 ),                     'visitor_score'] = 1
        stats_df.loc[( stats_df['home_score'] == 1 ),                     'visitor_score'] = 0

    def unique_ids(self,stats_df):
        home_id     = stats_df['home_id'].unique()
        visitor_id  = stats_df['visitor_id'].unique()
        teams_id = np.concatenate((home_id,visitor_id))
        teams_id = np.unique(teams_id)

        return teams_id

    def output(self,stats:pd.DataFrame):
        goal = self.goal
        path = str(Path.cwd())

        if goal == "csv":
            stats.to_csv(path+"/output.csv", index=False)

        elif goal == "json":
            stats.to_json(path+"/output.json", orient="records",)

        elif goal == "sqlite":
            cnx = sqlite3.connect('stats.db')
            stats.to_sql(name='stats', con=cnx)

        elif goal == "stdout":
            print(stats)
        
        else:
            raise ValueError("Possible --output parameters: csv, json, sqlite, stdout (default)")
        


def main():
    
    arg = sys.argv[1:]
    if not arg:
        raise ValueError("No arguments. Try again. Possible arguments: 'grouped-teams', 'players-stats' and 'teams-stats'")
    
    try:
        data=Data(arg)
    except:
        raise TypeError("Try again. Possible arguments: 'grouped-teams', 'players-stats' and 'teams-stats'")

    data.validate()

    if arg[0] == "grouped-teams":
        data.grouped_teams()
    elif arg[0] == "players-stats":
        data.players_stats()
    else:
        data.teams_stats()


if __name__ == "__main__":
    main()
