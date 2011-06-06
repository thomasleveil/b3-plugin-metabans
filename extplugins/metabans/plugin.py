# encoding: utf-8
#
# Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011 Courgette
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
from ConfigParser import NoOptionError
from b3.events import EVT_CLIENT_AUTH, EVT_CLIENT_BAN, EVT_CLIENT_BAN_TEMP, \
    EVT_CLIENT_UNBAN
from b3.plugin import Plugin
from metabanproxy import MetabansProxy
from pymetabans import *
import b3
import b3.output
from datetime import datetime
import threading

__author__  = 'Courgette'
__version__ = '0.2'

USER_AGENT =  "B3 Metabans plugin/%s" % __version__
SUPPORTED_PARSERS = ('bfbc2', 'moh', 'cod4', 'cod5', 'cod6', 'cod7', 'homefront')

metabanslog = logging.getLogger('pymetabans')
metabanslog.setLevel(logging.DEBUG)
metabanslog.addHandler(b3.output.getInstance())


class MetabansPlugin(Plugin):
    _adminPlugin = None
    _message_method = None
    _metabans = None
    _admins_level = None

    def onLoadConfig(self):
        self._metabans = MetabansProxy(self.console.gameName, user_agent=USER_AGENT)
        
        # get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        # register our commands
        if 'commands' in self.config.sections():
            def getCmd(cmd):
                cmd = 'cmd_%s' % cmd
                if hasattr(self, cmd):
                    func = getattr(self, cmd)
                    return func
                return None
    
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        # load Metabans_account
        try:
            self._metabans.username = self.config.get('metabans_account', 'username')
        except NoOptionError, err:
            self.error('cannot read metabans_account/username from config file (%s)', err)
            raise Exception("cannot read metabans_account/username from config file")

        try:
            self._metabans.apikey = self.config.get('metabans_account', 'api_key')
        except NoOptionError, err:
            self.error('cannot read metabans_account/api_key from config file (%s)', err)
            raise Exception("cannot read metabans_account/api_key from config file")
        
        try:
            self._metabans.group_name = self.config.get('metabans_account', 'group_name')
        except NoOptionError, err:
            self.error('cannot read metabans_account/group_name from config file (%s)', err)
        
        try:
            self._admins_level = self._adminPlugin.config.get('settings', 'admins_level')
        except NoOptionError, err:
            self.error('cannot read settings/admins_level from admin plugin config file (%s)', err)
            self._admins_level = 60
        self.info("using %s for admins level", self._admins_level)
        
        
            
        # load preferences
        try:
            msgtype = self.config.get('preferences', 'message_type')
            if msgtype.lower() == 'normal':
                self._message_method = self.console.say
                self.info("message_type is : normal")
            elif msgtype.lower() == 'big':
                self._message_method = self.console.saybig
                self.info("message_type is : big")
            else:
                self._message_method = self.info
                self.info("message_type is : none")
        except NoOptionError, err:
            self.warning('cannot read preferences/message_type from config file (%s)', err)
            


    def onStartup(self):
        if self.console.gameName not in SUPPORTED_PARSERS:
            self.error("This game is not supported by this plugin")
            self.disable()
            return
        self.registerEvent(EVT_CLIENT_AUTH)
        self.registerEvent(EVT_CLIENT_BAN)
        self.registerEvent(EVT_CLIENT_BAN_TEMP)
        self.registerEvent(EVT_CLIENT_UNBAN)

