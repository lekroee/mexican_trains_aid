# This script, given a set of 12 dominos, builds all possible domino trains, according to the rules of Mexican Trains,
# and returns the train that has the most dots and the train that has the most dominos. Often this is the same train,
# however it could easily differ and strategy could call for a specific one.

from copy import deepcopy       # Necessary for storing all possible train combinations
from dotenv import load_dotenv  # Getting environment
import logging                  # Helpful for getting information
import os                       # Needed for logging to get environment variable for log level
import json

load_dotenv('config.env')
# Logging setup
log_level = os.getenv('LOG_LEVEL', 'ERROR').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.ERROR), format='%(message)s')
logger = logging.getLogger(__name__)

imgProcessorOutputPath = os.getenv('IMAGE_PROCESSOR_OUTPUT_PATH')
rootNumberPath = os.getenv('ROOT_NUM_PATH')
finalOutputPath = os.getenv('TRAIN_BUILDER_OUTPUT_PATH')


# This represents a single Domino with two numbers divided by a horizontal line. The numbers are internally called top
# and bottom for clarity's sake but referred to externally with the root number and other number. The root number of a
# domino can be changed according to the train being built so top and bottom will not be consistent.
# The class stores the two numbers, their sum, and the defined root number. These can only be accessed and modified
# with methods since the Dominoes numbers, and therefore sum, should never change. The root number may be redefined
# as many times as needed, but it is handled through the method call since it changes the positions of the numbers
# in the internally stored tuple for readability when the final train is built. The root domino is considered the first
# number in the tuple.
# Two dominoes are considered equal if the two numbers on the domino are the same, even if their root numbers differ.
# A Domino is represented by a tuple when printed. ex. (4, 2)
class Domino:
    def __init__(self, top, bottom):
        self.__pair = (top, bottom)
        self.__dotCount = top + bottom
        self.__rootNumber = None

    def __str__(self):
        return f"({self.__pair[0]}, {self.__pair[1]})"

    def __repr__(self):
        return f"({self.__pair[0]}, {self.__pair[1]})"

    def __eq__(self, otherObj):
        if isinstance(otherObj, Domino):
            return set(self.__pair) == set(otherObj.getPair())
        return False

    def __hash__(self):
        return hash(self.__pair)

    def setRootNumber(self, newRootNumber):
        if newRootNumber not in self.__pair:
            return
        if self.__pair[1] == newRootNumber:
            self.__pair = (self.__pair[1], self.__pair[0])
        self.__rootNumber = newRootNumber

    def getRootNumber(self):
        return self.__rootNumber

    def getPair(self):
        return self.__pair

    def getDotCount(self):
        return self.__dotCount

    def getOtherNumber(self, number):
        if number not in self.__pair:
            return None
        return self.__pair[0] if number == self.__pair[1] else self.__pair[1]


# This represents a chain of dominoes, "train", ordered according to matching sides. I played around with different ways
# of internally storing the dominoes and found that a list was the easiest way of thinking about it. It doesn't need
# to be incredibly memory efficient or processor efficient because the longest train possible is only 12 dominoes
# according to the rules of the game. Only one domino can be added to a Train at a time.
# The only data the Train maintains about itself is the dominoes and their order. You may ask a train what it's dot
# count or domino count is but that is calculated when asked instead of maintaining it. I had pretty much already
# written both those methods elsewhere in the file and then decided to make them internal to the Train class so that
# you could just ask the Train about itself instead of calling another function to figure it out.
# Individual dominoes cannot be accessed in the Train. You can ask the train if it has a certain domino, but you can't
# directly access them to figure what ones are in there.
# You can ask a Train to "reset" itself back to a certain domino you know is in the train.  When you reset the Train
# back a certain domino, it removes every domino after and including the specified domino. This was for building all of
# the possible combinations of Trains.
# A Train is represented with a list of dominoes (tuples) pointing to each other. The numbers should match up on either
# side of a tuple with the tuple next to it.
class Train:
    def __init__(self):
        self.__dominos = []

    def __str__(self):
        prettyTrainStr = ""
        for domino in self.__dominos:
            prettyTrainStr += str(domino) + " -> "
        return prettyTrainStr[:-4]

    def __repr__(self):
        prettyTrainStr = ""
        for domino in self.__dominos:
            prettyTrainStr += str(domino) + " -> "
        return prettyTrainStr[:-4]

    def __eq__(self, otherObj):
        if isinstance(otherObj, Train):
            return set(self.__dominos) == set(otherObj.__dominos)
        return False

    def __hash__(self):
        return hash((len(self.__dominos) * self.getDotCount() + self.getDominoCount()) * 71)

    def addDomino(self, newDomino):
        self.__dominos.append(newDomino)

    # This method rewrites the train to remove all dominos after and including the domino passed.
    # If no domino is passed, the train is erased completely.
    def reset(self, domino=None):
        if domino is None:
            self.__dominos = []
        elif domino not in self.__dominos:
            return
        else:
            self.__dominos = self.__dominos[:self.__dominos.index(domino)]

    def getDotCount(self):
        count = 0
        for domino in self.__dominos:
            count += domino.getDotCount()
        return count

    def getDominoCount(self):
        return len(self.__dominos)

    def getCopy(self):
        return deepcopy(self)

    def isInTrain(self, domino):
        return domino in self.__dominos


