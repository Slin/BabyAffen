import discord
import json
import logging
from colorhash import ColorHash
from fetchvrmldata import scrape_players, scrape_teams
from discord.ext import commands, tasks

class BotActions:
	def __init__(self, client, logger):
		self.client = client
		self.playerData = []
		self.teamsData = []
		self.logger = logger


	def load_player_data(self):
		with open('playerdata.json') as file:
			self.playerData = json.load(file)


	def load_teams_data(self):
		with open('teamsdata.json') as file:
			self.teamsData = json.load(file)


	def update_teams_data(self):
		scrape_teams(self.logger)
		self.load_teams_data()


	def update_player_data(self):
		scrape_players(self.logger)
		self.load_player_data()


	#Create new team and division roles for everyone / update them if they changed
	async def update_roles(self):
		for guild in self.client.guilds:
			await self.update_roles_for_guild(guild)


	#Create new team and division roles for everyone in the guild / update them if they changed
	async def update_roles_for_guild(self, guild):
		self.logger.info("start updating user roles in " + guild.name)

		if len(self.playerData) == 0:
			self.logger.info("no player data. aborting...")
			return

		if len(self.teamsData) == 0:
			self.logger.info("no teams data. aborting...")
			return

		clientRolePosition = 0
		for role in guild.roles:
			if role.name == 'Echo EU - VRML Bridge':
				clientRolePosition = role.position
				break

		divisionRoles = []
		rolesToDelete = []
		for role in guild.roles:
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

		for member in guild.members:
			playerDiscordHandle = member.name + "#" + member.discriminator
			player = None
			if playerDiscordHandle in self.playerData:
				player = self.playerData[playerDiscordHandle]
			if player and player["teamID"] in self.teamsData:
				team = self.teamsData[player["teamID"]]
				teamName = team["name"]
				teamDivision = 'VRML ' + team["division"]

				self.logger.info("Handling player " + playerDiscordHandle + " from team " + teamName)

				playerRolesToAdd = []
				playerRolesToDelete = []
				memberRoleNames = [x.name for x in member.roles]
				if not teamName in memberRoleNames:
					teamRole = next((x for x in guild.roles if x.name == teamName), None)
					if not teamRole:
						teamRole = await guild.create_role(name=teamName, hoist=True, mentionable=True)
						self.logger.info("created new role for team: " + teamName)
					playerRolesToAdd.append(teamRole)
					for role in member.roles:
						if role.position < clientRolePosition and role.position != 0 and not role in divisionRoles:
							playerRolesToDelete.append(role)

				if not teamDivision in memberRoleNames:
					tierRole = next((x for x in guild.roles if x.name == teamDivision), None)
					if not tierRole:
						tierRole = await guild.create_role(name=teamDivision, hoist=False, mentionable=True)
					playerRolesToAdd.append(tierRole)
					for role in member.roles:
						if role in divisionRoles:
							playerRolesToDelete.append(role)

				if len(playerRolesToAdd) > 0:
					self.logger.info("updating: " + playerDiscordHandle + " - " + teamName + " - " + teamDivision)
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
					self.logger.info("removing vrml roles for " + playerDiscordHandle)
					await member.remove_roles(*playerVRMLRoles)

		for roleName in rolesToDelete:
			self.logger.info("deleting role: " + roleName)
			role = next((x for x in guild.roles if x.name == roleName), None)
			await role.delete()

		self.logger.info("finished updating user roles")


	#Update the order of team roles to match the VRML EU ranking
	async def update_ranking(self):
		for guild in self.client.guilds:
			await self.update_roles_for_guild(guild)


	#Update the order of team roles in guild to match the VRML EU ranking
	async def update_ranking_for_guild(self, guild):
		self.logger.info("start updating team ranking")

		if len(self.teamsData) == 0:
			self.logger.info("no teams data. aborting...")
			return

		clientRolePosition = 0
		botRole = None
		for role in guild.roles:
			if role.name == 'Echo EU - VRML Bridge':
				botRole = role
				clientRolePosition = role.position
				print("bot position: " + str(clientRolePosition))
				break

		vrmlRoles = {}
		rolesToRemove = []
		for role in guild.roles:
			print("Role: " + role.name + " - " + str(role.position))
			if role.position < clientRolePosition and role.position != 0:
				if role.name in vrmlRoles:
					rolesToRemove.append(role)
				else:
					vrmlRoles[role.name] = role

		newTeamsList = []
		for key in self.teamsData:
			team = self.teamsData[key]
			teamName = team['name']
			if teamName in vrmlRoles:
				newTeamsList.append(vrmlRoles[teamName])

		divisions = ["VRML Master", "VRML Diamond", "VRML Gold", "VRML Silver", "VRML Bronze"]
		for division in divisions:
			if division in vrmlRoles:
				newTeamsList.append(vrmlRoles[division])

		for role in vrmlRoles:
			if not vrmlRoles[role] in newTeamsList:
				rolesToRemove.append(vrmlRoles[role])

		newTeamsList.reverse()
		teamPositionDict = {}
		for position, role in enumerate(newTeamsList):
			teamPositionDict[role] = position

		#This hopefully reorders everything, so they are not all on position 1 and hopefully also increases the bots role position in case of new roles being added
		if len(newTeamsList) > 0:
			await newTeamsList[0].edit(position=0)

		print(teamPositionDict)
		await guild.edit_role_positions(positions=teamPositionDict)

		for role in rolesToRemove:
			self.logger.info("deleting unexpected role: " + role.name)
			await role.delete()

		self.logger.info("finished updating team ranking")


	#Update the master tier team role colors
	async def update_colors(self):
		for guild in self.client.guilds:
			await self.update_colors_for_guild(guild)


	#Update the master tier team role colors for guild
	async def update_colors_for_guild(self, guild):
		self.logger.info("start updating colors")

		if len(self.teamsData) == 0:
			self.logger.info("no teams data. aborting...")
			return

		clientRolePosition = 0
		for role in guild.roles:
			if role.name == 'Echo EU - VRML Bridge':
				clientRolePosition = role.position
				break

		allRoles = {}
		for role in guild.roles:
			if role.position < clientRolePosition and role.position != 0:
				allRoles[role.name] = role

		for key in self.teamsData:
			team = self.teamsData[key]
			if team['name'] in allRoles:
				if team['division'] == 'Master': #is top 10 team
					color = ColorHash(team['name'])
					await allRoles[team['name']].edit(colour=discord.Colour.from_rgb(color.rgb[0], color.rgb[1], color.rgb[2]))
				else:
					await allRoles[team['name']].edit(colour=discord.Colour.default())

		self.logger.info("finished updating colors")


	#Deletes all bot created team and division roles from the guild
	async def clear_roles_for_guild(self, guild):
		self.logger.info("start clearing roles")

		clientRolePosition = 0
		for role in guild.roles:
			if role.name == 'Echo EU - VRML Bridge':
				clientRolePosition = role.position
				break

		rolesToDelete = [role for role in guild.roles if role.position < clientRolePosition and role.position != 0]
		for role in rolesToDelete:
			self.logger.info("delete role: " + role.name)
			await role.delete()
		self.logger.info("finished clearing roles")




