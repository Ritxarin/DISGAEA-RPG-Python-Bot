import datetime
from abc import ABCMeta
import random
from api.base import Base
from dateutil import parser

from api.constants import Constants, Mission_Status


class PvP(Base, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def pvp_do_battle(self, pvp_team:int=1):
        pvp_data = self.client.pvp_info()

        if not pvp_data['result']['t_arena']['is_previous_reward_received']:
            self.log("Claimed previous season PvP reward")
            self.client.pvp_receive_rewards()

        current_orbs = pvp_data['result']['t_arena']['act']

        if current_orbs == 0:
            # When 10 orbs are remaining it displays act=0. Calculate based on last recovery time
            pvp_recover_date_string = pvp_data['result']['t_arena']['act_at']
            pvp_recover_date = parser.parse(pvp_recover_date_string)        
            server_time = datetime.datetime.utcnow() + datetime.timedelta(hours=-4)
            pvp_arena_fully_recovered_time = pvp_recover_date + datetime.timedelta(minutes=500)
            if server_time > pvp_arena_fully_recovered_time:
                current_orbs = 10
            else:
                self.log("No PvP orbs remaining.")
                return

        while current_orbs > 0:
            oponent = self.pvp_select_opponent()
            oponent_details = self.client.pvp_enemy_player_detail(t_player_id=oponent['t_player_id'])
            self.log(f"Battling player {oponent['user_name']} - Ranking {oponent['ranking']}. Orbs remaining: {current_orbs}")
            self.client.pvp_start_battle(pvp_team, oponent['t_player_id'])
            self.client.pvp_battle_give_up()
            self.client.pvp_info()
            current_orbs -=1

    def pvp_select_opponent(self):
        opponent_data = self.client.pvp_enemy_player_list()
        pos = random.randint(0, len(opponent_data['result']['enemy_players'])-1)	
        random_oponent = opponent_data['result']['enemy_players'][pos]
        return random_oponent

    def pvp_get_remaining_orbs(self):
        pvp_data = self.client.pvp_info()
        return pvp_data['result']['t_arena']['act']