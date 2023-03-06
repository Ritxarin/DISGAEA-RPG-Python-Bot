import datetime
from api.constants import Mission_Status

from dateutil import parser

from api.constants import Constants
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

## Specify event team to be used here
event_team = 5
raid_team = 6

## Run stages with daily 500% bonus
a.story_event_daiy_500Bonus(team_to_use=event_team)

# Buy 5 AP pots daily - ID needs to be updated
a.event_buy_daily_AP(289001)

# Claim daily missions
a.event_claim_daily_missions()

# Claim event missions
a.event_claim_story_missions()

# Claim character missions
a.event_claim_character_missions()