/*
 * View model for OctoPrint-Cmfg3dApi
 *
 * Author: Zeric Zhao
 * License: AGPLv3
 */
$(function() {
    function Cmfg3dapiViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        // TODO: Implement your plugin's view model here.
        self.settings = parameters[0];
        self.currentUrl = ko.observable();
        self.newUrl = ko.observable();
        self.displayed = ko.observableArray([]);

        self.register = function () {
            $.get("/plugin/cmfg3dapi/register",{}).done(function (content) {
                if (content.startsWith("http")) {
                    self.displayed.push({line: "Authorize client trough the following url:"})
                    self.displayed.push({line: content});
                } else {
                    self.displayed.push({line: content});
                }
            });
        };

        self.onBeforeBinding = function () {
            self.newUrl(self.settings.settings.plugins.cmfg3dapi.url())
        };

        self.getAccessToken = function () {
            $.get("/plugin/cmfg3dapi/getAccessToken", {}).done(function (content) {
                if (Boolean(content["tokenKey"])){
                    self.displayed.push({line: "Please setup token manually."});
                    self.displayed.push({line: "token key: "+content["tokenKey"]});
                    self.displayed.push({line: "token secret: "+content["tokenSecret"]});
                } else {
                    self.displayed.push({line: content});
                }
            })
        };

        self.updateOptions = function () {
            $.get("/plugin/cmfg3dapi/updateOptions", {}).done(function (options) {
                console.log(options);
                var content = "ports: ";
                for (var i=0; i<options.ports.length; i++){
                    content += options.ports[i];
                }
                self.displayed.push({line: content});
            })
        };

        self.startPrint = function () {

        };

        self.listQueue = function () {
            $.get("/plugin/cmfg3dapi/listQueue", {}).done(function (content) {
                console.log(content);
                var queues = JSON.parse(content);
                for (var i=0; i<queues.length; i++){
                    var queue = queues[i];
                    self.displayed.push({line: "queue id: "+queue.id+" name: "+queue.name});
                }
            });
        };

        self.getBots = function () {
            $.get("/plugin/cmfg3dapi/getBots", {}, function (content) {
                console.log(content);
                var bots = JSON.parse(content);
                for (var i=0; i<bots.length; i++){
                    var bot = bots[i];
                    self.displayed.push({line: "bot id: "+bot.id+" name: "+bot.name});
                }
            });
        };

        self.listJobs = function () {
            $.get("/plugin/cmfg3dapi/listJobs", {}, function (content) {
                console.log(content);
                var jobs = JSON.parse(content);
                for (var i=0; i<jobs.length; i++){
                    var job = jobs[i];
                    self.displayed.push({line: "job id: "+job.id+" name: "+job.name});
                }
            });
        };

        self.grabJob = function () {
            $.get("/plugin/cmfg3dapi/grabJob", {}).done(function (content) {
                console.log(content);
                self.displayed.push({line: "grab job: "+content});
            });
        };

        self.getJob = function () {
            $.get("/plugin/cmfg3dapi/getJob",{},function (content) {
                console.log(content);
                self.displayed.push({line: "get job: "+content});
            });
        };

        self.download = function () {
            $.get("/plugin/cmfg3dapi/download", {}, function (content) {
                console.log(content);
            });
        };

        self.startPrint = function () {
            $.get("/plugin/cmfg3dapi/startPrint",{},function (content) {
                console.log(content);
                self.displayed.push({line: content});
            });
        };

        self.autorun = function () {
            $.get("/plugin/cmfg3dapi/autorun",{},function (content) {
                console.log(content);
            });
        };

        self.clearTerminal = function () {
            self.displayed = ko.observableArray([]);
        };

        self.checkSettings = function () {
            $.get("/plugin/cmfg3dapi/checkSettings", {}).done(function (content) {
                console.log(content);
                self.displayed.push({line: "consumerKey from set: "+content["consumerKey"]});
                self.displayed.push({line: "consumerSecret from set: "+content["consumerSecret"]});
                self.displayed.push({line: "authorized: "+content["authorized"]});
                if (Boolean(content['tokenKey'])){
                    self.displayed.push({line: "tokenKey from obj: "+content['tokenKey']});
                    self.displayed.push({line: "tokenSecret from obj: "+content['tokenSecret']});
                }
            })
        }
    }

    // view model class, parameters for constructor, container to bind to
    OCTOPRINT_VIEWMODELS.push([
        Cmfg3dapiViewModel,

        // e.g. loginStateViewModel, settingsViewModel, ...
        [ "settingsViewModel" ],

        // e.g. #settings_plugin_cmfg3dapi, #tab_plugin_cmfg3dapi, ...
        [ "#tab_plugin_cmfg3dapi" ]
    ]);
});
