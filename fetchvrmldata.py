import requests
import time
from html.parser import HTMLParser
import json

#data = {"encrValue":"RXEzNy9vYi9tSXM90", "name":"Slin#8120"}
#url = "https://vrmasterleague.com/Services.asmx/GetPlayersByDiscordHandle"
#response = requests.post(url, data)
#print(response.content)

class PlayerListParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isInTable = False
		self.isInTableRow = False
		self.isInCountryCell = False
		self.isInPlayerCell = False
		self.isInTeamCell = False
		self.isEUPlayer = False

		self.playerCount = 0
		self.players = []
		self.teams = []

	def handle_starttag(self, tag, attrs):
		if self.isInCountryCell and tag == "img":
			if attrs[2][1] in ['AL','AD','AT','AZ','BY','BE','BA','BG','HR','CY','CZ','DK','EE','FI','FR','GE','DE','GR','HU','IS','IE', 'IT','KZ','XK','LV','LI','LT','LU','MK','MT','MD','MC','ME','NL','NO','PL','PT','RO','RU','SM','RS','SK', 'SI','ES','SE','CH','TR','UA','GB','VA']:
				self.isEUPlayer = True

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


	def handle_endtag(self, tag):
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

	def handle_data(self, data):
		if data.startswith("There are currently "):
			if data.endswith(" players in active teams."):
				self.playerCount = int(data[20:-25])


class PlayerParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.discordID = None
		self.foundData = False
		self.isInsideTag = False

	def handle_starttag(self, tag, attrs):
		if self.foundData and tag == "td" and not self.discordID:
			self.isInsideTag = True

	def handle_data(self, data):
		if self.isInsideTag:
			self.discordID = str(data)
			self.isInsideTag = False

		if data == "Discord":
			self.foundData = True


class TeamParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isInTeamName = False
		self.isInMMR = False
		self.teamName = None
		self.teamDivision = None
		self.teamMMR = 0

	def handle_starttag(self, tag, attrs):
		if tag == "div" and len(attrs) > 0 and attrs[0][1] == "title team-name":
			self.isInTeamName = True

		if tag == "div" and len(attrs) > 0 and attrs[0][1] == "team-mmr":
			self.isInMMR = True

		if tag == "img" and len(attrs) == 3 and attrs[1][1] == "team-division" and not self.teamDivision:
			self.teamDivision = str(attrs[2][1])

	def handle_endtag(self, tag):
		if self.isInTeamName and tag == "div":
			self.isInTeamName = False

		if self.isInMMR and tag == "div":
			self.isInMMR = False

	def handle_data(self, data):
		if self.isInTeamName and not self.teamName:
			self.teamName = str(data)

		if self.isInMMR:
			mmrSubstring = data[4:].strip()
			if not mmrSubstring.startswith("TBD"):
				self.teamMMR = int(mmrSubstring)

class TeamListParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isInTeamName = False
		self.isInTeamPosition = False
		self.teamNames = []
		self.teamPositions = []

	def handle_starttag(self, tag, attrs):
		if tag == "td" and len(attrs) > 0 and attrs[0][1] == "pos_cell":
			self.isInTeamPosition = True

		if tag == "span" and len(attrs) > 0 and attrs[0][1] == "team_name":
			self.isInTeamName = True

	def handle_endtag(self, tag):
		if self.isInTeamPosition and tag == "td":
			self.isInTeamPosition = False

		if self.isInTeamName and tag == "span":
			self.isInTeamName = False

	def handle_data(self, data):
		if self.isInTeamPosition:
			self.teamPositions.append(int(data))

		if self.isInTeamName:
			self.teamNames.append(str(data))


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
	time.sleep(5)

print("Total number of players: " + str(numberOfPlayers))
print("Number of EU players: " + str(len(playerListParser.players)))
playerData = {}
teamList = []
for i, player in enumerate(playerListParser.players):
	playerParser = PlayerParser()
	response = requests.get("https://vrmasterleague.com" + player)
	playerParser.feed(str(response.content))
	if not playerParser.discordID or playerParser.discordID == "Unlinked":
		continue

	playerData[playerParser.discordID] = {"team": playerListParser.teams[i]}
	if not playerListParser.teams[i] in teamList:
		teamList.append(playerListParser.teams[i])
	time.sleep(1)

teamData = {}
for team in teamList:
	teamParser = TeamParser()
	response = requests.get("https://vrmasterleague.com" + team)
	teamParser.feed(str(response.content))
	teamData[team] = {"name": teamParser.teamName, "division": teamParser.teamDivision, "mmr": teamParser.teamMMR}
	time.sleep(1)

for key in playerData:
	team = teamData[playerData[key]["team"]]
	del playerData[key]["team"]
	playerData[key]["teamName"] = team["name"]
	playerData[key]["teamDivision"] = team["division"]
	playerData[key]["teamMMR"] = team["mmr"]

print(playerData)

with open('playerdata.json', 'w') as outfile:
	json.dump(playerData, outfile)



teamListParser = TeamListParser()
url = "https://vrmasterleague.com/EchoArena/Standings/N2xDeWlHMGUvZGc90?rankMin="
numberOfTeams = 110
counter = 0
while counter < numberOfTeams:
	response = requests.get(url + str(counter))
	teamListParser.feed(str(response.content))
	counter += 99
	time.sleep(1)

teamData = []
for i, name in enumerate(teamListParser.teamNames):
	teamData.append({'position': teamListParser.teamPositions[i], 'name':name})
teamData = sorted(teamData, key=lambda k: k['position']) 

print(teamData)

with open('teamsdata.json', 'w') as outfile:
	json.dump(teamData, outfile)
