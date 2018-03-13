"""This

"""

import json
import logging
import socket
import time
import traceback

from oauth_hook import OAuthHook
import requests


class NetworkError(Exception):
    pass


class ServerError(Exception):
    pass


class AuthError(Exception):
    pass


class Cmfg3dAPI():
    version = 0.1
    name = 'Bumblebee'
    localIp = None
    consumer_key = ""
    consumer_secret = ""

    def __init__(self):
        self.log = logging.getLogger('octoprint.plugins.cmfg3dapi')
        self.log.setLevel(logging.DEBUG)
        self.netStatus = False
        self.netErrors = 0

        # url default settings
        self.authorize_url = "http://192.168.2.127:8080/oauth"
        self.endpoint_url = "http://192.168.2.127:8080/api"
        self.token_key = ""
        self.token_secret = ""

        # create our requests session.
        self.session = requests.session()

        # initialize authorize status
        self._authorized = False

    def config(self, consumer_key, consumer_secret, authorizeUrl, endpointUrl):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.authorize_url = authorizeUrl
        self.endpoint_url = endpointUrl

    def setToken(self, token_key, token_secret):
        self.token_key = token_key
        self.token_secret = token_secret
        self.my_oauth_hook = OAuthHook(
            access_token=token_key,
            access_token_secret=token_secret,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret
        )

    def apiCall(self, method="GET", call='/test', parameters=None, filepath=None, url=None, retries=999999,
                ignoreInvalid=False, ignoreData=False):

        # what url to use?
        if not parameters:
            parameters = {}
        if url is None:
            url = self.endpoint_url

        # add in our special variables
        parameters['_client_version'] = self.version
        parameters['_client_name'] = self.name

        # parameters['api_call'] = call
        parameters['api_output'] = 'json'

        # Format any weird objects to strings
        for key, value in parameters.iteritems():
            if isinstance(value, Exception):
                parameters[key] = traceback.format_exc(value)

        # make the call for as long as it takes.
        while retries > 0:
            try:
                self.log.debug("Calling %s - %s (%d tries remaining)" % (url, call, retries))

                # single file?
                if isinstance(filepath, basestring):
                    files = {'file': (filepath, open(filepath, 'rb'))}
                # multiple files?
                elif isinstance(filepath, dict):
                    files = {}
                    for idx, val in filepath.iteritems():
                        files[idx] = (val, open(val, 'rb'))
                elif isinstance(filepath, list):
                    files = {}
                    for idx, val in enumerate(filepath):
                        files[idx] = (val, open(val, 'rb'))
                else:
                    files = None

                # prepare and make our request now.
                request = requests.Request(method, url+call, data=parameters, files=files)
                request = self.my_oauth_hook(request)
                response = self.session.send(request.prepare(), timeout=600)
                self.log.debug("Response status code: %d" % response.status_code)

                if response.status_code == 401:
                    raise AuthError("Wait for user's authorization.")
                #
                if response.status_code == 414:
                    for key, value in parameters.iteritems():
                        self.log.debug("%s: %d" % (key, len(value)))
                    raise ServerError("Request was too long for this server.")
                # convert it to json
                result = True if ignoreData else response.json()
                # sweet, our request must have gone through.
                self.netStatus = True

                # Do we even care if there's an error?
                if ignoreInvalid:
                    return result
                # did we get the right http response code?
                if response.status_code != 200:
                    raise ServerError("Bad response code (%s)" % response.status_code)
                return result

            # we need to re-auth, do it.
            except AuthError as ex:
                self.log.error(ex)
                retries -= 1
            # these are our known errors that typically mean the network is down.
            except (requests.ConnectionError, requests.Timeout) as ex:
                # raise NetworkError(str(ex))
                self.log.error("%s call failed: internet connection is down: %s" % (call, ex))
                self.netError()
                retries = retries - 1
            except ServerError as ex:
                self.log.error("%s call failed: %s" % (call, ex))
                self.netError()
                retries = retries - 1
            # unknown exceptions... get a stacktrace for debugging.
            except ValueError as ex:
                self.log.error("%s call failed: value error" % call)
                self.log.exception(ex)
                self.netError(True)
                retries = retries - 1
            except Exception as ex:
                self.log.error("%s call failed: unknown API error: %s" % (call, ex))
                self.log.error("exception: %s.%s" % (ex.__class__, ex.__class__.__name__))
                self.log.exception(ex)
                self.netError()
                retries = retries - 1
        # something bad happened.
        return False

    def netError(self, netStatus=False):
        self.netStatus = netStatus
        if not netStatus:
            self.netErrors = self.netErrors + 1
        time.sleep(10)

    def requestToken(self):
        # make our token request call or error
        self.my_oauth_hook = OAuthHook(consumer_key=self.consumer_key, consumer_secret=self.consumer_secret)
        result = self.apiCall('GET', '/request_token', ignoreInvalid=True, url=self.authorize_url, retries=5)
        if result["oauth_token"]:
            self.setToken(result['oauth_token'], result['oauth_token_secret'])
        else:
            raise Exception("Error requesting token, please check console and log for details.")

    def getAuthorizeUrl(self):
        return self.authorize_url + "/authorize?oauth_token=" + self.token_key

    def convertToken(self):
        # switch our temporary auth token for our real credentials
        result = self.apiCall('GET', '/access_token', ignoreInvalid=True, url=self.authorize_url, retries=180)
        if result['oauth_token']:
            self.setToken(result['oauth_token'], result['oauth_token_secret'])
        else:
            raise Exception("Error converting token: %s" % result['error'])

    def authorize(self):
        try:
            # Step 0: Initialize to just our consumer key and secret.Now moved to self.requestToken()

            # Step 1: Get a request token. This is a temporary token that is used for
            # having the user authorize an access token and to sign the request to obtain
            # said access token.
            self.requestToken()

            # Step 2: Redirect to the provider. Since this is a CLI script we do not
            # redirect. In a web application you would redirect the user to the URL
            # below.
            print
            print "Please visit BotQueue.com or simply visit this URL to authenticate Bumblebee: %s" % \
                  self.getAuthorizeUrl()
            print
            # webbrowser.open_new(self.getAuthorizeUrl())

            authorized = False
            while not authorized:
                try:
                    # After the user has granted access to you, the consumer, the provider will
                    # redirect you to whatever URL you have told them to redirect to. You can
                    # usually define this in the oauth_callback argument as well.
                    # oauth_verifier = raw_input('What is the PIN? ')

                    # Step 3: Once the consumer has redirected the user back to the oauth_callback
                    # URL you can request the access token the user has approved. You use the
                    # request token to sign this request. After this is done you throw away the
                    # request token and use the access token returned. You should store this
                    # access token somewhere safe, like a database, for future use.
                    self.convertToken()
                    authorized = True

                # we're basically polling the convert function until the user approves it.
                # throwing the exception is totally normal.
                except Exception as ex:
                    time.sleep(10)

            # TODO record the key in our config

        except Exception as ex:
            self.log.exception(ex)
            print "There was a problem authorizing the app: %s" % (ex)
            raise RuntimeError("There was a problem authorizing the app: %s" % (ex))

    def listQueues(self):
        return self.apiCall('GET', '/queues')

    def grabQueue(self, queue_id):
        return self.apiCall('GET', '/queue-'+str(queue_id)+'/info')

    def listJobs(self, queue_id):
        return self.apiCall('GET', '/queue-'+str(queue_id)+'/jobs')

    def grabJob(self, bot_id, job_id):
        # type: (str, str) -> object
        return self.apiCall('PUT', '/bot-'+str(bot_id)+'/grab-job-'+str(job_id), retries=5)

    def dropJob(self, bot_id, job_id, error=False):
        return self.apiCall('PUT', '/bot-'+bot_id+'/drop-job-'+job_id, {'error': error})

    def cancelJob(self, job_id):
        return self.apiCall('PUT', '/cancel-job-'+job_id)

    def failJob(self, job_id):
        return self.apiCall('PUT', '/fail-job-'+job_id)

    # def createJobFromJob(self, job_id, quantity=1, queue_id=0, name=None):
    #     params = {'job_id': job_id, 'queue_id': queue_id, 'quantity': quantity}
    #     if name:
    #         params['name'] = name
    #
    #     return self.apiCall('POST', 'job-'+job_id, params)
    #
    # def createJobFromURL(self, url, quantity=1, queue_id=0, name=None):
    #     params = {'job_url': url, 'queue_id': queue_id, 'quantity': quantity}
    #     if name:
    #         params['name'] = name
    #
    #     return self.apiCall('POST', 'createjob', params)
    #
    # def createJobFromFile(self, filename, quantity=1, queue_id=0, name=None):
    #     params = {'quantity': quantity, 'queue_id': queue_id}
    #     if name:
    #         params['name'] = name
    #
    #     return self.apiCall('POST', 'createjob', params, filename)

    def downloadedJob(self, bot_id, job_id):
        return self.apiCall('PUT', '/bot-'+str(bot_id)+'/downloaded-job-'+str(job_id))

    def completeJob(self, bot_id, job_id):
        return self.apiCall('PUT', '/bot-'+str(bot_id)+'/complete-job-'+str(job_id))

    def updateJobProgress(self, bot_id, job_id, progress, temps=None):
        if not temps:
            temps = {}
        return self.apiCall('PUT', '/bot-'+str(bot_id)+'/update-progress-job-'+str(job_id),
                            {'progress': json.dumps(progress), 'temperatures': json.dumps(temps)}, retries=1)

    def webcamUpdate(self, filename, bot_id=None, job_id=None, progress=None, temps=None):
        return self.apiCall('PUT', '/bot-'+bot_id+'/update-webcam', {
            'job_id': job_id, 'progress': progress,
            'temperatures': json.dumps(temps)
        }, filepath=filename, retries=1)

    def jobInfo(self, job_id):
        return self.apiCall('GET', '/job-'+str(job_id)+'/info')

    def downloadGcode(self, fileId):
        return self.apiCall('GET', '/file-content-'+str(fileId), retries=5)

    def getMyBots(self):
        return self.apiCall('GET', '/bots', retries=1)

    def update_device_options(self, options):
        return self.apiCall('PUT', '/device/update-options', {'options': json.dumps(options)}, ignoreData=True)

    def findNewJob(self, bot_id, can_slice):
        return self.apiCall('GET', '/bot-'+str(bot_id)+'/new-job'+'/can-slice-'+can_slice)

    def getBotInfo(self, bot_id):
        return self.apiCall('GET', '/bot-info-'+str(bot_id))

    def updateBotInfo(self, bot_id, data):
        return self.apiCall('PUT', '/update-bot-'+str(bot_id), data)

    def updateSliceJob(self, job_id, status="", output="", errors="", filename=""):
        if len(output) > 7000:
            output = "Note: Output has been truncated by BotQueue:\n%s" % output[:7000]
            output = output[:output.rfind('\n')]
        return self.apiCall('PUT', '/update-slice-job-'+str(job_id), {'status': status, 'output': output, 'errors': errors},
                            filepath=filename)

    def get_config(self, bot_id):
        return self.apiCall('GET', '/bot-'+str(bot_id)+'/config')