AUTH_TOKEN = ""
with open('auth.json') as authFile:
	data = json.load(authFile)
	AUTH_TOKEN = data['token']

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

#Log to file
logFileHandler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logFileHandler.setFormatter(formatter)
logger.addHandler(logFileHandler)

#Log to console
logConsoleHandler = logging.StreamHandler()
logConsoleHandler.setFormatter(formatter)
logger.addHandler(logConsoleHandler)

intents = discord.Intents.none()
intents.guilds = True
intents.members = True
intents.messages = True
client = discord.Client(intents=intents)

actions = BotActions(client, logger)

@client.event
async def on_ready():
	logger.info('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
	if message.author == client.user:
		return

	if not type(message.author) is discord.Member or not message.author.guild_permissions.administrator:
		return

	#Downloads new data and updates roles and users accordingly
	if message.content.startswith('!update_all'):
		await message.channel.send("started scraping players")
		actions.update_player_data()
		await message.channel.send("finished scraping players")

		await message.channel.send("started scraping teams")
		actions.update_teams_data()
		await message.channel.send("finished scraping teams")

		await message.channel.send("started updating roles")
		await actions.update_roles_for_guild(message.guild)
		await message.channel.send("finished updating roles")

		await message.channel.send("started updating ranking")
		await actions.update_ranking_for_guild(message.guild)
		await message.channel.send("finished updating ranking")

		await message.channel.send("started updating colors")
		await actions.update_colors_for_guild(message.guild)
		await message.channel.send("finished updating colors")

	#Create new team and division roles for everyone / update them if they changed
	if message.content.startswith('!update_roles'):
		await message.channel.send("started updating roles")
		await actions.update_roles_for_guild(message.guild)
		await message.channel.send("finished updating roles")

	#Update the order of team roles to match the VRML EU ranking
	if message.content.startswith('!update_ranking'):
		await message.channel.send("started updating ranking")
		await actions.update_ranking_for_guild(message.guild)
		await message.channel.send("finished updating ranking")

	#Update the master tier team colors
	if message.content.startswith('!update_colors'):
		await message.channel.send("started updating colors")
		await actions.update_colors_for_guild(message.guild)
		await message.channel.send("finished updating colors")

	#Deletes all team and division roles from the server
	if message.content.startswith('!clear_roles'):
		await message.channel.send("started clearing roles")
		await actions.clear_roles_for_guild(message.guild)
		await message.channel.send("finished clearing roles")

	#Download latest teams data
	if message.content.startswith('!scrape_teams'):
		await message.channel.send("started scraping teams")
		actions.update_teams_data()
		await message.channel.send("finished scraping teams")

	#Download latest players data
	if message.content.startswith('!scrape_players'):
		await message.channel.send("started scraping players")
		actions.update_player_data()
		await message.channel.send("finished scraping players")

	if message.content.startswith('!users_for_role'):
		roleToFind = message.content[15:].strip()
		for member in message.guild.members:
			for role in member.roles:
				if role.name == roleToFind:
					await message.channel.send("user with role " + roleToFind + ": " + member.name)


#Automatically assign team and division role for new members when joining the server
@client.event
async def on_member_join(member):
	await actions.update_roles_for_guild(member.guild)


#@tasks.loop(hours=2)
#async def update_rankings():
#	actions.update_teams_data()
#	await actions.update_ranking()
#	await actions.update_colors()

#@update_rankings.before_loop
#async def before_update_rankings():
#	await client.wait_until_ready()


#@tasks.loop(hours=24)
#async def update_players():
#	actions.update_player_data()
#	await actions.update_roles()

#@update_players.before_loop
#async def before_update_players():
#	await client.wait_until_ready()

#actions.update_teams_data()

actions.load_teams_data()
actions.load_player_data()

#update_players.start()
#update_rankings.start()
client.run(AUTH_TOKEN)
