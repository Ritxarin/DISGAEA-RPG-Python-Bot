import datetime
from abc import ABCMeta
import random
from api.base import Base
from dateutil import parser

from api.constants import Constants, Mission_Status


class PvP(Base, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def pvp_do_battle(self, pvp_team:int=1, battle_num:int=0):
        pvp_data = self.client.pvp_info()

        if not pvp_data['result']['t_arena']['is_previous_reward_received'] or not pvp_data['result']['t_arena']['is_half_reward_received']:
            self.log("Claiming PvP season reward")
            reward = self.client.pvp_receive_rewards()
            if 'api_error' in reward and (reward['api_error']['message'] == 'ランキング集計期間中です'  or reward['api_error']['message'] == 'Calculating Ranking'):
                self.log('PvP is calculating ranking, please try again later...')
                return

        current_orbs = self.pvp_get_remaining_orbs()

        if current_orbs == 0:
            self.log("No PvP orbs remaining.")
            return

        if battle_num == 0:
            while current_orbs > 0:
                oponent = self.pvp_select_opponent()
                oponent_details = self.client.pvp_enemy_player_detail(t_player_id=oponent['t_player_id'])
                self.log(f"Battling player {oponent['user_name']} - Ranking {oponent['ranking']}. Orbs remaining: {current_orbs}")
                self.client.pvp_start_battle(pvp_team, oponent['t_player_id'])
                self.client.pvp_battle_give_up()
                self.client.pvp_info()
                current_orbs -=1
        else:
            while battle_num > 0 and current_orbs > 0:
                oponent = self.pvp_select_opponent()
                oponent_details = self.client.pvp_enemy_player_detail(t_player_id=oponent['t_player_id'])
                self.log(f"Battling player {oponent['user_name']} - Ranking {oponent['ranking']}. Orbs remaining: {current_orbs}")
                self.client.pvp_start_battle(pvp_team, oponent['t_player_id'])
                self.client.pvp_battle_give_up()
                self.client.pvp_info()
                battle_num -=1
                current_orbs -=1

    def pvp_select_opponent(self):
        opponent_data = self.client.pvp_enemy_player_list()
        pos = random.randint(0, len(opponent_data['result']['enemy_players'])-1)	
        random_oponent = opponent_data['result']['enemy_players'][pos]
        return random_oponent

    def pvp_get_remaining_orbs(self):
        pvp_data = self.client.pvp_info()
        current_orbs = pvp_data['result']['t_arena']['act']
        time_delta = -4 if self.o.region == 2 else 9

        if current_orbs == 0:
            # When 10 orbs are remaining it displays act=0. Calculate based on last recovery time
            pvp_recover_date_string = pvp_data['result']['t_arena']['act_at']
            pvp_recover_date = parser.parse(pvp_recover_date_string)        
            server_time = datetime.datetime.utcnow() + datetime.timedelta(hours=time_delta)
            orb_recovery_time = 50  # Orbs recover every 50 minutes
            total_orbs = 10         # Total number of orbs
            # Calculate how many orbs have recovered since the last full recovery
            time_difference = (server_time - pvp_recover_date).total_seconds() / 60  # Time difference in minutes
            # Calculate how many orbs have recovered
            recovered_orbs = min(total_orbs, int(time_difference // orb_recovery_time))
            pvp_arena_fully_recovered_time = pvp_recover_date + datetime.timedelta(minutes=500)
            if server_time > pvp_arena_fully_recovered_time:
                return 10
            return recovered_orbs
        else:
            return current_orbs