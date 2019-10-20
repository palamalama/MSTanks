#!/usr/bin/python
import math 
import json
import socket
import logging
import binascii
import struct
import argparse
import random
import time
import numpy as np

current_milli_time = lambda: int(round(time.time() * 1000))
import sys


class ServerMessageTypes(object):
	TEST = 0
	CREATETANK = 1
	DESPAWNTANK = 2
	FIRE = 3
	TOGGLEFORWARD = 4
	TOGGLEREVERSE = 5
	TOGGLELEFT = 6
	TOGGLERIGHT = 7
	TOGGLETURRETLEFT = 8
	TOGGLETURRETRIGHT = 9
	TURNTURRETTOHEADING = 10
	TURNTOHEADING = 11
	MOVEFORWARDDISTANCE = 12
	MOVEBACKWARSDISTANCE = 13
	STOPALL = 14
	STOPTURN = 15
	STOPMOVE = 16
	STOPTURRET = 17
	OBJECTUPDATE = 18
	HEALTHPICKUP = 19
	AMMOPICKUP = 20
	SNITCHPICKUP = 21
	DESTROYED = 22
	ENTEREDGOAL = 23
	KILL = 24
	SNITCHAPPEARED = 25
	GAMETIMEUPDATE = 26
	HITDETECTED = 27
	SUCCESSFULLHIT = 28
    
	strings = {
		TEST: "TEST",
		CREATETANK: "CREATETANK",
		DESPAWNTANK: "DESPAWNTANK",
		FIRE: "FIRE",
		TOGGLEFORWARD: "TOGGLEFORWARD",
		TOGGLEREVERSE: "TOGGLEREVERSE",
		TOGGLELEFT: "TOGGLELEFT",
		TOGGLERIGHT: "TOGGLERIGHT",
		TOGGLETURRETLEFT: "TOGGLETURRETLEFT",
		TOGGLETURRETRIGHT: "TOGGLETURRENTRIGHT",
		TURNTURRETTOHEADING: "TURNTURRETTOHEADING",
		TURNTOHEADING: "TURNTOHEADING",
		MOVEFORWARDDISTANCE: "MOVEFORWARDDISTANCE",
		MOVEBACKWARSDISTANCE: "MOVEBACKWARDSDISTANCE",
		STOPALL: "STOPALL",
		STOPTURN: "STOPTURN",
		STOPMOVE: "STOPMOVE",
		STOPTURRET: "STOPTURRET",
		OBJECTUPDATE: "OBJECTUPDATE",
		HEALTHPICKUP: "HEALTHPICKUP",
		AMMOPICKUP: "AMMOPICKUP",
		SNITCHPICKUP: "SNITCHPICKUP",
		DESTROYED: "DESTROYED",
		ENTEREDGOAL: "ENTEREDGOAL",
		KILL: "KILL",
		SNITCHAPPEARED: "SNITCHAPPEARED",
		GAMETIMEUPDATE: "GAMETIMEUPDATE",
		HITDETECTED: "HITDETECTED",
		SUCCESSFULLHIT: "SUCCESSFULLHIT"
	}
    
	def toString(self, id):
		if id in self.strings.keys():
			return self.strings[id]
		else:
			return "??UNKNOWN??"


class ServerComms(object):
	'''
	TCP comms handler
	
	Server protocol is simple:
	
	* 1st byte is the message type - see ServerMessageTypes
	* 2nd byte is the length in bytes of the payload (so max 255 byte payload)
	* 3rd byte onwards is the payload encoded in JSON
	'''
	ServerSocket = None
	MessageTypes = ServerMessageTypes()
	
	
	def __init__(self, hostname, port):
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ServerSocket.connect((hostname, port))

	def readTolength(self, length):
		messageData = self.ServerSocket.recv(length)
		while len(messageData) < length:
			buffData = self.ServerSocket.recv(length - len(messageData))
			if buffData:
				messageData += buffData
		return messageData

	def readMessage(self):
		'''
		Read a message from the server
		'''
		messageTypeRaw = self.ServerSocket.recv(1)
		messageLenRaw = self.ServerSocket.recv(1)
		messageType = struct.unpack('>B', messageTypeRaw)[0]
		messageLen = struct.unpack('>B', messageLenRaw)[0]
		
		if messageLen == 0:
			messageData = bytearray()
			messagePayload = {'messageType': messageType}
		else:
			messageData = self.readTolength(messageLen)
			logging.debug("*** {}".format(messageData))
			messagePayload = json.loads(messageData.decode('utf-8'))
			messagePayload['messageType'] = messageType
			
		logging.debug('Turned message {} into type {} payload {}'.format(
			binascii.hexlify(messageData),
			self.MessageTypes.toString(messageType),
			messagePayload))
		return messagePayload
		
	def sendMessage(self, messageType=None, messagePayload=None):
		'''
		Send a message to the server
		'''
		message = bytearray()
		
		if messageType is not None:
			message.append(messageType)
		else:
			message.append(0)
		
		if messagePayload is not None:
			messageString = json.dumps(messagePayload)
			message.append(len(messageString))
			message.extend(str.encode(messageString))
			    
		else:
			message.append(0)
		
		logging.debug('Turned message type {} payload {} into {}'.format(
			self.MessageTypes.toString(messageType),
			messagePayload,
			binascii.hexlify(message)))
		return self.ServerSocket.send(message)


# Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
parser.add_argument('-H', '--hostname', default='127.0.0.1', help='Hostname to connect to')
parser.add_argument('-p', '--port', default=8052, type=int, help='Port to connect to')
parser.add_argument('-t', '--team', default='BIGJEFF', help='Bot Team')
args = parser.parse_args()

# Set up console logging
if args.debug:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)


def PolarCoordinates(origin,target):
	deltaX = -origin["X"]+target["X"]
	deltaY = -origin["Y"]+target["Y"]
	
	distance = math.sqrt(deltaX*deltaX + deltaY*deltaY)
	angle = 0
	if(deltaY != 0):
		if deltaX<0:
			if deltaY>0:
				angle = (180+math.atan(deltaY/-deltaX)*180/math.pi + 360)%360
			else:	
				angle = (90+math.atan(-deltaX/-deltaY)*180/math.pi )%360
		else:
			if deltaY>0:
				angle = (math.atan(deltaX/deltaY)*180/math.pi + 270)%360
			else:	
				angle = (math.atan(deltaX/-deltaY)*180/math.pi )%360
	else:
		if deltaX > 0:
			angle = 90
		elif deltaX < 0: 
			angle = 270

	return {"distance":distance,"angle":angle}

def GoToLocation(gameServer,origin, destination):
	coordinates = PolarCoordinates(origin,destination)
	if(coordinates["distance"] <= 3):
		gameServer.sendMessage(ServerMessageTypes.STOPMOVE)
		return True
	gameServer.sendMessage(ServerMessageTypes.TURNTOHEADING,{"Amount":coordinates["angle"]})
	gameServer.sendMessage(ServerMessageTypes.TOGGLEFORWARD)
	return False
def AveragePosition(origin, target):
	X = (origin["X"] + target["X"])/2
	Y = (origin["Y"] + target["Y"])/2
	return {"X":X,"Y":Y}

def NearestThing(origin,thingsDict):
	distances = []
	for key in thingsDict.keys():
		deltaX = -origin["X"] + thingsDict[key]["X"]
		deltaY = -origin["Y"] + thingsDict[key]["Y"]
		distance = math.sqrt(deltaX*deltaX+deltaY*deltaY)
		distances.append(distance)
	min_idx = np.argmin(distances)
	return list(thingsDict.keys())[min_idx]

def NoFriendlyFire(tankKey):
	tankInfo = global_state.friends[tankKey]
	for key in global_state.friends.keys():
		if(key != tankKey):
			coordinates = PolarCoordinates(tankInfo,global_state.friends[key])
			angle = math.sqrt((coordinates["angle"]-tankInfo["TurretHeading"])**2)
			requiredAngle = math.atan(10/(coordinates["distance"]-4.5))*180/math.pi
			if angle < requiredAngle : 
				return False
	return True

def enemyPosition(target):
    x = target["X"]
    y= target["Y"]
    return x,y
def HitMoving(gameserver, origin, target):
    x = origin["X"]
    y = origin["Y"]
    xt1,yt1 = enemyPosition(target)
    time.sleep(0.4)
    xt2, yt2 = enemyPosition(target)
    direction = (yt2-yt1)/(xt2-xt1)
    tankv = 9.4628
    bulletv = 10
    t = ((bulletv*(xt1 - x)) + (2*tankv *(np.sin(direction))*(yt1-y)))/(bulletv*tankv*np.cos(direction)-(bulletv**2)+(tankv**2)*((np.sin(direction))**2))
    tanalpha = (tankv*t*np.sin(direction)- (yt1-y))/(tankv*t*np.cos(direction)-(xt1-x))
    alpha = np.arctan(tanalpha) * 180/np.pi
    return alpha

