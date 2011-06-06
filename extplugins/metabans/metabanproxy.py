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
'''Class that makes it easy to make calls to Metabans.com API from B3'''

class UnsupportedGameError(Exception): pass

class MetabansProxy(object):
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
                                                   reason=reason)

    def watch(self, client, duration=None, reason=None):
        """set the 'watch' assessment on the client
        duration is in second"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='watch',
                                                   assessment_length=duration,
                                                   reason=reason)

    def ban(self, client, duration=None, reason=None):
        """set the 'black' assessment on the client
        duration is in second"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='black',
                                                   assessment_length=duration,
                                                   reason=reason)

    def protect(self, client, duration=None, reason=None):
        """set the 'white' assessment on the client
        duration is in second"""
        if client:
            return self._metabans.mb_assess_player(game_name=self._game_name,
                                                   player_uid=client.guid, 
                                                   assessment_type='white',
                                                   assessment_length=duration,
                                                   reason=reason)

