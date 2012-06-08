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

import imp
import os
import pkg_resources

from nova import exception
from nova import flags
from nova import log as logging
from nova.openstack.common import cfg
from nova.notifier import list_notifier


FLAGS = flags.FLAGS

LOG = logging.getLogger(__name__)


class PluginManager(object):
    """Manages plugin entrypoints and loading."""

    def __init__(self, service_name):
        self._service_name = service_name
        self._load_plugins()

    def _load_plugins(self):
        self.plugins = []

        for entrypoint in pkg_resources.iter_entry_points('nova.plugin'):
            try:
                pluginclass = entrypoint.load()
                plugin = pluginclass()
                self.plugins.append(plugin)
            except Exception, exc:
                LOG.error(_("Failed to load plugin %(plug)s: %(exc)s") %
                          {'plug': entrypoint, 'exc': exc})

        for plugin in self.plugins:
            plugin.on_service_load(self._service_name)

    def plugin_extension_factory(self, ext_mgr):
        for plugin in self.plugins:
            descriptors = plugin.get_api_extension_descriptors()
            for descriptor in descriptors:
                ext_mgr.load_extension(descriptor)
