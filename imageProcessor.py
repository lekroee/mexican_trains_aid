# This module is for processing images of dominos to return identified dominoes and their pips to be passed to
# other modules.
# Chat GPT was used to write much of this code.

# There is a lot of room for improvement. Thinking of running some parts of this multiple times with different
# parameters to whittle down the most common data and improve quality returned.

import cv2          # Image processing
import numpy as np  # Image processing
import json         # Dominoes output dumping
import os           # Image retrieval and logging work
import logging      # Helpful for getting information
from dotenv import load_dotenv  # Getting environment

load_dotenv('config.env')
# Logging setup
log_level = os.getenv('LOG_LEVEL', 'ERROR').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.ERROR), format='%(message)s')
logger = logging.getLogger(__name__)

dominoesOutputPath = os.getenv('IMAGE_PROCESSOR_OUTPUT_PATH')
photoPath = os.getenv('DOMINOES_IMG_PATH')
imagesOutputPath = os.getenv('IMAGES_PATH')

PIP_THRESHOLD = 15  # Defines maximum allowed output of pips for dominoes. Should be higher than 12 for margin of error


# Main wrapper method. Outputs raw domino data to a txt file
def processRawImage():
    dominoes = getDominoes(photoPath)

    with open(dominoesOutputPath, "w+") as outputFile:
        print(json.dumps(dominoes), file=outputFile)


# Processes the dominoes image and returns the identified dominoes data
def getDominoes(photo):
    logger.info("BEGIN IMAGE PROCESSING".center(40, "="))
    # Photo preprocessing
    img = cv2.imread(photo)
    filteredBlackAndWhite = whiteFilter(img)
    domino_corners = identifyDominoes(filteredBlackAndWhite)

    # Identifying dominoes
    dominoes = dict()
    for i, corners in enumerate(domino_corners, 1):
        domino = extract_domino(filteredBlackAndWhite, corners)
        circles = identifyPips(domino)
        bottom_pips, top_pips = split_domino_and_count_pips(domino, circles)
        dominoes[i] = (top_pips, bottom_pips)
        pipCount = 0
        if circles is not None:
            pipCount = len(circles)

        logger.info(f"Domino {i} has {pipCount} pips. Top: {top_pips}, bottom: {bottom_pips}")

        # For website
        colorDomino = extract_domino(img, corners)
        drawIdentifiedPips(colorDomino, circles, i)

    logger.info("END IMAGE PROCESSING".center(40, "=") + "\n")
    return dominoes


# Draws in color what the program identified on individual dominoes. Helpful to user when correcting the raw data.
def drawIdentifiedPips(dominoImg, pips, id):
    # Optional: draw circles on the domino for visualization
    pipCount = 0
    if pips is not None:
        pipCount = len(pips)
    if pipCount > 0:
        if pips is not None:
            for (x, y, r) in pips:
                cv2.circle(dominoImg, (x, y), r, (0, 0, 255), 4)

        # Save or display the domino image with circles drawn
    cv2.imwrite(imagesOutputPath + fr'\domino_{id}.jpg', dominoImg)


# HELPERS
# getWhiteColorMask actually returns an hsv filtered photo because it works better than black and white
# Returns an image filtered with hsv
def getWhiteColorMask(img):
    lowerBound = np.array([0, 0, 180])  # Lower bound for white color in HSV
    upperBound = np.array([165, 30, 255])  # Upper bound for white color in HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, lowerBound, upperBound)


# Returns a black and white filtered image. Good at identifying pips
def whiteFilter(img):
    # Color filter image to get black and white
    masked = cv2.bitwise_and(img, img, mask=getWhiteColorMask(img))
    return cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)


# Returns the corners of all identified dominoes in a photo
def identifyDominoes(img):
    # ChatGPT code to identify dominoes
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(img, (5, 5), 0)

    # Use Canny edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Apply morphological operations to close gaps in the edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours and approximate to get the corners
    domino_corners = []
    for contour in contours:
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the approximated contour has 4 vertices (i.e., is a rectangle)
        cornerCount = 0
        if approx is not None:
            cornerCount = len(approx)
        if cornerCount == 4:
            # Check the aspect ratio and area to further filter out non-dominoes
            _, _, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(approx)

            if 0.5 < aspect_ratio < 2.0 and area > 1000:  # Adjust thresholds as needed
                corners = approx.reshape(4, 2)
                domino_corners.append(corners)

                # Draw the corners on the image for visualization
                # for corner in corners:
                #     cv2.circle(img, tuple(corner), 5, (255, 100, 255), -1)
    return domino_corners


# Returns an image of a cropped domino. Used to identify pips
def extract_domino(image, corners):
    # Get the bounding box of the domino using the corners
    rect = cv2.boundingRect(corners)
    x, y, w, h = rect
    cropped_domino = image[y:y+h, x:x+w]
    return cropped_domino


# Identifies the pips of a black and white domino image
def identifyPips(domino):
    blurred = cv2.GaussianBlur(domino, (5, 5), 0)
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.4, minDist=15,
                               param1=50, param2=30, minRadius=5, maxRadius=30)

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")

    return circles


# Uses the data extracted to actually generate identifiable domino data
def split_domino_and_count_pips(img, pips):

    if pips is None:
        return 0, 0
    # Get image dimensions
    height, width = img.shape[:2]

    # Calculate half mark (vertical split)
    half_mark = height // 2

    # Split pips into two halves
    top = [pip for pip in pips if pip[1] < half_mark]
    bottom = [pip for pip in pips if pip[1] >= half_mark]

    # Count pips in each half
    bottom_count, top_count = 0, 0
    if bottom is not None:
        bottom_count = len(bottom)
    if top is not None:
        top_count = len(top)

    return ceiling(bottom_count, top_count)


def ceiling(bottom_pips, top_pips):
    top_ret = top_pips
    bot_ret = bottom_pips
    if top_pips > PIP_THRESHOLD:
        top_ret = 0
    if bottom_pips > PIP_THRESHOLD:
        bot_ret = 0
    return bot_ret, top_ret

# Run program
processRawImage()
