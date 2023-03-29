import json
from typing import Iterable

from api.constants import EquipmentType
from api.game_data import GameData
from api.logger import Logger
from api.options import Options


class PlayerData:
    def __init__(self, options):
        self.o: Options = options
        self.gd: GameData = GameData(self.o.region)
        self.decks: [dict[Iterable]] = []
        self.gems: [dict[Iterable]] = []
        self.items: [dict[Iterable]] = []
        self.weapons: [dict[Iterable]] = []
        self.equipment: [dict[Iterable]] = []
        self.innocents: [dict[Iterable]] = []
        self.characters: [dict[Iterable]] = []
        self.character_collections: [dict[Iterable]] = []
        self.weapon_effects: [dict[Iterable]] = []
        self.equipment_effects: [dict[Iterable]] = []
        self.clear_stages: [dict[Iterable]] = []
        self.stage_missions: [dict[Iterable]] = []
        self.equipment_presets: [dict[Iterable]] = []

    def dump_to_file(self, file_path: str, extra_data=None):
        data = {
            "decks": self.decks,
            "gems": self.gems,
            "items": self.items,
            "weapons": self.weapons,
            "equipment": self.equipment,
            "innocents": self.innocents,
            "characters": self.characters,
            "character_collections": self.character_collections,
            "clear_stages": self.clear_stages,
            "stage_missions": self.stage_missions,
            "weapon_effects": self.weapon_effects,
            "equipment_effects": self.equipment_effects,
        }

        if extra_data is not None:
            data["extra_data"] = extra_data

        f = open(file_path, "w")
        f.write(json.dumps(data, indent=2, sort_keys=True))
        f.close()

    def deck(self, team_num: int = None):
        if team_num is None:
            deck_index = self.o.deck_index
        else:
            deck_index = team_num - 1

        deck = self.decks[deck_index]
        d = []
        for x in deck['t_character_ids']:
            if deck['t_character_ids'][x] != 0:
                d.append(deck['t_character_ids'][x])
        return d

    def get_character_by_id(self, _id: int):
        for i in self.characters:
            if i['id'] == _id:
                return i
        return None

    def get_character_by_m_character_id(self, m_character_id: int):
        character = next((x for x in self.characters if x['m_character_id'] == m_character_id), None)
        return character

    def get_character_collection_by_id(self, _id: int):
        for i in self.character_collections:
            if i['id'] == _id:
                return i
        return None

    def get_character_collection_by_mid(self, _id: int):
        for i in self.character_collections:
            if i['m_character_id'] == _id:
                return i
        return None

    # Returns a list of player items with matching m_item_id
    def get_item_by_m_item_id(self, m_item_id):
        item = next((x for x in self.items if x['m_item_id'] == m_item_id), None)
        return item

    def get_item_by_id(self, iid):
        for i in self.items:
            if i['id'] == iid:
                return i
        return None

    def update_items(self, result):
        if 't_items' in result:
            for item in result['t_items']:
                if 'id' in item:
                    index = self.items.index(self.get_item_by_id(item['id']))
                    self.items[index] = item

    def get_weapon_by_id(self, eid):
        for w in self.weapons:
            if w['id'] == eid:
                return w
        return None

    def get_equipment_by_id(self, eid):
        for w in self.equipment:
            if w['id'] == eid:
                return w
        return None

    def get_innocent_by_id(self, iid):
        for inno in self.innocents:
            if inno['id'] == iid:
                return inno
        return None

    def update_equip(self, result):
        if 't_weapon' in result:
            index = self.weapons.index(self.get_weapon_by_id(result['t_weapon']['id']))
            self.weapons[index] = result['t_weapon']
        elif 't_equipment' in result:
            index = self.equipment.index(self.get_equipment_by_id(result['t_equipment']['id']))
            self.equipment[index] = result['t_equipment']
        else:
            Logger.warn("unable to update item from result")

    def update_innocent(self, inno):
        old_inno = self.get_innocent_by_id(inno['id'])
        index = self.innocents.index(old_inno)
        self.innocents[index] = inno

    def update_character(self, char):
        old_char = self.get_character_by_id(char['id'])
        index = self.characters.index(old_char)
        self.characters[index] = char

    # e can be an equipment id or actual equipment/weapon
    def get_item_innocents(self, e):
        if isinstance(e, int):
            place_id = e
        elif 'm_weapon_id' in e:
            place_id = e['id']
        elif 'm_equipment_id' in e:
            place_id = e['id']
        elif 'id' in e:
            place_id = e['id']
        else:
            raise Exception('unable to determine item id')

        equipment_innocents = []
        for i in self.innocents:
            if i['place_id'] == place_id:
                equipment_innocents.append(i)
        return equipment_innocents

    # Will check item against provided settings and return True if it meets the criteria
    def check_item(self, item: dict,
                   max_rarity: int = 99, min_rarity: int = 0,
                   max_item_rank: int = 39, min_item_rank: int = 0,
                   max_item_level: int = 9999, min_item_level: int = 0,
                   skip_max_lvl: bool = False, only_max_lvl: bool = False,
                   skip_equipped: bool = False, skip_locked: bool = True,
                   max_innocent_rank: int = 8, max_innocent_type: int = 8,
                   min_innocent_rank: int = 0, min_innocent_type: int = 0,
                   min_innocent_count: int = 0, max_innocent_count: int = 999,
                   item_type: int = 0, skip_locked_innocent: bool= False) -> bool:

        # Change this to DEBUG (10) or INFO (20) if you want to see logs
        log_level = 0

        if log_level > 0:
            self.__log_item("checking", item)

        equip_type = self.get_equip_type(item)
        rank = self.gd.get_item_rank(item)

        if item_type is not None and 0 < item_type != equip_type:
            Logger.log('skip due to item_type', log_level)
            return False
        if skip_max_lvl and item['lv'] == item['lv_max']:
            Logger.log('skip due to lv_max', log_level)
            return False
        if skip_locked and item['lock_flg']:
            Logger.log('skip due to lock_flg', log_level)
            return False
        if item['lv'] > max_item_level:
            Logger.log('skip due to max_item_level', log_level)
            return False
        if item['lv'] < min_item_level:
            Logger.log('skip due to min_item_level', log_level)
            return False
        if rank > max_item_rank:
            Logger.log('skip due to max_item_rank', log_level)
            return False
        if rank < min_item_rank:
            Logger.log('skip due to min_item_rank', log_level)
            return False
        if item['rarity_value'] > max_rarity:
            Logger.log('skip due to max_rarity', log_level)
            return False
        if item['rarity_value'] < min_rarity:
            Logger.log('skip due to min_rarity', log_level)
            return False
        if skip_equipped and item['set_chara_id'] != 0:
            Logger.log('skip due to equipped to char', log_level)
            return False

        innos = self.get_item_innocents(item)
        if len(innos) > max_innocent_count:
            Logger.log('skip due to max innocent count', log_level)
            return False

        if len(innos) < min_innocent_count:
            Logger.log('skip due to min innocent count', log_level)
            return False

        if min_innocent_rank > 0 or min_innocent_type > 0:
            if len(innos) == 0:
                Logger.log('skip due to missing innocent', log_level)
                return False

        for i in innos:
            if skip_locked_innocent and i['lock_flg']:
                Logger.log('skip due to locked innocent', log_level)
                return False
            if i and i['effect_rank'] > max_innocent_rank:
                Logger.log('skip due to max_innocent_rank', log_level)
                return False
            if i['m_innocent_id'] > max_innocent_type:
                Logger.log('skip due to max_innocent_type', log_level)
                return False

            if i and i['effect_rank'] < min_innocent_rank:
                Logger.log('skip due to min_innocent_rank', log_level)
                return False
            if i['m_innocent_id'] < min_innocent_type:
                Logger.log('skip due to min_innocent_type', log_level)
                return False

        if only_max_lvl and item['lv'] < item['lv_max']:
            Logger.log('skip due to only_max_lvl', log_level)
            return False

        Logger.log('item passed check', log_level)
        return True

    def filter_items(self, max_rarity: int = 999, min_rarity: int = 0,
                     max_item_rank: int = 999, min_item_rank: int = 0,
                     max_item_level: int = 9999, min_item_level: int = 0,
                     skip_max_lvl: bool = False, only_max_lvl: bool = False,
                     skip_equipped: bool = False, skip_locked: bool = False,
                     max_innocent_rank: int = 8, max_innocent_type: int = 8,
                     min_innocent_rank: int = 0, min_innocent_type: int = 0,
                     min_innocent_count: int = 0, max_innocent_count: int = 999,
                     item_type=0, skip_locked_innocent : bool = False):
        matches = []
        skipping = 0
        for w in (self.weapons + self.equipment):
            result = self.check_item(item=w, max_rarity=max_rarity, max_item_rank=max_item_rank,
                                     min_rarity=min_rarity, min_item_rank=min_item_rank,
                                     max_item_level=max_item_level, min_item_level=min_item_level,
                                     skip_max_lvl=skip_max_lvl, only_max_lvl=only_max_lvl,
                                     skip_equipped=skip_equipped, skip_locked=skip_locked,
                                     max_innocent_rank=max_innocent_rank, max_innocent_type=max_innocent_type,
                                     min_innocent_rank=min_innocent_rank, min_innocent_type=min_innocent_type,
                                     min_innocent_count=min_innocent_count, max_innocent_count=max_innocent_count,
                                     item_type=item_type, skip_locked_innocent = skip_locked_innocent)
            if not result:
                skipping += 1
                continue
            matches.append(w)
        return matches, skipping

    def get_equip_type(self, item):
        return EquipmentType.WEAPON if 'm_weapon_id' in item else EquipmentType.ARMOR

    def innocent_get_all_of_type(self, m_innocent_id, only_unequipped):
        innocents_of_type = [x for x in self.innocents if x['m_innocent_id'] == m_innocent_id]
        if only_unequipped:
            innocents_of_type = [x for x in innocents_of_type if x['place_id'] == 0 and x['place'] == 0]
        return innocents_of_type

    def __log_item(self, msg, w):
        item = self.gd.get_weapon(w['m_weapon_id']) if 'm_weapon_id' in w else self.gd.get_weapon(w['m_equipment_id'])
        Logger.info(
            '%s: "%s" rarity: %s rank: %s lv: %s lv_max: %s locked: %s' %
            (msg, item['name'], w['rarity_value'], self.gd.get_item_rank(w), w['lv'],
             w['lv_max'], w['lock_flg'])
        )

    def get_item_alchemy_effects(self, i):

        if isinstance(i, int):
            id = i
            i = self.get_weapon_by_id(id)
            if i is None:
                i = self.get_equipment_by_id(id)
        effects = []
        if 'm_weapon_id' in i:
            effects = self.get_weapon_alchemy_effects(i['id'])
        elif 'm_equipment_id' in i:
            effects = self.get_equipment_alchemy_effects(i['id'])

        for effect in effects:
            effect_data = self.gd.get_alchemy_effect(effect['m_equipment_effect_type_id'])
            is_max_value = effect['effect_value'] == effect_data['effect_value_max']

            Logger.info('%s - Effect: "%s" - Value: %s - IsMaxValue: %s - Locked: %s' % (
                i['id'],
                effect_data['description'].format(effect['effect_value']),
                effect['effect_value'],
                is_max_value,
                effect['lock_flg']
            ))

        return effects

    def get_weapon_alchemy_effects(self, i):

        if isinstance(i, int):
            item_id = i
        else:
            item_id = i['id']

        all_effects = self.weapon_effects
        weapon_effects = [x for x in all_effects if x['t_weapon_id'] == item_id]
        return weapon_effects

    def get_equipment_alchemy_effects(self, i):

        if isinstance(i, int):
            item_id = i
        else:
            item_id = i['id']

        all_effects = self.equipment_effects
        equipment_effects = [x for x in all_effects if x['t_equipment_id'] == item_id]
        return equipment_effects

    def update_from_resp(self, resp):
        if 'result' in resp:
            if 'after_t_data' in resp['result']:
                if 'innocents' in resp['result']['after_t_data']:
                    for i in resp['result']['after_t_data']['innocents']:
                        self.update_innocent(i)
                if 'items' in resp['result']['after_t_data']:
                    for i in resp['result']['after_t_data']['items']:
                        self.update_items(i)
                if 'characters' in resp['result']['after_t_data']:
                    for character in resp['result']['after_t_data']['characters']:
                        self.characters.append(character)
            if 'after_t_characters' in resp['result']:
                for char in resp['result']['after_t_characters']:
                    self.update_character(char)
            if 'after_t_character' in resp['result']:
                 self.update_character(resp['result']['after_t_character'])
            if 'consume_t_innocent_ids' in resp['result']:
                for i in resp['result']['consume_t_innocent_ids']:
                    self.innocents.remove(self.get_innocent_by_id(i))
            # craft innocent using recipe
            if 't_innocent' in resp['result']:
                self.innocents.append(resp['result']['t_innocent'])

    # Fetch effects on weapon based on id
    def get_weapon_effects(self, wid: int):
        effects = []
        for effect in self.weapon_effects:
            if effect['t_weapon_id'] == wid:
                effects.append(effect)
        return effects

    # Fetch effects on equipment based on id
    def get_equipment_effects(self, eid: int):
        effects = []
        for effect in self.equipment_effects:
            if effect['t_equipment_id'] == eid:
                effects.append(effect)
        return effects

    def is_item_in_equipment_preset(self, item_id):
        for preset in self.equipment_presets:
            if self.is_item_in_equipment_gearset(item_id, preset['position1']):
                return True
            if self.is_item_in_equipment_gearset(item_id, preset['position2']):
                return True
            if self.is_item_in_equipment_gearset(item_id, preset['position3']):
                return True
            if self.is_item_in_equipment_gearset(item_id, preset['position4']):
                return True
        return False

    def is_item_in_equipment_gearset(self, item_id, gear_set):
        return gear_set['t_weapon_id'] == item_id or gear_set['t_equipment_id1'] == item_id or gear_set['t_equipment_id2'] == item_id or gear_set['t_equipment_id3'] == item_id

