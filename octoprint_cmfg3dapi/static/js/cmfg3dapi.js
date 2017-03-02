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

        self.goToUrl = function () {
            self.currentUrl(self.newUrl);
        };
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
