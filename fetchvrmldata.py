import requests
from requests_futures.sessions import FuturesSession
import time
import json
import logging

class PlayerListParser:
	def __init__(self):
		self.playerCount = 0
		self.playerIDs = []
		self.teams = []
		self.names = []
		self.countries = []

	def parse(self, data):
		parsedData = json.loads(data.decode('utf8'))
		playersData = parsedData["players"]

		if "total" in parsedData:
			self.playerCount = parsedData["total"]

		for player in playersData:
			if not player["country"] in ['AL','AD','AT','AZ','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','GE','DE','GR','HU','IS','IE', 'IT','KZ','XK','LV','LI','LT','LU','MK','MT','MD','MC','ME','NL','NO','PL','PT','RO','RU','SM','RS','SK', 'SI','ES','SE','CH','TR','UA','GB','VA', 'JE', 'RU']:
				continue

			self.countries.append(player["country"])
			self.playerIDs.append(player["playerID"])
			self.teams.append(player["teamID"])
			if "playerName" in player:
				self.names.append(str(player["playerName"]).replace('\\', ''))
			else:
				self.names.append("No Name")


class PlayerParser:
	def __init__(self):
		self.discordID = None
		self.logo = None

	def parse(self, data):
		parsedData = json.loads(data)
		playerData = parsedData["user"]

		if "discordID" in playerData:
			self.discordID = playerData["discordID"]
		if "userLogo" in playerData:
			self.logo = playerData["userLogo"]


class TeamListParser:
	def __init__(self):
		self.teamIDs = []
		self.teamNames = []
		self.teamLogos = []
		self.teamPositions = []
		self.teamDivisions = []
		self.noMoreData = False

	def parse(self, data):
		parsedData = json.loads(data)
		teamsData = parsedData["teams"]

		if len(teamsData) < 100:
			self.noMoreData = True

		for team in teamsData:
			self.teamIDs.append(team["teamID"])
			self.teamLogos.append(team["teamLogo"])
			self.teamDivisions.append(team["divisionName"])
			self.teamPositions.append(team["rank"])
			teamName = str(team["teamName"]).replace('\\', '') #Not sure if this is actually still needed when using the API instead of scraping from html...
			self.teamNames.append(teamName)


def scrape_players(logger):
	logger.info("Start scraping player data")

	playerListParser = PlayerListParser()
	url = "https://api.vrmasterleague.com/EchoArena/Players?posMin="
	numberOfPlayers = 2
	counter = 1
	while counter < numberOfPlayers:
		playerListParser.playerCount = 0
		response = requests.get(url + str(counter))
		if response.status_code == 429:
			#was rate limited, wait until the rate limit is reset and try again
			time.sleep(float(response.headers["X-RateLimit-Reset-After"]))
			continue
		playerListParser.parse(response.content)
		numberOfPlayers = playerListParser.playerCount
		counter += 100

	logger.info("Total number of players: " + str(numberOfPlayers))
	logger.info("Number of EU players: " + str(len(playerListParser.playerIDs)))

	session = FuturesSession(max_workers=16)
	futures = []
	for playerID in playerListParser.playerIDs:
		futures.append(session.get("https://api.vrmasterleague.com/Players/" + playerID))

	playerData = {}
	for i, playerID in enumerate(playerListParser.playerIDs):
		response = futures[i].result()

		if response.status_code != 200:
			logger.info("error fetching user: " + response.content.decode('utf8'))
			print(response.status_code)
			print(response.headers)

		playerParser = PlayerParser()
		playerParser.parse(response.content.decode('utf8'))
		if not playerParser.discordID or playerParser.discordID == "Unlinked":
			continue

		logger.info(playerParser.discordID)
		playerData[playerParser.discordID] = {"teamID": playerListParser.teams[i], "name": playerListParser.names[i], "country": playerListParser.countries[i], "logo": playerParser.logo}

	logger.info("Scraped all player data")

	with open('playerdata.json', 'w') as outfile:
		json.dump(playerData, outfile)


def scrape_teams(logger):
	logger.info("Start scraping team data")

	teamListParser = TeamListParser()
	url = "https://api.vrmasterleague.com/EchoArena/Standings?region=EU&rankMin="
	counter = 1
	while not teamListParser.noMoreData:
		response = requests.get(url + str(counter))
		if response.status_code == 429:
			#was rate limited, wait until the rate limit is reset and try again
			time.sleep(float(response.headers["X-RateLimit-Reset-After"]))
			continue
		teamListParser.parse(response.content.decode('utf8'))
		counter += 100
		#time.sleep(1)

	teamData = {}
	for i, teamID in enumerate(teamListParser.teamIDs):
		teamData[teamID] = {'position': teamListParser.teamPositions[i], 'name': teamListParser.teamNames[i], 'logo': teamListParser.teamLogos[i], 'division': teamListParser.teamDivisions[i]}

	logger.info("Scraped all team data")

	with open('teamsdata.json', 'w') as outfile:
		json.dump(teamData, outfile)

