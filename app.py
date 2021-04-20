import time
from absl import app, logging
import cv2
import numpy as np
import tensorflow as tf

from tensorflow.python.saved_model import tag_constants
from PIL import Image
import warnings

import core.utils as utils
from core.config import cfg

# from yolov3_tf2.models import (
#     YoloV3, YoloV3Tiny
# )
# from yolov3_tf2.dataset import transform_images, load_tfrecord_dataset
# from yolov3_tf2.utils import draw_outputs
from flask import Flask, request, Response, jsonify, send_from_directory, abort
import os

# print("Setting up GPU")

# # Enable GPU dynamic memory allocation
# gpus = tf.config.experimental.list_physical_devices('GPU')
# for gpu in gpus:
#     tf.config.experimental.set_memory_growth(gpu, True)

# print("Done...setting up GPU")
print("Starting flask")
# Initialize Flask application
app = Flask(__name__)
port = int(os.environ.get("PORT", 5000))
environment = os.environ.get("ENV", "production")
# TODO need to implment CORS for local development with local frontend
if environment=="development":
    print("Using CORS in Development enviornment")
    # from flask_cors import CORS 
    # cors = CORS(app)
print(f"getting port: {port}")
print("Loading in Saved Object Detection Model")
t1 = time.time()
saved_model_loaded = tf.saved_model.load('./models/license_plate-416', tags=[tag_constants.SERVING])
t2 = time.time()
print('time: {}'.format(t2 - t1))
print("Done Loading Object detection model")
input_size = 416


@app.route('/image', methods=['POST'])
def detect_license_plate():
    image = request.files["images"]
    image_name = image.filename
    image.save(os.path.join(os.getcwd(), image_name))
    # import pdb;pdb.set_trace()
    # img_raw = tf.image.decode_image(
    #     open(image_name, 'rb').read(), channels=3)
    # img = tf.expand_dims(img_raw, 0)
    # img = transform_images(img, size)
    print('looking for license_plates...:')
    print('Running inference for {}... '.format(image_name), end='')

    #From detect.py
    original_image = cv2.imread(image_name)
    original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

    #From detect.py
    image_data = cv2.resize(original_image, (input_size, input_size))
    image_data = image_data / 255.

    images_data = []
    for i in range(1):
        images_data.append(image_data)
    images_data = np.asarray(images_data).astype(np.float32)

    infer = saved_model_loaded.signatures['serving_default']
    batch_data = tf.constant(images_data)
    pred_bbox = infer(batch_data)
    for key, value in pred_bbox.items():
        boxes = value[:, :, 0:4]
        pred_conf = value[:, :, 4:]

    boxes, scores, classes, valid_detections = tf.image.combined_non_max_suppression(
        boxes=tf.reshape(boxes, (tf.shape(boxes)[0], -1, 1, 4)),
        scores=tf.reshape(
            pred_conf, (tf.shape(pred_conf)[0], -1, tf.shape(pred_conf)[-1])),
        max_output_size_per_class=50,
        max_total_size=50,
        iou_threshold=0.45,
        score_threshold=0.25
    )
    pred_bbox = [boxes.numpy(), scores.numpy(), classes.numpy(), valid_detections.numpy()]

    # read in all class names from config
    # class_names = utils.read_class_names("./license_plate.names")
    class_names = utils.read_class_names(cfg.YOLO.CLASSES)

    # by default allow all classes in .names file
    allowed_classes = list(class_names.values())
    
    # custom allowed classes (uncomment line below to allow detections for only people, 
    # this would only be relevant if my model was training on people and more)
    #allowed_classes = ['person']

    image = utils.draw_bbox(original_image, pred_bbox, allowed_classes = allowed_classes)

    #Convert colors back to original image colors
    image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)

    # prepare image for response
    _, img_encoded = cv2.imencode('.png', image)
    response = img_encoded.tostring()

    #remove temporary image
    os.remove(image_name)

    try:
        return Response(response=response, status=200, mimetype='image/png')
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=port)