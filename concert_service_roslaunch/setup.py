#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

d = generate_distutils_setup(
    packages=['concert_service_roslaunch'],
    package_dir={'':'src'},
    requires=['rospy', 
              'unique_id',
              'uuid_msgs',
              'concert_msgs',
              'rocon_std_msgs',
              'scheduler_msgs',
              'rocon_scheduler_requests'
             ]
)

setup(**d)
