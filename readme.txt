Metabans plugin for Big Brother Bot (www.bigbrotherbot.net)
===========================================================

By Courgette


Description
-----------

This plugin will link your game server to your Metabans account.

As such :
 - all bans found from your Metabans account will be applied on the server.
 - all bans made from B3 will be sent to Metabans
 - when a player connects to your game server, its status will be checked from
   your Metabans account and B3 will tell connected admins if that player is 
   marked as watched or protected.
 
This plugin also provides the following commands :
 - !metabanscheck <player> - display Metabans info for player
 - !metabanswatch <player> [<reason>] - mark a player as watched
 - !metabansprotect <player> [<reason>] - mark a player as protected
 - !metabansclear <player> [<reason>] - clear any Metabans mark on the player

Visit http://metabans.com for more information


Installation
------------

 * copy the metabans folder into b3/extplugins
 * copy plugin_metabans.xml into b3/extplugins/conf
 * create an account on the Metabans website : http://metabans.com and copy
   your Metabans API key in plugin_metabans.xml
 * update your main b3 config file with :
<plugin name="metabans" config="@b3/extplugins/conf/plugin_metabans.xml" />



Changelog
---------

0.1 - 2011-06-06
 * first alpha release preview only


Support
-------

http://forum.bigbrotherbot.net/plugins-by-courgette/metabans-plugin/
