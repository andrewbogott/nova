# Copyright 2011 OpenStack LLC.
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

import pkg_resources

import nova
from nova.api.openstack.compute import contrib
from nova.api.openstack import extensions
from nova.api.openstack.compute import extensions as computeextensions
from nova import flags
from nova import log
from nova.notifier import api as notifier_api
import nova.notifier.no_op_notifier
from nova.plugin import plugin
from nova.plugin import pluginmanager
from nova import test


class SimpleNotifier(object):
    def __init__(self):
        self.message_list = []

    def notify(self, context, message):
        self.context = context
        self.message_list.append(message)


class ManagerTestCase(test.TestCase):
    def tearDown(self):
        super(ManagerTestCase, self).tearDown()

    def test_constructs(self):
        manager1 = pluginmanager.PluginManager("test")
        self.assertNotEqual(manager1, False)


class NotifyTestCase(test.TestCase):
    """Test case for the plugin notification interface"""
    def setUp(self):
        super(NotifyTestCase, self).setUp()

        # Set up a 'normal' notifier to make sure the plugin logic
        #  doesn't mess anything up.
        self.flags(notification_driver='nova.notifier.no_op_notifier')

        def mock_notify(cls, *args):
            self.no_op_notify_called = True
        self.stubs.Set(nova.notifier.no_op_notifier, 'notify',
                mock_notify)

    def tearDown(self):
        super(NotifyTestCase, self).tearDown()

    def test_init(self):
        notifier = SimpleNotifier()
        testplugin = plugin.Plugin()
        testplugin.add_notifier(notifier)

        notifier_api.notify('contextarg', 'publisher_id', 'event_type',
                            nova.notifier.api.WARN, dict(a=3))

        self.assertEqual(len(notifier.message_list), 1)
        self.assertTrue(self.no_op_notify_called)

    def test_add_and_remove(self):
        notifier1 = SimpleNotifier()
        notifier2 = SimpleNotifier()
        notifier3 = SimpleNotifier()

        testplugin = plugin.Plugin()
        testplugin.add_notifier(notifier1)
        testplugin.add_notifier(notifier2)

        notifier_api.notify('contextarg', 'publisher_id', 'event_type',
                            nova.notifier.api.WARN, dict(a=3))

        self.assertEqual(len(notifier1.message_list), 1)
        self.assertEqual(len(notifier2.message_list), 1)
        self.assertTrue(self.no_op_notify_called)

        testplugin.add_notifier(notifier3)

        self.no_op_notify_called = False
        notifier_api.notify('contextarg', 'publisher_id', 'event_type',
                            nova.notifier.api.WARN, dict(a=3))

        self.assertEqual(len(notifier1.message_list), 2)
        self.assertEqual(len(notifier2.message_list), 2)
        self.assertEqual(len(notifier3.message_list), 1)
        self.assertTrue(self.no_op_notify_called)

        testplugin.remove_notifier(notifier1)
        testplugin.remove_notifier(notifier3)

        self.no_op_notify_called = False
        notifier_api.notify('contextarg', 'publisher_id', 'event_type',
                            nova.notifier.api.WARN, dict(a=3))

        self.assertEqual(len(notifier1.message_list), 2)
        self.assertEqual(len(notifier2.message_list), 3)
        self.assertEqual(len(notifier3.message_list), 1)
        self.assertTrue(self.no_op_notify_called)

        testplugin.remove_notifier(notifier2)

        self.no_op_notify_called = False
        notifier_api.notify('contextarg', 'publisher_id', 'event_type',
                            nova.notifier.api.WARN, dict(a=3))

        self.assertEqual(len(notifier1.message_list), 2)
        self.assertEqual(len(notifier2.message_list), 3)
        self.assertEqual(len(notifier3.message_list), 1)
        self.assertTrue(self.no_op_notify_called)


class StubController(object):

    def i_am_the_stub(self):
        pass


class StubControllerExtension(extensions.ExtensionDescriptor):
    """This is a docstring.  We need it."""
    name = 'stubextension'
    alias = 'stubby'

    def get_resources(self):
        print "Andrew: get_resources"
        resources = []
        res = extensions.ResourceExtension('testme',
                                           StubController())
        resources.append(res)
        return resources


class TestPluginClass(plugin.Plugin):

    def __init__(self):
        super(TestPluginClass, self).__init__()
        self.add_api_extension_descriptor(StubControllerExtension)


class MockEntrypoint(pkg_resources.EntryPoint):
    def load(self):
        return TestPluginClass


class APITestCase(test.TestCase):
    """Test case for the plugin api extension interface"""
    def tearDown(self):
        super(APITestCase, self).tearDown()

    def test_add_extension(self):
        def mock_load(_s):
            return TestPluginClass()

        def mock_iter_entry_points(_t):
            return [MockEntrypoint("fake", "fake", "fake")]

        self.stubs.Set(pkg_resources, 'iter_entry_points',
                mock_iter_entry_points)

        stubLoaded = False

        # Marking out the default extension paths makes this test MUCH faster.
        self.flags(osapi_compute_extension=[])
        self.flags(osapi_volume_extension=[])

        found = False
        mgr = computeextensions.ExtensionManager()
        for res in mgr.get_resources():
            # We have to use this weird 'dir' check because
            #  the plugin framework muddies up the classname
            #  such that 'isinstance' doesn't work right.
            if 'i_am_the_stub' in dir(res.controller):
                found = True

        self.assertTrue(found)
