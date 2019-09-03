seed = 123

import numpy as np

np.random.seed(seed)
import tensorflow as tf

tf.set_random_seed(seed)

import random

random.seed(seed)

import os

import sys

import time

from my_crypts_dataset import CryptsDataset

import model as modellib
from model import log

import numpy as np
from imgaug import augmenters as iaa

import skimage.io

#######################################################################################
## SET UP CONFIGURATION
from config import Config


class CryptsConfig(Config):
    """Configuration for training on the toy shapes dataset.
    Derives from the base Config class and overrides values specific
    to the toy shapes dataset.
    """
    # Give the configuration a recognizable name
    NAME = "crypt"

    IMAGE_RESIZE_MODE = "square"
    IMAGE_MIN_DIM = 800
    IMAGE_MAX_DIM = 1024
    IMAGE_MIN_SCALE = False  ## Not using this


    IMAGE_CHANNEL_COUNT = 3
    # Augmentation parameters
    ASPECT_RATIO = 1.3  ## Maximum aspect ratio modification when scaling
    MIN_ENLARGE = 1.2  ## Minimum enlarging of images, note that this will be randomized
    ZOOM = 1.5  ## Maximum zoom per image, note that this will be randomized


    ROT_RANGE = 10.
    CHANNEL_SHIFT_RANGE = 15

    LEARNING_RATE = 0.001
    # Train on 1 GPU and 8 images per GPU. We can put multiple images on each
    # GPU because the images are small. Batch size is 8 (GPUs * images/GPU).
    GPU_COUNT = 4
    IMAGES_PER_GPU = 1

    # Number of classes (including background)
    NUM_CLASSES = 1 + 1  # background + nuclei


    # Use smaller anchors because our image and objects are small
    RPN_ANCHOR_SCALES = (32, 64, 128, 256, 512)  # anchor side in pixels
    # RPN_ANCHOR_SCALES = (4, 8 , 16, 32, 64)  # anchor side in pixels

    # Reduce training ROIs per image because the images are small and have
    # few objects. Aim to allow ROI sampling to pick 33% positive ROIs.
    TRAIN_ROIS_PER_IMAGE = 200

    STEPS_PER_EPOCH = 664 // IMAGES_PER_GPU
    VALIDATION_STEPS = 1  # 2//IMAGES_PER_GPU ## We are training with the whole dataset so validation is not very meaningfull, I put a two here so it is faster. We either use train loss or calculate in a separate procceses the mAP for each epoch

    # use small validation steps since the epoch is small
    # VALIDATION_STEPS = 5

    USE_MINI_MASK = True

    MAX_GT_INSTANCES = 256

    DETECTION_MAX_INSTANCES = 512


bowl_config = CryptsConfig()
bowl_config.display()
#######################################################################################

# Root directory of the project
ROOT_DIR = os.getcwd()

## Change this dir to the stage 1 training data
train_dir = os.path.join(ROOT_DIR, 'dataset/new_crypts/train/Images')
print(train_dir)

# Get train IDs
train_ids = next(os.walk(train_dir))[2]

# Training dataset
dataset_train = CryptsDataset()
dataset_train.load_bowl(train_ids, 'dataset/new_crypts/train')
dataset_train.prepare()

# # Validation dataset, same as training.. will use pad64 on this one
val_dir = os.path.join(ROOT_DIR, 'dataset/new_crypts/valid/Images/')
valid_ids = next(os.walk(val_dir))[2]
dataset_val = CryptsDataset()
dataset_val.load_bowl(valid_ids, 'dataset/new_crypts/valid')
dataset_val.prepare()

# Directory to save logs and trained model
MODEL_DIR = os.path.join(ROOT_DIR, "logs")

# Local path to trained weights file
## https://github.com/matterport/Mask_RCNN/releases/download/v2.0/mask_rcnn_coco.h5
COCO_MODEL_PATH = os.path.join(ROOT_DIR, "mask_rcnn_coco.h5")

model = modellib.MaskRCNN(mode="training", config=bowl_config,
                          model_dir=MODEL_DIR)

model.load_weights(COCO_MODEL_PATH, by_name=True,
                   exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",
                            "mrcnn_bbox", "mrcnn_mask"])

import time

start_time = time.time()

## Augment True will perform flipud fliplr and 90 degree rotations on the 512x512 images

# Image augmentation
# http://imgaug.readthedocs.io/en/latest/source/augmenters.html

# ## This should be the equivalente version of my augmentations using the imgaug library
# ## However, there are subtle differences so I keep my implementation
augmentation = iaa.Sequential([
    iaa.Fliplr(0.5),
    iaa.Flipud(0.5),
    iaa.OneOf([iaa.Affine(rotate=0),
               iaa.Affine(rotate=90),
               iaa.Affine(rotate=180),
               iaa.Affine(rotate=270)]),
    iaa.Sometimes(0.5,iaa.Affine(rotate=(-10,10))),
    iaa.Add((-15, 15), per_channel=1)

])

# augmentation = False

model.train(dataset_train, dataset_val,
            learning_rate=bowl_config.LEARNING_RATE,
            epochs=30,
            augmentation=augmentation,
            # augment=True,
            layers="all")

model.train(dataset_train, dataset_val,
            learning_rate=bowl_config.LEARNING_RATE / 10,
            epochs=50,
            augmentation=augmentation,
            # augment=True,
            layers="all")

model.train(dataset_train, dataset_val,
            learning_rate=bowl_config.LEARNING_RATE / 30,
            epochs=75,
            augmentation=augmentation,
            # augment=True,
            layers="all")

end_time = time.time()
ellapsed_time = (end_time - start_time) / 3600

print(model.log_dir)
model_path = os.path.join(model.log_dir, 'final.h5')
model.keras_model.save_weights(model_path)
