from api.constants import Constants, Item_World_Mode, Item_World_Drop_Mode, Innocent_ID
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

# Team to use for IW
a.o.team_num = 1

# Party you want to use to farm raid bosses. 0 to disable it
raid_party_to_use = 0

# Configure items to run
max_innocent_rank_to_donate = 7  # do not donate items with innocents above this rank
max_item_rarity_to_donate = 60  # do not donate items above this rarity
max_item_rank_to_donate = 40  # do not donate items above this rank
min_item_rank_to_run = 40  # do not run IW for items below this rank
a.options.min_item_rank = 40 # lowest item rank to run
a.options.min_drop_item_rarity = 0 # lowest item rarity drop

# select if you want to run only weapons, equipments or all items (default option)
# Item_World_Mode.Run_Weapons_Only Item_World_Mode.Run_Equipment_Only Item_World_Mode.Run_All_Items
a.options.item_world_mode = Item_World_Mode.Run_All_Items 
# set to Item_World_Drop_Mode.Drop_Weapons_Only if you want to get only weapons
a.options.item_world_drop_mode = Item_World_Drop_Mode.Drop_All_Items
# set to true to ensure drops on every boss stage. If false the bot won't retry boss stages
a.options.item_world_ensure_drops = True
# Specify the minimum rarity of items to farm for
a.o.min_rarity = 0

# Will run through X items in a batch
# Uncomment lines inside the loop to activate additional functionality (check depository status, donate items, farm raid...)
# item_limit is the number of item clears after which the bot checks the depository/raid/IW expedition status

batch_size = 15
batches_to_run = 2

batch_count = 0
while batch_count < batches_to_run:
    item_count = 0
    while item_count < batch_size:
        a.upgrade_items(item_limit=1)

        # # Uncomment this line for automatically fetching maxed items from the depository and filling it again with new items
        # a.etna_resort_check_deposit_status(max_innocent_rank = max_innocent_rank_to_donate, max_item_rank_to_donate=max_item_rank_to_donate, max_item_rarity_to_donate = max_item_rarity_to_donate, min_item_rank_to_deposit=min_item_rank_to_run)

        ## Uncomment this line to check the status of item world survey after every clear
        # a.item_survey_complete_and_start_again(min_item_rank_to_deposit=40, auto_donate=True)          

        ## Uncomment this line to farm raid bosses after every clear
        # if raid_party_to_use != 0:
        #     a.raid_farm_shared_bosses(party_to_use= raid_party_to_use)

        item_count += 1
    
    ## After running a batch, donate items. If the items have important innocents, remove them first
    a.etna_resort_donate_items(max_innocent_rank=6, max_item_rank = max_item_rank_to_donate, max_item_rarity = max_item_rarity_to_donate, remove_innocents=True)
    ## Donate innocents we may have removed in the step above
    a.etna_donate_innocents(max_innocent_rank=6, max_innocent_type= Innocent_ID.HL)
    #a.sell_r40_commons_with_no_innocents(item_count=20)
    batch_count += 1

a.etna_resort_get_all_daily_rewards()