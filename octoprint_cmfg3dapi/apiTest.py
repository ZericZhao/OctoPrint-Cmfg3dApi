import botqueueapi
import shutil
import json
import os
import logging
import logging.handlers

class apiTest():
	def __init__(self):
		self.testURL = "http://localhost:8080/oauth"
		self.consumerKey = "133f1b38-8a3f-464c-b2d0-ca8bb7887aaf"
		self.loadLogger()
		self.apiSDK = botqueueapi.BotQueueAPI()

	def testApiCall(self):
		method = "GET"
		data = self.apiSDK.apiCall(method, "test")
		print data["status"]
		print data["data"]

	def testQueues(self):
		queues = self.apiSDK.listQueues()
		for queue in queues:
			print queue["id"]
			print queue["name"]
		print queues[0]

	def testListJobs(self):
		queue = self.apiSDK.listJobs()

	def load(self):
		try:
			if not os.path.exists(self.path):
				# Move the old config?
				if os.path.exists("config.json"):
					shutil.move("config.json", self.path)
				else:
					config_dist = os.path.dirname(os.path.realpath(__file__)) + os.sep + "config-dist.json"
					shutil.copy(config_dist, self.path)
			f = open(self.path, "r")
			self.data = json.load(f)
			f.close()

			return f
		except ValueError as e:
			print("Error parsing config file: %s" % e)
			raise RuntimeError("Error parsing config file: %s" % e)

	def loadLogger(self):
		# create logger with 'spam_application'
		logger = logging.getLogger('botqueue')
		logger.setLevel(logging.DEBUG)

		# create formatter and add it to the handlers
		formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')

		# create file handler which logs even debug messages (max 25mb)
		log_file = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'test.log'
		fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=26214400, backupCount=3)
		fh.setLevel(logging.DEBUG)
		fh.setFormatter(formatter)
		logger.addHandler(fh)


if __name__ == '__main__':
	api = apiTest()
	api.testApiCall()
	api.testQueues()
