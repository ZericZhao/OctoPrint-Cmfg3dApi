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

        self.grabJob = function () {
            console.log("grab job");
            self.displayed.push({line: "grab job"});
            console.log(self.displayed());
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
