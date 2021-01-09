---
title: EVNotify API
language_tabs:
  - shell: Shell
  - javascript: JavaScript
toc_footers:
  - >-
    <a href="https://github.com/GPlay97/EVNotifyAPI">Edit the doc files</a>
includes: []
search: true
highlight_theme: darkula
headingLevel: 2

---

<h1 id="EVNotify-API">EVNotify API</h1>

> Scroll down for code samples, example requests and responses. Select a language for code samples from the tabs above or the mobile navigation menu.
> Complete documentation and libraries for EVNotify API can be found on <a href="https://github.com/GPlay97/EVNotifyAPI">GitHub</a>

Welcome to the EVNotify API! You can use the API to set and fetch useful information.

This API is in an early-access development. 

Feel free to enhance this API Documentation and send suggestions to improve the API by itself.

To be able to use this API, you must register an account. With registering an account, you agree to the terms of use of EVNotify.

Base URLs:

* <a href="https://github.com/GPlay97/EVNotifyAPI">EVNotify API on GitHub</a>

* <a href="https://evnotify.de">EVNotify Website</a>

<h1 id="EVNotify-API-v1">v1</h1>

EVNotify API v1.

HTTPS endpoint uses port <b>8743</b> (https://evnotify.de:8743).
HTTP endpoint is no longer available.
<b>HTTPS is required.</b>

<aside class="warning">
Using the v1 API is deprecated and no longer recommended. You should switch to the improved v2 API as soon as possible.
</aside>

## Authentication

<a id="opIdAuthentication"></a>

To be able to interact with the EVNotify API, most requests requires an authentication.
This is done by providing your so called AKey, which is your account identifier, to the request together with
your personal token.
<aside class="warning">
Don't share your personal token with others! Keep it safe!
</aside>

## Get a new key

If you don't have an AKey yet, you have to create a new account in order to be able to interact with the whole API.
To get a new AKey, you can do so with the following request. This will return a currently unused AKey, which you can
register.

<aside class="notice">
This will not reserve the requested AKey. It just returns a possible AKey combination, which isn't in use yet.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/getkey`

```shell
curl "https://evnotify.de:8743/getkey"
  -H "Content-Type: application/json"
```

> The request returns JSON like this:

```json
{
  "akey": 1234
}
```

```javascript
var evnotify = new EVNotify();

// get an unused key
evnotify.getKey(function(err, key) {
  console.log('Key: ', key);  // Key: 1234 for example
});
```

## Register a new account

<a id="opIdRegister"></a>

After retrieving an unused AKey, you can register it. You need to specify the AKey, as well as a password. For your own safety, you should choose a strong password. The minimum length for a valid password is 6 characters.

<aside class="warning">
Currently there is no possibility to recover a lost password. You can only change the password if you know the old one.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/register`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey to register
password | The password to use

```shell
curl "https://evnotify.de:8743/register"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","password":"password"}'
```

> The request returns JSON like this:

```json
{
  "message": "Registration successful",
  "token": "secrettoken"
}
```

```javascript
var evnotify = new EVNotify();

// register new account
evnotify.register('akey', 'password', function(err, token) {
  console.log('Token: ', token);  // Contains the token for authentication
});
```

<aside class="success">
The AKey and the retrieved token will be stored within the EVNotify instance.
In this sample, you would access them with evnotify.akey and evnotify.token.
</aside>


## Login with existing account

<a id="opIdLogin"></a>

Once you've registered an account - or already have an account, you can login with your credentials.
This will give you the token, which authenticates your account.

<aside class="notice">
As long as you don't force a renewal of your token, the token will stay the same.
Because of that you can save the token safely so you don't need to login every time.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/register`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to login
password | The password of the account

```shell
curl "https://evnotify.de:8743/login"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","password":"password"}'
```

> The request returns JSON like this:

```json
{
  "message": "Login successful",
  "token": "secrettoken"
}
```

```javascript
var evnotify = new EVNotify();

// login with account
evnotify.login('akey', 'password', function(err, token) {
  console.log('Token: ', token);  // Contains the token for authentication
});
```

## Change the password for an account

<a id="opIdChangePW"></a>

In order to be able to change the password for an account, you need to first enter your old password.
Currently it is not possible to recover a lost password.

<aside class="warning">
Changing the password will NOT change the token. It just sets a new password, so next time
you try login, you will have to use the new password instead of the old one.
If you want to change the token instead, have a further look at the token renewal section.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/password`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to change the password for
token | The token of the account
password | The old password of the account
newpassword | The new password to set

```shell
curl "https://evnotify.de:8743/password"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token": "token","password":"oldpassword", "newpassword": "newpassword"}'
```

> The request returns JSON like this:

```json
{
  "message": "Password change succeeded"
}
```

```javascript
var evnotify = new EVNotify();

// change password for account
evnotify.changePW('oldpassword', 'newpassword', function(err, changed) {
  console.log('Password changed: ', changed);  // True, if change was successful
});
```

## Renew the account token

<a id="opIdRenewToken"></a>

In order to be able to renew the token of your account, you will need to provide the AKey as well as the password of the account.
Changing the account token in regular periods is a good security manner.

<aside class="warning">
Renewing the token instantly changes the token of the account, so the old token is no longer usable.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/renewtoken`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to renew the token for
password | The password of the account

```shell
curl "https://evnotify.de:8743/renewtoken"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","password":"password"}'
```

> The request returns JSON like this:

```json
{
  "message": "Token renewed",
  "token": "newtoken"
}
```

```javascript
var evnotify = new EVNotify();

// renew token of the account
evnotify.renewToken('password', function(err, token) {
  console.log('New token: ', token);  // The new token
});
```

## Get settings and stats from account

<a id="opIdGetSettings"></a>

Every account has a collection of settings and stats. Those collection store information about the connection and settings for the state of charge monitoring and notification.

<aside class="notice">
This request returns all settings and stats. If you only want to fetch the current state of charge, you can use the syncSoC request.
This will decrease the data usage and processing time for the request.
</aside>

<aside class="notice">
If you want to get the settings without providing the password, use the sync request instead.
This require to have 'autoSync' enabled for the account.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/settings`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to retrieve the settings for
token | The token of the account
password | The password of the account
option | must be 'GET' to retrieve the settings

```shell
curl "https://evnotify.de:8743/settings"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token": "token","password":"password", "option": "GET"}'
```

> The request returns JSON like this:

```json
{
  "message": "Get settings succeeded",
  "settings": {
    "email": "email",
    "telegram": "telegram",
    "soc": "soc",
    "curSoC": "curSoC",
    "device": "device",
    "polling": "polling",
    "autoSync": "autoSync",
    "lng": "lng",
    "push": "push"
  }
}
```

```javascript
var evnotify = new EVNotify();

// get the settings and stats for account
evnotify.getSettings('password', function(err, settingsObj) {
  console.log('Settings: ', settingsObj);  // Object containing all the settings and stats
});
```

## Set settings and stats for account

<a id="opIdSetSettings"></a>

You can modify the settings for the state of charge monitoring, notification and other settings and stats for the account.
Be careful, since wrong changes can break a working notification or other things.

<aside class="warning">
Even when you only want to modify one setting property, you will need to send all the settings.
Otherwise missing keys will be reseted and emptied.
So it is recommended to first retrieve all the current settings with the getSettings request and then just modify the properties you want to change.
</aside>

<aside class="notice">
If you want to set the settings without providing the password, use the sync request instead.
This require to have 'autoSync' enabled for the account.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/settings`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to retrieve the settings for
token | The token of the account
password | The password of the account
option | must be 'SET' to apply the settings
optionObj | object containing all the properties to save (see getSettings properties output to get full list)

```shell
curl "https://evnotify.de:8743/settings"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token": "token","password":"password", "option": "SET", "optionObj": "{}"}'
```

> The request returns JSON like this:

```json
{
  "message": "Set settings succeeded"
}
```

```javascript
var evnotify = new EVNotify(),
    settingsObj = {}; // the settings object containing all properties

// set the settings and stats for account
evnotify.setSettings('password', settingsObj, function(err, set) {
  console.log('Settings saved: ', set);  // True, if successful
});
```

## Synchronize the settings and stats

<a id="opIdSyncSettings"></a>

If you want to synchronize the settings and stats of an account without entering a password (for example when you want to synchronize them in the background),
you can make use of the sync request. This request allows you to retrieve or set the settings without being prompted for a password.
Please note, that this requires to have 'autoSync' option set previously with the setSettings request, if not enabled yet.

<aside class="warning">
Disabling 'autoSync' prevents you from using the sync request, so you can't retrieve or set the settings and stats without a password.
You still need a token, even when 'autoSync' has been enabled.
</aside>

<aside class="notice">
This request does the same as getSettings or setSettings request, but it doesn't require a password.
If you want to use the normal requests to change or get the settings, use those requests instead.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/sync`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to sync the settings for
token | The token of the account
type | determines whether you want to retrieve the settings ('PULL' as type) or set the settings ('PUSH' as type)
syncObj | the settings object you want to set (only necessary if 'PUSH' as type)

```shell
curl "https://evnotify.de:8743/sync"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token":"token", "type": "PULL"}'
```
> The sync request (PULL) returns JSON like this:

```json
{
  "message": "Pull for sync succeeded",
  "syncRes": {
      "email": "email",
      "telegram": "telegram",
      "soc": "soc",
      "curSoC": "curSoC",
      "device": "device",
      "polling": "polling",
      "autoSync": "autoSync",
      "lng": "lng",
      "push": "push"
  }
}
```

```shell
curl "https://evnotify.de:8743/sync"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token":"token", "type": "PUSH", syncObj: "{}"}'
```

> The sync request (PUSH) returns JSON like this:

```json
{
  "message": "Push for sync succeeded",
  "syncRes": true
}
```

```javascript
var evnotify = new EVNotify(),
    syncObj = {};   // the settings object containing all required information

// retrieve the settings
evnotify.pullSettings(function(err, settingsObj) {
  console.log('Settings: ', settingsObj);  // The settings and stats of the account
});

// set the settings
evnotify.pushSettings(syncObj, function(err, pushed) {
  console.log('Push succeeded: ', pushed);
});
```

## Synchronize the state of charge

<a id="opIdSyncSoC"></a>

The main advantage of EVNotify is the monitoring of the state of charge. To be able to track it and fetch it at any time, you'll need to inform the server about the current value.
You can also manually set the 'curSoC' property within the sync (type 'PUSH') or setSettings request. But the syncSoC request will only update the state of charge and decreases the data usage.

<aside class="notice">
The syncSoC request only sets the current state of charge. To be able to retrieve the state of charge later, you will need to use the sync request (type 'PULL') or the getSettings request.
Later, there will also be an additional request, which will directly give you the last submitted state of charge along with some other information.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/syncSoC`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to sync the state of charge for
token | The token of the account
soc | The state of charge you want to submit

```shell
curl "https://evnotify.de:8743/syncSoC"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token":"token", "soc": 42}'
```
> The request returns JSON like this:

```json
{
  "message": "Sync for soc succeeded"
}
```

```javascript
var evnotify = new EVNotify();

// submit the current state of charge
evnotify.syncSoC(42, function(err, synced) {
  console.log('SoC sync succeeded: ', synced);
});
```

## Notifications

<a id="opIdNotifications"></a>

After submitting the current state of charge, you may want to send out notifications, if the desired state of charge has been achieved.
This process will NOT be automatically triggered, even when you set a soc threshold.
The notification request will send the notifications to all available notification ways, which were available / enabled at the time of the request.
If no notification way has been declared, no notification will be sent out, but also no error will be received.

<aside class="warning">
This request will be processed completely asynchronously and run in the background. For that reason, you will not informed about eventually mistakes (e.g. non-existing mail).
You can not choose a specific way of notification, all available notifications, which were activated for the account, will be sent out.
</aside>

<aside class="notice">
There are currently three types of notification ways: Mail, Telegram and Push. But Push isn't available yet.
Telegram also offers real-time information and many more things. More information will be found within the EVNotify Wiki.
</aside>

### HTTPS Request

`POST https://evnotify.de:8743/notification`

### URL Parameters

Parameter | Description
--------- | -----------
akey | The AKey of the account to send the notifications for
token | The token of the account

```shell
curl "https://evnotify.de:8743/notification"
  -H "Content-Type: application/json"
  -X POST -d '{"akey":"akey","token":"token"}'
```
> The request returns JSON like this:

```json
{
  "message": "Notifications successfully sent"
}
```

```javascript
var evnotify = new EVNotify();

// sends all available notification types which are enabled for account
evnotify.sendNotification(function(err, sent) {
  console.log('Notifications sent: ', sent);
});
```
