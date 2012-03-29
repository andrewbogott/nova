# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova import exception
from nova import flags
from nova import log as logging
from nova.openstack.common import cfg
from nova.notifier import list_notifier


FLAGS = flags.FLAGS

LOG = logging.getLogger(__name__)


class Plugin(object):
    """Defines an interface for a contained extension to Nova functionality.

    A plugin interacts with nova in the following ways:

    - An optional set of notifiers, managed via __init__(),
      add_notifier() and remove_notifier()

    - A set of api extensions, set at __init__ time.

    - Direct calls to nova functions.

    - Whatever else the plugin wants to do on its own.

    If you find yourself needing to call between plugins then you're
    probably doing something wrong.

    This is the reference implementation.
    """

    def __init__(self, api_extension_descriptors=[],
                 notifiers=[]):
        self._notifiers = notifiers
        self._api_extension_descriptors = api_extension_descriptors

        # Make sure we're using the list_notifier.
        if not hasattr(FLAGS, "list_notifier_drivers"):
            FLAGS.list_notifier_drivers = []
        old_notifier = FLAGS.notification_driver
        FLAGS.notification_driver = 'nova.notifier.list_notifier'
        if old_notifier and old_notifier != 'nova.notifier.list_notifier':
            list_notifier.add_driver(old_notifier)

        # Hook up our current list of notifiers.
        for notifier in self._notifiers:
            list_notifier.add_driver(notifier)

    def api_extension_descriptors(self):
        """Return a list of API extension descriptors.

           Called by the Nova API during its load sequence.
        """
        return self._api_extension_descriptors

    def on_service_load(self, service_name):
        """Called when the Nova API service loads this plugin."""
        pass

    def add_notifier(self, notifier):
        """Add a notifier to the notification driver chain.

           Notifier objects should implement the function notify(message).
        """
        self._notifiers.append(notifier)
        list_notifier.add_driver(notifier)

    def remove_notifier(self, notifier):
        """Remove a notifier from the notification driver chain."""
        self._notifiers.remove(notifier)
        list_notifier.remove_driver(notifier)

    def notifiers(self):
        """Returns list of notifiers for this plugin."""
        return self._notifiers
