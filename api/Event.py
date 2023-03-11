from abc import ABCMeta
from api.player import Player
from api.constants import Mission_Status, Constants, Event_Types

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

    def event_claim_story_missions(self):
        r = self.client.story_event_missions()
        mission_ids = []
        incomplete_mission_ids = []

        # character missions and story missions have to be claimed separately
        m_event_id = Constants.Current_Story_Event_ID if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
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
        m_event_id = Constants.Current_Story_Event_ID if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
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