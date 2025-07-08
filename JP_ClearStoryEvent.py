import datetime
from bot import Bot
from dateutil import parser
from api.constants import Battle_Type, Constants, Event_Type, Item_Types, Item_World_Mode, Item_World_Drop_Mode, Items, Innocent_ID
from main import API

a = API()
a.config(
    sess='',
    uin='',
    wait=0,
    region=1,
    device=3
)
try:
    with open('transfercode.txt') as f:
        lines = f.readlines()
    if lines is not None:
        code = lines[0] 
except FileNotFoundError:
    print("transfercode.txt does not exist")
    code = 'TRANSFER CODE GOES HERE THE FIRST TIME YOU USE THE BOT'



a.loginfromcache()
#a.loginfromcache_fast()

#a.print_team_info(5)

a.print_event_info()

a.o.use_potions = True

events = a.client.event_index()
for event in events['result']['events']:
    event_id = event['m_event_id']
    event_data = next((x for x in a.gd.events if x['id'] == event_id),None)
    if event_data is None:
        continue
    if event_data['event_type'] == Event_Type.Story_Event or event_data['event_type'] == Event_Type.Story_Event_New:
        a.farm_story_event(event_id)
        a.clear_story_event(event_data)
        story_event_id = event_id
        story_event_data = event_data
    elif event_data['event_type'] == Event_Type.Story_Event_Special_Gate:
        if event['challenge_num'] == 0:
            story_event_special_gate_id = event_id
            story_event_special_gate_event_data = event_data
            area = next((x for x in a.gd.areas if x['m_episode_id'] == story_event_special_gate_event_data['m_episode_id']),None)
            stage =  next((x for x in a.gd.stages if x['m_area_id'] == area['id']),None)
            a.log(f"Clearing Event Special Stage...") 
            a.doQuest(stage['id'], team_num=1, send_friend_request=False)
    elif event_data['event_type'] == Event_Type.Etna_Defense:
        a.log('Completing Etna Defense event...')      
        a.client.apply_equipment_preset_to_team(2, 2)
        max_challenges = event_data['challenge_max']
        event_area =  next((x for x in a.gd.areas if x['m_episode_id'] == event_data['m_episode_id']),None)
        a.clear_etna_or_udt_event(team_to_use=2, event_area_id=event_area['id'], daily_run_limit=max_challenges, event_id=event['m_event_id'])

a.doQuest(m_stage_id=18052016, use_item_id=5927, use_item_num=50)
a.event_claim_daily_missions()
a.event_claim_character_missions()
a.event_claim_story_missions()
a.event_claim_mission_repetitions()

#a.complete_netherworld_travel()
a.do_single_netherworld_travel(force_travel_id=21)

i = 0   
while i < 40:
    a.do_single_netherworld_travel(force_travel_id=10)
    i += 1

