#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_concert/license/LICENSE
#
##############################################################################
# Imports
##############################################################################


import rospy
import os
import subprocess
import tempfile
import roslaunch
import rocon_python_utils.ros
import concert_msgs.msg as concert_msgs

class SoftwareInstance(object):
        
    shutdown_timeout = 5
    kill_timeout = 10
    
    def __init__(self, profile):
        self._profile = profile
        self._namespace = concert_msgs.Strings.SOFTWARE_NAMESPACE  + '/' + str(self._profile.name)
        self._users = []

    def to_msg(self):
        msg = concert_msgs.SoftwareInstance()
        msg.name = self._profile.msg.name
        msg.resource_name = self._profile.msg.resource_name
        msg.max_count =  self._profile.msg.max_count
        msg.namespace = self._namespace
        msg.users = self._users
        return msg

    def start(self, user):
        success = False
        try:
            force_screen = rospy.get_param(concert_msgs.Strings.PARAM_ROCON_SCREEN, True)
            roslaunch_file_path = rocon_python_utils.ros.find_resource_from_string(self._profile.msg.launch, extension='launch')
            temp = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
            launch_text =self._prepare_launch_text(roslaunch_file_path, self._namespace)
            temp.write(launch_text)
            temp.close()
            self._roslaunch = roslaunch.parent.ROSLaunchParent(rospy.get_param('/run_id'), [temp.name], is_core=False, process_listeners=[], force_screen=force_screen)
            self._roslaunch._load_config()
            self._roslaunch.start()
        finally:
            if temp:
                os.unlink(temp.name)
        
        self.add_user(user)
        return success

    def stop(self):
        count = 0
        while self._roslaunch.pm and not self._roslaunch.pm.done:
            if count == 2 * SoftwareInstance.shutdown_timeout: 
                self._roslaunch.shutdown()
            rospy.rostime.wallsleep(0.5)
            count = count + 1
        self._users = []
        return True

    def _prepare_launch_text(self, roslaunch_filepath, namespace):
        launch_text = '<launch>\n   <include ns="%s" file="%s">\n' % (namespace, roslaunch_filepath)
        launch_text += '</include>\n</launch>\n'

        return launch_text

    def add_user(self, user):
        if user in self._users:
            return False, len(self._users)
        else:
            self._users.append(user)
        return True, len(self._users)
        
    def remove_user(self, user):
        if user in self._users:
            self._users.remove(user)
            return True, len(self._users)
        else:
            return False, len(self._users) 

    def is_max_capacity(self):
        return len(self._users) == self._profile.msg.max_count

    def get_namespace(self):
        return self._namespace
