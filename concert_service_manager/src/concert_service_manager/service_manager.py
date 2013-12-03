# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_concert/license/LICENSE
#
##############################################################################
# Imports
##############################################################################

import rospy
import traceback
import threading
import roslaunch.pmon
import concert_msgs.msg as concert_msgs
import concert_msgs.srv as concert_srvs
import concert_roles
import unique_id

# Local imports
from .concert_service_instance import ConcertServiceInstance
from .service_list import load_service_descriptions_from_service_lists

##############################################################################
# ServiceManager
##############################################################################


class ServiceManager(object):

    def __init__(self):
        self._param = {}
        self._services = {}
        self._publishers = {}
        self._concert_services = {}
        self._setup_ros_parameters()
        self.lock = threading.Lock()
        self._role_app_loader = concert_roles.RoleAppLoader()
        roslaunch.pmon._init_signal_handlers()
        self._setup_ros_api()
        self._initialise_concert_services()

    def _initialise_concert_services(self):
        '''
          Currently only called at the end of service manager construction.
        '''
        self.lock.acquire()
        service_descriptions = load_service_descriptions_from_service_lists(self._param['service_lists'])
        for service_description in service_descriptions:
            self._concert_services[service_description.name] = ConcertServiceInstance(service_description=service_description,
                                                                                      update_callback=self.update)
            self._setup_service_parameters(service_description)
        self.lock.release()
        if self._param['auto_enable_services']:
            for service in self._concert_services.values():
                service.enable(self._role_app_loader)
        self.update()

    def _setup_ros_parameters(self):
        rospy.logdebug("Service Manager : parsing parameters")
        self._param = {}
        self._param['service_lists']        = [x for x in rospy.get_param('~service_lists', '').split(';') if x != '']  #@IgnorePep8
        self._param['auto_enable_services'] = rospy.get_param('~auto_enable_services', False)  #@IgnorePep8

    def _setup_service_parameters(self, service_description):
        '''
          Dump some important information for the services to self-introspect on in the namespace in which
          they will be started.

          @param service_description : entity with the configured fields for a service
          @type concert_msgs.ConcertService
        '''
        namespace = '/services/' + service_description.name
        rospy.set_param(namespace + "/name", service_description.name)
        rospy.set_param(namespace + "/description", service_description.description)
        rospy.set_param(namespace + "/uuid", unique_id.toHexString(service_description.uuid))

    def _setup_ros_api(self):
        self._services['enable_service'] = rospy.Service('~enable', concert_srvs.EnableConcertService, self._ros_service_enable_concert_service)
        self._publishers['list_concert_services'] = rospy.Publisher('list_concert_services', concert_msgs.ConcertServices, latch=True)

    def _unload_resources(self, service_name):
        # Taken out temporarily until the scheduler handles 'groups',
        pass
        #request_resources = concert_msgs.RequestResources()
        #request_resources.service_name = service_name
        #request_resources.enable = False
        #self._publishers['request_resources'].publish(request_resources)

    def _ros_service_enable_concert_service(self, req):
        name = req.concertservice_name

        success = False
        message = "unknown error"

        if req.enable:
            self.loginfo("serving request to enable '%s'" % name)
        else:
            self.loginfo("serving request to disable '%s'" % name)
        if name in self._concert_services:
            if req.enable:
                success, message = self._concert_services[name].enable(self._role_app_loader)
            else:
                success, message = self._concert_services[name].disable(self._role_app_loader, self._unload_resources)
        else:
            service_names = self._concert_services.keys()
            message = "'" + str(name) + "' does not exist " + str(service_names)
            self.logwarn(message)
            success = False

        return concert_srvs.EnableConcertServiceResponse(success, message)

    def update(self):
        rs = [v.to_msg() for v in self._concert_services.values()]
        self._publishers['list_concert_services'].publish(rs)

    def loginfo(self, msg):
        rospy.loginfo("Service Manager : " + str(msg))

    def logwarn(self, msg):
        rospy.logwarn("Service Manager : " + str(msg))

    def spin(self):
        rospy.spin()
