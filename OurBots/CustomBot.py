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
#import numpy as np

current_milli_time = lambda: int(round(time.time() * 1000))
import sys
from curses import wrapper

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
parser.add_argument('-n', '--name', default='SEXY:I_KNOW_IT', help='Name of bot')
args = parser.parse_args()

# Set up console logging
if args.debug:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)


def polarCoordinates(origin,target):
	deltaX = -origin["X"]+target["X"]
	deltaY = -origin["Y"]+target["Y"]
	
	distance = math.sqrt(deltaX*deltaX + deltaY*deltaY)
	print("your distance: ",distance)
	angle = 0
	print("dX:",deltaX,"dY:",deltaY)
	if(deltaY != 0):
		if deltaX<0:
			if deltaY>0:
				angle = (math.atan(-deltaX/deltaY)*180/math.pi + 360)%360
			else:	
				angle = (90+math.atan(-deltaY/-deltaX)*180/math.pi )%360
		else:
			if deltaY>0:
				angle = (math.atan(-deltaX/deltaY)*180/math.pi + 360)%360
			else:	
				angle = (180+math.atan(deltaX/-deltaY)*180/math.pi )%360
	else:
		if deltaX > 0:
			angle = 90
		elif deltaX < 0: 
			angle = 270

	print("your angle:", angle)
	return {"distance":distance,"angle":angle}

# Connect to game server
GameServer1 = ServerComms(args.hostname, args.port)
GameServer2 = ServerComms(args.hostname, args.port)
GameServer3 = ServerComms(args.hostname, args.port)
GameServer4 = ServerComms(args.hostname, args.port)

# Spawn our tank
logging.info("Creating tank with name '{}'".format(args.name))
GameServer1.sendMessage(ServerMessageTypes.CREATETANK, {'Name': "BigJeff:Frank"})
GameServer2.sendMessage(ServerMessageTypes.CREATETANK, {'Name': "BigJeff:Amy"})
GameServer3.sendMessage(ServerMessageTypes.CREATETANK, {'Name': "BigJeff:Bert"})
GameServer4.sendMessage(ServerMessageTypes.CREATETANK, {'Name': "BigJeff:Chris"})

input_streams = [GameServer1,GameServer2,GameServer3,GameServer4]

global_state = {
	"tanks":{},
	"ammoPickups":{},
	"healthPickups":{}
}


def messageToGlobal(message):
	try:
		message_type = message["Type"]
		if message_type == "Tank":
			message["timestamp"] = current_milli_time()
			global_state["tanks"][message["Id"]] = message
	# 	elif message_type == "AmmoPickup":
	# 		print("Ammo message:", message)
	# 		message["timestamp"] = current_milli_time()
	# 		global_state["ammoPickups"].append(message)
	# 	elif message_type == "HealthPickup":
	# 		print("Health pickup message:", message)
	# 		message["timestamp"] = current_milli_time()
	# 		global_state["healthPickups"].append(message)
	except:
		print(message)
		
def pruneGlobalState(data_ttl = 400):         # 0.5 seconds time to live
	for k in global_state.keys():
		for key, val in list(global_state[k].items()):
			if val["timestamp"] + data_ttl < current_milli_time():
				del global_state[k][key]

#ACTUAL GAME AFTER INITIALISATION
import threading
def GetInfo(stream):
	print("starting Info Thread")
	while True:
		start = current_milli_time()
		message = stream.readMessage()
		messageToGlobal(message)
		pruneGlobalState()
		delta = current_milli_time() - start


t1 = threading.Thread(target=GetInfo, args=(GameServer1,))
t1.start()
t2 = threading.Thread(target=GetInfo, args=(GameServer2,))
t2.start()
t3 = threading.Thread(target=GetInfo, args=(GameServer3,))
t3.start()
t4 = threading.Thread(target=GetInfo, args=(GameServer4,))
t4.start()
state = "ROTATE"

def print_separator():
	print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")

def main():
	while True:
	#		GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': str((["TurretHeading"] + 20)%360)})
		print(sorted(["Name: {0:s}, X: {1:.2f}, Y: {2:.2f}".format(v["Name"], v["X"], v["Y"]) for k, v in list(global_state["tanks"].items())]))
		time.sleep(0.1)

<<<<<<< HEAD:OurBots/Random.py
main()
"""
message = {}
resources = []
myInfo = {}
def ResourceView():
	global message 
	global resources
	if "Type" in message:
		if message["Type"] == "AmmoPickup":
			for resource in range(0,len(resources)):
				if resource == message:
					resources
def Move():
	global message 
	if "Type" in message:
		if "Name" in message:
			if message["Name"] == 'SEXY:I_KNOW_IT': 
				myInfo = message
				if nearestResource != {}:
					print("Chasing the ammo")
					GameServer.sendMessage(ServerMessageTypes.TOGGLEFORWARD)
				else:
V					GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': str((message["TurretHeading"] + 20)%360)})

while True:
	global message = GameServer.readMessage()
	global message = GameServer.readMessage()

	
	NearestResource()
	Move() 

"""
=======
main()
>>>>>>> 4fcbe9ba244c142ea1dc1d8cc2139ad8397d13cc:OurBots/CustomBot.py
