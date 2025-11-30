import datetime
import random
from abc import ABCMeta
from typing import List
from api.CustomExceptions import NoAPLeftException
from api.constants import Constants, Items as ItemsC
from api.constants import Item_Types, Mission_Status
from api.player import Player


class FinalBossLab(Player, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def __get_highest_area_id(self, points:int) -> int:
        
        thresholds = [
            {"m_area_id": 1001, "need_score": 0},
            {"m_area_id": 1002, "need_score": 10000000},
            {"m_area_id": 1003, "need_score": 50000000}
        ]

        area_id = 1001  # fallback to the first stage
        for stage in thresholds:
            if points >= stage["need_score"]:
                area_id = stage["m_area_id"]
            else:
                break
        return area_id
    
    def final_boss_lab_claim_daily_missions(self):
        r = self.client.custombattle_dailies()
        mission_ids = []
        incomplete_mission_ids = []
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.custombattle_dailies_receive(mission_ids)
            self.log(f"Claimed {len(mission_ids)} daily missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Daily missions to be completed: {len(incomplete_mission_ids)}")
            
    def final_boss_lab_claim_monthly_missions(self):
        r = self.client.custombattle_monthlies()
        mission_ids = []
        incomplete_mission_ids = []
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.custombattle_monthlies_receive(mission_ids)
            self.log(f"Claimed {len(mission_ids)} monthly missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Monthly missions to be completed: {len(incomplete_mission_ids)}")

    def final_boss_lab_claim_missions(self):
        r = self.client.custombattle_missions()
        mission_ids = []
        incomplete_mission_ids = []
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.custombattle_missions_receive(mission_ids)
            self.log(f"Claimed {len(mission_ids)} final boss lab missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Final Boss Lab missions to be completed: {len(incomplete_mission_ids)}")

    def final_boss_lab_clear_battle(self, deck_no:int, enemy_t_player_id:int):
        
        if self.current_ap < 10:
            self.use_potion(item_id=ItemsC.AP_Pot)
        battle_start = self.client.custombattle_battle_start(deck_no=deck_no, enemy_t_player_id=enemy_t_player_id)
        if 'api_error' in battle_start:
            return
        
        battle_type = battle_start['result']['battle_type']
        deck_data = self.player_decks()
        team = deck_data[deck_no - 1]['t_character_ids']
        character_ids = [team['pos1']]       
        end_prms = self.__get_custombattle_battle_end_data(character_ids)
        end = self.client.battle_end_end_with_payload(end_prms)


    def final_boss_lab_battle_player(self):
        find_players = self.client.custombattle_search_player()
        players = find_players['result']['players']
        sorted_data = sorted(players, key=lambda x: x['score'], reverse=True)
        self.log(f"\tBattling player: {sorted_data[0]['user_name']} - Score: {sorted_data[0]['score']}")
        self.final_boss_lab_clear_battle(deck_no=1, enemy_t_player_id=sorted_data[0]['t_player_id']) 

    def final_boss_daily_tasks(self):
        
        self.log(f"Completing Final Boss Lab daily missions...")
        
        data = self.client.custombattle_current()
        player_id = data['result']['t_custom_battle']['t_player_id']
        challenge_num = data['result']['t_custom_battle']['current_challenge_num']
        points = data['result']['t_custom_boss']['max_score']
        
        # Do Daily stage runs
        #area_id = self.__get_highest_area_id(points)
        self.clear_custom_lab_stages(1001, 3)
        items = self.gd.items
        materials =  [x for x in items if x['item_type'] == Item_Types.Final_Boss_Material]    
        # Use custom boss parts
        self.log(f"\tUsing Final Boss parts...")
        self.player_items(True)
        self.__final_boss_lab_use_custom_parts(m_custom_parts_ids = [1001,1002,1003,1004,1005], effect_id=0, materials=materials)        
        
        red_geo_mats = [2001,2002,2003,2004,2005]
        self.__final_boss_lab_use_custom_parts(m_custom_parts_ids = red_geo_mats, effect_id=1, materials=materials)   

        green_geo_mats = [5001,5002,5003,5004,5005]
        self.__final_boss_lab_use_custom_parts(m_custom_parts_ids = green_geo_mats, effect_id=14, materials=materials)          

        # Battle own boss
        while challenge_num < 5:
            self.log(f"\tBattling own boss...")
            self.final_boss_lab_clear_battle(deck_no=1, enemy_t_player_id=player_id)
            challenge_num += 1
            
        # Battle one oponent
        self.final_boss_lab_battle_player()  

        # Complete monthly missions on the last day of the month
        self.final_boss_farm_monthly_points()
        
        self.log(f"\tClaiming missions...")
        self.final_boss_lab_claim_daily_missions()
        self.final_boss_lab_claim_monthly_missions()
        self.final_boss_lab_claim_missions()
        
    def clear_custom_lab_stages(self, area_id:int=1001, number_of_runs:int=3):
        run_count = 0
        area_stages = [x for x in self.gd.stages if x['m_area_id'] == area_id]
        for stage in area_stages:
            if run_count == number_of_runs:
                break
            if self.is_stage_3starred(stage['id']):
                self.log('Stage already 3 starred - area: %s stage: %s rank: %s name: %s' % (
                            stage['m_area_id'], stage['id'], stage['rank'], stage['name']))      
            else:
                self.doQuest(stage['id'], team_num=1, send_friend_request=False)
                run_count += 1
        # repeat on last stage until all 3 runs are done
        while run_count < number_of_runs:
            self.doQuest(stage['id'], team_num=1, send_friend_request=False)
            run_count += 1
        
    def __get_custombattle_battle_end_data(self, character_ids:List[int]):   
                
        payload = {
            "m_stage_id": 0,
            "m_tower_no": 0,
            "equipment_id": 0,
            "equipment_type": 0,
            "innocent_dead_flg": 0,
            "t_raid_status_id": 0,
            "raid_battle_result": "",
            "m_character_id": 0,
            "division_battle_result": "",
            "arena_battle_result": "",
            "battle_type": 13,
            "result": 1,
            "battle_exp_data": [
                {
                    "m_enemy_id": 1,
                    "finish_type": 2,
                    "finish_member_ids": [
                        [character_ids[0]]
                    ]
                }
            ],
            "common_battle_result": self.o.common_battle_result_custombattle,
            "skip_party_update_flg": True,
            "m_event_id": 0,
            "board_battle_result": "",
            "tournament_score": 0,
            "tournament_battle_result": "",
            "travel_battle_result": {
                "character_results": []
            }
        }
        return payload
    
    def __final_boss_lab_use_custom_parts(self, m_custom_parts_ids: list[int], effect_id: int, materials: list[dict]):
        use_nums = []
        filtered_part_ids = []

        for part_id in m_custom_parts_ids:
            material = next((x for x in materials if x['effect_value'] == [part_id]), None)
            if material is not None:
                material_pd = self.pd.get_item_by_m_item_id(material['id'])
                if material_pd is not None and material_pd['num'] > 0:
                    filtered_part_ids.append(part_id)
                    use_nums.append(material_pd['num'])
                    self.log(f"\t\tUsing {material_pd['num']} {material['name']}")

        if filtered_part_ids:
            effect_ids = [effect_id] * len(filtered_part_ids)
            self.client.custombattle_use_parts(
                m_custom_parts_ids=filtered_part_ids,
                use_nums=use_nums,
                m_custom_boss_effect_ids=effect_ids
            )


    def final_boss_farm_monthly_points(self):
        data = self.client.custombattle_current()
        monthly_points = data['result']['t_custom_battle']['challenge_point']
        if monthly_points < Constants.Final_Boss_Lab_Monthly_Points and self.__is_last_day_of_month():
            self.log(f"\tFarming points for monthly missions:...")
            while monthly_points < Constants.Final_Boss_Lab_Monthly_Points:
                self.final_boss_lab_battle_player()
                data = self.client.custombattle_current()
                monthly_points = data['result']['t_custom_battle']['challenge_point']
                self.log(f"\tCurrent monthly points: {monthly_points}")
            self.final_boss_lab_claim_monthly_missions()


    def __is_last_day_of_month(self):
    # Get today's date
        today = datetime.date.today()

        # Find the first day of the next month
        next_month = today.replace(day=28) + datetime.timedelta(days=4)
        # Get the last day of the current month by subtracting the days to get to the last day
        last_day_of_month = next_month - datetime.timedelta(days=next_month.day)

        # Check if today is the last day of the month
        return today == last_day_of_month