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
from pymetabans import Metabans, Player
import re
import time
'''Class that makes it easy to make calls to Metabans.com API from B3'''

class UnsupportedGameError(Exception): pass

class MetabansProxy(object):
    _reColor = re.compile(r'(\^[0-9])')
    group_name = None
    
    def __init__(self, game_name, user_agent='pymetabans'):
        self._game_name = self._getMetabansGameName(game_name)
        self._metabans = Metabans(user_agent=user_agent)
        
    
    @property
    def username(self):
        return self._metabans.username

    @username.setter
    def username(self, value):
        self._metabans.username = value
    
    @property
    def apikey(self):
        return self._metabans.apikey

    @apikey.setter
    def apikey(self, value):
        self._metabans.apikey = value
    
    def _getMetabansGameName(self, B3_game_name):
        if B3_game_name == 'bfbc2':
            return "BF_BC2"
        elif B3_game_name == 'moh':
            return "MOH_2010"
        elif B3_game_name == 'cod4':
            return "COD_4"
        elif B3_game_name == 'cod5':
            return "COD_5"
        elif B3_game_name == 'cod6':
            return "COD_6"
        elif B3_game_name == 'cod7':
            return "COD_7"
        elif B3_game_name == 'homefront':
            return "HOMEFRONT"
        else:
            raise UnsupportedGameError, "unsupported game %s" % B3_game_name
            
    def _stripColors(self, text):
        return re.sub(self._reColor, '', text).strip()
    
    def sight(self, client):
        if client:
            metabans_player = Player(client.guid, client.name, client.ip, client.pbid)
            return self._metabans.mb_sight_player(self._game_name, 
                                                  metabans_player,
                                                  self.group_name)
    def check(self, client):
        if client:
            return self._metabans.mbo_player_status(self._game_name, client.guid)



    def clear(self, client, reason=None):
        """remove any assessment on the client"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='none',
                                                   reason=self._stripColors(reason))

    def watch(self, client, duration=None, reason=None):
        """set the 'watch' assessment on the client
        duration is in second"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='watch',
                                                   assessment_length=duration,
                                                   reason=self._stripColors(reason))

    def ban(self, client, duration=None, reason=None):
        """set the 'black' assessment on the client
        duration is in second"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='black',
                                                   assessment_length=duration,
                                                   reason=self._stripColors(reason))

    def protect(self, client, duration=None, reason=None):
        """set the 'white' assessment on the client
        duration is in second"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='white',
                                                   assessment_length=duration,
                                                   reason=self._stripColors(reason))


    def send_bulk_queries(self, queries):
        """send a bunch of queries in one single call to the metabans API"""
        nb_queries = 0
        query_parameters = {}
        for query in queries:
            for k, v in query.iteritems():
                query_parameters['requests[%d][%s]' % (nb_queries, k)] = v
            nb_queries += 1
        responses = self._metabans._query(query_parameters)
        errors = []
        success = []
        fetch_times = {}
        for r in responses:
            if 'status' in r and r['status'] == 'OK':
                success.append(r)
                key = r['request']['action']
            else:
                errors.append(r)
                key = r['request']['action'] + '_error_%s' % r['error']['code']
            if not key in fetch_times:
                fetch_times[key] = []
            fetch_times[key].append(float(r['fetch_time'].rstrip(' s')) * 1000)
        return (success, errors, fetch_times)
    
if __name__ == '__main__':
    import logging
    from datetime import datetime
    logging.basicConfig(level=logging.DEBUG)
    
    """
    Calculate mean and standard deviation of data x[]:
        mean = {\sum_i x_i \over n}
        std = sqrt(\sum_i (x_i - mean)^2 \over n-1)
    credit: http://www.physics.rutgers.edu/~masud/computing/WPark_recipes_in_python.html
    """
    def meanstdv(x):
        from math import sqrt
        n, mean, std = len(x), 0, 0
        for a in x:
            mean = mean + a
        try:
            mean = mean / float(n)
        except ZeroDivisionError:
            mean = 0
        for a in x:
            std = std + (a - mean)**2
        try:
            std = sqrt(std / float(n-1))
        except ZeroDivisionError:
            std = 0
        return mean, std


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


    proxy = MetabansProxy('bfbc2')
    proxy.username = api_username
    proxy.apikey = api_key
    
    queries = []
    for i in range(1,100):
        queries.append({
            'action': 'mbo_player_status',
            'game_name': proxy._game_name,
            'player_uid': 'qsd654sqf_c%s' % i
        })
    t1 = datetime.now()
    oks, fails, stats = proxy.send_bulk_queries(queries)
    print("test took %s" % (datetime.now() - t1))
    for k in stats:
        mean, stdv = meanstdv(stats[k])
        print("%s (%s calls): (ms) min(%0.3f), max(%0.3f), mean(%0.3f), stddev(%0.3f)" % ( 
             k, len(stats[k]),
             min(stats[k]), max(stats[k]), 
             mean, stdv))
        
                