# This is the main method of this module. Pass a pool of dominos to this method and a number to start the train with
# and it will return two trains of all the possible ones you could make with the pool of dominos and specified start
# number: the train with the most dots and the train with the most dominoes.
# The dominoPool should be a set
def buildTrain():
    # CODE
    rootNumber = __getRootNumber()
    rawDominoes = __extractDominoes()
    dominoPool = __buildPool(rawDominoes)

    # INFO LOGGING
    logger.info("BEGIN BUILDTRAIN".center(40, '='))
    logger.info("---STARTING INFO---")
    logger.info(f"pool: {dominoPool}")
    rootDominoPool = _findRootDominos(dominoPool, rootNumber)
    logger.info(f"root num: {rootNumber}, root dominos: {rootDominoPool}")
    logger.info("")

    # CODE
    allTrains = __buildTrain_helper(dominoPool, rootNumber, Train(), set())
    allTrains = sorted(list(allTrains), key=lambda x: x.getDotCount(), reverse=True)
    finalTrain = allTrains[0]
    longestTrain = _findLongestTrain(allTrains)

    # INFO LOGGING
    logger.info(f"---HIGHEST DOT COUNT TRAIN, COUNT: {finalTrain.getDotCount()}---")
    logger.info(finalTrain)
    if finalTrain != longestTrain:
        logger.info(f"---LONGEST TRAIN, COUNT {longestTrain.getDotCount()}---")
        logger.info(longestTrain)
    else:
        logger.info("---LONGEST TRAIN SAME AS HIGHEST DOT COUNT---")
    logger.info("END BUILDTRAIN".center(40, '='))
    logging.info("\n")

    with open(finalOutputPath, "w+") as file:
        print("Most Pips:\t" + f"{finalTrain}", file=file)
        print("Longest:\t" + f"{longestTrain}", file=file)
    # CODE
    return finalTrain, longestTrain


# This is the helper method to the main method. This builds and returns all possible trains with the specified starting
# number and domino pool.
# Internal use only.
def __buildTrain_helper(dominoPool, rootNumber, train, allTrains):
    if len(dominoPool) == 0:
        allTrains.add(train.getCopy())
        return allTrains

    rootDominoPool = _findRootDominos(dominoPool, rootNumber)
    if len(rootDominoPool) == 0:
        allTrains.add(train.getCopy())
        return allTrains

    for rootDomino in rootDominoPool:
        train.addDomino(rootDomino)
        rootDomino.setRootNumber(rootNumber)
        newRootNumber = rootDomino.getOtherNumber(rootNumber)
        allTrains = __buildTrain_helper(_poolWithout(dominoPool, rootDomino), newRootNumber, train, allTrains)
        train.reset(rootDomino)
    return allTrains


# This method finds and returns the train with the most dominos given a set of trains.
# Mostly internal but could have an external use
def _findLongestTrain(trainPool):
    longestTrain = trainPool[0]
    for train in trainPool[1:]:
        if train.getDominoCount() > longestTrain.getDominoCount():
            longestTrain = train
    return longestTrain


# This method finds all possible dominos you could use to start or add to a Train given a pool of dominos and a root
# number. Used mainly in the buildTrain_helper.
# Mostly internal but could have an external use
def _findRootDominos(dominoPool, rootNumber):
    returnPool = set()
    for domino in dominoPool:
        if rootNumber in domino.getPair():
            returnPool.add(domino)
    return returnPool


# This method returns a pool of dominos with a specified domino removed. For example you have a pool of 12 dominos and
# it contains the domino with the numbers 5 and 7. You would pass the domino pool and specify you want to remove the
# (5, 7) domino and it would return all of the dominos except that one. Used in the buildTrain_helper.
# Mostly internal but could have an external use
def _poolWithout(dominoPool, dominoRemove):
    returnPool = set()
    for domino in dominoPool:
        if domino != dominoRemove:
            returnPool.add(domino)
    return returnPool


def __buildPool(rawDominoes):
    dominoPool = set()
    for domino in rawDominoes.values():
        dominoPool.add(Domino(domino[0], domino[1]))
    return dominoPool


def __extractDominoes():
    with open(imgProcessorOutputPath, "r") as file:
        return json.loads(file.read())


def __getRootNumber():
    with open(rootNumberPath, "r") as file:
        return int(file.read().strip())


# Run program
buildTrain()
