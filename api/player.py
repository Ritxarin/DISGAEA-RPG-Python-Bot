from api.base import Base


class Player(Base):
    def __init__(self):
        super().__init__()

    def player_characters(self, refresh=False):
        if len(self.pd.characters) > 0 and not refresh:
            return self.pd.characters
        self.pd.characters = []
        self.logger.debug("refreshing player characters...")

        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_characters(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.characters = self.pd.characters + data['result']['_items']
            page_index += 1

        return self.pd.characters

    def player_character_collections(self, refresh=False):
        if len(self.pd.character_collections) > 0 and not refresh:
            return self.pd.character_collections
        self.pd.character_collections = []
        self.logger.debug("refreshing player character collections...")
        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_character_collections(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0 or len(data['result']['_items']) > 100:
                iterate_next_page = False
            self.pd.character_collections =  self.pd.character_collections + data['result']['_items']
            page_index += 1      
        return self.pd.character_collections

    def player_weapons(self, refresh=False):
        if len(self.pd.weapons) > 0 and not refresh:
            return self.pd.weapons
        self.pd.weapons = []
        self.logger.debug("refreshing player weapons...")
        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_weapons(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.weapons = self.pd.weapons + data['result']['_items']
            page_index += 1
        return self.pd.weapons

    def player_weapon_effects(self, refresh=False):
        if len(self.pd.weapon_effects) > 0 and not refresh:
            return self.pd.weapon_effects
        self.pd.weapon_effects = []
        self.logger.debug("refreshing player weapon effects...")

        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_weapon_effects(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.weapon_effects = self.pd.weapon_effects + data['result']['_items']
            page_index += 1
        return self.pd.weapon_effects

    def player_equipment(self, refresh=False):
        if len(self.pd.equipment) > 0 and not refresh:
            return self.pd.equipment
        self.pd.equipment = []
        self.logger.debug("refreshing player equipments...")

        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_equipments(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.equipment = self.pd.equipment + data['result']['_items']
            page_index += 1
        return self.pd.equipment

    def player_equipment_effects(self, refresh=False):
        if len(self.pd.equipment_effects) > 0 and not refresh:
            return self.pd.equipment_effects
        self.pd.equipment_effects = []
        self.logger.debug("refreshing player equipment effects...")

        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_equipment_effects(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.equipment_effects = self.pd.equipment_effects + data['result']['_items']
            page_index += 1
        return self.pd.equipment_effects

    def player_innocents(self, refresh=False):
        if len(self.pd.innocents) > 0 and not refresh:
            return self.pd.innocents
        self.pd.innocents = []
        self.logger.debug("refreshing player innocents...")

        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_innocents(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.innocents = self.pd.innocents + data['result']['_items']
            page_index += 1
        return self.pd.innocents

    def player_decks(self, refresh=False):
        if len(self.pd.decks) > 0 and not refresh:
            return self.pd.decks
        data = self.client.player_decks()
        self.pd.decks = data['result']['_items']
        return self.pd.decks

    def player_items(self, refresh=False):
        if len(self.pd.items) > 0 and not refresh:
            return self.pd.items
        self.pd.items = []
        self.logger.debug("refreshing player items...")

        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_items(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.items = self.pd.items + data['result']['_items']
            page_index += 1
        return self.pd.items

    def player_stone_sum(self):
        data = self.client.player_stone_sum()
        self.log('free stones:%s paid stones:%s' % (
            data['result']['_items'][0]['num'],
            data['result']['_items'][1]['num']))
        self.pd.gems = data['result']['_items'][0]['num']
        return data

    def player_clear_stages(self, refresh=False):
        if len(self.pd.clear_stages) > 0 and not refresh:
            return self.pd.clear_stages
        self.pd.clear_stages = []
        self.logger.debug("refreshing cleared stages...")
        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_clear_stages(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.clear_stages = self.pd.clear_stages + data['result']['_items']
            page_index += 1
        return self.pd.clear_stages

    def player_stage_missions(self, refresh=False):
        if len(self.pd.stage_missions) > 0 and not refresh:
            return self.pd.stage_missions
        self.pd.stage_missions = []
        self.logger.debug("refreshing player stage missions...")
        page_index = 1
        iterate_next_page = True
        while iterate_next_page:
            data = self.client.player_stage_missions(updated_at=0, page=page_index)
            if len(data['result']['_items']) <= 0:
                iterate_next_page = False
            self.pd.stage_missions = self.pd.stage_missions + data['result']['_items']
            page_index += 1
        return self.pd.stage_missions

    def char_stage_info(self, unit_id, use_cache=False):
        self.log("Looking for character stage info, with id: %s" % unit_id)
        m_character_id = 0
        for i in self.pd.characters:
            if i['id'] == unit_id:
                m_character_id = i['m_character_id']
                break

        if len(self.pd.character_collections) <= 0 or use_cache is False:
            self.player_character_collections(refresh=True)

        c = next((x for x in self.pd.character_collections if x['m_character_id'] == m_character_id), None)
        return c

    # Updates equipment with innocents list
    def player_update_equip_detail(self, e, innos=None):
        if innos is None:
            innos = []
        data = self.client.player_update_equip_detail(e, innos)
        self.pd.update_equip(data['result'])

    def print_team_info(self, team_num):
        data = self.player_decks()
        team = data[team_num - 1]['t_character_ids']
        for key in team.keys():
            unit_id = team[key]
            if unit_id == 0: continue
            unit = self.pd.get_character_by_id(unit_id)
            character = self.gd.get_character(unit['m_character_id'])
            unit_equipments = [x for x in self.player_equipment() if x['set_chara_id'] == unit_id]
            unit_weapons = [x for x in self.player_weapons() if x['set_chara_id'] == unit_id]
            unit_gear = unit_weapons + unit_equipments
            max_level = min((unit['rebirth_num'] +1) *100,9999)
            character_name = character['name'] if character is not None else f"unknown - ID: {unit['m_character_id']}"
            self.log(f"{character_name} - ID: {unit_id} - Level: {unit['lv']} / { max_level} - SR count: {unit['super_rebirth_num']} - Equipped items:")
            for equipment in unit_gear:
                if 'm_equipment_id' in equipment:
                    e = self.gd.get_equipment(equipment['m_equipment_id'])
                else:
                    e = self.gd.get_weapon(equipment['m_weapon_id'])
                print(
                    f"\t{e['name']} - Rarity: {equipment['rarity_value']} - Remake Count: {equipment['remake_count']} - ID: {equipment['id']}")

    def friend_print_full_list(self):
        print("\nPrinting full friend list....")
        data = self.client.friend_index()
        for friend in data['result']['friends']:
            print(f"\tName: {friend['name']} - ID: {friend['id']}")

    def player_get_equipment_presets(self, refresh=False):
        if len(self.pd.equipment_presets) > 0 and not refresh:
            return self.pd.equipment_presets
        self.pd.equipment_presets = self.client.player_equipment_decks()['result']['_items']
        return self.pd.equipment_presets
    
    def player_get_arena_defense(self):
        if len(self.pd.arena_gear_ids) == 0:        
            player_id = self.get_player_id()
            arena_data = self.client.pvp_enemy_player_detail(t_player_id=player_id)
            gear_ids = []
            for character in arena_data['result']['enemy_player']['characters']:
                if 'weapons' in character:
                    for weapon in character['weapons']:
                        gear_ids.append(weapon['id'])
                if 'equipments' in character:
                    for equipment in character['equipments']:
                        gear_ids.append(equipment['id'])
            self.pd.arena_gear_ids = gear_ids
        return self.pd.arena_gear_ids
    
    def get_player_id(self):
        return self.client.player_index()['result']['profile']['id'] 