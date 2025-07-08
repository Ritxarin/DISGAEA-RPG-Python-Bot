from api.constants import Item_World_Mode, Item_World_Drop_Mode

class Options:

    def __init__(self, region, device):
        self.main_url: (str, None) = None
        self.version: (str, None) = None
        self.region: (str, None) = None
        self.device: (str, None) = None
        self.platform: (str, None) = None
        self.pid: (str, None) = None
        self.session_id: (str, None) = None
        self.password: (str, None) = None
        self.sess: (str, None) = None
        self.uin: (str, None) = None
        self.current_iv: (str, None) = None
        self.newest_resource_version: (str, None) = None
        self.wait: int = 0
        self.uuid: (str, None) = None
        self.sdk: (str, None) = None

        self.common_battle_result: str = "eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiMSwxLDEi" \
                                         "LCJ5cGIyODJ1dHR6ejc2Mnd4Ijo5MDY3NDE5NzQsImRwcGNiZXc5bXo4Y" \
                                         "3V3d24iOjAsInphY3N2NmpldjRpd3pqem0iOjAsImt5cXluaTNubm0zaT" \
                                         "JhcWEiOjAsImVjaG02dGh0emNqNHl0eXQiOjAsImVrdXN2YXBncHBpazM" \
                                         "1amoiOjAsInhhNWUzMjJtZ2VqNGY0eXEiOjJ9.4kuAV7qO3Rp5Bq1ikSH" \
                                         "bn5nPxhvjsg5POnnlFNDlEu0"
        
        self.common_battle_result_iw:str = "eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MTA5NTkyOTY1MTg1OTIwLCJkcHBjYmV3OW16OGN1d3duIjowLCJ6YWNzdjZqZXY0aXd6anptIjowLCJreXF5bmkzbm5tM2kyYXFhIjowLCJlY2htNnRodHpjajR5dHl0IjowLCJla3VzdmFwZ3BwaWszNWpqIjoxODkwLCJ4YTVlMzIybWdlajRmNHlxIjoyMX0.JutnUBw7xPoWfB6DzJL_cv52pnzMlqFqTLy-bAGwTgI"
        self.common_battle_result_custombattle:str = "eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MTEwNTUwNjYzNjMsImRwcGNiZXc5bXo4Y3V3d24iOjAsInphY3N2NmpldjRpd3pqem0iOjAsImt5cXluaTNubm0zaTJhcWEiOjAsImVjaG02dGh0emNqNHl0eXQiOjAsImVrdXN2YXBncHBpazM1amoiOjAsInhhNWUzMjJtZ2VqNGY0eXEiOjF9.l8kCPjmBvKzkJExRe0ZHwM7vkYQZCjrOD1n2_xyBWOY"

        self.set_region(region)
        self.set_device(device)

        self.deck_index: int = 0
        self.min_rarity: int = 0 # This changes the minimum rarity of equipments found in the item-world. 1 = common, 40 = rare, 70 = Legendary
        self.min_rank: int = 0
        self.min_item_level: int = 0
        self.min_item_rank: int = 0
        self.min_drop_item_rarity: int = 0
        self.auto_rebirth: bool = False
        self.auto_rebirth_character_ids: list[int] = []
        self.use_potions: bool = False
        self.current_ap = 0
        ## Item world options
        self.item_world_mode: Item_World_Mode = Item_World_Mode.Run_All_Items
        self.item_world_drop_mode: Item_World_Drop_Mode = Item_World_Drop_Mode.Drop_All_Items
        self.item_world_ensure_drops: bool = True

    @property
    def team_num(self):
        return self.deck_index + 1

    @team_num.setter
    def team_num(self, r: int):
        self.deck_index = r - 1

    def disable_potion_usage(self):
        self.use_potions = False

    def enable_potion_usage(self):
        self.use_potions = True

    def set_region(self, r):
        if r == 1:
            self.main_url = 'https://api.rpg.disgaea-app.com/'
            self.version='3.6.2'
            self.region = 1
        else:
            self.main_url = 'https://disgaea-game-live-en.boltrend.com/'
            self.version = '2.16.4'
            self.region = 2

    def set_device(self, r):
        self.device = str(r)
        if self.device == '1':
            self.platform = 'iOS'
        if self.device == '2':
            self.platform = 'Android'
        if self.device == '3':
            self.platform = 'Steam'
            self.device = '2'
