(function () {
    'use strict';

    var RESTURL = 'https://app.evnotify.de/';

    /**
     * Function which sends a specific request to backend server and returns the information/data (or error information if any)
     * @param {String}      [type]      the HTTP method to use (POST|GET|PUT|DELETE)
     * @param  {String}     [fnc]       the function which should be used (e.g. login)
     * @param  {*}          [data]      the data to send (mostly an object)
     * @param  {Function}   callback    callback function
     * @return {void}
     */
    var sendRequest = function(type, fnc, data, callback) {
        try {
            var xmlHttp = new XMLHttpRequest(),
                retData;

            type = type.toUpperCase();
            data = ((typeof data === 'object' && data != null) ? data : '');

            // apply listener for the request
            xmlHttp.onreadystatechange = function() {
                if (this.readyState === 4) {
                    // try to parse the response as JSON
                    try {retData = JSON.parse(this.responseText);} catch (e) {retData = this.responseText}

                    callback(((this.status !== 200)? this.status : null), {
                        status: this.status,
                        data: retData
                    });
                }
            };
            xmlHttp.onerror = function(e) {
                callback(e, null);
            };
            // send the request
            xmlHttp.open(type, RESTURL + ((fnc)? fnc : '') + ((type === 'GET' && data) ?
                    "?" + Object
                        .keys(data)
                        .map(function(key){
                            return key+"="+encodeURIComponent(data[key])
                        })
                        .join("&") : ''
            ), true);
            xmlHttp.setRequestHeader('Content-Type', 'application/json');
            xmlHttp.send(((data)? JSON.stringify(data) : data));
        } catch (e) {
            callback(e, null);
        }
    };

    /**
     * The EVNotify constructor class
     * @constructor                 EVNotify
     */
    function EVNotify() {
        // prevent wrong declaration
        if(!(this instanceof EVNotify) || this.__previouslyConstructedByEVNotify) throw new Error('EVNotify must be called as constructor. Missing new keyword?');
        this.__previouslyConstructedByEVNotify = true;
    }

    /**
     * Function to retrieve a random akey which was available at the time of the request
     * @param  {Function} [callback]    callback function
     * @return {Object}                   returns this
     */
    EVNotify.prototype.getKey = function(callback) {
        var self = this;

        sendRequest('get', 'key', null, function(err, res) {
            // send response to callback if applied
            if(typeof callback === 'function') callback(err, ((err)? null : ((res && res.data)? res.data.akey : null)));
        });

        return self;
    };

    /**
     * Function to register account for given akey with specified password to retrieve and set token and the AKey
     * @param  {String}   akey          the AKey to register
     * @param  {String}   password      the password to use for the AKey
     * @param  {Function} [callback]    callback function
     * @return {Object}                 returns this
     */
    EVNotify.prototype.register = function (akey, password, callback) {
        var self = this;

        sendRequest('post', 'register', {akey: akey, password: password}, function(err, res) {
            // attach token
            self.token = ((!err && res && res.data)? res.data.token : null);
            // attach AKey
            self.akey = ((self.token)? akey : null);
            // send response to callback if applied
            if(typeof callback === 'function') callback(err, ((err)? null : self.token));
        });

        return self;
    };

    /**
     * Function to login account with given credentials and applies the AKey the returned token
     * @param  {String}   akey          the AKey to login
     * @param  {String}   password      the password to use for the account
     * @param  {Function} [callback]    callback function
     * @return {Object}                 returns this
     */
    EVNotify.prototype.login = function (akey, password, callback) {
        var self = this;

        sendRequest('post', 'login', {akey: akey, password: password}, function(err, res) {
            // attach token
            self.token = ((!err && res && res.data)? res.data.token : null);
            // attach AKey
            self.akey = ((self.token)? akey : null);
            // send response to callback if applied
            if(typeof callback === 'function') callback(err, ((err)? null : self.token));
        });

        return self;
    };

    /**
     * Function to change the password of the account for specified AKey with given old password and the new password
     * NOTE: Requires previous authentication via login request
     * @param  {String}   oldpassword   the old (current) password
     * @param  {String}   newpassword   the new password to set
     * @param  {Function} [callback]    callback function
     * @return {Object}                 returns this
     */
    EVNotify.prototype.changePW = function(oldpassword, newpassword, callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('post', 'changepw', {akey: self.akey, token: self.token, oldpassword: oldpassword, newpassword: newpassword}, function(err, res) {
                if(typeof callback === 'function') callback(err, (!!(!err && res)));
            });
        }

        return self;
    };

    /**
     * Function to renew and change the current token to a new persistent one
     * NOTE: Requires previous authentication via login request
     * @param  {String}   password      the password of the AKey to change the token for
     * @param  {Function} [callback]    callback function
     * @return {Object}                 returns this
     */
    EVNotify.prototype.renewToken = function(password, callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('put', 'renewtoken', {akey: self.akey, password: password}, function(err, res) {
                // attach new token
                self.token = ((!err && res && res.data && res.data.token)? res.data.token : self.token);
                if(typeof callback === 'function') callback(err, ((err)? null : self.token));
            });
        }

        return self;
    };

    /**
     * Function to get the settings and stats of the account for the given AKey
     * @param  {Function} [callback]    callback function
     * @return {Object}                 returns this
     */
    EVNotify.prototype.getSettings = function(callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('get', 'settings', {akey: self.akey, token: self.token}, function(err, res) {
                if(typeof callback === 'function') callback(err, ((!err && res && res.data && res.data.settings)? res.data.settings : null));
            });
        }

        return self;
    };

    /**
     * Function to set the settings and stats of the account for the given AKey
     * @param  {Object}   settingsObj   the object containing all keys to set
     * @param  {Function} [callback]    callback function
     * @return {Object}                 returns this
     */
    EVNotify.prototype.setSettings = function(settingsObj, callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('put', 'settings', {
                akey: self.akey,
                token: self.token,
                settings: settingsObj
            }, function(err, res) {
                if(typeof callback === 'function') callback(err, (!!(!err && res)));
            });
        }

        return self;
    };

    /**
     * Function to submit the current state of charge for the AKey
     * @param  {Number} display       the state of charge (display) to set
     * @param {Number} bms the state of charge (bms) to set
     * @param  {Function} callback  callback function
     * @return {Object}             returns this
     */
    EVNotify.prototype.setSOC = function(display, bms, callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('post', 'soc', {
                akey: self.akey,
                token: self.token,
                display: display,
                bms: bms
            }, function(err, res) {
                if(typeof callback === 'function') callback(err, (!!(!err && res)));
            });
        }

        return self;
    };

    /**
     * Function to get the current state of charge for the AKey
     * @param  {Function} callback  callback function
     * @return {Object}             returns this
     */
    EVNotify.prototype.getSOC = function(callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('get', 'soc', {
                akey: self.akey,
                token: self.token
            }, function(err, socObj) {
                if(typeof callback === 'function') callback(err,  ((!err && socObj && socObj.data) ? socObj.data : null));
            });
        }

        return self;
    };

    /**
     * Function to send out all available / enabled notifications for the AKey
     * @param  {Function} callback  callback function
     * @return {Object}             returns this
     */
    EVNotify.prototype.sendNotification = function(abort, callback) {
        var self = this;

        // check authentication
        if(!self.akey || !self.token) {
            if(typeof callback === 'function') callback(401, null); // missing previous login request
        } else {
            sendRequest('post', 'notification', {
                akey: self.akey,
                token: self.token,
                abort: abort
            }, function(err, res) {
                if(typeof callback === 'function') callback(err, (!!(!err && res)));
            });
        }

        return self;
    };

    // apply to window
    window.EVNotify = EVNotify;
}());
