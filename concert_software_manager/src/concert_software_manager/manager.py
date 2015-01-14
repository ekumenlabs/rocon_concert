# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_concert/license/LICENSE
#
##############################################################################
# Imports
##############################################################################

import rospy
import concert_msgs.srv as concert_srvs
import concert_msgs.msg as concert_msgs
from .pool import SoftwarePool
from .instance import SoftwareInstance

##############################################################################
# Manager
##############################################################################

class Manager(object):
    
    __slots__ = ['_params', '_software_pool', '_running_software', '_pub', '_srv']

    def __init__(self):
        self._params = self._setup_ros_parameters()
        self._setup_ros_apis()
        self._software_pool = SoftwarePool()
        self._running_software = {}

    def _setup_ros_parameters(self):
        params = {}
        return params

    def _setup_ros_apis(self):
        pub = {}
        pub['list']   = rospy.Publisher('~list',concert_msgs.Softwares,latch=True, queue_size=1)
        pub['status'] = rospy.Publisher('~status', concert_msgs.Softwares, latch=True, queue_size=1)

        srv = {}
        srv['allocate'] = rospy.Service('~allocate', concert_srvs.AllocateSoftware, self._process_allocate_software)
        
        self._pub = pub
        self._srv = srv

    def _process_allocate_software(self, req): 
        if req.allocate:
            response = self._allocate_software(req.software, req.user)
        else:
            response = self._deallocate_software(req.software, req.user)
        self._pub_status()
        return response

    def _allocate_software(self, software, user):
        resp = concert_srvs.AllocateSoftwareResponse()
        if software in self._running_software.keys():
            instance = self._running_software[software]
            if instance.is_max_capacity(): 
                resp.success = False
                resp.error_message = "It exceeds software capacity" 
            else:
                success, num_user = instance.add_user(user):
        
                if success:
                    resp.success = True
                    resp.namespace = instance.get_namespace()
                else:
                    resp.success = False
                    resp.error_message = "User[%s] already exist"%str(user)
        else:
            try:
                software_profile = self._software_pool.get_profile(software)
                instance = SoftwareInstance(software_profile)
                instance.start()
                self._running_software[software] = instance
                resp.success = True
                resp.namespace = instance.get_namespace() 
            except (SoftwareProfileException, SoftwareInstanceException) as e:
                if instance:
                    instance.stop()
                resp.success = False
                resp.error_message = str(e)
        return resp

    def _deallocate_software(self, software, user):
        success = False
        message = ""
        if software in self._running_software.keys():
            success, num_user = software.remove_user(user)
            if success: 
                if num_user == 0:
                    software.stop()
                message = "success!"
            else:
                message = "%s not exist"%stR(user)
        else:
            success = False
            message = "%s is not running!"%str(software)

        return concert_srvs.AllocateSoftwareResponse(success,"",error_message)

    def spin(self):
        self.print_pool_status()
        self.pub_pool_status()
        rospy.spin()

    def pub_status(self):
        instances = self._running_software.values() 
        msg = [i.to_msg() for i in instances]
        self._pub['status'].publish(concert_msgs.Softwares(msg))

    def pub_pool_status(self):
        profiles, invalid_profiles = self._software_pool.status()
        msg = [p.to_msg() for p in profiles.values()]
        self._pub['list'].publish(concert_msgs.Softwares(msg))

    def print_pool_status(self):
        profiles, invalid_profiles = self._software_pool.status()

        self.loginfo("===== Available Softwares =====")
        for name, profile in profiles.items():
            self.loginfo("- %s : %s"%(name, str(profile.msg.description)))
        self.loginfo("===== Invalid Softwares =====")
        for name, reason in invalid_profiles.items():
            self.loginfo("- %s : %s"%(str(name),str(reason)))

    def loginfo(self, msg):
        rospy.loginfo('Software Farm : %s'%str(msg))

    def logwarn(self, msg):
        rospy.logwarn('Software Farm : %s'%str(msg))
