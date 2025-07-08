import random
from abc import ABCMeta
from typing import List

import jwt

from api.constants import Mission_Status
from api.player import Player


class FinalBossLab(Player, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def __get_highest_area_id(self) -> int:
        
        points = self.client.custombattle_current()
        #['result']['events'][0]['total_point']
        thresholds = [
            {"m_area_id": 1001, "need_score": 0},
            {"m_area_id": 1002, "need_score": 10000000},
            {"m_area_id": 1003, "need_score": 50000000}
        ]

        selected_id = 1  # fallback to the first stage
        for stage in thresholds:
            if points >= stage["need_score"]:
                selected_id = stage["m_area_id"]
            else:
                break

        return selected_id
    
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

    def final_boss_lab_claim_story_missions(self):
        r = self.client.custombattle_battle_start()
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
        
        battle_start = self.client.custombattle_battle_start(deck_no=deck_no, enemy_t_player_id=enemy_t_player_id)
        if 'api_error' in battle_start:
            return
        
        deck_data = self.player_decks()
        team = deck_data[deck_no - 1]['t_character_ids']
        battle_type = battle_start['result']['battle_type']     
        self.print_team_info()           
        end_prms = self.__get_custombattle_battle_end_data([])
        end = self.client.battle_end_end_with_payload(end_prms)


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
