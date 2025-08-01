import random
from abc import ABCMeta

from api.constants import Battle_Finish_Type, Constants, Mission_Status, ErrorMessages, Raid_Gacha_Type, JP_ErrorMessages
from api.player import Player
from data import data as gamedata


class Raid(Player, metaclass=ABCMeta):

    def __init__(self):
        super().__init__()
        self.raid_boss_count = 0

    def raid_get_raid_id(self):
        return Constants.Current_Raid_ID_GL if self.o.region == 2 else Constants.Current_Raid_ID_JP
    
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
        raid_data = self.client.event_index(event_ids=self.raid_get_raid_id())
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

        raid_event_point_gacha_id = self.raid_get_gacha_id(gacha_type = Raid_Gacha_Type.Raid_Point_Gacha)

        while uses_left > 0 and current_points >= 100:
            uses_to_claim = min(uses_left, 100)
            points_needed = uses_to_claim * 100
            if current_points < points_needed:
                uses_to_claim = current_points // 100
            data = self.client.raid_gacha(raid_event_point_gacha_id, uses_to_claim)
            current_points = data['result']['after_t_data']['t_events'][0]['point']
            uses_left = 5000 - data['result']['after_t_data']['t_events'][0]['gacha_data']['sum']
            if len(data['result']['after_t_data']['stones']) > 0:
                current_stones = data['result']['after_t_data']['stones'][0]['num']
                self.log(f"Nether Quartz gained: {current_stones - initial_stones_spin}")
                initial_stones_spin = current_stones
        self.log(f"Finished claiming raid rewards. Total Nether Quartz gained: {current_stones - initial_stones}")

    def raid_spin_innocent_roulette(self):
        self.log("Spinning raid innocent roulette.")

        innocent_roulette_id = self.raid_get_gacha_id(gacha_type = Raid_Gacha_Type.Innocent_Roulette)
        special_innocent_roulette_id = self.raid_get_gacha_id(gacha_type = Raid_Gacha_Type.Special_Innocent_Roulette)

        raid_data = self.client.event_index(event_ids=self.raid_get_raid_id())
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
                data = self.client.raid_gacha(special_innocent_roulette_id, 1)
                special_spin = "Special Spin - "
            else:
                data = self.client.raid_gacha(innocent_roulette_id, 1)
                special_spin = ""

            if 'error' in data and (data['error'] == ErrorMessages.Innocent_Full_Error or data['error'] == JP_ErrorMessages.Innocent_Full_Error):
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
            battle_logs = self.client.raid_history(self.raid_get_raid_id())['result']['battle_logs']
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
                    else:
                        self.log(f"Obtained innocent of type {innocent_type['name']} and value: {reward_data['result']['after_t_data']['innocents'][0]['effect_values'][0]}")
        self.log("Finished claiming raid rewards.")

    def raid_claim_surplus_points(self):
        print("Exchanging surplus raid points for HL...")
        raid_data = self.client.event_index(self.raid_get_raid_id())
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
        r = self.client.raid_event_missions(self.raid_get_raid_id())
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

    def raid_get_gacha_id(self, gacha_type:Raid_Gacha_Type):
        raid_ID = self.raid_get_raid_id()
        raid_gacha_data = gamedata['event_gacha']
        raid_gacha = next((x for x in raid_gacha_data if x['m_event_id'] == raid_ID and x['gacha_type'] == gacha_type),None)
        if gacha_type is None:
            self.log("Raid data not found. Please make sure constants are up to date")
            return
        return raid_gacha['id']

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
    
    def raid_clear_special_stage(self, team_num:int, stage_id:int=1):
        highest_stage_id = self.raid_get_special_stage_id()
        stage_id = min(stage_id, highest_stage_id)
        start = self.client.raid_start_special_stage(stage_id, team_num)
        battle_exp_data = self.get_raid_special_stage_battle_exp_data(start, self.pd.deck(team_num)[0])
        end_prms = self.get_raid_special_stage_end_data(battle_exp_data)
        end = self.client.battle_end_end_with_payload(end_prms)
        self.raid_share_own_boss(party_to_use=team_num)
    
    def get_raid_special_stage_end_data(self, battle_exp_data):      
        payload = {
            "m_stage_id":0,
            "m_tower_no":0,
            "equipment_id":0,
            "equipment_type":0,
            "innocent_dead_flg":0,
            "t_raid_status_id":0,
            "raid_battle_result":"",
            "m_character_id":0,
            "division_battle_result":"",
            "arena_battle_result":"",
            "battle_type":15,
            "result":1,
            "battle_exp_data":battle_exp_data,
            "common_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6ODIyNjA1OTk0Mzc0NSwiZHBwY2JldzltejhjdXd3biI6MCwiemFjc3Y2amV2NGl3emp6bSI6MCwia3lxeW5pM25ubTNpMmFxYSI6MCwiZWNobTZ0aHR6Y2o0eXR5dCI6MCwiZWt1c3ZhcGdwcGlrMzVqaiI6MCwieGE1ZTMyMm1nZWo0ZjR5cSI6Mn0.pZqqUqyZ7fsMqrELoxWWGIOTs7pVOOOGKaW5JXnzHs4",
            "skip_party_update_flg":True,
            "m_event_id":0,
            "board_battle_result":"",
            "tournament_score":0,
            "tournament_battle_result":"",
            "travel_battle_result":{"character_results":[]}
            }
        return payload 
    
    def get_raid_special_stage_battle_exp_data(self, start, character_id:int):
        res = []
        for d in start['result']['enemy_list']:
            for r in d:
                if d[r] != 0:
                    res.append({
                        "finish_member_ids": [character_id],
                        "finish_type": 2,
                        "m_enemy_id": d[r]
                    })
        return res
    
    def raid_get_special_stage_id(self) -> int:
        event = self.client.event_index([Constants.Current_Raid_ID_JP])
        points = event['result']['events'][0]['total_point']
        thresholds = [
            {"id": 1, "need_point": 0},
            {"id": 2, "need_point": 1500},
            {"id": 3, "need_point": 5000},
            {"id": 4, "need_point": 10000},
            {"id": 5, "need_point": 15000},
            {"id": 6, "need_point": 25000},
            {"id": 7, "need_point": 35000},
            {"id": 8, "need_point": 50000},
            {"id": 9, "need_point": 65000},
            {"id": 10, "need_point": 100000},
        ]

        selected_id = 1  # fallback to the first stage
        for stage in thresholds:
            if points >= stage["need_point"]:
                selected_id = stage["id"]
            else:
                break

        return selected_id