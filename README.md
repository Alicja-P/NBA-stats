# NBA-stats
## A NBA data processing script created with Python
Script processes data from external API about NBA related data and can give information about
* teams grouped by their division
* the tallest and the heaviest player with a given name
* won and lost games statistics for a given season (optionaly storing)

## Technologies
Project is created with:
* Python 3.9.7
* pandas 1.3.4
* numpy 1.20.3

## Examples of usage
Script should be executed from a command line with specified inputs:

* **teams grouped by their division**  
  python script.py grouped-teams

* **the tallest and the heaviest player with a given name**  
  python script.py players-stats --name 'player name'

* **won and lost games statistics for a given season (optionaly storing)**  
  python script.py teams-stats --season 'year of 1979-current' --output 'file format' (optional)

  --output option is optional and if missing a default option is printing the results in the console (without saving results).  
  Possible --output parameters are:
  - csv - save stats in csv format
  - json - save stats in json format
  - sqlite - save stats to sqlite database
  - stdout - print the results in the console (without saving results)
