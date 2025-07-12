from abc import ABCMeta
import datetime
from dateutil import parser
import random
from typing import List
from api.player import Player
from api.constants import Battle_Type, Event_Type, Item_Types, Mission_Status, Constants, Event_Type

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
            self.doQuest(m_stage_id=event_stage['id'], team_num=team_to_use)
            number_of_runs +=1
 
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
       
    def complete_netherworld_travel(self):
        
        data = self.client.netherworld_travel_index() 
        # Calculate how many travels have been completed already
        cleared_travel_ids = data['result']['t_travel'].get('cleared_m_travel_ids', [])
        current_travel_id = len(cleared_travel_ids) + 1

        # If there's an ongoing or waiting-for-negative-effect travel, complete it first
        status = data['result']['t_travel']['status']
        if status in (1, 3):
            current_travel_id = data['result']['t_travel_status']['m_travel_id']
            self.log(f"Resuming current travel (ID {current_travel_id})")
            self.do_single_netherworld_travel(force_travel_id=current_travel_id)
            current_travel_id += 1  # Finished one, move to the next

        # Continue until we reach travel 10
        while current_travel_id <= 10:
            self.log(f"Starting travel {current_travel_id} of 10")
            self.do_single_netherworld_travel(force_travel_id=current_travel_id)
            current_travel_id += 1

        self.log("All 10 Netherworld Travels completed!")
        
        if data['result']['t_travel']['shura_played'] == False:
            self.log("Clearing Carnage Netherworld travel!")
        
    def do_single_netherworld_travel(self, force_travel_id: int = None):
        
        if force_travel_id > 10 and force_travel_id != 21:
            self.log(f"Travel id cannot exceed 10. Returning...")
            return
        
        data = self.client.netherworld_travel_index()        
        if force_travel_id == 21 and data['result']['t_travel']['shura_played'] == True:
            self.log(f"Carnage Netherworld Travel already cleared today. Returning...")
            return
        
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
            remaining_stages = 3
            cleared_areas = 0
            
            # either the travel id passed as param or the highest available
            if force_travel_id != 21:
                travel_id = min(force_travel_id or len(data['result']['t_travel'].get('cleared_m_travel_ids', [])) + 1, 10)
            else:
                travel_id = force_travel_id
                
            required_character_count = self.get_netherworld_travel_required_characters(travel_id)
            used_character_ids = data['result']['t_travel']['used_t_character_ids']
            available_characters = self.netherworld_travel_get_team(required_character_count, used_character_ids)
            t_character_ids = [char['id'] for char in available_characters] + [0] * (5 - len(available_characters))
            
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
                end = self.client.battle_end_end_with_payload(end_prms)
                
                # Select the benefit
                rewards = end['result']['after_t_travel_status']['lotteried_m_travel_benefit_ids']
                benefit = self.get_netherworld_travel_benefit_id(rewards)
                
                self.client.netherworld_travel_receive_reward(benefit)
                remaining_stages -= 1
                if remaining_stages == 0 and is_last_area == False:
                    negative_effect_selection = self. get_netherworld_travel_negative_effect(t_character_ids, cleared_areas)
                    self.client.netherworld_travel_select_negative_effect(t_character_id=negative_effect_selection['character_id'], 
                            effect_id=negative_effect_selection['effect_id'])
            
    def get_netherworld_travel_benefit_id(self, possible_rewards: List[int]) -> int:
        skip_ranges = [
            (203001, 203125),  # axe statue
            (200501, 201250),  # statues
            (200001, 200250),
            (100001, 100165),  # restore
            (202755, 202875),  # grazing ticket
            (201626, 201750),
        ]

        def is_not_skipped(x):
            return all(not (start <= x <= end) for start, end in skip_ranges)

        # Filter out skipped ranges
        filtered_array = [x for x in possible_rewards if is_not_skipped(x)]

        # Choose from filtered or fallback to original if nothing remains
        if filtered_array:
            return random.choice(filtered_array)
        else:
            return random.choice(possible_rewards)

    def get_netherworld_travel_negative_effect(self, character_ids:List[int], cleared_areas:int):
        if cleared_areas == 0:
            return {"character_id": character_ids[0], "effect_id": 1}
        if cleared_areas <= 3:
            return {"character_id": character_ids[0], "effect_id": 2}
        if cleared_areas == 4:
            return {"character_id": character_ids[0], "effect_id": 3}
        if cleared_areas == 5:
            return {"character_id": character_ids[1], "effect_id": 1}
        if cleared_areas <= 8:
            return {"character_id": character_ids[1], "effect_id": 2}
        if cleared_areas == 9:
            return {"character_id": character_ids[1], "effect_id": 3}  
        if cleared_areas == 10:
            return {"character_id": character_ids[2], "effect_id": 1} 
        if cleared_areas <= 13:
            return {"character_id": character_ids[2], "effect_id": 2} 
        if cleared_areas == 14: 
            return {"character_id": character_ids[2], "effect_id": 3}
        if cleared_areas == 15:
            return {"character_id": character_ids[3], "effect_id": 1} 
        if cleared_areas <= 18:
            return {"character_id": character_ids[3], "effect_id": 2} 
        if cleared_areas == 19: 
            return {"character_id": character_ids[3], "effect_id": 3} 
        if cleared_areas == 20: 
            return {"character_id": character_ids[4], "effect_id": 3}
        if cleared_areas == 21:
            return {"character_id": character_ids[4], "effect_id": 1} 
        if cleared_areas <= 24:
            return {"character_id": character_ids[4], "effect_id": 2} 
        if cleared_areas == 25: 
            return {"character_id": character_ids[4], "effect_id": 3} 
                      
    def get_netherworld_travel_required_characters(self, travel_id):
        if travel_id <= 4:
            return 1
        if travel_id <= 6:
            return 2
        if travel_id <= 8:
            return 3
        if travel_id == 9:
            return 4
        return 5
    
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
    
    def netherworld_travel_get_team(self, required_characters: int, used_character_ids: list[int]) -> list[dict]:
        seen_m_ids = set()
        unique_chars = []
        
        for char in self.pd.characters:
            if char['id'] in used_character_ids:
                continue
            m_id = char['m_character_id']
            if m_id in seen_m_ids:
                continue
            unique_chars.append(char)
            seen_m_ids.add(m_id)
            if len(unique_chars) == required_characters:
                break

        if len(unique_chars) < required_characters:
            raise ValueError(f'Not enough unused and unique characters available (need at least {required_characters})')

        return unique_chars
    
    def farm_story_event(self, story_event_id:int):
        server_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9) 
        server_date = server_time.date()
        event_data = self.client.event_index([story_event_id])
        for challenge_stage in event_data['result']['t_event_stage_challenges']:
            stage_id = challenge_stage['m_stage_id']
            last_play_at_string = challenge_stage['last_play_at']
            last_play_at_date = parser.parse(last_play_at_string).replace(tzinfo=datetime.timezone.utc)
            challenges = challenge_stage['challenge_num']
            # If not challenged today, set remaining attempts to max
            if  last_play_at_date.date() < server_date:
                challenges = 0
            if challenges < 3:
                chalenges_left = 3 - challenges
                self.battle_skip(m_stage_id=stage_id, skip_number = chalenges_left, battle_type = Battle_Type.Story_Event)
            
    def clear_story_event(self, story_event_data):
        cleared_stages = self.get_cleared_stages()
        story_event_id = story_event_data["id"]
        items = self.gd.items
        key =  next((x for x in items if x['item_type'] == Item_Types.Event_Stage_Key and x['effect_value'] == [story_event_id]),None)
        areas = [x for x in self.gd.areas if x['m_episode_id'] == story_event_data['m_episode_id']]
        for area in areas:
            self.clear_story_event_area(area['id'], key)
            
        another_areas = areas = [x for x in self.gd.areas if x['m_episode_id'] == story_event_data['another_m_episode_id']]
        if another_areas is not None:
            for area in another_areas:
                self.clear_story_event_area(area['id'], key)
                
    def get_story_event_boss_stage_key_cost(self, defense_point:int):
        if defense_point < 4200:
            return 5
        if defense_point < 11400:
            return 15
        if defense_point < 23000:
            return 30
        return 50

    def clear_story_event_area(self, area_id:int, key):
        area_stages = [x for x in self.gd.stages if x['m_area_id'] == area_id]
        for stage in area_stages:
            if self.is_stage_3starred(stage['id']):
                self.log('Stage already 3 starred - area: %s stage: %s rank: %s name: %s' % (
                            stage['m_area_id'], stage['id'], stage['rank'], stage['name']))      
            else:
                if(stage['defense_point'] != 0):
                    use_item_id = key['id']
                    use_item_num = self.get_story_event_boss_stage_key_cost(stage['defense_point'])
                    self.player_items(refresh=True)
                    key_pd = self.pd.get_item_by_m_item_id(key['id'])
                    if key is None or key_pd['num']< use_item_num:
                        self.log(f"Not enough Boss Keys left. Exiting...")            
                        break
                else:
                    use_item_id = 0
                    use_item_num = 0
                self.doQuest(stage['id'], team_num=1, send_friend_request=False, use_item_id=use_item_id, use_item_num=use_item_num)