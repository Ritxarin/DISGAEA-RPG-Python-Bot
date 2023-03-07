import random
from abc import ABCMeta

from api.constants import Constants, Mission_Status, ErrorMessages
from api.player import Player
from data import data as gamedata


class Raid(Player, metaclass=ABCMeta):

    def __init__(self):
        super().__init__()
        self.raid_boss_count = 0

    def raid_battle_start(self, stage_id, raid_status_id, raid_party):
        return self.client.battle_start(m_stage_id=stage_id, raid_status_id=raid_status_id, deck_no=raid_party)

    def raid_battle_end_giveup(self, stage_id, raid_status_id):
        return self.client.battle_end(
            m_stage_id=stage_id,
            battle_type=1,
            raid_status_id=raid_status_id,
            raid_battle_result="eyJhbGciOiJIUzI1NiJ9.eyJoamptZmN3Njc4NXVwanpjIjowLCJzOW5lM2ttYWFuNWZxZHZ3Ijo5MD" \
                               "AsImQ0Y2RrbncyOGYyZjVubmwiOjUsInJnajVvbTVxOWNubDYxemIiOltdfQ.U7hhaGeDBZ3lYvgkh0" \
                               "ScrlJbamtNgSXvvaqsqUcZYOU",
            common_battle_result="eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6" \
                                 "MCwiZHBwY2JldzltejhjdXd3biI6MCwiemFjc3Y2amV2NGl3emp6bSI6MCwia3lxeW5pM25ubTNpM" \
                                 "mFxYSI6MCwiZWNobTZ0aHR6Y2o0eXR5dCI6MCwiZWt1c3ZhcGdwcGlrMzVqaiI6MCwieGE1ZTMyMm" \
                                 "1nZWo0ZjR5cSI6MH0.9DYl6QK2TkTIq81M98itbAqafdUE4nIPTYB_pp_NTd4",
        )

    def get_battle_exp_data_raid(self, start, deck):
        characters_in_deck = [x for x in deck if x != 0]
        _id = random.randint(0, len(characters_in_deck) - 1)
        rnd_char = characters_in_deck[_id]
        res = [{
            "m_enemy_id": start['result']['enemy_list'][0]['pos1'],
            "finish_type": 1,
            "finish_member_ids": rnd_char
        }]
        return res

    def raid_find_stageid(self, m_raid_boss_id, raid_boss_level):
        all_boss_level_data = gamedata['raid_boss_level_data']
        raid_boss_level_data = [x for x in all_boss_level_data if x['m_raid_boss_id'] == m_raid_boss_id]
        stage = next((x for x in raid_boss_level_data if
                      raid_boss_level >= x['min_level'] and raid_boss_level <= x['max_level']), None)
        if stage is not None:
            return stage['m_stage_id']
        return 0

    def raid_get_all_bosses(self):
        return self.client.raid_index()['result']['t_raid_statuses']

    def raid_set_boss_level(self, m_raid_boss_id, step):
        data = self.client.raid_update(m_raid_boss_id=m_raid_boss_id, step=step)
        return data['result']

    def raid_find_all_available_bosses(self):
        all_bosses = self.raid_get_all_bosses()
        available_bosses = [x for x in all_bosses if not x['is_discoverer'] and x['current_battle_count'] < 1]
        return available_bosses

    # Will check for if there is an active boss, fight, give up and share.
    def raid_share_own_boss(self, party_to_use:int=1):
        own_boss = self.client.raid_current()['result']['current_t_raid_status']
        if own_boss is not None:
            # Battle and give up automatically
            if own_boss['current_battle_count'] == 0:
                raid_stage_id = self.raid_find_stageid(own_boss['m_raid_boss_id'], own_boss['level'])
                if raid_stage_id != 0:
                    self.raid_battle_start(raid_stage_id, own_boss['id'], party_to_use)
                    self.raid_battle_end_giveup(raid_stage_id, own_boss['id'])
            # share
            if not own_boss['is_send_help']:
                sharing_result = self.client.raid_send_help_request(own_boss['id'])
                self.log("Shared boss with %s users" % sharing_result['result']['send_help_count'])

    def raid_claim_all_point_rewards(self):
        self.log("Claiming raid point rewards.")
        initial_stones = self.player_stone_sum()['result']['_items'][0]['num']
        raid_data = self.client.event_index(event_ids=Constants.Current_Raid_ID)
        if raid_data['result']['events'][0]['gacha_data'] is None:
            self.log("Raid data not found. Please make sure the Current_Raid_ID value is correct on the constants file")
            return
        current_uses = raid_data['result']['events'][0]['gacha_data']['sum']
        if current_uses == 5000:
            self.log(f"All rewards claimed.")
            return
        current_points = raid_data['result']['events'][0]['point']
        if current_points < 100:
            self.log(f"Not enough points left to claims rewards: {current_points}")
            return
        initial_stones_spin = initial_stones
        uses_left = 5000 - current_uses
        current_stones = 0

        while uses_left > 0 and current_points >= 100:
            uses_to_claim = min(uses_left, 100)
            points_needed = uses_to_claim * 100
            if current_points < points_needed:
                uses_to_claim = current_points // 100
            data = self.client.raid_gacha(Constants.Current_Raid_Event_Point_Gacha, uses_to_claim)
            current_points = data['result']['after_t_data']['t_events'][0]['point']
            uses_left = 5000 - data['result']['after_t_data']['t_events'][0]['gacha_data']['sum']
            if len(data['result']['after_t_data']['stones']) > 0:
                current_stones = data['result']['after_t_data']['stones'][0]['num']
                self.log(f"Nether Quartz gained: {current_stones - initial_stones_spin}")
                initial_stones_spin = current_stones
        self.log(f"Finished claiming raid rewards. Total Nether Quartz gained: {current_stones - initial_stones}")

    def raid_spin_innocent_roulette(self):
        self.log("Spinning raid innocent roulette.")
        raid_data = self.client.event_index(event_ids=Constants.Current_Raid_ID)
        if raid_data['result']['events'][0]['gacha_data'] is None:
            self.log("Raid data not found. Please make sure the Current_Raid_ID value is correct on the constants file")
            return
        spins_left = raid_data['result']['events'][0]['gacha_data']['chance_stock_num']
        innocent_types = gamedata['innocent_types']
        is_big_chance = raid_data['result']['events'][0]['gacha_data']['exist_big_chance']

        if spins_left == 0 and is_big_chance is False:
            self.log(f"All spins used.")
            return

        while spins_left > 0 or is_big_chance is True:
            if is_big_chance:
                data = self.client.raid_gacha(Constants.Current_Raid_Innocent_Special_Roulette, 1)
                special_spin = "Special Spin - "
            else:
                data = self.client.raid_gacha(Constants.Current_Raid_Innocent_Regular_Roulette, 1)
                special_spin = ""

            if('error' in data and "Max possession number of Innocents reached." in data['error']):
                return

            spins_left = data['result']['after_t_data']['t_events'][0]['gacha_data']['chance_stock_num']
            is_big_chance = data['result']['after_t_data']['t_events'][0]['gacha_data']['exist_big_chance']
            innocent_type = next((x for x in innocent_types if
                             x['id'] == data['result']['after_t_data']['innocents'][0]['m_innocent_id']),None)
            self.log(
                f"{special_spin}Obtained innocent of type {innocent_type['name']} and" +
                f" value: {data['result']['after_t_data']['innocents'][0]['effect_values'][0]}")

        self.log(f"Finished spinning the raid roulette")

    def raid_claim_all_boss_rewards(self):
        print("Claiming raid boss battle rewards.")
        innocent_types = gamedata['innocent_types']
        finished = False
        while not finished:
            battle_logs = self.client.raid_history(Constants.Current_Raid_ID)['result']['battle_logs']
            battles_to_claim = [x for x in battle_logs if not x['already_get_present']]
            finished = len(battles_to_claim) == 0
            for i in battles_to_claim:
                reward_data = self.client.raid_reward(i['t_raid_status']['id'])
                if len(reward_data['result']['after_t_data']['innocents']) > 0:
                    innocent_type = next((x for x in innocent_types if
                                          x['id'] == reward_data['result']['after_t_data']['innocents'][0][
                                              'm_innocent_id']), None)
                    if innocent_type is None:
                        self.log(
                            f"Special type id = {reward_data['result']['after_t_data']['innocents'][0]['m_innocent_id']}")
                    self.log(
                        f"Obtained innocent of type {innocent_type['name']} and value: {reward_data['result']['after_t_data']['innocents'][0]['effect_values'][0]}")
        self.log("Finished claiming raid rewards.")

    def raid_claim_surplus_points(self):
        print("Exchanging surplus raid points for HL...")
        raid_data = self.client.event_index(Constants.Current_Raid_ID)
        if raid_data['result']['events'][0]['gacha_data'] is None:
            self.log("Raid data not found. Please make sure the Current_Raid_ID value is correct on the constants file")
            return
        exchanged_points = raid_data['result']['events'][0]['exchanged_surplus_point']
        if exchanged_points == 1000000:
            self.log(f"\tAll surplus points exchanged.", 30)
            return
        current_points = raid_data['result']['events'][0]['point']
        if current_points < 100:
            self.log(f"Not enough points to exchange: {current_points}", 30)
            return
        points_to_exchange = min(1000000 - exchanged_points, current_points)
        self.client.raid_exchange_surplus_points(points_to_exchange)
        self.log(f"Exchanged {points_to_exchange} points")

    def raid_claim_missions(self):
        r = self.client.raid_event_missions()
        mission_ids = []
        incomplete_mission_ids = []
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared and mission['id']:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed and mission['id']:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.story_event_claim_missions(mission_ids)
            self.log(f"Claimed {len(mission_ids)} story missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Story missions to be completed: {len(incomplete_mission_ids)}")

    def raid_farm_shared_bosses(self, party_to_use:int=1):
        available_raid_bosses = self.raid_find_all_available_bosses()
        for raid_boss in available_raid_bosses:
            raid_stage_id = self.raid_find_stageid(raid_boss['m_raid_boss_id'], raid_boss['level'])
            if raid_stage_id != 0:
                self.raid_battle_start(raid_stage_id, raid_boss['id'], party_to_use)
                self.raid_battle_end_giveup(raid_stage_id, raid_boss['id'])
                self.raid_boss_count += 1
                self.log(f"Farmed boss with level {raid_boss['level']}. Total bosses farmed: {self.raid_boss_count}")

    def raid_defeat_own_boss(self, party_to_use):
        own_boss = self.client.raid_current()['result']['current_t_raid_status']
        if own_boss is not None:
            #Battle and give up automatically
            raid_stage_id = self.raid_find_stageid(own_boss['m_raid_boss_id'], own_boss['level'])   
            if raid_stage_id != 0:
                if own_boss['level'] == 50:
                    battle_start_data = self.raid_battle_start(raid_stage_id, own_boss['id'], party_to_use)
                    if 'error' in battle_start_data and battle_start_data['error'] == ErrorMessages.Raid_Battle_Finished:
                        return
                    enemy_id = battle_start_data['result']['enemy_list'][0]['pos1']
                    battle_end_data = self.raid_battle_finish_lvl50_boss(raid_stage_id, own_boss['id'], enemy_id)
                    #reward_date = self.raid_reward(own_boss['id'])
                if own_boss['level'] == 100:
                    battle_start_data = self.raid_battle_start(raid_stage_id, own_boss['id'], party_to_use)
                    if 'error' in battle_start_data and battle_start_data['error'] == ErrorMessages.Raid_Battle_Finished:
                        return
                    enemy_id = battle_start_data['result']['enemy_list'][0]['pos1']
                    battle_end_data = self.raid_battle_finish_lvl100_boss(raid_stage_id, own_boss['id'], enemy_id)
                    #reward_date = self.raid_reward(own_boss['id'])
                if own_boss['level'] != 100 and own_boss['level'] != 50 and not own_boss['is_send_help']:                          
                    sharing_result = self.client.raid_send_help_request(own_boss['id'])
                    self.log("Shared boss with %s users" % sharing_result['result']['send_help_count'])
    
    def raid_battle_finish_lvl50_boss(self, stage_id, raid_status_id, enemy_id):
        data = self.client.raid_battle_finish_lvl50_boss(stage_id, raid_status_id, enemy_id)
        return data

    def raid_battle_finish_lvl100_boss(self, stage_id, raid_status_id, enemy_id):
        data = self.client.raid_battle_finish_lvl100_boss(stage_id, raid_status_id, enemy_id)
        return data  