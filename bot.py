import discord
import json
import logging
from colorhash import ColorHash
from fetchvrmldata import scrape_players, scrape_teams

AUTH_TOKEN = ""
with open('auth.json') as authFile:
	data = json.load(authFile)
	AUTH_TOKEN = data['token']

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logFileHandler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logFileHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(logFileHandler)

playerData = {}
def load_player_data():
	global playerData
	with open('playerdata.json') as file:
		playerData = json.load(file)

teamsData = []
def load_teams_data():
	global teamsData
	with open('teamsdata.json') as file:
		teamsData = json.load(file)
	teamsData.append({'name': 'VRML Master', 'position': len(teamsData)})
	teamsData.append({'name': 'VRML Diamond', 'position': len(teamsData)})
	teamsData.append({'name': 'VRML Gold', 'position': len(teamsData)})
	teamsData.append({'name': 'VRML Silver', 'position': len(teamsData)})
	teamsData.append({'name': 'VRML Bronze', 'position': len(teamsData)})


intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
	print('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
	global teamsData
	if message.author == client.user:
		return

	#Print some basic information about a team for any mentioned user
	if message.content.startswith('!team'):
		for member in message.mentions:
			playerDiscordHandle = member.name + "#" + member.discriminator
			player = None
			if playerDiscordHandle in playerData:
				player = playerData[playerDiscordHandle]
			if player:
				teamName = player["teamName"].replace('\\', '')
				await message.channel.send("Name: " + teamName + " - Division: " + player["teamDivision"] + " - MMR: " + str(player["teamMMR"]))
			else:
				await message.channel.send("Not in a team")


	if message.author.id != 329735546467385344:
		return

	clientRolePosition = 0
	for role in message.guild.roles:
		if role.name == 'Echo EU - VRML Bridge':
			clientRolePosition = role.position
			break

	#Create new team and division roles for everyone / update them if they changed
	if message.content.startswith('!update_roles'):
		divisionRoles = []
		rolesToDelete = []
		for role in message.guild.roles:
			if role.position < clientRolePosition and role.position != 0:
				rolesToDelete.append(role.name)
			if role.name == 'VRML Master':
				divisionRoles.append(role)
			if role.name == 'VRML Diamond':
				divisionRoles.append(role)
			if role.name == 'VRML Gold':
				divisionRoles.append(role)
			if role.name == 'VRML Silver':
				divisionRoles.append(role)
			if role.name == 'VRML Bronze':
				divisionRoles.append(role)

		for member in message.guild.members:
			playerDiscordHandle = member.name + "#" + member.discriminator
			player = None
			if playerDiscordHandle in playerData:
				player = playerData[playerDiscordHandle]
			if player:
				teamName = player["teamName"].replace('\\', '')
				teamDivision = 'VRML ' + player["teamDivision"]

				playerRolesToAdd = []
				playerRolesToDelete = []
				memberRoleNames = [x.name for x in member.roles]
				if not teamName in memberRoleNames:
					teamRole = next((x for x in message.guild.roles if x.name == teamName), None)
					if not teamRole:
						teamRole = await message.guild.create_role(name=teamName, hoist=True, mentionable=True)
					playerRolesToAdd.append(teamRole)
					for role in member.roles:
						if role.position < clientRolePosition and role.position != 0 and not role in divisionRoles:
							playerRolesToDelete.append(role)

				if not teamDivision in memberRoleNames:
					tierRole = next((x for x in message.guild.roles if x.name == teamDivision), None)
					if not tierRole:
						tierRole = await message.guild.create_role(name=teamDivision, hoist=False, mentionable=True)
					playerRolesToAdd.append(tierRole)
					for role in member.roles:
						if role in divisionRoles:
							playerRolesToDelete.append(role)

				if len(playerRolesToAdd) > 0:
					print("updating: " + playerDiscordHandle + " - " + teamName + " - " + teamDivision)
					await member.add_roles(*playerRolesToAdd)

				if len(playerRolesToDelete) > 0:
					await member.remove_roles(*playerRolesToDelete)

				if teamName in rolesToDelete:
					rolesToDelete.remove(teamName)

				if teamDivision in rolesToDelete:
					rolesToDelete.remove(teamDivision)
			else:
				playerVRMLRoles = [x for x in member.roles if x.position < clientRolePosition and x.position != 0]
				if len(playerVRMLRoles) > 0:
					print("removing vrml roles for " + playerDiscordHandle)
					await member.remove_roles(*playerVRMLRoles)

		for roleName in rolesToDelete:
			role = next((x for x in message.guild.roles if x.name == roleName), None)
			await role.delete()


	#Update the order of team roles to match the VRML EU ranking
	if message.content.startswith('!update_ranking'):
		vrmlRoles = {}
		for role in message.guild.roles:
			if role.position < clientRolePosition and role.position != 0:
				vrmlRoles[role.name] = role

		newTeamsData = []
		for team in teamsData:
			teamName = team['name'].replace('\\', '')
			if teamName in vrmlRoles:
				newTeamsData.append(team)

		teamPositionDict = {}
		for position, team in enumerate(newTeamsData):
			teamName = team['name'].replace('\\', '')
			if teamName in vrmlRoles:
				teamPositionDict[vrmlRoles[teamName]] = len(newTeamsData) - position

		print(teamPositionDict)

		await message.guild.edit_role_positions(positions=teamPositionDict)


	#Deletes all team and division roles from the server
	if message.content.startswith('!clear_roles'):
		print("clear roles")
		rolesToDelete = [role for role in message.guild.roles if role.position < clientRolePosition and role.position != 0]
		for role in rolesToDelete:
			print("delete role: " + role.name)
			await role.delete()


	if message.content.startswith('!update_color'):
		allRoles = {}
		for role in message.guild.roles:
			if role.position < clientRolePosition and role.position != 0:
				allRoles[role.name] = role

		for team in teamsData:
			if team['name'] in allRoles and team['position'] <= 10: #is top 10 team
				color = ColorHash(team['name'])
				await allRoles[team['name']].edit(colour=discord.Colour.from_rgb(color.rgb[0], color.rgb[1], color.rgb[2]))


	#Download latest teams data
	if message.content.startswith('!scrape_teams'):
		scrape_teams()
		load_teams_data()


	#Download latest players data
	if message.content.startswith('!scrape_players'):
		scrape_players()
		load_player_data()



#Automatically assign team and division role for new members when joining the server
@client.event
async def on_member_join(member):
	playerDiscordHandle = member.name + "#" + member.discriminator
	player = None
	if playerDiscordHandle in playerData:
		player = playerData[playerDiscordHandle]

	if player:
		teamName = player["teamName"].replace('\\', '')
		teamDivision = player["teamDivision"]

		guild = client.guilds[0]

		playerRolesToAdd = []
		teamRole = next((x for x in guild.roles if x.name == teamName), None)
		if not teamRole:
			teamRole = await guild.create_role(name=teamName, hoist=True, mentionable=True)
		playerRolesToAdd.append(teamRole)

		tierRole = next((x for x in guild.roles if x.name == teamDivision), None)
		if not tierRole:
			tierRole = await guild.create_role(name=teamDivision, hoist=False, mentionable=True)
		playerRolesToAdd.append(tierRole)

		if len(playerRolesToAdd) > 0:
			print("updating: " + playerDiscordHandle + " - " + teamName + " - " + teamDivision)
			await member.add_roles(*playerRolesToAdd)


client.run(AUTH_TOKEN)
