import discord
import json
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logFileHandler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logFileHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(logFileHandler)

playerData = {}
with open('playerdata.json') as file:
	playerData = json.load(file)

teamsData = []
with open('teamsdata.json') as file:
	teamsData = json.load(file)
teamsData.append({'name': 'Master', 'position': len(teamsData)})
teamsData.append({'name': 'Diamond', 'position': len(teamsData)})
teamsData.append({'name': 'Gold', 'position': len(teamsData)})
teamsData.append({'name': 'Silver', 'position': len(teamsData)})
teamsData.append({'name': 'Bronze', 'position': len(teamsData)})

AUTH_TOKEN = ""
with open('auth.json') as authFile:
	data = json.load(authFile)
	AUTH_TOKEN = data['token']

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
	print('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
	if message.author == client.user:
		return

	if message.content.startswith('$team'):
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

	if message.content.startswith('$update_roles'):
		divisionRoles = []
		rolesToDelete = []
		for role in message.guild.roles:
			if role.name.startswith('VRML '):
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
				teamName = "VRML " + player["teamName"].replace('\\', '')
				teamDivision = "VRML " + player["teamDivision"]

				playerRolesToAdd = []
				playerRolesToDelete = []
				memberRoleNames = [x.name for x in member.roles]
				if not teamName in memberRoleNames:
					teamRole = next((x for x in message.guild.roles if x.name == teamName), None)
					if not teamRole:
						teamRole = await message.guild.create_role(name=teamName, hoist=True, mentionable=True)
					playerRolesToAdd.append(teamRole)
					for role in member.roles:
						if role.name.startswith('VRML ') and not role in divisionRoles:
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
				playerVRMLRoles = [x for x in member.roles if x.name.startswith('VRML ')]
				if len(playerVRMLRoles) > 0:
					print("removing vrml roles for " + playerDiscordHandle)
					await member.remove_roles(*playerVRMLRoles)

		for roleName in rolesToDelete:
			role = next((x for x in message.guild.roles if x.name == roleName), None)
			await role.delete()


	if message.content.startswith('$clear_roles'):
		for role in message.guild.roles:
			if role.name.startswith('VRML '):
				await role.delete()


	if message.content.startswith('$update_ranking'):
		vrmlRoles = {}
		for role in message.guild.roles:
			if role.name.startswith('VRML'):
				vrmlRoles[role.name] = role

		newTeamsData = []
		for team in teamsData:
			teamName = 'VRML ' + team['name'].replace('\\', '')
			if teamName in vrmlRoles:
				newTeamsData.append(team)
				print(team)

		teamPositionDict = {}
		for position, team in enumerate(newTeamsData):
			teamName = 'VRML ' + team['name'].replace('\\', '')
			if teamName in vrmlRoles:
				teamPositionDict[vrmlRoles[teamName]] = len(newTeamsData) - position

		print(teamPositionDict)
		await message.guild.edit_role_positions(positions=teamPositionDict)


	if message.content.startswith('$my_roles'):
		for role in message.guild.roles:
			print(role.name + " - " + str(role.position))


@client.event
async def on_member_join(member):
	playerDiscordHandle = member.name + "#" + member.discriminator
	player = None
	if playerDiscordHandle in playerData:
		player = playerData[playerDiscordHandle]

	if player:
		teamName = "VRML " + player["teamName"].replace('\\', '')
		teamDivision = "VRML " + player["teamDivision"]

		playerRolesToAdd = []
		teamRole = next((x for x in message.guild.roles if x.name == teamName), None)
		if not teamRole:
			teamRole = await message.guild.create_role(name=teamName, hoist=True, mentionable=True)
		playerRolesToAdd.append(teamRole)

		tierRole = next((x for x in message.guild.roles if x.name == teamDivision), None)
		if not tierRole:
			tierRole = await message.guild.create_role(name=teamDivision, hoist=False, mentionable=True)
		playerRolesToAdd.append(tierRole)

		if len(playerRolesToAdd) > 0:
			print("updating: " + playerDiscordHandle + " - " + teamName + " - " + teamDivision)
			await member.add_roles(*playerRolesToAdd)


client.run(AUTH_TOKEN)
