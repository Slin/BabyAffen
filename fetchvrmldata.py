import requests
from requests_futures.sessions import FuturesSession
import time
from html.parser import HTMLParser
import json
import logging

class PlayerListParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isInPlayerCount = False
		self.isInTable = False
		self.isInTableRow = False
		self.isInCountryCell = False
		self.isInPlayerCell = False
		self.isInPlayerNameCell = False
		self.didHaveName = False
		self.isInTeamCell = False
		self.isEUPlayer = False

		self.playerCount = 0
		self.players = []
		self.teams = []
		self.names = []
		self.countries = []

	def handle_starttag(self, tag, attrs):
		if tag == "div" and len(attrs) > 0 and len(attrs[0]) > 0 and attrs[0][1] == "players-list-header-count":
			self.isInPlayerCount = True

		if self.isInCountryCell and tag == "img":
			if attrs[2][1] in ['AL','AD','AT','AZ','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','GE','DE','GR','HU','IS','IE', 'IT','KZ','XK','LV','LI','LT','LU','MK','MT','MD','MC','ME','NL','NO','PL','PT','RO','RU','SM','RS','SK', 'SI','ES','SE','CH','TR','UA','GB','VA', 'JE', 'RU']:
				self.isEUPlayer = True
				self.countries.append(str(attrs[2][1]))

		if self.isInPlayerCell and tag == "a" and self.isEUPlayer:
			self.players.append(str(attrs[0][1]))

		if self.isInTeamCell and tag == "a" and self.isEUPlayer:
			self.teams.append(str(attrs[0][1]))

		if self.playerCount > 0 and tag == "tbody":
			self.isInTable = True

		if self.isInTable and tag == "tr" and attrs[0][1].startswith("vrml_table_row"):
			self.isInTableRow = True

		if self.isInTable and tag == "td" and attrs[0][1] == "country_cell":
			self.isInCountryCell = True

		if self.isInTable and tag == "td" and attrs[0][1] == "player_cell":
			self.isInPlayerCell = True

		if self.isInTable and tag == "td" and attrs[0][1] == "team_cell":
			self.isInTeamCell = True

		if self.isInPlayerCell and tag == "span":
			self.isInPlayerNameCell = True

	def handle_endtag(self, tag):
		if tag == "div" and self.isInPlayerCount:
			self.isInPlayerCount = False

		if tag == "td" and self.isInCountryCell:
			self.isInCountryCell = False

		if tag == "td" and self.isInPlayerCell:
			self.isInPlayerCell = False

		if tag == "td" and self.isInTeamCell:
			self.isInTeamCell = False

		if tag == "tbody" and self.isInTable:
			self.isInTable = False

		if tag == "tr" and self.isInTableRow:
			self.isInTableRow = False
			self.isEUPlayer = False

		if tag == "span" and self.isInPlayerNameCell:
			self.isInPlayerNameCell = False
			if not self.didHaveName and self.isEUPlayer:
				self.names.append("No Name")

	def handle_data(self, data):
		if self.isInPlayerCount:
			numbers = [int(s) for s in str(data).split() if s.isdigit()]
			if len(numbers) > 0:
				self.playerCount = numbers[0]

		if self.isInPlayerNameCell and self.isEUPlayer:
			self.didHaveName = True
			self.names.append(str(data).replace('\\', ''))


class PlayerParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.foundData = False
		self.isInsideTag = False

		self.discordID = None
		self.logo = None

	def handle_starttag(self, tag, attrs):
		if self.foundData and tag == "td" and not self.discordID:
			self.isInsideTag = True

		if tag == "img" and len(attrs) > 1 and attrs[1][1] == "player_logo":
			self.logo = attrs[0][1]

	def handle_data(self, data):
		if self.isInsideTag:
			self.discordID = str(data)
			self.isInsideTag = False

		if data == "Discord":
			self.foundData = True


class TeamListParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isInTeamName = False
		self.isInTeamPosition = False
		self.isInTeamDivision = False
		self.teamIDs = []
		self.teamNames = []
		self.teamLogos = []
		self.teamPositions = []
		self.teamDivisions = []

	def handle_starttag(self, tag, attrs):
		if tag == "td" and len(attrs) > 0 and attrs[0][1] == "pos_cell":
			self.isInTeamPosition = True

		if tag == "td" and len(attrs) > 0 and attrs[0][1] == "div_cell":
			self.isInTeamDivision = True

		if tag == "a" and len(attrs) > 1 and attrs[1][1] == "team_link":
			self.teamIDs.append(str(attrs[0][1]))

		if tag == "img" and len(attrs) > 1 and attrs[1][1] == "team_logo":
			self.teamLogos.append(str(attrs[0][1]))

		if tag == "span" and len(attrs) > 0 and attrs[0][1] == "team_name":
			self.isInTeamName = True

		if tag == "img" and self.isInTeamDivision:
			self.teamDivisions.append(str(attrs[1][1]))

	def handle_endtag(self, tag):
		if self.isInTeamPosition and tag == "td":
			self.isInTeamPosition = False

		if self.isInTeamDivision and tag == "td":
			self.isInTeamDivision = False

		if self.isInTeamName and tag == "span":
			self.isInTeamName = False

	def handle_data(self, data):
		if self.isInTeamPosition:
			self.teamPositions.append(int(data))

		if self.isInTeamName:
			self.teamNames.append(str(data).replace('\\', ''))


def scrape_players(logger):
	logger.info("Start scraping player data")

	playerListParser = PlayerListParser()
	url = "https://vrmasterleague.com/EchoArena/Players/List/?posMin="
	numberOfPlayers = 1
	counter = 0
	while counter < numberOfPlayers:
		playerListParser.playerCount = 0
		response = requests.get(url + str(counter))
		playerListParser.feed(str(response.content))
		numberOfPlayers = playerListParser.playerCount
		counter += 99
		#time.sleep(1)

	logger.info("Total number of players: " + str(numberOfPlayers))
	logger.info("Number of EU players: " + str(len(playerListParser.players)))

	session = FuturesSession(max_workers=4)
	futures = []
	for player in playerListParser.players:
		futures.append(session.get("https://vrmasterleague.com" + player))

	playerData = {}
	for i, player in enumerate(playerListParser.players):
		response = futures[i].result()

		if str(response.content).find("error") != -1:
			logger.info("error fetching user: " + str(response.content))

		playerParser = PlayerParser()
		playerParser.feed(str(response.content))
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
	url = "https://vrmasterleague.com/EchoArena/Standings/bMvm-nOAdg-ofBzJfEr3ag2?rankMin="
	numberOfTeams = 110
	counter = 0
	while counter < numberOfTeams:
		response = requests.get(url + str(counter))
		teamListParser.feed(str(response.content))
		counter += 99
		#time.sleep(1)

	teamData = {}
	for i, teamID in enumerate(teamListParser.teamIDs):
		teamData[teamID] = {'position': teamListParser.teamPositions[i], 'name': teamListParser.teamNames[i], 'logo': teamListParser.teamLogos[i], 'division': teamListParser.teamDivisions[i]}

	logger.info("Scraped all team data")

	with open('teamsdata.json', 'w') as outfile:
		json.dump(teamData, outfile)