# Connect to game server
GameServer1 = ServerComms(args.hostname, args.port)
GameServer2 = ServerComms(args.hostname, args.port)
GameServer3 = ServerComms(args.hostname, args.port)
GameServer4 = ServerComms(args.hostname, args.port)

# Spawn our tank
print("Creating Tank Team: " + args.team)
GameServer1.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.team+":Frank"})
GameServer2.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.team+":Amy"})
GameServer3.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.team+":Bert"})
GameServer4.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.team+":Chris"})

input_streams = [GameServer1,GameServer2,GameServer3,GameServer4]

class GlobalState():
	def __init__(self):
		self.enemies = {}
		self.friends = {}
		self.ammoPickups = {}
		self.healthPickups = {}
		self.health = {}
		self.last_refresh = current_milli_time()
		self.kills = {
			args.team+":Frank":False,
			args.team+":Amy":False,
			args.team+":Bert":False,
			args.team+":Chris":False,
			"":False
		}
	
	def take_message(self, message, sender=""):
		# this method incorporates a message into the global state
		message["timestamp"] = current_milli_time()
		try:
			if message.get("Type",0) == "Tank":
				if message["Name"].split(":")[0] == args.team:
					self.friends[message["Id"]] = message
				else:
					self.enemies[message["Id"]] = message
			elif message.get("Type",0) == "AmmoPickup":
				self.ammoPickups[message["Id"]] = message
			elif message.get("Type",0) == "HealthPickup":
				self.healthPickups[message["Id"]] = message
			elif message.get("messageType",0) == 24:
				self.kills[sender] = True
			else:
				pass
		except:
			pass
	
	def prune(self):
		self.dictPrune(self.friends)
		self.dictPrune(self.enemies)
		self.dictPrune(self.ammoPickups)
		self.dictPrune(self.healthPickups)
		self.dictPrune(self.health)
				
	def dictPrune(self, dictionary, data_ttl = 1000):
		for key, val in list(dictionary.items()): 
			if val["timestamp"] + data_ttl < current_milli_time():
				del dictionary[key]
	
global_state = GlobalState()

def search_alg(stream, tank):
	at_center = GoToLocation(stream,tank,{"X":0,"Y":0})
	stream.sendMessage(ServerMessageTypes.TOGGLETURRETLEFT)


#ACTUAL GAME AFTER INITIALISATION
import threading
def GetInfo(stream,name):
	while True:
		start = current_milli_time()
		message = stream.readMessage()
		global_state.take_message(message,name)
		global_state.prune()
		delta = current_milli_time() - start
	
def randomsearch_ollie(gameserver):
    coordinates = np.array(([0,75], [35,0], [-35,0], [0,-50]))
    pick = np.random.randint(0,4)
    coordinates = coordinates[pick]
    coordinates = {"X":str(coordinates[0]), "Y":coordinates[1]}
    GoToLocation(gameserver, gameserver.friends,coordinates)
    