#        self._checkConnectedPlayers()


    def onEvent(self, event):
        if event.type == EVT_CLIENT_AUTH:
            threading.Thread(target=self.onClientAuth, args=(event,)).start()
        elif event.type == EVT_CLIENT_BAN:
            threading.Thread(target=self.onClientBan, args=(event,)).start()
        elif event.type == EVT_CLIENT_BAN_TEMP:
            threading.Thread(target=self.onClientTempBan, args=(event,)).start()
        elif event.type == EVT_CLIENT_UNBAN:
            threading.Thread(target=self.onClientUnBan, args=(event,)).start()


    #===============================================================================
    # 
    #    Event handling
    #
    #===============================================================================

    def onClientAuth(self, event):
        client = event.client
        if client:
            self.info("sending sighting event to Metabans for %s", client.name)
            try:
                response = self._metabans.sight(client)
                self._onMetabanResponse(client, response)
            except MetabansAuthenticationError:
                self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                self.disable()
            except MetabansError, err:
                self.error(err)


    def onClientBan(self, event):
        client = event.client
        if client:
            self.info("sending ban event to Metabans for %s", client.name)
            try:
                if isinstance(event.data, basestring):
                    reason = event.data
                else:            
                    try:
                        reason = event.data['reason']
                    except KeyError:
                        reason = None
                self._metabans.ban(client, reason=reason)
            except MetabansAuthenticationError:
                self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                self.disable()
            except MetabansException, err:
                self.error(err)


    def onClientTempBan(self, event):
        client = event.client
        if client:
            self.info("sending tempban event to Metabans for %s", client.name)
            try:
                try:
                    duration = event.data['duration']
                except KeyError:
                    duration = 60*60*24 # 1 day in seconds
                if isinstance(event.data, basestring):
                    reason = event.data
                else:            
                    try:
                        reason = event.data['reason']
                    except KeyError:
                        reason = None
                self._metabans.ban(client, 
                                   duration=duration,
                                   reason=reason)
            except MetabansAuthenticationError:
                self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                self.disable()
            except MetabansException, err:
                self.error(err)


    def onClientUnBan(self, event):
        client = event.client
        if client:
            self.info("sending unban event to Metabans for %s", client.name)
            try:
                if isinstance(event.data, basestring):
                    reason = event.data
                else:            
                    try:
                        reason = event.data['reason']
                    except KeyError:
                        reason = None
                self._metabans.clear(client, reason=reason)
            except MetabansAuthenticationError:
                self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                self.disable()
            except MetabansException, err:
                self.error(err)


    #===========================================================================
    # 
    # Commands implementations
    # 
    #===========================================================================

    def cmd_metabanscheck(self, data=None, client=None, cmd=None):
        """\
        <player> get Metabans info for a player
        """
        # this will split the player name and the message
        inputparam = self._adminPlugin.parseUserCmd(data)
        if not inputparam:
            client.message('^7Invalid parameters')
        else:
            sclient = self._adminPlugin.findClientPrompt(inputparam[0], client)
            if not sclient:
                # a player matching the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return False
            else:
                self.debug('checking %s (%s)', sclient, sclient.guid)
                try:
                    response = self._metabans.check(sclient)
                    self._tellMetabansResponse(client, sclient, response)
                    self._onMetabanResponse(sclient, response)
                except MetabansAuthenticationError:
                    self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                    client.message("bad METABANS username or api_key. Disabling Metaban plugin")
                    self.disable()
                except MetabansError, err:
                    self.error(err)
                    client.message("Metabans replied with error %s" % err)


    def cmd_metabanswatch(self, data=None, client=None, cmd=None):
        """\
        <player> [<reason>] - mark a player as watched
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        
        cid, keyword = m
        reason = self._adminPlugin.getReason(keyword)

        if not reason and client.maxLevel < self._adminPlugin.config.getint('settings', 'noreason_level'):
            client.message('^1ERROR: ^7You must supply a reason')
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.maxLevel > client.maxLevel:
                if sclient.maskGroup:
                    client.message('^7%s ^7is a masked higher level player, can\'t watch' % sclient.name)
                else:
                    client.message('^7%s ^7is a higher level player, can\'t do' % sclient.name)
                return True
            else:
                try:
                    self.info("telling Metabans that %s is under watch", sclient.name)
                    response = self._metabans.watch(sclient, reason=reason)
                    self._tellMetabansResponse(client, sclient, response)
                except MetabansAuthenticationError:
                    self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                    client.message("bad METABANS username or api_key. Disabling Metaban plugin")
                    self.disable()
                except MetabansError, err:
                    self.error(err)
                    client.message("Metabans replied with error %s" % err)


    def cmd_metabansprotect(self, data=None, client=None, cmd=None):
        """\
        <player> [<reason>] - mark a player as protected
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        
        cid, keyword = m
        reason = self._adminPlugin.getReason(keyword)

        if not reason and client.maxLevel < self._adminPlugin.config.getint('settings', 'noreason_level'):
            client.message('^1ERROR: ^7You must supply a reason')
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.maxLevel > client.maxLevel:
                if sclient.maskGroup:
                    client.message('^7%s ^7is a masked higher level player, can\'t protect' % sclient.name)
                else:
                    client.message('^7%s ^7is a higher level player, can\'t do' % sclient.name)
                return True
            else:
                try:
                    response = self._metabans.protect(sclient, reason=reason)
                    self._tellMetabansResponse(client, sclient, response)
                except MetabansAuthenticationError:
                    self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                    client.message("bad METABANS username or api_key. Disabling Metaban plugin")
                    self.disable()
                except MetabansError, err:
                    self.error(err)
                    client.message("Metabans replied with error %s" % err)


    def cmd_metabansclear(self, data=None, client=None, cmd=None):
        """\
        <player> [<reason>] - remove any Metabans mark on a player
        """
        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid parameters')
            return False
        
        cid, keyword = m
        reason = self._adminPlugin.getReason(keyword)

        if not reason and client.maxLevel < self._adminPlugin.config.getint('settings', 'noreason_level'):
            client.message('^1ERROR: ^7You must supply a reason')
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.maxLevel > client.maxLevel:
                if sclient.maskGroup:
                    client.message('^7%s ^7is a masked higher level player, can\'t clear' % sclient.name)
                else:
                    client.message('^7%s ^7is a higher level player, can\'t clear' % sclient.name)
                return True
            else:
                try:
                    response = self._metabans.clear(sclient, reason=reason)
                    self._tellMetabansResponse(client, sclient, response)
                except MetabansAuthenticationError:
                    self.error("bad METABANS username or api_key. Disabling Metaban plugin")
                    client.message("bad METABANS username or api_key. Disabling Metaban plugin")
                    self.disable()
                except MetabansError, err:
                    self.error(err)
                    client.message("Metabans replied with error %s" % err)


    #=======================================================================
    # 
    # Other
    # 
    #=======================================================================

    def _notify_admins(self, player, msg):
        """send a message to each connected admin"""
        clients = self.console.clients.getList()
        for c in clients:
            if c.maxLevel >= self._admins_level:
                if c is player:
                    self.info("not telling %s because the msg is about him : %s" % (
                                                                c.name, msg))
                else:
                    c.message(msg)

    def _checkClient(self, client):
        """\
        get Metaban info for a player and allow/deny connection.
        """
        self.debug('checking %s (%s)', client, client.guid)
        try:
            self._onMetabanResponse(client, self._metabans.check(client))
        except MetabansAuthenticationError:
            self.error("bad METABANS username or api_key. Disabling Metaban plugin")
            self.disable()
        except MetabansError, err:
            self.error(err)

    def _tellMetabansResponse(self, client, target_client, response):
        self.debug("response: %r", response)
        if response:
            if response['is_blacklisted'] == True:
                if response['inherited_blacklist']:
                    client.message("%s Metabans status is : banned by %s" % (target_client.name, response['inherited_blacklist']))
                else:
                    client.message("%s Metabans status is : banned" % target_client.name)
                if response['assessment_expires']:
                    dt = datetime.fromtimestamp(float(response['assessment_expires']))
                    client.message("ban will expire on %s" % dt.strftime("%A, %d. %B %Y %I:%M%p %z"))
                if response['reason']:
                    client.message("reason: %s" % response['reason'])
            elif response['is_whitelisted'] == True:
                client.message("%s Metabans status is : protected" % target_client.name)
                if response['reason']:
                    client.message("reason: %s" % response['reason'])
            elif response['is_watched'] == True:
                client.message("%s Metabans status is : watched" % target_client.name)
                if response['reason']:
                    client.message("reason: %s" % response['reason'])
            else:
                client.message("%s has no particular status on Metabans" % target_client.name)
            self._onMetabanResponse(target_client, response)
        else:
            client.message("no response from Metabans")

    def _onMetabanResponse(self, client, response):
        if response:
            if response['is_blacklisted'] == True:
                self.onBlacklisted(client, reason=response['reason'], 
                                   inherited_blacklist=response['inherited_blacklist'])
            elif response['is_whitelisted'] == True:
                self.onWhitelisted(client, reason=response['reason'])
            elif response['is_watched'] == True:
                self.onWatched(client, reason=response['reason'])
        else:
            self.warning("no response from Metabans")


    def onBlacklisted(self, client, reason=None, inherited_blacklist=None):
        client.tempban('METABANS BANNED [%s]' % client.name, keyword="METABANS", silent=True, reason=reason)
        try:
            msg = self.getMessage('ban_message', 
                                  b3.parser.Parser.getMessageVariables(
                                                               self.console, 
                                                               client=client,
                                                               reason=reason))
            if msg and msg!="":
                self._message_method(msg)
        except NoOptionError:
            self.warning("could not find message ban_message in config file")


    def onWatched(self, client, reason=None):
        self._notify_admins(client, "METABANS: %s is under watch for : %s" % (client.name, reason))


    def onWhitelisted(self, client, reason=None):
        self._notify_admins(client, "METABANS: %s is protected" % client)


