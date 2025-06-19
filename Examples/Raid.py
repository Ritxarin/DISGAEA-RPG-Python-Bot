from api.constants import Constants
import time
from main import API

a = API()
a.config(
    sess=Constants.session_id,
    uin=Constants.user_id,
    wait=0,
    region=2,
    device=2
)
a.quick_login()

# List of all raid methods
# Make sure the raid constants have the correct value on the constants file
# The following values need to be updated for every raid
# Current_Raid_ID = 165

# claims rewards for all boss battles
a.raid_claim_all_boss_rewards()

# claim all point rewards
a.raid_claim_all_point_rewards()

#exchange excess points for HL
a.raid_claim_surplus_points()

# Spin innocent roulette
a.raid_spin_innocent_roulette()

# Claim raid missions
a.raid_claim_missions()

# Party that will be used to farm raids. Use the party with innocent boost characters
raid_farming_party = 5

# Share own raid boss (will enter the fight and give up to get innocent chance bonus)
a.raid_share_own_boss(party_to_use = raid_farming_party)

# Farm raid bosses until script is stopped
while True:
    
    a.raid_farm_shared_bosses(party_to_use = raid_farming_party)

    time.sleep(10)