def tankController(stream, name):
	while True:
		for key in list(global_state.friends.keys()):
			if global_state.friends[key]["Name"] == name:
				infinity = {"distance":10000000,"angle":0}

				me = global_state.friends[key]
				goals = {1:{"X":0,"Y":110},2:{"X":0,"Y":-110}}

				nearest_goal = NearestThing(me,goals)
				goal_coords = PolarCoordinates(me,goals[nearest_goal])
				
				nearest_enemy = ""
				enemy_coords = infinity
				if global_state.enemies != {}:
					nearest_enemy = NearestThing(me,global_state.enemies)
					enemy_coords = PolarCoordinates(me,global_state.enemies[nearest_enemy])

				allies = global_state.friends.copy()
				del allies[key]
				nearest_ally = ""
				ally_coords = infinity
				if allies != {}:
					nearest_ally = NearestThing(me,allies)
					ally_coords = PolarCoordinates(me,allies[nearest_ally])
				nearest_ammo = ""
				ammo_coords = infinity
				if global_state.ammoPickups != {} :
					nearest_ammo = NearestThing(me,global_state.ammoPickups)
					ammo_coords = PolarCoordinates(me,global_state.ammoPickups[nearest_ammo])

				nearest_HP = ""
				hp_coords = infinity
				if global_state.healthPickups != {}:
					nearest_HP = NearestThing(me,global_state.healthPickups)
					hp_coords = PolarCoordinates(me,global_state.healthPickups[nearest_HP])
				#print(global_state.healthPickups)
				#print(nearest_HP)
				#if global_state.healthPickups != {}:
				#	print(global_state.healthPickups[nearest_HP])
				#MOVE AROUND CONTROL		
				try:
					if global_state.kills[name]:
						if me["Health"] == 1 and hp_coords["distance"] < 10:
							GoToLocation(stream,me,global_state.healthPickups[nearest_HP])
							stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(hp_coords['angle'])})
							print(me["Name"] + " - SCORED - HP COLLECT")
						
						elif me["Ammo"] < 2 and ammo_coords["distance"] < 15:
							GoToLocation(stream,me,global_state.ammoPickups[nearest_ammo])
							stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(ammo_coords['angle'])})
							print(me["Name"] + " - SCORED - AMMO COLLECT")
						
						else:	
							print(me["Name"] + " - SCORED - GOING HOME")
							arrived = GoToLocation(stream,me,goals[nearest_goal])
							stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(goal_coords['angle'])})
							if arrived:
								global_state.kills[name] = False
					elif me["Health"] == 1:
						if global_state.healthPickups != {}:
							if hp_coords["distance"] < ally_coords["distance"]:
								print(me["Name"] + " - NO HEALTH - GETTING HEALTH", hp_coords["distance"])
								if GoToLocation(stream,me,global_state.healthPickups[nearest_HP]):
									del global_state.healthPickups[nearest_HP]
							else:
								print(me["Name"] + " - NO HEALTH - SUICIDE ALLY CLOSEST")
								GoToLocation(stream,me,AveragePosition(me,allies[nearest_ally]))
						else:
							print(me["Name"] + " - NO HEALTH - SUICIDE")
							GoToLocation(stream,me,allies[nearest_ally])
					elif me["Ammo"] < 2 and global_state.ammoPickups != {}:
						print(me["Name"] + " - NO AMMO - GETTING AMMO")
						GoToLocation(stream,me,global_state.ammoPickups[nearest_ammo])
					else:
						if allies[nearest_ally]["Health"] == 1:
							print(me["Name"] + " - NOTHING TO DO - SUICIDE")
							GoToLocation(stream,me,AveragePosition(me,allies[nearest_ally])) 
						elif global_state.ammoPickups != {} and global_state.healthPickups != {}:
							if ammo_coords["distance"] < hp_coords["distance"]:
								print(me["Name"] + " - NOTHING TO DO - GETTING AMMO CLOSEST")
								if GoToLocation(stream,me,global_state.ammoPickups[nearest_ammo]):
									del global_state.ammoPickups[nearest_ammo]
							else:
								print(me["Name"] + " - NOTHING TO DO - GETTING HP CLOSEST")
								if GoToLocation(stream,me,global_state.healthPickups[nearest_HP]):
									del global_state.ammoPickups[nearest_HP]
						elif global_state.ammoPickups != {}:
							if GoToLocation(stream,me,global_state.ammoPickups[nearest_ammo]):
								del global_state.ammoPickups[nearest_ammo]
							print(me["Name"] + " - NOTHING TO DO - GETTING AMMO")
						elif global_state.healthPickups != {}:
							if GoToLocation(stream,me,global_state.healthPickups[nearest_HP]):
								del global_state.healthPickups[nearest_HP]
							print(me["Name"] + " - NOTHING TO DO - GETTING HP")
						elif global_state.enemies != {}:
							print(me["Name"] + " - NOTHING TO DO - ENEMY WATCH")
							GoToLocation(stream,me,{"X":0,"Y":0})
						else:
							print(me["Name"] + " - NOTHING TO DO - ABSOLUTELY NOTHING IN VIEW")
							GoToLocation(stream,me,{"X":0,"Y":0})
				except Exception as e:
					print(e)	
				
				try:
					if global_state.friends[nearest_ally]["Health"] == 1:
						print(me["Name"] + " - KILLING ALLY ")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':ally_coords["angle"]})
						stream.sendMessage(ServerMessageTypes.FIRE)
					elif global_state.enemies != {}:
						print(me["Name"] + " - KILLING ENEMY ")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':enemy_coords["angle"]})
						stream.sendMessage(ServerMessageTypes.FIRE)
						
								
					 
				except Exception as e:
					print(e)	


				time.sleep(0.1)
