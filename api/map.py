"""
Module map: classes, functions and constants for working with the game map and
its contents (e.g. companies)
Created on January 15, 2013

@author: Windward Studios, Inc. (www.windward.net).

No copyright claimed - do anything you want with this code.
"""

from __future__ import print_function
from __future__ import division

import debug

DIRECTION = {"NORTH_SOUTH":0, "EAST_WEST":1, "INTERSECTION":2,
             "NORTH_UTURN":3, 'EAST_UTURN':4, 'SOUTH_UTURN':5, 'WEST_UTURN':6,
             'T_NORTH':7, 'T_EAST':8, 'T_SOUTH':9, 'T_WEST':10,
             'CURVE_NE':11, 'CURVE_NW':12, 'CURVE_SE':13, 'CURVE_SW':14}
"""The direction of the road. Do not change these numbers, they are used as an index into an array.

NORTH_SOUTH: Road running north/south.
EAST_WEST: Road running east/west.
INTERSECTION: A 4-way intersection.
NORTH_UTURN: A north/south road ended on the north side.
EAST_UTURN:   An east/west road ended on the east side.
SOUTH_UTURN: A north/south road ended on the south side.
WEST_UTURN:   An east/west road ended on the west side.
T_NORTH: A T junction where the | of the T is entering from the north.
T_EAST:  A T junction where the | of the T is entering from the east.
T_SOUTH: A T junction where the | of the T is entering from the south.
T_WEST:  A T junction where the | of the T is entering from the west.
CURVE_NE: A curve entered northward and exited eastward (or vice-versa).
CURVE_NW: A curve entered northward and exited westward (or vice-versa).
CURVE_SE: A curve entered southward and exited eastward (or vice-versa).
CURVE_SW: A curve entered southward and exited westward (or vice-versa).
"""

STOP_SIGNS = {"NONE": 0, "STOP_NORTH": 0x01, "STOP_EAST": 0x02,
              "STOP_SOUTH": 0x04, "STOP_WEST": 0x08}
"""Stop signs and signals for an intersection square."""

TYPE = ('PARK', 'ROAD', 'BUS_STOP', 'COMPANY')
"""The different types a MapSquare can be.

PARK: Nothing on this, does nothing, cannot be driven on.
ROAD: A road. The road DIRECTION determines which way cars can travel on the road.
BUS_STOP: A company's bus stop. This is where passengers are loaded and unloaded.
COMPANY: Company building. Nothing on this, does nothing, cannot be driven on.
"""


