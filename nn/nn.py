"""
Create the NN for training

Takes input from 3 areas:

1) Camera input
2) Top view of pointcloud (includes LIDAR and RADAR)
3) Surround view of pointcloud (includes LIDAR and RADAR)

Training approach:

1) Train each individual part of the network to see if it gives a reasonable approximation (TODO - Render bounding box on camera and surround images)
2) Merge in turn (note this may mean playing about with the individual parts of the NN to ensure the merge works!!

Note we'll overfit on a single dataset (say 15.bag) to start with to assure there's no bugs in the code!!

"""

import tensorflow as tf
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Flatten, Conv2DTranspose, \
                         Activation, Conv2D, MaxPooling2D, UpSampling2D, \
                         Reshape, core, Dropout
from keras.layers.merge import add, concatenate
from keras.optimizers import Adam, SGD
from keras.callbacks import Callback, TensorBoard, EarlyStopping, ModelCheckpoint
import keras.backend as K

#TODO - Just a starter!!!
num_filters = 32
filter_length = 2
num_pooling = 2
border_mode = "valid"
activation = "relu"
smooth = 1.

# Input shapes (note surround and top and the .npy files)
surround_x, surround_y, surround_z = 400, 8, 3 # TODO - Confirm surround_z, if z=1 then remove completely from the code!!
top_x, top_y, top_z = 400, 400, 8
camera_x, camera_y, camera_z = 1400, 800, 3    #TODO - Get correct values here!!

# from https://github.com/jocicmarko/ultrasound-nerve-segmentation/blob/master/train.py
def dice_coef(y_true, y_pred):
    y_true_f = K.flatten(y_true)
    y_pred_f = K.flatten(y_pred)
    intersection = K.sum(y_true_f * y_pred_f)
    return (2. * intersection + smooth) / (K.sum(y_true_f) + K.sum(y_pred_f) + smooth)


def dice_coef_loss(y_true, y_pred):
    return -dice_coef(y_true, y_pred)


# Based on https://github.com/vxy10/p5_VehicleDetection_Unet/blob/master/main_car_Unet_train_IoU.ipynb
# Aligned with http://angusg.com/writing/2016/12/28/optimizing-iou-semantic-segmentation.html
def IOU_calc(y_true, y_pred):
    y_true_f = K.flatten(y_true)
    y_pred_f = K.flatten(y_pred)
    # inter=tf.reduce_sum(tf.mul(logits,trn_labels))
    intersection = K.sum(y_true_f * y_pred_f)
    # union=tf.reduce_sum(tf.sub(usum=tf.add(logits,trn_labels),intersection=tf.mul(logits,trn_labels)))
    usum = K.sum(y_pred_f + y_true_f)
    union = K.sum(usum - intersection)
    #IoU = (2. * intersection + smooth) / (union + smooth)
    IoU = ( intersection + smooth)  / ( union + smooth )
    return IoU


def IOU_calc_loss(y_true, y_pred):
    return 1-IOU_calc(y_true, y_pred)


