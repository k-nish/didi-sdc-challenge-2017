
import rosbag
import cv2
from cv_bridge import CvBridge
import os
import rosbag
import sensor_msgs.point_cloud2 as pc2
from cv_bridge import CvBridge
from mayavi import mlab
import numpy as np

bag_file_dir = '/media/sf_vol/didi/Didi-Training-Release-1'
image_size = (512, 1400, 3)
# lidar_size = (42034, 5)
#
# fig = mlab.figure(bgcolor=(0, 0, 0), size=(500, 300))
# lidar = np.zeros(lidar_size)
# plt = mlab.points3d(lidar[:, 0], lidar[:, 1], lidar[:, 2],
#                     np.ones(lidar.shape[0])*128, #lidar[:, 0] ** 2 + lidar[:, 1] ** 2,
#                     mode="point",
#                     colormap='spectral',
#                     figure=fig,
#                     )
# msplt = plt.mlab_source

# Load images from the ROS databag, resize accordingly and ensure orientation (w x h instead of h x w)
def load_rosbag_data(bag_file):
    print ('Loading databag {}'.format(bag_file))
    cvbridge = CvBridge()
    bag = rosbag.Bag(os.path.join(bag_file_dir, bag_file))

    img = np.zeros(image_size)
    #lidar = np.zeros(lidar_size)
    _obs1_gps_fix = []
    _gps_fix = []

    for topic, msg, t in bag.read_messages(
        topics=[
            # '/gps/time',
            '/gps/fix',
            '/gps/rtkfix',
            '/obs1/gps/fix',
            '/image_raw',
            '/velodyne_points'
        ]):
        #print ('Topic: {}'.format(topic))
        if topic == '/image_raw':
            img = cvbridge.imgmsg_to_cv2(msg, "bgr8")

        elif topic == '/velodyne_points':
            lidar_msg = pc2.read_points(msg)
            lidar = np.array(list(lidar_msg))
            #print ('LIDAR: {}'.format(lidar.shape))
            yield img, lidar

        elif topic == '/obs1/gps/fix':
            latitude = msg.latitude
            longitude = msg.longitude
            altitude = msg.altitude
            _obs1_gps_fix.append((latitude, longitude, altitude))
            # gps_count +=1

        elif topic == '/gps/fix':
            latitude = msg.latitude
            longitude = msg.longitude
            altitude = msg.altitude
            _gps_fix.append((latitude, longitude, altitude))

    bag.close()

# Main loop
# TODO - Make sure it's main (if '__main__'... etc) and also add in argparse...
lidar_scale = 10  # Initial guess!
ground_truth = -10 # Guess!! For z measurement, if below 0 then who cares??

size = (640, 640)
center_x = size[0]/2
center_y = size[1]/2
center_z = 128
color_b, color_g = 240, 240  # Change later?

for image, lidar in load_rosbag_data('spin_shoreline.bag'):
    # msplt.reset(x=lidar[:, 0], y=lidar[:, 1], z=lidar[:, 2],
    #           scalars=lidar[:, 0] ** 2 + lidar[:, 1] ** 2)
    # cv2.imshow('Image', image)
    # cv2.waitKey(1)
    #print ('LIDAR.shape: {}'.format(lidar.shape))
    lidar_top = np.zeros((size[0],size[1], 3))
    #lmin_x, lmax_x = min(lidar[:,0]), max(lidar[:,0])
    #lmin_y, lmax_y = min(lidar[:,1]), max(lidar[:,1])
    #lmin_z, lmax_z = min(lidar[:,2]), max(lidar[:,2])
    #lmin_i, lmax_i = min(lidar[:,3]), max(lidar[:,3])
    #print ('LIDAR.dims:')
    #print ('  x: {}, {}'.format(lmin_x, lmax_x))
    #print ('  y: {}, {}'.format(lmin_y, lmax_y))
    #print ('  z: {}, {}'.format(lmin_z, lmax_z))
    #print ('  i: {}, {}'.format(lmin_i, lmax_i))

    # Render the pointmap using np/cv2
    # See http://ronny.rest/tutorials/module/pointclouds_01/point_cloud_coordinates/
    for idx in range(lidar.shape[0]):
        _y = (-lidar[idx, 0] * lidar_scale) + center_y   # LIDAR +x is forward facing, CV2 +y is down from top left (0,0)
        _x = (-lidar[idx, 1] * lidar_scale) + center_x   # LIDAR +y is left facing, CV2 +x is right from top left (0,0)
        _z = lidar[idx, 2]
        #_i = lidar[idx, 3]   # Intensity
        #color = abs(int(_x ** 2 + _y ** 2))
        #print ('_x: {}/{}, _y: {}/{}'.format(lidar[idx, 0],_x, lidar[idx, 1], _y))
        if (abs(_x) < size[0] and abs(_y) < size[1]) and _z > ground_truth:
            color_r = (_z + 10) * 10
            lidar_top[int(_y), int(_x)] = [color_b, color_g, color_r]
    cv2.imshow('LIDAR', lidar_top)
    cv2.imshow('Camera', image)
    cv2.waitKey(1)
    #print ('*' * 20)

cv2.destroyAllWindows()