class Map(object):
    """The game map."""
    def __init__(self, element, companies):
        """Creates the game map from XML and a list of Companies.

        squares -- A 2-d list of MapSquares that represent each tile on the board.
        unitsPerTile -- The number of map units in a tile. Some points are in
            map units and some are in tile units.
        width -- the width of the map. Units are squares.
        height -- The height of the map. Units are squares.

        """
        self.width  = width  = int(element.get('width'))
        self.height = height = int(element.get('height'))
        self.unitsPerTile = int(element.get('units-tile'))
        squares = [[None for i in range(height)] for j in range(width)]
        for tileElement in element.findall('tile'):
            x = int(tileElement.get('x'))
            y = int(tileElement.get('y'))
            squares[x][y] = MapSquare(tileElement)
        for company in companies:
            squares[company.busStop[0]][company.busStop[1]].setCompany(company)
        self.squares = squares
        self.dist = {}
        
        locs = []
        for i in range(self.width):
          for j in range(self.height):
            this = self.squareOrDefault((i,j))
            if this and this.isDriveable():
              self.dist[(this,this)] = (0, None)
              for di,dj in ((0,1),(1,0),(-1,0),(0,-1)):
                other = self.squareOrDefault((i+di,j+dj))
                if other and other.isDriveable():
                  this.neighbors.append(other)
              if len(this.neighbors) != 2:
                locs.append(this)
        
        for loc in locs:
          for n in loc.neighbors:
            last = loc
            cur = n
            dist = 1
            while len(cur.neighbors) == 2:
              self.dist[(loc,cur)] = (dist, None if loc is last else last)
              self.dist[(cur,loc)] = (dist, None if loc is last else last)
              cur.intersect.append(loc)
              last, cur = cur, [next for next in cur.neighbors if next is not last][0]
              dist += 1
            self.dist[(loc,cur)] = (dist, None if loc is last else last)
        
        print("Starting FW")
        for i in locs:
          self.dist[(i,i)] = (0, None)
          for j in locs:
            if (i,j) not in locs:
              self.dist[(i,j)] = (float("inf"), None)
        for k in locs:
          for i in locs:
            for j in locs:
              if self.dist[(i, k)] + self.dist[(k, j)] < self.dist[(i, j)]:
                self.dist[(i,j)] = (self.dist[(i, k)] + self.dist[(k, j)], k)
        print("Finished FW")
    def distance(self, a, b):
      if type(a) is not MapSquare: a = self.squareOrDefault(a)
      if type(b) is not MapSquare: b = self.squareOrDefault(b)
      print("Calculating distance between %s and %s" % (a.loc, b.loc))
      if (a,b) not in self.dist:
        print("Unknown distance")
        if a is b:
          print("Same location")
          self.dist[(a,b)] = (0,None)
        if not a or not b:
          print("Inv  alid location")
          self.dist[(a,b)] = (float("inf"),None)
        print("a.neighbors = %s, b.neighbors = %s" % (a.neighbors, b.neighbors))
        if len(a.neighbors) == 2:
          best = (float("inf"), None)
          for n in a.intersect:
            print("Trying intersect %s" % (n.loc,))
            if self.distance(a,n) + self.distance(n,b) < best[0]:
              best = (self.distance(a,n) + self.distance(n,b), n)
          self.dist[(a,b)] = best
        elif len(b.neighbors) == 2:
          best = (float("inf"), None)
          for n in b.intersect:
            print("Trying intersect %s" % (n.loc,))
            if self.distance(a,n) + self.distance(n,b) < best[0]:
              best = (self.distance(a,n) + self.distance(n,b), n)
          self.dist[(a,b)] = best
      return self.dist[(a, b)][0]
    def path(self, a, b):
      if type(a) is not MapSquare: a = self.squareOrDefault(a)
      if type(b) is not MapSquare: b = self.squareOrDefault(b)
      print("Calculating path between %s and %s" % (a.loc, b.loc))
      if (a,b) not in self.dist:
        self.distance(a,b)
      if (a,b) not in self.dist:
        print("Cannot calculate distance")
        return None
      if a == b:
        print("This is the path")
        return (a.loc,)
      else:
        k = self.dist[(a,b)][1]
        if k is None:
          print("Neighbors")
          return (a.loc,b.loc)
        print("Calculate path between %s" % k)
        return self.path(a.loc,k.loc) + self.path(k.loc,b.loc)[1:]
    def squareOrDefault(self, point):
        """Return the requested point or None if off the map."""
        if (point[0] < 0 or point[1] < 0 or
            point[0] >= self.width or point[1] >= self.height):
            return None
        else:
            return self.squares[point[0]][point[1]]

class MapSquare(object):
    """A tile on the map. May contain a Company."""

    def __init__(self, element):
        """Create the MapSquare from XML.

        stopSigns -- Which sides of this tile have stop signs. None for none.
        signal -- Whether or not this square has a traffic signal on it.
        type -- The type of square this is (an element of TYPE).
        company -- The company for this tile. None unless this is a BUS_STOP.
        direction -- The direction of the road. None unless this is a ROAD or
            BUS_STOP.

        """
        self.type = element.get('type')
        self.x = int(element.get('x'))
        self.y = int(element.get('y'))
        self.loc = (self.x, self.y)
        self.neighbors = []
        self.intersect = []
        assert self.type in TYPE
        if self.isDriveable():
            self.direction = element.get('direction')
            assert self.direction in DIRECTION
            stops = element.get('stop-sign')
            if stops is None:
                self.stopSigns = STOP_SIGNS["NONE"]
            else:
                self.stopSigns = reduce(lambda x,y: x + STOP_SIGNS[y],
                                        [s.strip() for s in stops.split(',')],
                                        0)
            sig = element.get('signal')
            self.signal = (sig is not None and sig.lower() == 'true')
      
    def isDriveable(self):
        """True if the square can be driven on (e.g., its type is ROAD or BUS_STOP)."""
        return self.type == "ROAD" or self.type == "BUS_STOP"

    def setCompany(self, company):
        self.company = company

class Company(object):
    def __init__(self, element):
        """Creates a company on the map from an XML Element.

        name -- The name of the company.
        busStop -- The tile with the company's bus stop.
        passengers -- List of Passengers waiting at this company's bus stop.

        """
        self.name = element.get('name')
        self.busStop = ( int(element.get('bus-stop-x')), int(element.get('bus-stop-y')) )
        self.passengers = []

    def __str__(self):
        return "%s; %s" % (self.name, self.busStop)

    def __eq__(self, other):
        if isinstance(other, Company) and other.name == self.name:
            return True
        else:
            return False

def companiesFromXml(element):
    return [Company(e) for e in element.findall('company')]