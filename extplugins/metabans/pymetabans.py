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
'''A library that provides a Python interface to the Metabans API'''
__author__  = 'courgette@bigbrotherbot.net'
__version__ = '1.0'

try:
    # Python >= 2.6
    import json
except ImportError:
    try:
        # Python < 2.6
        import simplejson as json
    except ImportError:
        raise ImportError, "Unable to load a json library"

import logging
import urllib
import urllib2

log = logging.getLogger('pymetabans')

"""whenever the Metabans service answers with an error""" 
class MetabansException(Exception): pass
"""whenever the Metabans service answers with a known error""" 
class MetabansError(MetabansException): pass
class MetabansAuthenticationError(MetabansError): pass

class Player:
    def __init__(self, uid, name, ip=None, alternate_uid=None):
        self.uid = uid
        self.name = name
        self.ip = ip
        self.alternate_uid = alternate_uid
        
class Metabans(object):
    def __init__(self, username=None, apikey=None, user_agent='pymetabans', 
                 url="http://metabans.com/api"):
        self._service_url = url
        self._user_agent = user_agent
        self.username = username
        self.apikey = apikey


    def mbo_player_status(self, game_name, player_uid):
        """Discovers a players current status
        
             game_name : game identifier http://wiki.metabans.com/Supported_Games
            player_uid : a Player identifier
            
        """
        query_parameters = {}
        query_parameters['requests[0][action]'] = 'mbo_player_status'
        query_parameters['requests[0][game_name]'] = game_name
        query_parameters['requests[0][player_uid]'] = player_uid
        return self._query(query_parameters)


    def mbo_availability_account_name(self, usernames):
        """Ask Metabans for a usernames availability"""
        if isinstance(usernames, basestring):
            usernames = (usernames,)
        query_parameters = {}
        i = 0
        for name in usernames:
            query_parameters['requests[%s][action]' % i] = 'mbo_availability_account_name'
            query_parameters['requests[%s][account_name]' % i] = name
            i += 1
        return self._query(query_parameters)


    def mb_sight_player(self, game_name, players,  group_name=None):
        """Tells Metabans that we have seen one or many players on our game 
            server    
        
             game_name : game identifier http://wiki.metabans.com/Supported_Games
               players : a Player object or a collection of Player objects
            group_name : if you have multiple game servers under a single 
                         Metabans account, this can be used to identify each
                         game server 
            
        """
        if isinstance(players, Player):
            players = (players, )
        i = 0
        query_parameters = {}
        for _p in players:
            query_parameters['requests[%s][action]' % i] = 'mb_sight_player'
            query_parameters['requests[%s][game_name]' % i] = game_name
            if group_name:
                query_parameters['requests[%s][group_name]' % i] = group_name
            # now player info :
            query_parameters['requests[%s][player_uid]' % i] = _p.uid
            query_parameters['requests[%s][player_name]' % i] = _p.name
            if _p.ip:
                query_parameters['requests[%s][player_ip]' % i] = _p.ip
            if _p.alternate_uid:
                query_parameters['requests[%s][alternate_uid]' % i] = _p.alternate_uid
            i += 1
        return self._query(query_parameters)


    def mb_assess_player(self, game_name, player_uid, assessment_type, 
                         assessment_length=None, reason=None):
        """Assess a player at Metabans
        
                game_name : game identifier http://wiki.metabans.com/Supported_Games
               player_uid : player identifier for that game (guid)
          assessment_type : one of 'none', 'watch', 'white', 'black'
        assessment_length : The length of time in seconds that a ban should be 
                            enforced. This can be negative which would be the 
                            same as having no assessment at all.
                   reason : string, max 200 chars - A reason for the assessment. 
                            Can be any text, but #hashtags are encouraged to 
                            allow for easier grouping of ban types
            
        """
        query_parameters = {}
        query_parameters['requests[0][action]'] = 'mb_assess_player'
        query_parameters['requests[0][game_name]'] = game_name
        # now player info :
        query_parameters['requests[0][player_uid]'] = player_uid
        query_parameters['requests[0][assessment_type]'] = assessment_type
        if assessment_length:
            query_parameters['requests[0][assessment_length]'] = int(assessment_length)
        if reason:
            query_parameters['requests[0][reason]'] = reason
        return self._query(query_parameters)


    def _query(self, parameters):
        """Make the HTTP request to the Metabans service and decode the json
        response. 
        
        If we have a single response, then only the 'data' part of the response
        will be return and errors will raise MetabansExceptions
        
        If we have multiples responses, then raw json response is returned
        """
        query_parameters = {'options': 'mirror,json,profiler'}
        if self.username and self.apikey:
            query_parameters['username'] = self.username
            query_parameters['apikey'] = self.apikey
        for k,v in parameters.iteritems():
            query_parameters[k] = v
        log.debug("querying %s with %r", self._service_url, query_parameters)
        data = urllib.urlencode(query_parameters)
        req =  urllib2.Request(self._service_url, headers={'User-Agent': self._user_agent})
        opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=0))
        fp = opener.open(req, data)
        try:
            http_body = fp.read()
            log.info('received : %r', http_body)
            responses = json.loads(http_body)['responses']
            if len(responses) > 1:
                return responses
            else:
                response = responses[0]
                log.debug("responses[0]: %r", response)
                if 'status' in response and response['status'] == 'OK':
                    return response['data']
                elif 'error' in response:
                    if 'code' in response['error'] and response['error']['code'] == 5:
                        raise MetabansAuthenticationError(response['error'])
                    else:
                        raise MetabansError(response['error'])
                else:
                    raise MetabansException(response)
        finally:
            fp.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import pprint

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

    metabans = Metabans(api_username, api_key)
    
    pprint.pprint(metabans.mbo_availability_account_name('cucurb'))
        
    for data in metabans.mbo_availability_account_name(('cucurb','courgette', 'Courgette')):
        pprint.pprint(data, indent=4)
        print '-'*30
        
    p = Player('EA_12345BBBBBBBBBBBBBBBBBBBBBBBBBBB', 'test_Mike')
    pprint.pprint(metabans.mb_sight_player('MOH_2010', p))
    print('-'*30)
    
    try:
        pprint.pprint(metabans.mb_assess_player('MOH_2010', 'EA_12345BBBBBBBBBBBBBBBBBBBBBBBBBBB', 'white', 3600, 'good guy'))
    except MetabansError, err:
        print err
    print('-'*30)
            


    