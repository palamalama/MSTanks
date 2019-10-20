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
	print("my coordinates",origin["X"],origin["Y"])
	print("origin, heading",origin["Heading"])
	print("desired heading",coordinates["angle"])
	if(coordinates["distance"] <= 3):
		gameServer.sendMessage(ServerMessageTypes.STOPMOVE)
		return True
	gameServer.sendMessage(ServerMessageTypes.TURNTOHEADING,{"Amount":coordinates["angle"]})
	gameServer.sendMessage(ServerMessageTypes.TOGGLEFORWARD)
	return False

def NearestThing(origin,thingsDict):
	distances = []
	for key in thingsDict.keys():
		deltaX = -origin["X"] + thingsDict[key]["X"]
		deltaY = -origin["Y"] + thingsDict[key]["Y"]
		distance = math.sqrt(deltaX*deltaX+deltaY*deltaY)
		distances.append(distance)
	min_idx = np.argmin(distances)
	return list(thingsDict.keys())[min_idx]

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
				print("###################### MESSAGE #################")
				print(message)
		except:
			pass
# 			print("############ MESSAGE NOT PROCESSED ###############")
# 			print(message)
# 			print("##################################################")
	
	def prune(self):
		self.dictPrune(self.friends)
		self.dictPrune(self.enemies)
		self.dictPrune(self.ammoPickups)
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
	print("starting Info Thread")
	while True:
		start = current_milli_time()
		message = stream.readMessage()
		global_state.take_message(message,name)
		global_state.prune()
		delta = current_milli_time() - start
		
def tankController(stream, name):
	print("starting Tank Controller")
	while True:
		for key in list(global_state.friends.keys()):
			if global_state.friends[key]["Name"] == name:
				if global_state.kills[name]:
					## If you have killed go score the point
					goals = {1:{"X":0,"Y":110},2:{"X":0,"Y":-110}}
					nearest_goal = NearestThing(global_state.friends[key],goals)
					arrived = GoToLocation(stream,global_state.friends[key],goals[nearest_goal])
					if arrived:
						global_state.kills[name] = False
				elif (global_state.friends[key]["Ammo"] == 0) and (global_state.ammoPickups != {}):
					## If you have no ammo and know where ammo is go get it
					nearest_ammo = NearestThing(global_state.friends[key],global_state.ammoPickups)
					GoToLocation(stream,global_state.friends[key],global_state.ammoPickups[nearest_ammo])
				elif (global_state.friends[key]["Ammo"] == 0) and (global_state.ammoPickups == {}):
					## If you have no ammo, but don't know where ammo is make a random search
					search_alg(stream, global_state.friends[key])
				elif global_state.enemies != {}:  
					## If there are emenies go get them!
					#tracks and SHOOTS the enemy
					nearest_enemy = NearestThing(global_state.friends[key],global_state.enemies)
					info = PolarCoordinates(global_state.friends[key],global_state.enemies[nearest_enemy])
					stream.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(info['angle'])})
					dist = PolarCoordinates(global_state.friends[key],global_state.enemies[nearest_enemy])["distance"]
					if dist < 20:
						stream.sendMessage(ServerMessageTypes.FIRE)
					#tracks and FOLLOW the enemy
					nearestEnemy = NearestThing(global_state.friends[key],global_state.enemies) 
					GoToLocation(stream,global_state.friends[key],global_state.enemies[nearestEnemy])
				else:
					search_alg(stream, global_state.friends[key])
				
#                else:
#					GoToLocation(stream,global_state.friends[key],{"X":0,"Y":0})
		time.sleep(0.3)

	
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

def main():
	while True:
#	#		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': str((["TurretHeading"] + 20)%360)})
##		print(sorted(["Name: {0:s}, X: {1:.2f}, Y: {2:.2f}".format(v["Name"], v["X"], v["Y"]) for k, v in list(global_state.enemies.items())]))
##		print(sorted(["Name: {0:s}, X: {1:.2f}, Y: {2:.2f}".format(v["Name"], v["X"], v["Y"]) for k, v in list(global_state.friends.items())]))
#		
#		if not list(global_state.enemies.items()):
#			pass
#		else:
#			k_en, v_en = list(global_state.enemies.items())[0]
#			k_us, v_us = list(global_state.friends.items())[0]
#			info = polarCoordinates(v_us,v_en)
#			print(info)
#			GameServer1.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount':int(info['angle'])})
#			GameServer1.sendMessage(ServerMessageTypes.FIRE)
#            
            
		time.sleep(0.1)

main()