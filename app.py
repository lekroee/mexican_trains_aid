# This is the front facing web app to handle user input and display output.
# This will call the backend module to process user submitted data. This is expected to prepare the backend module to
# be ran, such as cleaning out old submissions and handling user input.

from flask import Flask, render_template, url_for, redirect, request
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import FileField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import ValidationError
from dotenv import load_dotenv  # Getting environment
import glob
import json
import os
import logging
import subprocess
import threading
import time

# SETUP
load_dotenv("config.env")
app = Flask(__name__)
debug = json.loads(os.getenv("DEBUG"))
imagesPath = os.getenv('IMAGES_PATH')
log_level = os.getenv('LOG_LEVEL', 'ERROR').upper()

logging.basicConfig(level=getattr(logging, log_level, logging.ERROR), format='%(message)s')
logger = logging.getLogger(__name__)

app.config['SECRET_KEY'] = 'imexicantrainedatyourmomshouse'
app.config['UPLOAD_FOLDER'] = imagesPath


def validate_jpg(form, field):
    if not field.data:
        return
    filename = field.data.filename
    if not filename.lower().endswith('.jpg') or not filename.lower().endswith('.jpeg'):
        raise ValidationError('Only .jpg files are allowed.')


class UploadForm(FlaskForm):
    photo = FileField("File", validators=[FileRequired()])
    submit = SubmitField("Submit")


class TextForm(FlaskForm):
    data = TextAreaField('Dominoes', validators=[DataRequired()])
    submit = SubmitField('Submit')


# GLOBALS
APPROVED_EXNTENSIONS = ['jpg']
imgPath = os.getenv('DOMINOES_IMG_PATH')
dominoImgsPath = os.getenv('IMAGES_PATH')
processedDominoesNamePath_template = dominoImgsPath + r"\domino_*.jpg"
rawDominoesPath = os.getenv('IMAGE_PROCESSOR_OUTPUT_PATH')
finalTrainsPath = os.getenv('TRAIN_BUILDER_OUTPUT_PATH')
rootNumberPath = os.getenv('ROOT_NUM_PATH')
TIMEOUT = int(os.getenv('TIMEOUT'))
trainBuilderExePath = os.getenv('TRAIN_BUILDER_EXE')
imageProcessorExePath = os.getenv('IMAGE_PROCESSOR_EXE')


# MAIN WEB METHODS
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/photo-submit', methods=['GET', "POST"])
def photo_submit():
    resetResources()
    form = UploadForm()
    dominoesImgName = "Dominoes.jpg"
    if form.validate_on_submit():
        file = form.photo.data
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
                               secure_filename(dominoesImgName)))
        imgProcThread = threading.Thread(target=runImageProcessor)
        imgProcThread.start()
        return redirect(url_for('user_review'))

    return render_template('photo-submit.html', form=form)


@app.route('/user-review', methods=['GET', 'POST'])
def user_review():
    form = TextForm()
    if processFinished(rawDominoesPath):
        dominoesFromImg = json.loads(open(rawDominoesPath, "r").read())
        dominoesFromImg = {int(k): f"{v[0]}, {v[1]}" for k, v in dominoesFromImg.items()}
        logger.info(f"Dominoes retrieved from image processing: {dominoesFromImg}")
        dominoImgs = glob.glob(os.path.join(imagesPath, processedDominoesNamePath_template.split('\\')[-1]))
        dominoImgs = [os.path.basename(tmp) for tmp in dominoImgs]

    if request.method == "POST":
        logger.info("IN POST METHOD")
        resetOneResource(finalTrainsPath)       # Make sure the trainBuilder has to run every time

        # Get user approved data and write it to output
        rawData = {}
        text_area_keys = [key for key in request.form.keys() if key.endswith('top')]
        logger.info(f"ALL KEYS: {request.form.keys()}")
        for key in text_area_keys:
            top = request.form.get(key)
            bottom = request.form.get('-'.join(key.split('-')[:2]) + "-bottom")
            rawData[int(key.split('-')[1])] = tuple(map(int, [top, bottom]))

        rootNumber = request.form.get("round")
        userApprovedDominoes = rawData
        logger.info(f"User submitted dominoes: {userApprovedDominoes}, Round number: {rootNumber}")

        with open(rawDominoesPath, "w") as file:
            print(json.dumps(userApprovedDominoes), file=file)
        with open(rootNumberPath, "w") as file:
            print(rootNumber, file=file)

        # Run train builder
        trainBuilderThread = threading.Thread(target=runTrainBuilder)
        trainBuilderThread.start()
        return redirect(url_for('final_trains'))
    return render_template('user-review.html', form=form, dominoImgs=dominoImgs, domsFromImg=dominoesFromImg)


@app.route('/final-trains')
def final_trains():
    if processFinished(finalTrainsPath):
        data = open(finalTrainsPath, "r").read()
    else:
        data = None

    logger.info(f"data: {data}, data split: {data.split('Longest:')}")
    longSplit = data.split('Longest:')
    longest = longSplit[1].strip()
    mostPips = longSplit[0].split('Most Pips:')[1].strip()
    return render_template('final-trains.html', data=data, mostPips=mostPips, longest=longest)


# HELPERS
def resetResources():
    if debug:
        delete = False
    else:
        delete = True
    if os.path.exists(imgPath):
        if delete:
            logger.info("Deleting " + imgPath)
            os.remove(imgPath)
    if os.path.exists(rawDominoesPath):
        if delete:
            logger.info("Deleting " + rawDominoesPath)
            os.remove(rawDominoesPath)
    if os.path.exists(rootNumberPath):
        if delete:
            logger.info("Deleting " + rootNumberPath)
            os.remove(rootNumberPath)
    if os.path.exists(finalTrainsPath):
        if delete:
            logger.info("Deleting " + finalTrainsPath)
            os.remove(finalTrainsPath)

    allDominoesImgs = glob.glob(processedDominoesNamePath_template)
    for dominoImgPath in allDominoesImgs:
        if os.path.exists(dominoImgPath):
            if delete:
                logger.info("Deleting " + dominoImgPath)
                os.remove(dominoImgPath)


def resetOneResource(resPath):
    if os.path.exists(resPath):
        logger.info("Deleting " + resPath)
        os.remove(resPath)


def runImageProcessor():
    subprocess.run([imageProcessorExePath], check=True)


def runTrainBuilder():
    subprocess.run([trainBuilderExePath], check=True)


def processFinished(path):
    waiting = 0
    while not os.path.exists(path) and waiting < TIMEOUT:
        time.sleep(1)
        waiting += 1
    if waiting < TIMEOUT:
        return True
    return False


def getRootNumber():
    if os.path.exists(rootNumberPath):
        return int(open(rootNumberPath, "r").read().strip())
    return 13


# DEBUG RUN
if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
