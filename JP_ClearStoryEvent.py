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


#a.dologin(, code)
a.loginfromcache()
#a.loginfromcache_fast()

a.print_team_info(5)

def get_boss_stage_key_cost(defense_point:int):
    if defense_point < 4200:
        return 5
    if defense_point < 11400:
        return 15
    if defense_point < 23000:
        return 30
    return 50

def clear_area(area_id:int):
    area_stages = [x for x in a.gd.stages if x['m_area_id'] == area_id]
    for stage in area_stages:
        if a.is_stage_3starred(stage['id']):
            a.log('Stage already 3 starred - area: %s stage: %s rank: %s name: %s' % (
                        stage['m_area_id'], stage['id'], stage['rank'], stage['name']))      
        else:
            if(stage['defense_point'] != 0):
                use_item_id = key['id']
                use_item_num = get_boss_stage_key_cost(stage['defense_point'])
                key_pd = a.pd.get_item_by_m_item_id(key['id'])
                if key is None or key_pd['num_total']< use_item_num:
                    a.log(f"Not enough Boss Keys left. Exiting...")            
                    break
            else:
                use_item_id = 0
                use_item_num = 0
            a.doQuest(stage['id'], team_num=1, send_friend_request=False, use_item_id=use_item_id, use_item_num=use_item_num)


#a.complete_netherworld_travel()
a.print_event_info()

a.o.use_potions = True

story_event_id = 0
story_event_data = 0
story_event_special_gate_id = 0
story_event_special_gate_event_data = 0

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
    elif event_data['event_type'] == Event_Type.Etna_Defense:
        a.log('Completing Etna Defense event...')      
        a.client.apply_equipment_preset_to_team(2, 2)
        max_challenges = event_data['challenge_max']
        event_area =  next((x for x in a.gd.areas if x['m_episode_id'] == event_data['m_episode_id']),None)
        a.clear_etna_or_udt_event(team_to_use=2, event_area_id=event_area['id'], daily_run_limit=max_challenges, event_id=event['m_event_id'])

a.do_single_netherworld_travel(force_travel_id=21)

# i = 0    
# while i < 40:
#     a.do_single_netherworld_travel(force_travel_id=10)
#     i += 1


#farm story event stages
if story_event_id != 0:
    server_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9) 
    server_date = server_time.date()
    event_data = a.client.event_index([story_event_id])
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
            a.battle_skip(m_stage_id=stage_id, skip_number = chalenges_left, battle_type = Battle_Type.Story_Event)


a.event_claim_daily_missions()
a.event_claim_character_missions()
a.event_claim_story_missions()
a.event_claim_mission_repetitions()

if story_event_special_gate_id != 0:
    area_id = int("{0}{1}".format(story_event_special_gate_event_data['m_episode_id'], "01"))
    areas = [x for x in a.gd.areas if x['m_episode_id'] == story_event_special_gate_event_data['m_episode_id']]
    stage =  next((x for x in a.gd.stages if x['m_area_id'] == area_id),None)
    a.doQuest(stage['id'], team_num=1, send_friend_request=False)
        

if story_event_id != 0:
    cleared_stages = a.get_cleared_stages()
    items = a.gd.items
    key =  next((x for x in items if x['item_type'] == Item_Types.Event_Stage_Key and x['effect_value'] == [story_event_id]),None)
    areas = [x for x in a.gd.areas if x['m_episode_id'] == story_event_data['m_episode_id']]
    for area in areas:
        clear_area(area['id'])
        
    another_areas = areas = [x for x in a.gd.areas if x['m_episode_id'] == story_event_data['another_m_episode_id']]
    if another_areas is not None:
        for area in another_areas:
            clear_area(area['id'])