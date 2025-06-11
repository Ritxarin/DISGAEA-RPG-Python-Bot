from api.constants import Constants, Battle_Finish_Mode
from main import API

a = API()

#################################################################################################################################
## List of useful commands, pick whichever ones you like to build your script
#################################################################################################################################

# Complete overlord Tower
a.Complete_Overlord_Tower()

# Use Gate Keys - needs area ID and stage ID
m_area_id = 50101
m_stage_id = 5010125
a.client.item_use_gate_key(m_area_id=m_area_id, m_stage_id=m_stage_id)

# Prints data for a specific team
a.print_team_info(team_num=4)

# Aply an equipment preset to a team. Index starts at 1
a.client.apply_equipment_preset_to_team(team_number=4, equipment_preset=4)

# Sells common items with no rare or above innocents. You can choose to sell either weapons or equipments and the number of items to sell
a.shop_free_inventory_space(sell_weapons=True, sell_equipment=False, items_to_sell=30)
a.shop_free_inventory_space(sell_weapons=False, sell_equipment=True, items_to_sell=30)

# Sells all r40 items with no innocents
a.sell_r40_commons_with_no_innocents()

# Use shop lottery tickets
a.shop_use_lottery_tickets(ticket_to_use=50)

# Redeem code
a.client.boltrend_exchange_code('Ainuko0925')

# Send friend request using public ID or username
a.add_friend_by_public_id(82330659928)
a.add_friend_by_name('usename')

# Super reincarnate unit by character id (use print_team_info to get the id)
a.super_reincarnate(character_id=207410913)

#################################################################################################################################
## Present box methods
#################################################################################################################################

# Claims AP from present box
a.present_receive_ap()

# Claims all items from mailbox except equipments and AP
a.present_receive_all_except_equip_and_AP()

# Claims equipments from the present box until inventory is full
a.present_receive_equipment()

##########################################################################
# DoQuest parameters
###########################################################################

# team_to_use: specify which team to use to clear the quest
team_to_use = 5

# Friend ID. Specify a friend to use for a quest, useful for gates. Use the friend_print_full_list to get the id first
a.friend_print_full_list()
help_t_player_id = 0

# send_friend_request, set to True to automatically send a friend request after clearing the quest
send_friend_request = True

#  Choose the battle finish mode. Random is chosen by default
#  Battle_Finish_Mode.Random_Finish randomly choose which unit kills each enemy (default mode)
#  Battle_Finish_Mode.Tower_Finish all enemies are killed using tower attack, exp is shared evenly
#  Battle_Finish_Mode.Single_Character the character on the leader slot will kill all enemies and get all exp
finish_mode = Battle_Finish_Mode.Tower_Finish

a.doQuest(m_stage_id=m_stage_id, team_num=team_to_use, help_t_player_id=help_t_player_id,
          send_friend_request=send_friend_request, finish_mode=finish_mode)

##########################################################################
# Prism Ranger Stage farm
###########################################################################


indigo_ranger_stage_id = 106509
orange_ranger_stage_id = 105514
white_ranger_stage_id = 201509
blue_ranger_stage_id = 101509
purple_ranger_stage_id = 104509
green_ranger_stage_id = 103511
black_ranger_stage_id = 202509
pink_ranger_stage_id = 107509
yellow_ranger_stage_id = 102509