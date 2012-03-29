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
    "Singleton object for instantiating plugins."""

    _instance = None
    _pluginlist = None

    def __new__(cls, *args, **kwargs):
        """Returns the PluginManager singleton"""
        if not cls._instance or ('new' in kwargs and kwargs['new']):
            cls._instance = super(PluginManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def purge(cls):
        """Clean up in order to run a new test."""
        cls._instance = None

    def _load_plugins(self):
        pluginlist = []

        for entrypoint in pkg_resources.iter_entry_points('nova.plugin'):
            try:
                pluginclass = entrypoint.load()
                plugin = pluginclass()
                pluginlist.append(plugin)
            except (ImportError, ValueError, AttributeError, TypeError), exc:
                LOG.error(_("Failed to load plugin %(plug)s: %(exc)s") %
                          {'plug': entrypoint, 'exc': exc})

        for pluginopt in FLAGS.plugins:
            try:
                # plugin is identified as /path/to/module.classname
                path, _sep, cls = pluginopt.rpartition(".")
                if not path.endswith(".py"):
                    path += ".py"
                module = os.path.splitext(os.path.basename(path))[0]
                m = imp.load_source(module, path)
                pluginclass = getattr(m, cls)
                plugin = pluginclass()
                pluginlist.append(plugin)

            except (ImportError, ValueError, AttributeError), exc:
                LOG.error(_("Failed to load plugin %(plug)s: %(exc)s") %
                          {'plug': pluginopt, 'exc': exc})

        self._pluginlist = pluginlist

    def load_plugins(self, service):
        if self._pluginlist is None:
            self._load_plugins()

        for plugin in self._pluginlist:
            plugin.on_service_load(service)

        return self._pluginlist


def plugin_extension_factory(ext_mgr):
    plugins = PluginManager().load_plugins(ext_mgr)

    for plugin in plugins:
        descriptors = plugin.api_extension_descriptors()
        for descriptor in descriptors:
            ext_mgr.load_extension(descriptor)
