"""
Module myPlayerBrain: the sample Python AI.  Start with this project but write
your own code as this is a very simplistic implementation of the AI.

Created on January 15, 2013

@author: Windward Studios, Inc. (www.windward.net).

No copyright claimed - do anything you want with this code.
"""

import random
import simpleAStar
from calcdata import calc_data
from calcpath import calc_path
from api import units, map
from debug import printrap

from xml.etree import ElementTree as ET

NAME = "Zaphrod Beeblebrox"
SCHOOL = "The Diner at the Edge of the Universe"
TILE_WIDTH = 24
SCHOOL = "TDATEOTU"
data = None

class MyPlayerBrain(object):
    """The Python AI class.  This class must have the methods setup and gameStatus."""
    def __init__(self, name=NAME):
        self.name = name #The name of the player.
        
        #The player's avatar (looks in the same directory that this module is in).
        #Must be a 32 x 32 PNG file.
        try:
            avatar = open("MyAvatar.png", "rb")
            avatar_str = b''
            for line in avatar:
                avatar_str += line
            avatar = avatar_str
        except IOError:
            avatar = None # avatar is optional
        self.avatar = avatar
    
    def setup(self, gMap, me, allPlayers, companies, passengers, client):
        """
        Called at the start of the game; initializes instance variables.

        gMap -- The game map.
        me -- Your Player object.
        allPlayers -- List of all Player objects (including you).
        companies -- The companies on the map.
        passengers -- The passengers that need a lift.
        client -- TcpClient to use to send orders to the server.
        
        """
        self.gameMap = gMap
        self.players = allPlayers
        self.me = me
        self.companies = companies
        self.passengers = passengers
        self.client = client
        self.pickup = pickup = self.allPickups(me, passengers, allPlayers)

        # get the path from where we are to the dest.
        path = self.calculatePathPlus1(me, pickup[0].lobby.busStop)
        sendOrders(self, "ready", path, pickup)

    def gameStatus(self, status, playerStatus, players, passengers):
        """
        Called to send an update message to this A.I.  We do NOT have to send a response.

        status -- The status message.
        playerStatus -- The player this status is about. THIS MAY NOT BE YOU.
        players -- The status of all players.
        passengers -- The status of all passengers.

        """
        global data
        data = calc_data(self=self, status=status, playerStatus=playerStatus, players=players, passengers=passengers, data=data)
        move = calc_path(self=self, status=status, playerStatus=playerStatus, players=players, passengers=passengers, data=data)
        if move:
          sendOrders(self, *move)
        # bugbug - Framework.cs updates the object's in this object's Players,
        # Passengers, and Companies lists. This works fine as long as this app
        # is single threaded. However, if you create worker thread(s) or
        # respond to multiple status messages simultaneously then you need to
        # split these out and synchronize access to the saved list objects.

        try:
            # bugbug - we return if not us because the below code is only for
            # when we need a new path or our limo hits a bus stop. If you want
            # to act on other players arriving at bus stops, you need to
            # remove this. But make sure you use self.me, not playerStatus for
            # the Player you are updating (particularly to determine what tile
            # to start your path from).
            if playerStatus != self.me:
                return
            
            ptDest = None
            pickup = []
            
            if    status == "UPDATE":
                return
            elif (status == "PASSENGER_NO_ACTION" or
                  status == "NO_PATH"):
                if playerStatus.limo.passenger is None:
                    if len(pickup) == 0:
                        pickup = self.findCampsite(playerStatus, passengers, players)
                    else:
                        pickup = self.allPickups(playerStatus, passengers, players)
                    ptDest = pickup[0].lobby.busStop
                else:
                    ptDest = playerStatus.limo.passenger.destination.busStop
            elif (status == "PASSENGER_DELIVERED" or
                  status == "PASSENGER_ABANDONED"):
                if len(pickup) == 0:
                    pickup = self.findCampsite(playerStatus, passengers, players)
                else:    
                    pickup = self.allPickups(playerStatus, passengers, players)
                ptDest = pickup[0].lobby.busStop
            elif  status == "PASSENGER_REFUSED":
                ptDest = random.choice(filter(lambda c: c != playerStatus.limo.passenger.destination,
                    self.companies)).busStop
            elif (status == "PASSENGER_DELIVERED_AND_PICKED_UP" or
                  status == "PASSENGER_PICKED_UP"):
                pickup = self.allPickups(playerStatus, passengers, players)
                ptDest = playerStatus.limo.passenger.destination.busStop
            else:
                raise TypeError("unknown status %r", status)

            # get the path from where we are to the dest.
            path = self.calculatePathPlus1(playerStatus, ptDest)

            sendOrders(self, "move", path, pickup)
        except Exception as e:
            printrap ("somefin' bad, foo'!")
            raise e

    def calculateTime(self, me, path):
        count = 0
        speed = 0
        distance = 0.0
        for p in xrange(len(path)):
            if p >= 2:
                p1 = path[p-2]
                p3 = path[p]
                if p1[0] == p3[0] or p1[1] == p3[1]:
                    while distance < TILE_WIDTH:
                        speed = max(speed + 0.1,6)
                        distance += speed
                        count += 1
                else:
                    while distance < TILE_WIDTH:
                        speed = max(speed + 0.1,3)
                        distance += speed
                        count += 1
            else:
                while distance < TILE_WIDTH:
                        speed = max(speed + 0.1,6)
                        distance += speed
                        count += 1
            while distance > TILE_WIDTH:
                distance -= TILE_WIDTH
        return count
            
    def calculatePathPlus1 (self, me, ptDest):
        path = simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, ptDest)
        #list(self.gameMap.path(me.limo.tilePosition, ptDest))
        # add in leaving the bus stop so it has orders while we get the message
        # saying it got there and are deciding what to do next.
        if len(path) > 1:
            path.append(path[-2])
        return path

    def allPickups (self, me, passengers, players):
        pickup = [p for p in passengers if (not p in me.passengersDelivered and
                                            p != me.limo.passenger and
                                            p.car is None and
                                            p.lobby is not None and p.destination is not None)]
        paths = self.pickups(me,passengers,pickup,players)
        for player in players:
            opp = self.oppPickups(player,passengers,players)
            num = -1
            for i in range(len(paths)):
                if opp[0][0] == paths[i][0] and opp[0][1] < paths[i][1]:
                    num = i
                    break
            if num > -1:
                paths.pop(num)
        return [p[0] for p in paths]

    def oppPickups (self, me, passengers, players):
        pickup = [p for p in passengers if (not p in me.passengersDelivered and
                                            p != me.limo.passenger and
                                            p.car is None and
                                            p.lobby is not None and p.destination is not None)]
        paths = self.pickups(me,passengers,pickup,players)
        return paths
    
    def pickups (self, me, passengers, pickup, players):       
        paths = [(p,self.calculateTime(me,self.calculatePathPlus1(me,p.destination.busStop))
                  + self.calculateTime(me,self.calculatePathPlus1(me, p.lobby.busStop))) for p in pickup]
        paths.sort(key = lambda tup:tup[1])                    
        return paths
        
    def findCampsite(self, me, passengers, players):
        """ if all people we can pick up are in cars, where do we go to wait for them 
            returns a destination """
        passe = [(p, p.destination) for p in passengers if (not p in me.passengersDelivered
                                                            and  p.lobby is not None
                                                            and p.destination is not None)]
        # times is the soonest we could pick somebody up at a destination
        #times = [(max(self.gameMap.distance(me.car.tilePosition, p[1]),\
        #              self.gameMap.distance(p[0].car.tilePosition, p[1])), p[1]) for p in passe]
        #return min(times)[1]
        paths = self.pickups(me,passengers,pickup,players)
        return paths

def sendOrders(brain, order, path, pickup):
    """Used to communicate with the server. Do not change this method!"""
    xml = ET.Element(order)
    if len(path) > 0:
        brain.me.limo.path = path # update our saved Player to match new settings
        sb = [str(point[0]) + ',' + str(point[1]) + ';' for point in path]
        elem = ET.Element('path')
        elem.text = ''.join(sb)
        xml.append(elem)
    if len(pickup) > 0:
        brain.me.pickup = pickup # update our saved Player to match new settings
        sb = [psngr.name + ';' for psngr in pickup]
        elem = ET.Element('pick-up')
        elem.text = ''.join(sb)
        xml.append(elem)
    brain.client.sendMessage(ET.tostring(xml))
