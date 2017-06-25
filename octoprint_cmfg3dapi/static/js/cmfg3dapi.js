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

        self.requestToken = function () {
            $.get("/plugin/cmfg3dapi/authorize",{}).done(function (content) {
                self.displayed.push({line: content});
                self.log(content);
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
                // var settings = JSON.parse(content);
                // self.displayed.push({line: "consumerKey from set: "+settings["consumerKey"]});
                // self.displayed.push({line: "consumerSecret from set: "+settings["consumerSecret"]});
                // self.displayed.push({line: "consumerKey from obj: "+settings[2]});
                // self.displayed.push({line: "consumerSecret from obj: "+settings[3]});
                self.displayed.push({line: content});
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
