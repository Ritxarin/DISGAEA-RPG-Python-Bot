import datetime

from dateutil import parser

from api.constants import Constants, Event_Type
from main import API

a = API()
a.config(
    sess=Constants.session_id,
    uin=Constants.user_id,
    wait=0,
    region=2,
    device=2
)
a.dologin()

# Send sardines
player_data = a.client.player_index()
if player_data['result']['act_give_count']['act_send_count'] == 0:
    a.client.friend_send_sardines()

# Buy items from HL shop
a.buy_daily_items_from_shop()

# Buy equipments with innocents. Will use free shop refreshes
shop_rank = player_data['result']['status']['shop_rank']
a.buy_all_equipment_with_innocents(shop_rank)
# Sell all items with innocents that are below max_innocent_rank (5=rare)
# max_item_rank is the highest item rank to be sold
a.innocent_safe_sell_items(max_innocent_rank=5, max_item_rank=10)

# Use free gacha
if a.is_free_gacha_available():
    print("free gacha available")
    a.get_free_gacha()

# Spin bingo
a.bingo_spin_roulette()

# Clear available character gates
a.clear_character_gates()

#  Votes a dark assembly agenda for mission completion (make sure id is valid)
# use_bribes will bribe the 4 and 2 star enators
a.vote_dark_assembly_agenda(agenda_id=110016, use_bribes=False)

## Clear UDT or Etna Defense stages (if they are open)
a.clear_event(event_type=Event_Type.Etna_Defense)
a.clear_event(event_type=Event_Type.UDT_Training)

## Do event daily 500% stages, buy AP and claim quests
a.event_buy_daily_AP(542001)
a.story_event_daiy_500Bonus(team_to_use=5)
a.event_claim_daily_missions()
a.event_claim_character_missions()
a.event_claim_story_missions()

## Claims quests
a.client.trophy_get_reward_daily()
a.client.trophy_get_reward_weekly()
a.client.trophy_get_reward()

a.present_receive_all_except_equip_and_AP()