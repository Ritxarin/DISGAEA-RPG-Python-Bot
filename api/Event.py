from abc import ABCMeta
import json
import random
from typing import List
from api.player import Player
from api.constants import Event_Type, Mission_Status, Constants, Event_Types

class Event(Player, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def event_claim_daily_missions(self):
        r = self.client.story_event_daily_missions()
        mission_ids = []
        incomplete_mission_ids = []
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.story_event_claim_daily_missions(mission_ids)
            self.log(f"Claimed {len(mission_ids)} daily missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Daily missions to be completed: {len(incomplete_mission_ids)}")
            
    def event_claim_mission_repetitions(self):
        r = self.client.story_event_mission_repetitions()
        mission_ids = []
        incomplete_mission_ids = []
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.story_event_claim_mission_repetitions(mission_ids)
            self.log(f"Claimed {len(mission_ids)} event repeatable missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Repeatable missions to be completed: {len(incomplete_mission_ids)}")

    def event_claim_story_missions(self):
        r = self.client.story_event_missions()
        mission_ids = []
        incomplete_mission_ids = []

        # character missions and story missions have to be claimed separately
        m_event_id = Constants.Current_Story_Event_ID_GL if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
        character_mission_id = (m_event_id * 1000) + 500
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared and mission['id'] < character_mission_id:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed and mission['id'] < character_mission_id:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.story_event_claim_missions(mission_ids)
            self.log(f"Claimed {len(mission_ids)} story missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Story missions to be completed: {len(incomplete_mission_ids)}")

    def event_claim_character_missions(self):
        r = self.client.story_event_missions()
        mission_ids = []
        incomplete_mission_ids = []

        # character missions and story missions have to be claimed separately
        m_event_id = Constants.Current_Story_Event_ID_GL if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
        character_mission_id = (m_event_id * 1000) + 500
        
        for mission in r['result']['missions']:
            if mission['status'] == Mission_Status.Cleared and mission['id'] >= character_mission_id:
                mission_ids.append(mission['id'])
            if mission['status'] == Mission_Status.Not_Completed and mission['id'] >= character_mission_id:
                incomplete_mission_ids.append(mission['id'])
        if len(mission_ids) > 0:
            self.client.story_event_claim_missions(mission_ids)
            self.log(f"Claimed {len(mission_ids)} character missions")
        if len(incomplete_mission_ids) > 0:
            self.log(f"Character missions to be completed: {len(incomplete_mission_ids)}")

    ## TODO: is that ID static??
    def event_buy_daily_AP(self, ap_id:int):
        product_data = self.client.shop_index()['result']['shop_buy_products']['_items']
        ap_pot = next((x for x in product_data if x['m_product_id'] == ap_id),None)
        if ap_pot is not None and ap_pot['buy_num'] == 0:
            self.client.shop_buy_item(itemid=ap_id, quantity=5)

    ## Set event type. Constants need to be up to date
    def clear_event(self, event_type:Event_Types, team_to_use:int=1):        
        
        if event_type == Event_Types.UDT_Training: 
            event_area_id = Constants.UDT_Training_Area_ID_GL if self.o.region == 2 else Constants.UDT_Training_Area_ID_JP  
            event_id = Constants.UDT_Training_Event_ID_GL if self.o.region == 2 else Constants.UDT_Training_Event_ID_JP  
            daily_run_limit = Constants.UDT_Training_Daily_Run_Limit         
        if event_type == Event_Types.Etna_Defense:
            event_area_id = Constants.Etna_Defense_Area_ID_GL if self.o.region == 2 else Constants.Etna_Defense_Area_ID_JP
            event_id = Constants.Enta_Defense_Event_ID_GL if self.o.region == 2 else Constants.Enta_Defense_Event_ID_JP  
            daily_run_limit = Constants.Etna_Defense_Daily_Run_Limit
            
        self.clear_etna_or_udt_event(team_to_use=team_to_use, event_area_id=event_area_id, daily_run_limit=daily_run_limit, event_id=event_id)

    def clear_etna_or_udt_event(self, team_to_use:int=1, event_area_id:int=0, daily_run_limit:int = 0, event_id:int=0):    

        events = self.client.event_index()   
        event = next((x for x in events['result']['events'] if x["m_event_id"] == event_id), None)
        if event is None:
            self.log("Event not found")
            return
        number_of_runs = event['challenge_num']
        if number_of_runs == daily_run_limit:
            self.log("Reached daily challenge limit for the event")
            return
        stages = self.gd.stages
        event_stages = [x for x in stages if x["m_area_id"] == event_area_id]
        event_stages.sort(key=lambda x: x['sort'], reverse=True)
        
        # initial run, 3 star event first
        for event_stage in event_stages:
            if self.is_stage_3starred(stage_id=event_stage['id']):
                continue
            self.doQuest(m_stage_id=event_stage['id'], team_num=team_to_use)
            number_of_runs +=1
            if number_of_runs == daily_run_limit:
                return

        # If there are runs left, do them on the highest stagge
        while number_of_runs < daily_run_limit:
            self.doQuest(m_stage_id=event_stages[0]['id'], team_num=team_to_use)
            number_of_runs +=1

    def clear_story_event(self, team_to_use:int=1):        
        event_area_IDs =  Constants.Current_Story_Event_Area_IDs if self.o.region == 2 else Constants.Current_Story_Event_Area_IDs_JP
        self.player_stage_missions(True)
        stages = self.gd.stages
        rank = [1,2,3]
        for k in rank:
            for i in event_area_IDs:
                stage_for_area_and_rank = [x for x in stages if x["m_area_id"]==i and x["rank"]==k]
                for stage in stage_for_area_and_rank:
                    if self.is_stage_3starred(stage['id']):
                        continue
                    self.doQuest(m_stage_id=stage['id'], team_num=team_to_use)

    def story_event_daiy_500Bonus(self, team_to_use:int=1):        
        event_area_IDs =  Constants.Current_Story_Event_Area_IDs if self.o.region == 2 else Constants.Current_Story_Event_Area_IDs_JP
        from data import data as gamedata
        stages = self.gd.stages
        rank = [1,2,3]
        for k in rank:
            for area_id in event_area_IDs:
                bonus_stage = [x for x in stages if x["m_area_id"]==area_id and x["rank"]==k and x["no"] == 5]
                self.doQuest(m_stage_id=bonus_stage[0]['id'], team_num=team_to_use)
                self.raid_share_own_boss(party_to_use=team_to_use)
    
    def print_event_info(self):            
        events = self.client.event_index()
        for event in events['result']['events']:
            event_id = event['m_event_id']
            event_data = next((x for x in self.gd.events if x['id'] == event_id),None)
            if event_data is None:
                self.log('Event with id %s not found:' % (event_id))
            else:
                try:
                    event_enum = Event_Type(event_data['event_type'])
                    event_type = event_enum.name
                except ValueError:
                    event_type = 'unknown event type'
                self.log('Event with id %s - Name: %s - Type: %s' % (event_id, event_data['resource_name'], event_type))
                
    def do_netherworld_travel(self):
        
        data = self.client.netherworld_travel_index()
        status, travel_id, cleared_areas, t_character_ids, remaining_stages, remaining_areas = self.get_netherworld_travel_status(data)

        # ongoing travel
        if status == 1:  # ongoing travel
            self.log(f'Continuing Netherworld Travel {travel_id} - {remaining_areas} Areas remaining')
        # Need to select negative effect to complete area
        elif data['result']['t_travel']['status'] == 3:            
            effect_selection = self. get_netherworld_travel_negative_effect(t_character_ids, cleared_areas-1)
            self.client.netherworld_travel_select_negative_effect(t_character_id=effect_selection['character_id'], 
                            effect_id=effect_selection['effect_id'])   
            data = self.client.netherworld_travel_index()
            status, travel_id, cleared_areas, t_character_ids, remaining_stages, remaining_areas = self.get_netherworld_travel_status(data)
            self.log(f'Continuing Netherworld Travel {travel_id} - {remaining_areas} Areas remaining')  
        else:
            used_character_ids = data['result']['t_travel']['used_t_character_ids']
            # Find up to 2 unused characters
            available_chars = [
                char for char in self.pd.characters
                if char['id'] not in used_character_ids
            ][:2]  # Take the first 2
            if len(available_chars) < 2:
                raise ValueError("Not enough unused characters available (need at least 2)")
            # Fill the t_character_ids array: 2 valid IDs + 3 zeros
            t_character_ids = [char['id'] for char in available_chars] + [0] * (5 - len(available_chars))
            remaining_stages = 3
            cleared_areas = 0 
            travel_id = len(data['result']['t_travel']['cleared_m_travel_ids']) + 1 
            travel_start = self.client.netherworld_travel_start(
                m_travel_id=travel_id,
                t_character_ids=t_character_ids
            )
            remaining_areas = len(travel_start['result']['after_t_travel_status']['m_travel_area_ids'])
            self.log('Starting Netherworld Travel %s - %s Areas remainings' % (travel_id, remaining_areas))
           
        while remaining_areas > 0:
            self.log('\tClearing Area %s - %s Areas remainings' % (cleared_areas+1, remaining_areas-1))
            is_last_area = remaining_areas == 1
            self.nethworld_travel_clear_area(remaining_stages, t_character_ids, cleared_areas, is_last_area)
            remaining_areas -= 1
            cleared_areas += 1
        self.log('Netherworld Travel Complete!')          
     
    def nethworld_travel_clear_area(self, remaining_stages:int, t_character_ids:List[int], 
                                    cleared_areas:int, is_last_area:bool):
        while remaining_stages > 0:
                battle_start = self.client.netherworld_travel_battle_start()
                if 'api_error' in battle_start:
                    return
                
                battle_type = battle_start['result']['battle_type']                
                end_prms = self.get_netherworld_travel_battle_end_data(t_character_ids)
                end = self.client.battle_end_netherworld_travel(end_prms)
                
                # Select the benefit
                rewards = end['result']['after_t_travel_status']['lotteried_m_travel_benefit_ids']
                benefit = self.get_netherworld_travel_benefit_id(rewards)
                
                self.client.netherworld_travel_receive_reward(benefit)
                remaining_stages -= 1
                if remaining_stages == 0 and is_last_area == False:
                    negative_effect_selection = self. get_netherworld_travel_negative_effect(t_character_ids, cleared_areas)
                    self.client.netherworld_travel_select_negative_effect(t_character_id=negative_effect_selection['character_id'], 
                            effect_id=negative_effect_selection['effect_id'])
            
    def get_netherworld_travel_benefit_id(self, possible_rewards:List[int]):
        skip_min = 202751
        skip_max = 202875

        # Filter out numbers in the skip range
        filtered_array = [x for x in possible_rewards if not (skip_min <= x <= skip_max)]

        # If filtered list is not empty, pick from it; else fallback to full list
        if filtered_array:
            benefit = random.choice(filtered_array)
        else:
            benefit = random.choice(possible_rewards)  # fallback
        benefit = random.choice(possible_rewards)
        return benefit
    
    def get_netherworld_travel_negative_effect(self, character_ids:List[int], cleared_areas:int):
        if cleared_areas == 0:
            return {"character_id": character_ids[0], "effect_id": 1}
        if cleared_areas <= 3:
            return {"character_id": character_ids[1], "effect_id": 2}
        if cleared_areas == 4:
            return {"character_id": character_ids[1], "effect_id": 1}
        return {"character_id": character_ids[0], "effect_id": 2}        
        
    def get_netherworld_travel_battle_exp_data(self, start, unitID):
        res = []
        for d in start['result']['enemy_list']:
            for r in d:
                res.append({
                    "finish_member_ids": unitID,
                    "finish_type": 1,
                    "m_enemy_id": d[r]
                })
        return res
    
    def get_netherworld_travel_battle_exp_data_(self, unitID):
        res = [{"m_enemy_id":1,"finish_type":2,"finish_member_ids":[unitID]},{"m_enemy_id":2,"finish_type":2,"finish_member_ids":[unitID]},{"m_enemy_id":3,"finish_type":2,"finish_member_ids":[unitID]},{"m_enemy_id":4,"finish_type":2,"finish_member_ids":[unitID]},{"m_enemy_id":5,"finish_type":2,"finish_member_ids":[unitID]}]
        return res
    
    def get_netherworld_travel_battle_end_data(self, character_ids:List[int]):
        # Build the character result object
        # {"character_results":[{"t_character_id":1210284631,"hp":10000,"sp":2},{"t_character_id":1210284639,"hp":0,"sp":20},{"t_character_id":1210424191,"hp":0,"sp":20},{"t_character_id":1210284636,"hp":0,"sp":20},{"t_character_id":1211078400,"hp":5001,"sp":41}]}}          
        valid_character_ids = [cid for cid in character_ids if cid != 0]
        character_results = [
            {
                "t_character_id": cid,
                "hp": 10000,
                "sp": random.randint(1, 100)  # Random SP between 1–100
            }
            for cid in valid_character_ids
        ]      

        # Sample
        # end = self.client.battle_end(
        #     m_stage_id = 0,
        #     m_tower_no = 0,
        #     equipment_id = 0,
        #     equipment_type = 0,
        #     innocent_dead_flg = 0,
        #     raid_status_id = 0,
        #     raid_battle_result = '',
        #     division_battle_result = '',
        #     battle_type = battle_type,
        #     result =1,
        #     battle_exp_data = self.get_netherworld_travel_battle_exp_data_([t_character_ids[0]]),
        #     common_battle_result = 'eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6NTY5NTA3NTY1MDgsImRwcGNiZXc5bXo4Y3V3d24iOjAsInphY3N2NmpldjRpd3pqem0iOjQsImt5cXluaTNubm0zaTJhcWEiOjAsImVjaG02dGh0emNqNHl0eXQiOjAsImVrdXN2YXBncHBpazM1amoiOjAsInhhNWUzMjJtZ2VqNGY0eXEiOjF9.KahxV57rT2js8_GxbuxtFkmq1xILV1xXc3Jej3EWp6I',
        #     skip_party_update_flg = True,
        #     travel_battle_result = self.get_netherworld_travel_battle_result_(t_character_ids[0]) 
        # )
                
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
            "battle_type": 14,
            "result": 1,
            "battle_exp_data": [
                {"m_enemy_id": 2, "finish_type": 1, "finish_member_ids": [character_ids[0]]},
                {"m_enemy_id": 3, "finish_type": 1, "finish_member_ids": [character_ids[0]]},
                {"m_enemy_id": 1, "finish_type": 1, "finish_member_ids": [character_ids[0]]},
                {"m_enemy_id": 4, "finish_type": 1, "finish_member_ids": [character_ids[0]]},
                {"m_enemy_id": 5, "finish_type": 1, "finish_member_ids": [character_ids[0]]},
            ],
            "common_battle_result": "eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6NDc4Mjg1NzI2NjcsImRwcGNiZXc5bXo4Y3V3d24iOjAsInphY3N2NmpldjRpd3pqem0iOjQsImt5cXluaTNubm0zaTJhcWEiOjAsImVjaG02dGh0emNqNHl0eXQiOjAsImVrdXN2YXBncHBpazM1amoiOjAsInhhNWUzMjJtZ2VqNGY0eXEiOjB9.Rs6ryHWP7ch99lxUNE118fWHckgr_1vvMfjrpYcz6WA",
            "skip_party_update_flg": True,
            "m_event_id": 0,
            "board_battle_result": "",
            "tournament_score": 0,
            "tournament_battle_result": "",
            "travel_battle_result": {
                "character_results":character_results
            }
        }
        return payload
    
    def get_netherworld_travel_status(self, data):
        status = data['result']['t_travel']['status']
        travel_id = data['result']['t_travel_status']['m_travel_id']
        t_status = data['result']['t_travel_status']
        cleared_areas = t_status.get('cleared_area_num', 0)
        cleared_stages = t_status.get('cleared_stage_num', 0)
        t_character_ids = t_status.get('t_character_ids', [0]*5)
        total_areas = len(t_status.get('m_travel_area_ids', []))
        remaining_stages = 3 - cleared_stages  # 3 stages per area fixed
        remaining_areas = total_areas - cleared_areas
        return status, travel_id, cleared_areas, t_character_ids, remaining_stages, remaining_areas