# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Zeric Zhao <zhao5401@126.com; zhao5401@buaa.edu.cn>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 Cloud Manufacturing Platform Project - Released under terms of the AGPLv3 License"

import logging
import logging.handlers
import os
import flask
import botqueueapi

import octoprint.plugin

class Cmfg3dapiPlugin(octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.TemplatePlugin,
					  octoprint.plugin.StartupPlugin,
					  octoprint.plugin.BlueprintPlugin):

	def __init__(self):
		self._logger = logging.getLogger("octoprint.plugins.cmfg3dapi")
		self.cmfg3dapi = botqueueapi.BotQueueAPI();

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/cmfg3dapi.js"],
			css=["css/cmfg3dapi.css"],
			less=["less/cmfg3dapi.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			cmfg3dapi=dict(
				displayName="Cmfg3dapi Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="ZericZhao",
				repo="OctoPrint-Cmfg3dApi",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/ZericZhao/OctoPrint-Cmfg3dApi/archive/{target_version}.zip"
			)
		)

	##~~ StartupPlugin API

	def on_startup(self, host, port):
		# setup customized logger
		from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
		cmfg3d_logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(), when="D", backupCount=3)
		cmfg3d_logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
		cmfg3d_logging_handler.setLevel(logging.DEBUG)

		self._logger.addHandler(cmfg3d_logging_handler)
		self._logger.setLevel(logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.INFO)

	def on_after_startup(self):
		self._logger.info("Hello World! (more: %s)" % self._settings.get(["url"]))
		self.cmfg3dapi.setToken()

	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	@octoprint.plugin.BlueprintPlugin.route("/authorize", methods=["GET"])
	def authorize(self):
		if not "text" in flask.request.values:
			return flask.make_response("expected a text to echo back", 400)
		return flask.request.values["text"]


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Cmfg3dapi Plugin"
__plugin_version__ = "0.1.0"
__plugin_description__ = "Cloud Manufacturing platform api adapter."
__plugin_implementation__ = Cmfg3dapiPlugin()

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = Cmfg3dapiPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

