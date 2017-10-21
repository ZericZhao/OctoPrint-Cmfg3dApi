import cmfg3dAPI
import shutil
import json
import os
import logging
import logging.handlers

class apiTest():
	def __init__(self):
		self.testURL = "http://zericzhao.win:8080/oauth"
		self.consumerKey = "133f1b38-8a3f-464c-b2d0-ca8bb7887aaf"
		self.consumerSecret = "pSyXPRL1vVZAuePcfy6RvT5IvXxqAZj7/7u5ROD4k7BRkpqzZ/4rTxID+CRay2aOmAuGPTLzWQqLkGr+50QMrjrWtp57Wj5VGPNq4XMoko4="
		self.oauthToken = "8a364f8a-2feb-4ee8-9c79-9c2c67fc6486"
		self.tokenSecret = "5aTWR5kxuq10u3IsV/PHUEgjLXo0rkUFymvfsPk4dIJsG5XoQ8RojWmW2OLgyy/NJot64r7UpO9jSzmDTLXJCOG7x6hzkeoKAgELk4BYEDE="
		self.loadLogger()
		self.apiSDK = cmfg3dAPI.Cmfg3dAPI()
		self.apiSDK.config(self.consumerKey, self.consumerSecret, self.testURL, "http://zericzhao.win:8080/api")
		self.apiSDK.setToken(self.oauthToken, self.tokenSecret)

	def testApiCall(self):
		method = "GET"
		data = self.apiSDK.apiCall(method, "/test")
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
