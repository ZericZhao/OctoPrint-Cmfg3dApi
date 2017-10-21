# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Zeric Zhao <zhao5401@126.com; zhao5401@buaa.edu.cn>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 Cloud Manufacturing Platform Project - Released under terms of the AGPLv3 License"

import logging
import logging.handlers
import time
import threading
import os
import flask
from .cmfg3dAPI import Cmfg3dAPI
from octoprint.settings import Settings


import octoprint.plugin


class Cmfg3dapiPlugin(octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.StartupPlugin,
                      octoprint.plugin.BlueprintPlugin):

	def __init__(self):
		self._logger = logging.getLogger("octoprint.plugins.cmfg3dapi")
		self._cmfg3d_api = Cmfg3dAPI()
		# initialize authorize status
		self._authorized = False

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.self
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
		self._cmfg3d_api.config(self._settings.get(["consumerKey"]), self._settings.get(["consumerSecret"]),
							  self._settings.get(["authorize"]), self._settings.get(["endpoint"]))
		if self._settings.get(["tokenKey"]) is not None:
			self._authorized = True
			self._cmfg3d_api.setToken(self._settings.get(["tokenKey"]), self._settings.get(["tokenSecret"]))

	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	def _heartbeat_cmfg3d(self):
		if self._authorized:
			options = self._printer.get_connection_options()
			self._cmfg3d_api.update_device_options(options)
			return options

	@octoprint.plugin.BlueprintPlugin.route("/register", methods=["GET"])
	def register_client(self):
		if self._authorized:
			return "Client already registed!"
		try:
			self._cmfg3d_api.requestToken()
			self._start_authorize()
		except TypeError as ex:
			self._logger.error(ex)
			return "TypeError when requesting token: %s" % ex
		except Exception as ex:
			self._logger.exception(ex)
			return "There was a problem requesting token: %s" % ex
		return self._cmfg3d_api.getAuthorizeUrl()

	def _start_authorize(self):
		if not self._authorize_thread:
			self._logger.debug("start authorize thread")
			self._authorize_thread = threading.Thread(target=self._authorize, name="octoprint.plugin.cmfg3dapi.auth_thread")
			self._authorize_thread.daemon = True
			self._authorize_thread.start()

	def _authorize(self):
		while not self._authorized:
			try:
				self._cmfg3d_api.convertToken()
				self._authorized = True
			except Exception as ex:
				time.sleep(10)
		self._settings.set(["tokenKey"], self._cmfg3d_api.token_key)
		self._settings.set(["tokenSecret"], self._cmfg3d_api.token_secret)
		Settings.save(Settings)

	@octoprint.plugin.BlueprintPlugin.route("/listJobs", methods=["GET"])
	def grabJob(self):
		self._printer.isPrinting()
		return
		#jobList = self.cmfg3dapi.listJobs(flask.request.values["queueId"])

	@octoprint.plugin.BlueprintPlugin.route("/checkSettings", methods=["GET"])
	def checkSettings(self):
		result = dict(
			consumerKey = self._cmfg3d_api.consumer_key,
			consumerSecret = self._cmfg3d_api.consumer_secret,
			authorized = self._authorized,
		)
		if self._settings.get(["tokenKey"]) is not None:
			self._authorized = True
			self._cmfg3d_api.setToken(self._settings.get(["tokenKey"]), self._settings.get(["tokenSecret"]))
			result["authorized"] = True
			result["tokenKey"] = self._cmfg3d_api.token_key
			result["tokenSecret"] = self._cmfg3d_api.token_secret
		return flask.jsonify(result)

	@octoprint.plugin.BlueprintPlugin.route("/testRemoteServer", methods=["GET"])
	def testRemoteServer(self):
		if self._authorized:
			data = self._cmfg3d_api.apiCall('GET', '/test')
			return flask.jsonify(data)


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

