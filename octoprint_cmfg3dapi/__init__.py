# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Zeric Zhao <zhao5401@126.com; zhao5401@buaa.edu.cn>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 Cloud Manufacturing Platform Project - Released under terms of the AGPLv3 License"

import logging
import logging.handlers
import time
import threading
import Queue
import os
import flask
import requests
import json
import io
from time import sleep
from .cmfg3dAPI import Cmfg3dAPI


import octoprint.plugin
import octoprint.util
from octoprint.events import Events
from octoprint.filemanager import FileDestinations
from octoprint.filemanager.util import StreamWrapper

def str_safe_get(dictionary, *keys):
	return reduce(lambda d, k: d.get(k) if isinstance(d, dict) else "", keys, dictionary)
def float_safe_get(dictionary, *keys):
	s = str_safe_get(dictionary, *keys)
	return 0.0 if not s else float(s)

class Cmfg3dapiPlugin(octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.StartupPlugin,
                      octoprint.plugin.BlueprintPlugin,
					  octoprint.plugin.EventHandlerPlugin):

	PSTATE_IDLE = "idle"
	PSTATE_WORKING = "working"
	PSTATE_WAITING = "waiting"
	PSTATE_PAUSED = "paused"
	PSTATE_OFFLINE = "offline"

	def __init__(self):
		self._port = None
		self._logger = logging.getLogger("octoprint.plugins.cmfg3dapi")
		self._cmfg3d_api = Cmfg3dAPI()
		self._cmfg3d_status_worker = None
		# initialize authorize status
		self._authorized = False
		self._authorize_thread = None
		self._queues = None
		self._id = None
		self._detail = None
		self._job = None
		self._currentPath = None
		self._update_interval = 60
		self._pstate = self.PSTATE_OFFLINE
		self._queueId = None
		self._task_queue = Queue.Queue()

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
		self._port = port
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

	def _start_cmfg3d_status(self):
		if not self._cmfg3d_status_worker:
			self._logger.debug("starting heartbeat")
			self._cmfg3d_status_worker = threading.Thread(target=self._cmfg3d_status_heartbeat)
			self._cmfg3d_status_worker.setDaemon(True)
			self._cmfg3d_status_worker.start()

	def _cmfg3d_status_heartbeat(self):
		self._logger.debug("heartbeat")
		status_sent = 0
		if self._authorized:
			self._logger.debug("self authorized: {}".format(repr(self._authorized)))
			options = self._printer.get_connection_options()
			self._cmfg3d_api.update_device_options(options)
			bots = self._cmfg3d_api.getMyBots()
			self._logger.debug("set self bot id: %d", self._id)
			self._id = bots[0]["id"]
			while True:
				botInfo = self._cmfg3d_api.getBotInfo(self._id)
				if botInfo["status"] == self.PSTATE_OFFLINE or botInfo["status"] == self.PSTATE_WAITING:
					sleep(self._update_interval)
					continue
				elif botInfo["status"] == self.PSTATE_WORKING:
					if self._printer.is_printing():
						temperatures = self._printer.get_current_temperatures()
						status = self._printer.get_current_data()
						self._cmfg3d_api.updateJobProgress(self._id, self._job, status, temperatures)
						sleep(self._update_interval)
						continue
					elif self._printer.is_closed_or_error():
						self._cmfg3d_api.dropJob()
						continue
					else:
						sleep(self._update_interval)
						continue
				elif botInfo["status"] == self.PSTATE_IDLE:
					if not self._printer.is_operational():
						self._printer
					job = self._cmfg3d_api.listJobs()
					if connection[0] == "Closed":
						self._printer.connect()
		else:
			self._logger.warn("client unauthorized, please start after register on cmfg3d")
			return

	def _status_upload(self):
		self._logger.debug("progress sync")
		if self._authorized:
			while not self._printer.is_closed_or_error():
				temps = self._printer.get_current_temperatures()
				data = self._printer.get_current_data()
				job = self._printer.get_current_job()
				self._logger.debug("update progress: %s\ntemps: %s",json.dumps(data["progress"]), json.dumps(temps))
				self._cmfg3d_api.updateJobProgress(self._id, self._job["id"], data["progress"], temps)
				sleep(5)
		else:
			self._logger.warn("client unauthorized!")
			return

	def on_event(self, event, payload):
		self._logger.debug("on event: {}".format(repr(event)))
		if event == Events.PRINT_STARTED or event == Events.PRINT_RESUMED:
			self._pstate = self.PSTATE_WORKING
			self._update_interval = 10
			self._logger.debug("Update interval to {}".format(self._update_interval))
		elif event == Events.PRINT_PAUSED:
			self._pstate = self.PSTATE_PAUSED
		elif event == Events.PRINT_DONE:
			self._pstate = self.PSTATE_WAITING

	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	@octoprint.plugin.BlueprintPlugin.route("/register", methods=["GET"])
	def register_client(self):
		if self._authorized:
			return "Client already registed!"
		try:
			self._cmfg3d_api.requestToken()
		except TypeError as ex:
			self._logger.error(ex)
			return "TypeError when requesting token: %s" % ex
		except Exception as ex:
			self._logger.exception(ex)
			return "There was a problem requesting token: %s" % ex
		return self._cmfg3d_api.getAuthorizeUrl()

	@octoprint.plugin.BlueprintPlugin.route("/getAccessToken", methods=["GET"])
	def request_access_token(self):
		if self._authorized:
			return "Client already registed!"
		self._authorize()
		data = dict(
			tokenKey = self._cmfg3d_api.token_key,
			tokenSecret = self._cmfg3d_api.token_secret
		)
		return flask.jsonify(data)

	def _start_authorize(self):
		if not self._authorize_thread:
			self._logger.debug("start authorize thread")
			self._authorize_thread = threading.Thread(target=self._authorize, name="octoprint.plugin.cmfg3dapi.auth_thread")
			self._authorize_thread.daemon = True
			self._authorize_thread.start()

	def _authorize(self):
		while not self._authorized:
			self._logger.info("Prepare to request access token.")
			try:
				self._cmfg3d_api.convertToken()
				self._authorized = True
			except Exception as ex:
				sleep(10)
		# s = settings()
		# s.set(["plugins", "cmfg3dapi", "tokenKey"], self._cmfg3d_api.token_key)
		# s.set(["plugins", "cmfg3dapi", "tokenSecret"], self._cmfg3d_api.token_secret)
		# settings().save()
		self._logger.debug("Set token key: %s", self._cmfg3d_api.token_key)
		self._logger.debug("Set token secret: %s", self._cmfg3d_api.token_secret)

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

	@octoprint.plugin.BlueprintPlugin.route("/listQueue", methods=["GET"])
	def listQueue(self):
		self._queues = self._cmfg3d_api.listQueues()
		self._logger.debug("set queues: %s", self._queues)
		return json.dumps(self._queues)

	@octoprint.plugin.BlueprintPlugin.route("/updateOptions", methods=["GET"])
	def updateOptions(self):
		options = self._printer.get_connection_options()
		if not self._authorized:
			options["status"] = "not authorized"
			return flask.jsonify(options)
		self._cmfg3d_api.update_device_options(options)
		return flask.jsonify(options)

	@octoprint.plugin.BlueprintPlugin.route("/getBots", methods=["GET"])
	def getBots(self):
		bots = self._cmfg3d_api.getMyBots()
		device = bots[0]
		self._logger.debug("set self bot id: %d", device['id'])
		self._id = device['id']
		self._detail = device
		return json.dumps(bots)

	@octoprint.plugin.BlueprintPlugin.route("/listJobs", methods=["GET"])
	def listJobs(self):
		jobs = []
		for queue in self._queues:
			jobs.extend(self._cmfg3d_api.listJobs(queue["id"]))
		return json.dumps(jobs)

	@octoprint.plugin.BlueprintPlugin.route("/getJob", methods=["GET"])
	def getJob(self):
		jobId = self._detail["job_id"]
		if (jobId != 0):
			self._job = self._cmfg3d_api.jobInfo(jobId)
			return json.dumps(self._job)
		else:
			return "No current job"

	@octoprint.plugin.BlueprintPlugin.route("/grabJob", methods=["GET"])
	def grabJob(self):
		# self.getSelfBotInfo()
		for queue in self._queues:
			self._logger.debug("get jobs from queue: %d", queue['id'])
			jobs = self._cmfg3d_api.listJobs(queue['id'])
			if (len(jobs) <= 0):
				continue
			for job in jobs:
				self._logger.debug("self id: %d, grab job id: %d",self._id,job['id'])
				self._job = self._cmfg3d_api.grabJob(self._id, job['id'])
				if not self._job == False:
					break
			if not self._job == False:
				break
		if not self._job == False:
			return flask.jsonify(self._job)
		else:
			return "No job to grab."

	@octoprint.plugin.BlueprintPlugin.route("/download", methods=["GET"])
	def downloadGcode(self):
		if self._job == None:
			return "No current job found"
		gcodeFile = self._cmfg3d_api.downloadGcode(self._job["file_id"])
		# return json.dumps(gcodeFile)
		path = self._file_manager.add_folder(FileDestinations.LOCAL, "cmfg3d")
		path = self._file_manager.join_path(FileDestinations.LOCAL, path, "current-print")
		self._currentPath = path + ".gcode"
		self._file_manager.add_file(FileDestinations.LOCAL, self._currentPath,
									StreamWrapper(self._currentPath, io.StringIO(gcodeFile["content"])), allow_overwrite=True)
		return self._currentPath

	@octoprint.plugin.BlueprintPlugin.route("/startPrint", methods=["GET"])
	def startPrint(self):
		if self._printer.is_printing():
			return "is printing"
		if self._printer.is_closed_or_error():
			self._printer.disconnect()
			self._printer.connect()
		path = self._file_manager.path_on_disk(FileDestinations.LOCAL, self._currentPath)
		self._printer.select_file(path, False, printAfterSelect=True)
		return "Start printing file: "+path

	@octoprint.plugin.BlueprintPlugin.route("/autorun", methods=["GET"])
	def autoRun(self):
		if not self._authorized:
			return
		self._queues = self._cmfg3d_api.listQueues()
		bots = self._cmfg3d_api.getMyBots()
		device = bots[0]
		self._logger.debug("set self bot id: %d", device['id'])
		self._id = device['id']
		self._detail = device
		for queue in self._queues:
			self._logger.debug("get jobs from queue: %d", queue['id'])
			jobs = self._cmfg3d_api.listJobs(queue['id'])
			if (len(jobs) <= 0):
				continue
			for job in jobs:
				self._logger.debug("self id: %d, grab job id: %d",self._id,job['id'])
				self._job = self._cmfg3d_api.grabJob(self._id, job['id'])
				if not self._job == False:
					break
			if not self._job == False:
				break
		if self._job == None:
				return "No current job found"
		gcodeFile = self._cmfg3d_api.downloadGcode(self._job["file_id"])
		path = self._file_manager.add_folder(FileDestinations.LOCAL, "cmfg3d")
		path = self._file_manager.join_path(FileDestinations.LOCAL, path, "current-print")
		self._currentPath = path + ".gcode"
		self._file_manager.add_file(FileDestinations.LOCAL, self._currentPath,
									StreamWrapper(self._currentPath, io.StringIO(gcodeFile["content"])), allow_overwrite=True)
		if self._printer.is_printing():
			return "is printing"
		if self._printer.is_closed_or_error():
			self._printer.disconnect()
			self._printer.connect()
		path = self._file_manager.path_on_disk(FileDestinations.LOCAL, self._currentPath)
		self._printer.select_file(path, False, printAfterSelect=True)
		if not self._cmfg3d_status_worker:
			self._logger.debug("starting heartbeat")
			self._cmfg3d_status_worker = threading.Thread(target=self._status_upload())
			self._cmfg3d_status_worker.setDaemon(True)
			self._cmfg3d_status_worker.start()
			return "Start heartbeat"
		else:
			return "heartbeat already started"


	# jobList = self.cmfg3dapi.listJobs(flask.request.values["queueId"])


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