# TODO: Be DRY here... lots of code repetition... can this be a single function with different parameters calling it??
# TODO: Add in regularisers are they aren't used in this code yet!
def top_nn_orig(weights_path=None, b_regularizer = None, w_regularizer=None):
    class LossHistory(Callback):
        def on_train_begin(self, logs={}):
            self.losses = []

        def on_batch_end(self, batch, logs={}):
            self.losses.append(logs.get('loss'))

    inputs = Input(shape=(top_x, top_y, top_z))

    conv1 = Conv2D(32, (2,2), activation='relu', padding='same')(inputs)
    conv1 = Dropout(0.2)(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)

    conv2 = Conv2D(64, (2,2), activation='relu', padding='same')(pool1)
    conv2 = Dropout(0.2)(conv2)
    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)

    conv3 = Conv2D(128, (2,2), activation='relu', padding='same')(pool2)
    conv3 = Dropout(0.2)(conv3)

    ## Now split into objectness and bounding box layers
    ## TODO: Is keras.layers.merge.add the best approach here???

    # Objectness (object proposals)
    up4obj = UpSampling2D(size=(2, 2))(conv3)
    conv4obj = Conv2D(64, (2, 2), activation='relu', padding='same')(up4obj)
    conv4obj = Dropout(0.2)(conv4obj)
    merge4obj = add([conv2, conv4obj])

    up5obj = UpSampling2D(size=(2,2))(merge4obj)
    conv5obj = Conv2D(32, (2, 2), activation='relu', padding='same')(up5obj)
    conv5obj = Dropout(0.2)(conv5obj)
    merge5obj = add([conv1, conv5obj])

    #FIXME: Currently only 2 classes (background and obstacle)
    prediction_obj = Conv2D(1, (1, 1), activation='sigmoid', padding='same')(merge5obj)

    # Bounding box prediction
    # Objectness (is this the center of an object or not
    # up4box = UpSampling2D(size=(2, 2))(conv3)
    # conv4box = Conv2D(64, (2, 2), activation='relu', padding='same')(up4box)
    # conv4box = Dropout(0.2)(conv4box)
    # merge4box = add([conv2, conv4box])
    #
    # up5box = UpSampling2D(size=(2,2))(merge4box)
    # conv5box = Conv2D(32, (2, 2), activation='relu', padding='same')(up5box)
    # conv5box = Dropout(0.2)(conv5box)
    # merge5box = add([conv1, conv5box])

    #FIXME: This is a regressor??? so what does/should it return...??
    # prediction_box = Conv2D(2, (2, 2), activation='relu', padding='same')(merge5box)

    # model = Model(inputs=[inputs], outputs=[prediction_obj, prediction_box])
    model = Model(inputs=[inputs], outputs=[prediction_obj])
    model.compile(optimizer=Adam(lr=1e-4),
                  loss=IOU_calc_loss, metrics=[IOU_calc])

    if weights_path != None:
        print ('Loading weights from {}'.format(weights_path))
        model.load_weights(weights_path)
        print ('Loaded!')

    return LossHistory, model   # FIXME: Return both for now, handle LossHistory for merged NN later


def camera_nn(model, num_classes, weights_path=None, w_regularizer = None, b_regularizer = None):
    return model


def top_nn(weights_path=None, b_regularizer = None, w_regularizer=None, cnn_trainable=True):
    class LossHistory(Callback):
        def on_train_begin(self, logs={}):
            self.losses = []

        def on_batch_end(self, batch, logs={}):
            self.losses.append(logs.get('loss'))

    inputs = Input((top_x, top_y, top_z))
    conv1 = Conv2D(32, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(inputs)
    conv1 = Conv2D(32, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)

    conv2 = Conv2D(64, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(pool1)
    conv2 = Conv2D(64, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv2)
    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)

    conv3 = Conv2D(128, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(pool2)
    conv3 = Conv2D(128, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv3)
    pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)

    conv4 = Conv2D(256, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(pool3)
    conv4 = Conv2D(256, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv4)
    pool4 = MaxPooling2D(pool_size=(2, 2))(conv4)

    conv5 = Conv2D(512, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(pool4)
    conv5 = Conv2D(512, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv5)

    up6 = concatenate([Conv2DTranspose(256, (2, 2), strides=(2, 2), padding='same', trainable=cnn_trainable)(conv5), conv4], axis=3)
    conv6 = Conv2D(256, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(up6)
    conv6 = Conv2D(256, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv6)

    up7 = concatenate([Conv2DTranspose(128, (2, 2), strides=(2, 2), padding='same', trainable=cnn_trainable)(conv6), conv3], axis=3)
    conv7 = Conv2D(128, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(up7)
    conv7 = Conv2D(128, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv7)

    up8 = concatenate([Conv2DTranspose(64, (2, 2), strides=(2, 2), padding='same', trainable=cnn_trainable)(conv7), conv2], axis=3)
    conv8 = Conv2D(64, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(up8)
    conv8 = Conv2D(64, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv8)

    up9 = concatenate([Conv2DTranspose(32, (2, 2), strides=(2, 2), padding='same', trainable=cnn_trainable)(conv8), conv1], axis=3)
    conv9 = Conv2D(32, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(up9)
    conv9 = Conv2D(32, (3, 3), activation='relu', padding='same', trainable=cnn_trainable)(conv9)

    conv10 = Conv2D(1, (1, 1), activation='sigmoid', trainable=cnn_trainable)(conv9)

    model = Model(inputs=[inputs], outputs=[conv10])
    model.compile(optimizer=Adam(lr=1e-4),
                  loss=IOU_calc_loss, metrics=[IOU_calc])

    if weights_path != None:
        print ('Loading weights from {}'.format(weights_path))
        model.load_weights(weights_path)
        print ('Loaded!')

    return LossHistory, model