if __name__ == '__main__':
    import time
    from b3.fake import fakeConsole, superadmin, joe, moderator
    
    metabanlog = logging.getLogger('pymetabans')
    metabanlog.setLevel(logging.DEBUG)
    metabanlog.addHandler(logging.StreamHandler())
    
    conf1 = b3.config.XmlConfigParser()
    conf1.loadFromString("""
        <configuration plugin="metabans">
          <settings name="metabans_account">
              <!-- To use this plugin you need to register at http://metabans.com
              and report below your Metabans username and API key -->
              <set name="username">xxxxx</set>
              <set name="api_key">xxxxx</set>
              <!-- When you report player sightings to Metabans.com, you can 
              associate them to a group. This is usually used to identify the
              game server the player was seen on if you have many -->
              <set name="group_name"></set>
            </settings>
          <settings name="commands">
            <!-- !metabanscheck <player> - display Metabans info for player -->
            <set name="metabanscheck-mbc">20</set>
            <!-- !metabanswatch <player> [<reason>] - mark a player as watched -->
            <set name="metabanswatch-mbw">20</set>
            <!-- !metabansprotect <player> [<reason>] - mark a player as protected -->
            <set name="metabansprotect-mbp">20</set>
            <!-- !metabansclear <player> [<reason>] - clear any Metabans mark on the player -->
            <set name="metabansclear-mbc">20</set>
          </settings>
          <settings name="preferences">
            <!-- message_type defines how you want the ban message to be
              displayed on your game server :
                none : won't be displayed
                normal : normal chat message
                big : more noticeable message
            -->
            <set name="message_type">big</set>
          </settings>
          <settings name="messages">
            <!-- You can use the following keywords in your messages :
              $clientname
              $clientguid
              $reason 
            -->
            <!-- ban_message will be displayed to all players when a player is found on
            Metabans.com banlist -->
            <set name="ban_message">METABANS $clientname ($clientguid) $reason</set>
          </settings>
        </configuration>
    """)
    fakeConsole.gameName = 'bfbc2'
    p = MetabansPlugin(fakeConsole, conf1)
    
    from getopt import getopt
    import sys

    api_username = None
    api_key = None
    opts, args = getopt(sys.argv[1:], 'h:u:k:')
    for k, v in opts:
        if k == '-h':
            print("""
Usage: 
 -h : print this help
 -u : Metabans username
 -k : Metabans API key
""")
            sys.exit(0)
        elif k == '-u':
            api_username = int(v)
        elif k == '-k':
            api_key = v
    import shelve
    d = shelve.open('metabans_test_account.shelve')
    if api_username == api_key == None:
        if d.has_key('username'):
            api_username = d['username']
        if d.has_key('key'):
            api_key = d['key']
    if api_username is None:
        api_username = raw_input('Enter your Metabans username : ')
    if api_key is None:
        api_key = raw_input('Enter your Metabans API key : ')
    d['username'] = api_username
    d['key'] = api_key
    d.close()
    
    
    p._metabans.username = api_username
    p._metabans.apikey = api_key
    
    def test_Command_check():
        p.onStartup()
        
        superadmin.connects(0)
        time.sleep(1)
        
        joe._guid = "76561197976827962"
        joe.connects(1)
        
        time.sleep(1)
        superadmin.says('!metabanscheck joe')
        time.sleep(60)

    def test_ban_event():
        p.onStartup()
        
        superadmin.connects(0)
        time.sleep(1)
        
        joe._guid = "76561197976827962"
        joe.connects(1)
        
        time.sleep(1)
        superadmin.says('!permban joe test_perm_ban')
        
        time.sleep(3)
        joe.connects(2)
        
        time.sleep(60)

    def test_tempban_event():
        p.onStartup()
        
        superadmin.connects(0)
        time.sleep(1)
        
        joe._guid = "76561197976827962"
        joe.connects(1)
        
        time.sleep(1)
        superadmin.says('!tempban joe 1w test_1w_ban')
        
        time.sleep(3)
        joe.connects(2)
        
        time.sleep(60)
     
    #test_Command_check()
    test_ban_event()
    #test_tempban_event()