"""
				if global_state.kills[name]:
					if me["Health"] == 1 and hp_coords["distance"] < 10:
						GoToLocation(stream,me,global_state.healthPickups[nearest_HP])
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(hp_coords['angle'])})
						print(me["Name"] + " - SCORED - HP COLLECT")
					
					elif me["Ammo"] < 2 and ammo_coords["distance"] < 15:
						GoToLocation(stream,me,global_state.ammoPickups[nearest_ammo])
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(ammo_coords['angle'])})
						print(me["Name"] + " - SCORED - AMMO COLLECT")
					
					else:	
						print(me["Name"] + " - SCORED - GOING HOME")
						arrived = GoToLocation(stream,me,goals[nearest_goal])
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(goal_coords['angle'])})
						if arrived:
							global_state.kills[name] = False
					if allies[nearest_ally]["Health"] == 1 and ally_coords["distance"] < 40:
						print(me["Name"] + " - BONUS - ALLY MURDER")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':ally_coords["angle"]})
						stream.sendMessage(ServerMessageTypes.FIRE) 
					elif global_state.enemies != {}:
						print(me["Name"] + " - BONUS - ENEMY SHOOT")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(enemy_coords['angle'])})
						if NoFriendlyFire(key):
							stream.sendMessage(ServerMessageTypes.FIRE)
						
						
				elif global_state.friends[key]["Ammo"] == 0:
					if me["Health"] == 1 and ally_coords["distance"] < 40:
						print(me["Name"] + " - NO AMMO - SUICIDE")
						GoToLocation(stream,me,allies[nearest_ally])
					elif global_state.ammoPickups != {}:
						print(me["Name"] + " - NO AMMO - GETTING AMMO")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(ammo_coords['angle'])})
						GoToLocation(stream,me,global_state.ammoPickups[nearest_ammo])
					else:
						print(me["Name"] + " - NO AMMO - FINDING AMMO")
						search_alg(stream, me)

				elif "The Snitch has Been Spotted" == "True":
					print("Should chase the snitch")
	
				elif global_state.enemies != {}:
					if allies[nearest_ally]["Health"] == 1 and ally_coords["distance"] < 40:
						print(me["Name"] + " - KILLING - MURDER ALLY")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':ally_coords["angle"]})
						stream.sendMessage(ServerMessageTypes.FIRE)
					else:
						print(me["Name"] + " - KILLING - ENEMY SHOOT", enemy_coords["angle"])
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(enemy_coords['angle'])})
						if NoFriendlyFire(key):
							stream.sendMessage(ServerMessageTypes.FIRE)
						GoToLocation(stream,me,global_state.healthPickups[nearest_HP])	
						
				else:
					if allies[nearest_ally]["Health"] == 1 and ally_coords["distance"] < 40:
						print(me["Name"] + " - DEFAULT - MURDER ALLY")
						stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':ally_coords["angle"]})
						stream.sendMessage(ServerMessageTypes.FIRE)
					else:
						print(me["Name"] + " - DEFAULT - FIND STUFF")
						search_alg(stream, global_state.friends[key])
"""

	
t1 = threading.Thread(target=GetInfo, args=(GameServer1,args.team+":Frank",))
t1.start()
t2 = threading.Thread(target=GetInfo, args=(GameServer2,args.team+":Amy",))
t2.start()
t3 = threading.Thread(target=GetInfo, args=(GameServer3,args.team+":Bert",))
t3.start()
t4 = threading.Thread(target=GetInfo, args=(GameServer4,args.team+":Chris",))
t4.start()

# Tank threads
FrankThread = threading.Thread(target=tankController, args=(GameServer1,args.team+":Frank",))
FrankThread.start()
AmyThread = threading.Thread(target=tankController, args=(GameServer2,args.team+":Amy",))
AmyThread.start()
BertThread = threading.Thread(target=tankController, args=(GameServer3,args.team+":Bert",))
BertThread.start()
ChrisThread = threading.Thread(target=tankController, args=(GameServer4,args.team+":Chris",))
ChrisThread.start()


