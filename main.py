# UNUSED. MORE PRACTICAL TO SPLIT EACH MODULE INTO INDIVIDUAL EXECUTABLES INSTEAD OF TRYING TO MANAGE USER INTERACTION
# EXTERNALLY. EACH INDIVIDUAL EXECUTABLE CAN BE RAN WHEN READY

# This is the entry point for the Mexican Train aid. This will be called when the user uploads a picture to the website
# to process the picture and build the train with the highest dot count and most dominoes.
# This will be turned into an executable that will be called by the front facing web app when the user submits an
# image to be processed.

from dotenv import load_dotenv  # Getting environment
import os               # Image retrieval and logging work

load_dotenv("config.env")
log_level = os.getenv("LOG_LEVEL")
userTimeout = os.getenv("TIMEOUT")
debug = os.getenv("DEBUG")

import json             # Interprocess comms
import time             # Waiting on user input
import logging          # Helpful for getting information
import trainBuilder
import imageProcessor

userApprovalPath = r".\comms\userApproved"      # To check if user has approved dominoes to be submitted
rawImgPath = r".\images\Dominoes.JPG"           # Hard coded because it should always be the same
# userTimeout = 180       # Max time program will wait for user to submit final domino pool in seconds
# debug = True           # Conditional "compile"


def __main__():
    imageProcessor.processRawImage(rawImgPath)

    # Program will wait here until web app indicates that user has submitted dominoes for processing or times out
    rawDominoes = extractDominoes()

    highestTrain, longestTrain = trainBuilder.buildTrain(rawDominoes, 9)
    print(f"Highest train: {highestTrain}\nLongest Train: {longestTrain}")


def userApproved():
    timeOut = 0
    if debug:
        open(userApprovalPath, "w")
    while not os.path.exists(userApprovalPath) and timeOut < userTimeout:
        time.sleep(1)
        timeOut += 1
    return True if timeOut < userTimeout else False


if __name__ == '__main__':
    __main__()
