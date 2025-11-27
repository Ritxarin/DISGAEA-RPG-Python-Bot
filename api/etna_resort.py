from abc import ABCMeta
from inspect import ismemberdescriptor
import random

from api.constants import Constants, Innocent_Training_Result, Innocent_ID, Alchemy_Effect_Type, ErrorMessages, JP_ErrorMessages
from api.constants import Items as ItemsC
from api.items import Items


class EtnaResort(Items, metaclass=ABCMeta):

    def __init__(self):
        super().__init__()

    # Donate equipments
    def kingdom_weapon_equipment_entry(self, weapon_ids=[], equipment_ids=[]):
        data = self.client.kingdom_weapon_equipment_entry(weapon_ids, equipment_ids)
        if len(weapon_ids) > 0:
            self.player_weapons(True)
        if len(equipment_ids) > 0:
            self.player_equipment(True)
        return data

    # Donate innocents
    def kingdom_innocent_entry(self, innocent_ids=[]):
        res = self.client.kingdom_innocent_entry(innocent_ids)
        #self.player_innocents(True)
        return res

    def etna_resort_is_item_in_depository(self, item_id:int):
        depository_data = self.client.breeding_center_list()
        item_ids = []
        items_in_depository = depository_data['result']['t_weapons'] + depository_data['result']['t_equipments']
        for item in items_in_depository:
            item_ids.append(item['id'])
        return item_id in item_ids

    def etna_resort_get_all_daily_rewards(self):
        return self.client.trophy_get_reward_daily_request()

    # Looks for maxed items retrieves or donates them and fills it again
    def etna_resort_check_deposit_status(self, max_innocent_rank=5, max_item_rank_to_donate=40,
                                         max_item_rarity_to_donate=40, min_item_rank_to_deposit=40):
        self.log("Checking state of item depository...")

        self.etna_resort_retrieve_or_donate_items_from_depository(max_innocent_rank, max_item_rank_to_donate,
                                                                  max_item_rarity_to_donate)

        depository_data = self.client.breeding_center_list()
        items_in_depository = depository_data['result']['t_weapons'] + depository_data['result']['t_equipments']
        deposit_free_slots = Constants.Etna_Resort_Item_Deposit_Size - len(items_in_depository)
        if deposit_free_slots > 0:
            self.log(f"Finished retrieving equipment - {deposit_free_slots} slots available in repository")
            self.etna_resort_fill_depository(deposit_free_slots, max_innocent_rank, min_item_rank_to_deposit)

        self.log(f"Finished checking depository.")

        # Checks if any item is fully leveled

    # If item is locked, has rare innocents or is above specified rarity (default rare), it will be retrieved
    # Otherwise it will be donated
    # If there is no invetory space to retrieve, sell 20 items and retry
    def etna_resort_retrieve_or_donate_items_from_depository(self, max_innocent_rank=5, max_item_rank_to_donate=40,
                                                             max_item_rarity_to_donate=40):
        retry = True

        # execute once - repeat if there was an exception retrieving equipment
        while retry:
            retry = False

            depository_data = self.client.breeding_center_list()
            items_in_depository = depository_data['result']['t_weapons'] + depository_data['result']['t_equipments']
            weapons_to_retrieve = []
            equipments_to_retrieve = []
            weapons_to_donate = []
            equipments_to_donate = []
            weapons_to_retrieve_innocent_and_donate =[]
            equipments_to_retrieve_innocent_and_donate =[]
            finished_item_count = 0

            for i in items_in_depository:
                item_rank = self.gd.get_item_rank(i)
                isWeapon = 'm_weapon_id' in i
                if i['lv'] == i['lv_max']:
                    finished_item_count += 1
                    innos_to_keep = [x for x in self.pd.get_item_innocents(i['id']) if
                                     x['effect_rank'] >= max_innocent_rank]
                    # Keep if rare innocent, item is locked or is above rarity
                    if (len(innos_to_keep) > 0 or i['lock_flg'] or i[
                        'rarity_value'] > max_item_rarity_to_donate or item_rank > max_item_rank_to_donate):
                        # TODO check if slots available for retrieving?
                        if isWeapon:
                            weapons_to_retrieve.append(i['id'])
                        else:
                            equipments_to_retrieve.append(i['id'])
                    # Otherwise item can be donated
                    else:                    
                        ## If item has rare innocents, retrieve them first, then donate 
                        if len(innos_to_keep) > 0:
                            if(isWeapon):
                                weapons_to_retrieve_innocent_and_donate.append(i['id'])
                                weapons_to_retrieve.append(i['id'])
                            else:
                                equipments_to_retrieve_innocent_and_donate.append(i['id'])
                                equipments_to_retrieve.append(i['id'])
                        ## Otherwise donate diretly
                        else:
                            if(isWeapon):
                                weapons_to_donate.append(i['id'])
                            else:
                                equipments_to_donate.append(i['id'])

            total_to_donate = len(weapons_to_donate) + len(equipments_to_donate)
            total_to_retrieve = len(weapons_to_retrieve) + len(equipments_to_retrieve)
            total_to_retieve_innocent_and_donate = len(weapons_to_retrieve_innocent_and_donate) + len(equipments_to_retrieve_innocent_and_donate) 
            if finished_item_count > 0:
                self.log(
                    f"Finished leveling {finished_item_count} equipments - {total_to_retrieve} will be retrieved, {total_to_donate} will be donated")

            if total_to_retrieve > 0:
                result = self.client.breeding_center_pick_up(weapons_to_retrieve, equipments_to_retrieve)

                ## No storage space left. Sell some items first and retry
                if result['error'] == ErrorMessages.Armor_Full_Error or result['error'] == ErrorMessages.Weapon_Full_Error or result['error'] == JP_ErrorMessages.Armor_Full_Error or result['error'] == JP_ErrorMessages.Weapon_Full_Error:
                    sell_equipments = result['error'] == ErrorMessages.Armor_Full_Error or result['error'] == JP_ErrorMessages.Armor_Full_Error
                    sell_weapons = result['error'] == ErrorMessages.Weapon_Full_Error  or result['error'] == JP_ErrorMessages.Weapon_Full_Error
                    self.shop_free_inventory_space(sell_weapons, sell_equipments, 20)
                    retry = True

                ## Once we've retrieved the items, remove innocents and donate
                if total_to_retieve_innocent_and_donate > 0:
                    for weapon in weapons_to_retrieve_innocent_and_donate:
                        self.remove_innocents(weapon)
                    for equipment in equipments_to_retrieve_innocent_and_donate:
                        self.remove_innocents(equipment)
                    result = self.kingdom_weapon_equipment_entry(weapons_to_retrieve_innocent_and_donate, equipments_to_retrieve_innocent_and_donate)
            
            if total_to_donate > 0:
                self.kingdom_weapon_equipment_entry(weapons_to_donate, equipments_to_donate)

    # Will first try to fill the depository with items with rare innocents (any rank)
    # Rest of spots will be filled with any item of specified rank (r40 by default)
    def etna_resort_fill_depository(self, deposit_free_slots=0, max_innocent_rank=5, min_item_rank_to_deposit=40):
        if deposit_free_slots == 0:
            depository_data = self.client.breeding_center_list()
            items_in_depository = depository_data['result']['t_weapons'] + depository_data['result']['t_equipments']
            deposit_free_slots = Constants.Etna_Resort_Item_Deposit_Size - len(items_in_depository)

        if deposit_free_slots > 0:
            self.log(f"Filling depository with {deposit_free_slots} items...")
            # Fill depository with items that have rare innocents first, regrdless of item rank
            self.etna_resort_find_items_for_depository(deposit_free_slots, max_innocent_rank,
                                                       min_item_rank_to_deposit=0)

            # if slots available, fill with any item of specified rank
            depository_data = self.client.breeding_center_list()
            items_in_depository = depository_data['result']['t_weapons'] + depository_data['result']['t_equipments']
            deposit_free_slots = Constants.Etna_Resort_Item_Deposit_Size - len(items_in_depository)
            if deposit_free_slots > 0:
                self.etna_resort_find_items_for_depository(deposit_free_slots, 0, min_item_rank_to_deposit)

    # Look for items with specified criteria
    def etna_resort_find_items_for_depository(self, deposit_free_slots=0, max_innocent_rank=5,
                                              min_item_rank_to_deposit=40):
        if deposit_free_slots == 0:
            depository_data = self.client.breeding_center_list()
            items_in_depository = depository_data['result']['t_weapons'] + depository_data['result']['t_equipments']
            deposit_free_slots = Constants.Etna_Resort_Item_Deposit_Size - len(items_in_depository)

        if deposit_free_slots > 0:
            self.player_weapons(True)
            self.player_equipment(True)
            weapons_to_deposit = []
            weapons_lvl1 = [x for x in self.pd.weapons if x['lv'] < x['lv_max'] and x['set_chara_id'] == 0]
            equips_lvl1 = [x for x in self.pd.equipment if x['lv'] < x['lv_max'] and x['set_chara_id'] == 0]

            equipments_to_deposit = self.generate_array_for_deposit(equips_lvl1, deposit_free_slots, max_innocent_rank,
                                                                    min_item_rank_to_deposit)
            if len(equipments_to_deposit) > 0:
                self.client.breeding_center_entrust([], equipments_to_deposit)

            # If deposit cannot be filled with only equipment, find weapons to finish filling
            if len(equipments_to_deposit) < deposit_free_slots:
                deposit_free_slots = deposit_free_slots - len(equipments_to_deposit)
                weapons_to_deposit = self.generate_array_for_deposit(weapons_lvl1, deposit_free_slots,
                                                                     max_innocent_rank, min_item_rank_to_deposit)

                if len(weapons_to_deposit) > 0:
                    self.client.breeding_center_entrust(weapons_to_deposit, [])

    def generate_array_for_deposit(self, all_items, deposit_free_slots, max_innocent_rank, min_item_rank_to_deposit=40,
                                   max_rarity_to_deposit=40):
        deposit_count = 0
        items_to_deposit = []
        filled = False
        innocent_count = 0

        while not filled and innocent_count < 2:
            # Looking for rare, iterate only once
            if max_innocent_rank > 0:
                filled = True

            for item in all_items:
                if self.pd.is_item_in_equipment_preset(item['id']):
                    continue
                if self.pd.is_item_in_arena_defense(item['id']):
                    continue
                if item['id'] in items_to_deposit:
                    continue
                # If looking for rare innocents
                item_innocents = self.pd.get_item_innocents(item['id'])
                if max_innocent_rank > 0:
                    rare_innocents = [x for x in item_innocents if x['effect_rank'] >= max_innocent_rank]
                    if len(rare_innocents) > 0:
                        items_to_deposit.append(item['id'])
                        deposit_count += 1
                        if deposit_count == deposit_free_slots:
                            break

                # Otherwise fill with commons of specific rank
                # fill with items with no innocents first, 
                # if there aren't enough iterate all items once again and find items with 1 inno
                else:
                    item_rank = self.gd.get_item_rank(item)
                    if item['rarity_value'] > max_rarity_to_deposit or item_rank < min_item_rank_to_deposit:
                        continue
                    if len(item_innocents) > innocent_count: continue
                    items_to_deposit.append(item['id'])
                    deposit_count += 1
                    if deposit_count == deposit_free_slots:
                        filled = True
                        break
            innocent_count += 1
        return items_to_deposit

    def etna_donate_innocents(self, max_innocent_rank=8, innocent_types: list = None, max_innocent_type=None,
                              min_innocent_type=None, blacklist=[]):
        self.player_innocents()
        innos = []
        skipping = 0
        for i in self.pd.innocents:
            if i['id'] in blacklist:
                skipping += 1
                continue
            if not self._filter_innocent(i, max_innocent_rank,
                                         innocent_types=innocent_types,
                                         max_innocent_type=max_innocent_type,
                                         min_innocent_type=min_innocent_type,
                                         ):
                skipping += 1
                continue
            innos.append(i['id'])

        self.log('donating %s, skipping %s innocents' % (len(innos), skipping))
        if len(innos) > 0:
            for batch in (innos[i:i + 20] for i in range(0, len(innos), 20)):
                res = self.kingdom_innocent_entry(innocent_ids=batch)
                if 'error' not in res:
                    for i in batch:
                        self.pd.innocents.remove(self.get_innocent_by_id(i))

    def etna_resort_donate_items(self, max_innocent_rank: int = 10, max_innocent_type: int = Innocent_ID.HL,
                                 max_item_rank: int = 100, max_item_rarity: int = 40, remove_innocents: bool = False):
        self.log("Looking for items to donate...")
        self.player_equipment(True)
        self.player_weapons(True)
        self.player_innocents(True)

        # if we are removing innocents then it doesn't matter about the innocent filter
        if remove_innocents:
            max_innocent_rank = 10
            max_innocent_type = Innocent_ID.HL

        weapons_to_donate = []
        equipments_to_donate = []

        ec = 0
        wc = 0
        items, skipping = self.pd.filter_items(
            only_max_lvl=True, skip_locked=True,
            max_innocent_rank=max_innocent_rank,
            max_innocent_type=max_innocent_type,
            max_item_rank=max_item_rank,
            max_rarity=max_item_rarity,
            skip_locked_innocent=True
        )

        if len(items) > 0:
            for item in items:
                if self.pd.is_item_in_equipment_preset(item['id']):
                    continue
                if self.pd.is_item_in_arena_defense(item['id']):
                    continue
                equip_type = self.pd.get_equip_type(item)
                if remove_innocents:
                    self.remove_innocents(item)

                if equip_type == 2:
                    ec += 1
                    equipments_to_donate.append(item['id'])
                else:
                    wc += 1
                    weapons_to_donate.append(item['id'])
                self.log_donate(item)

        self.log(f"Will donate {wc} weapons and {ec} equipments")
        self.log('donate - skipping %s items' % skipping)

        for batch in (equipments_to_donate[i:i + 20] for i in range(0, len(equipments_to_donate), 20)):
            self.kingdom_weapon_equipment_entry(equipment_ids=batch)
        for batch in (weapons_to_donate[i:i + 20] for i in range(0, len(weapons_to_donate), 20)):
            self.kingdom_weapon_equipment_entry(weapon_ids=batch)

        self.log("Finished donating equipment")

    def etna_resort_refine_item(self, item_id):
        e = self.pd.get_weapon_by_id(item_id)
        if e is not None:
            item_type = 3
        else:
            item_type = 4
            e = self.pd.get_equipment_by_id(item_id)

        if e['rarity_value'] == 100:
            self.logger.warn("Item already has rarity 100...")
            return e['rarity_value']

        if e['lv'] != e['lv_max']:
            self.logger.warn("Item is not at max level...")
            return e['rarity_value']

        retry = True
        self.log("Attempting to refine item...")
        attempt_count = 0
        initial_rarity = e['rarity_value']
        while retry:
            attempt_count += 1
            res = self.client.etna_resort_refine(item_type, item_id)
            if 'result' in res and 'success_type' in res['result']:              
                if item_type == 3:
                    final_rarity = res['result']['t_weapon']['rarity_value']
                else:
                    final_rarity = res['result']['t_equipment']['rarity_value']
                if final_rarity != initial_rarity:
                    retry = False

        self.log(
            f"Refined item. Attempts used {attempt_count}. Rarity increase: {final_rarity-initial_rarity}. Current rarity {final_rarity}")
        e['rarity_value'] = final_rarity
        return final_rarity

    def etna_resort_remake_item(self, item_id):
        e = self.pd.get_weapon_by_id(item_id)
        if e is not None:
            item_type = 3
        else:
            item_type = 4
            e = self.pd.get_equipment_by_id(item_id)

        item_rank = self.gd.get_item_rank(e)
        if item_rank != 40:
            print("Can only remake r40 items")
            return
        if e['lv'] != e['lv_max']:
            print("Item is not at max level...")
            return
        if e['rarity_value'] < 70:
            print("Item is not legendary")
            return
        if e['remake_count'] == 10:
            print("Item at max rank already")
            return

        res = self.client.etna_resort_remake(item_type, item_id)
        if item_type == 3:
            remake_count = res['result']['after_t_data']['weapons'][0]['remake_count']
        else:
            remake_count = res['result']['after_t_data']['equipments'][0]['remake_count']
        self.log(f"\tItem rank increased. Rank upgrade count: {remake_count}")

    def innocent_get_training_result(self, training_result):
        if training_result == Innocent_Training_Result.NORMAL:
            return "Normal"
        if training_result == Innocent_Training_Result.NOT_BAD:
            return "Not bad"
        if training_result == Innocent_Training_Result.DREAMLIKE:
            return "Dreamlike"

    def log_donate(self, w):
        item = self.gd.get_weapon(w['m_weapon_id']) if 'm_weapon_id' in w else self.gd.get_equipment(
            w['m_equipment_id'])
        self.logger.debug(
            '[-] donate item: "%s" rarity: %s rank: %s lv: %s lv_max: %s locked: %s' %
            (item['name'], w['rarity_value'], self.gd.get_item_rank(w), w['lv'],
             w['lv_max'], w['lock_flg'])
        )

    def _filter_innocent(self, i, max_innocent_rank: int,
                         max_innocent_type: int = None, min_innocent_type: int = None,
                         innocent_types: set[int] = None):

        if i['place_id'] > 0:
            return False
        if i['effect_rank'] > max_innocent_rank:
            return False
        if innocent_types is not None:
            if i['m_innocent_id'] not in innocent_types:
                return False
        else:
            if max_innocent_type is not None and i['m_innocent_id'] > max_innocent_type:
                return False
            if min_innocent_type is not None and i['m_innocent_id'] < min_innocent_type:
                return False
        return True

    # verify that there are no locked effects so item can be rolled
    def etna_resort_can_item_be_rolled(self, item_id):
        effects = self.pd.get_item_alchemy_effects(item_id)
        locked_effects = [x for x in effects if x['lock_flg']]
        return len(locked_effects) == 0

    # verify that the effect is not locked so it can be rerolled
    def etna_resort_can_effect_be_rerolled(self, item_id: int, place_no: int):
        effects = self.pd.get_item_alchemy_effects(item_id)
        effect = next((x for x in effects if x['place_no'] == place_no), None)
        return effect is not None and not effect['lock_flg']

    # check that the effect is not already rolled with a higher value on that slot
    def etna_resort_is_effect_already_rolled(self, item_id: int, place_no: int, effect_id: int, effect_target: int):
        effects = self.pd.get_item_alchemy_effects(item_id)
        effect = next((x for x in effects if x['place_no'] == place_no), None)
        return effect['m_equipment_effect_type_id'] == effect_id and effect['effect_value'] >= effect_target

    def etna_resort_can_effect_be_rolled_in_equipment(self, alchemy_effect_id: int, equipment_type: int):
        if equipment_type == 3:
            return alchemy_effect_id in Constants.Weapon_Alchemy_Effects
        return alchemy_effect_id in Constants.Equipment_Alchemy_Effects

    # Will return innocents that match a recipe
    def find_recipe_innocents(self, override_min_rank=False, recipe_ids=None):
        innocents = []
        for recipe in self.gd.innocent_recipes:
            if recipe_ids is not None and recipe['id'] not in recipe_ids:
                continue
            materials = recipe['materials']
            for mat in materials:
                for i in self.find_recipe_material_innocents(mat, override_min_rank):
                    innocents.append(i)
        return innocents

    # find innocents that match a specific recipe material. May or may not check the innocent rank
    def find_recipe_material_innocents(self, material, override_min_rank=False, skip_equipped=False):
        innocents = []
        m_character_id = material['m_character_id']
        m_innocent_id = material['m_innocent_id']
        min_r, max_r = self.gd.get_innocent_rank_min_max(material['rank'])
        if override_min_rank:
            min_r = 0
        for i in self.player_innocents():
            if min_r <= i['effect_rank'] <= max_r and i['m_character_id'] == m_character_id and \
                    i['m_innocent_id'] == m_innocent_id:
                if skip_equipped and i['place_id'] > 0:
                    continue
                innocents.append(i)
        return innocents

    def etna_resort_graze(self, innocent: int | dict, target_character_id: int):
        if type(innocent) == dict and 'id' in innocent:
            iid = int(innocent['id'])
        else:
            iid = int(innocent)

        ticket_item_def = self.gd.get_ranch_ticket(target_character_id)
        ticket_item = self.pd.get_item_by_m_item_id(ticket_item_def['id'])
        if ticket_item['num'] <= 0:
            self.logger.error("Not enough tickets - %s" % ticket_item_def['name'])
            return

        self.log('using ticket: "%s" on %s' % (ticket_item_def['name'], iid))
        resp = self.client.innocent_grazing(iid, ticket_item_def['id'])
        self.check_resp(resp)
        return resp

    def etna_resort_complete_recipe(self, recipe_id: int, innocent_ids: list[int]):

        recipe = self.gd.get_innocent_recipe(recipe_id)
        self.log('completing recipe "%s" with innocents: %s' % (recipe['name'], innocent_ids))

        resp = self.client.innocent_combine(recipe_id, innocent_ids)
        self.check_resp(resp)
        return resp

    # This function re-rolls an item until a certain % boost is reached for a specific effect, ignoring all other rolls
    # Specify and item ID, and effect and a target for the effect. The script will keep re-rolling until the target is reached
    # unique_innocent will force the effect to contain a unique innocent
    # If user runs out of HL or priprism the script will stop execution
    # Use a.print_team_info(team_num) to get the ID of the item
    def etna_resort_roll_alchemy_effect(self, item_id: int, effect_target: int = 40,
                                        effect_id: int = Alchemy_Effect_Type.Innocent_Effect,
                                        unique_innocent: bool = False,
                                        all_effects_unlocked: bool = False):

        effect = self.gd.get_alchemy_effect(effect_id)
        if effect is None or effect_target > effect['effect_value_max']:
            self.log(
                f"The specified value is higher than the maximun possible roll ({effect['effect_value_max']}). Exiting...")
            return

        if not self.etna_resort_can_item_be_rolled(item_id):
            self.log(f"{item_id} - Item has effects(s) locked and cannot be rolled. Exiting...")
            return

        e = self.pd.get_weapon_by_id(item_id)
        if e is not None:
            item_type = 3
            t_data_key = 'weapon_effects'
        else:
            item_type = 4
            t_data_key = 'equipment_effects'

        if not self.etna_resort_can_effect_be_rolled_in_equipment(effect_id, item_type):
            self.log(f"The specified alchemy effect cannot be rolled for this equipment type. Exiting...")
            return
        
        item_effects = self.pd.get_item_alchemy_effects(item_id)
        item_effect = next((x for x in item_effects if x['m_equipment_effect_type_id'] == effect_id), None)
        if item_effect is not None and item_effect['effect_value'] >= effect_target:
            self.log(f"{effect['description']} is already rolled on slot {item_effect['place_no']} with a better or equal value.")
            return

        effect_value = 0
        attempt_count = 0

        prism_count = self.pd.get_item_by_m_item_id(ItemsC.PriPrism.value)['num']
        current_hl = self.pd.get_item_by_m_item_id(ItemsC.HL.value)['num']
        self.log(f"{item_id} - Rolling item - Priprism count: {prism_count} - Current HL: {current_hl}")

        while effect_value < effect_target and prism_count > 0 and current_hl > Constants.Alchemy_Alchemize_Cost:
            res = self.client.etna_resort_add_alchemy_effects(item_type, item_id)
            self.check_resp(res)
            effects = res['result']['after_t_data'][t_data_key]

            attempt_count += 1
            prism_count -= 1
            if prism_count == 0:
                self.log(f"{item_id} - Ran out of priprism. Exiting...")
            current_hl -= Constants.Alchemy_Alchemize_Cost
            if current_hl < Constants.Alchemy_Alchemize_Cost:
                self.log(f"{item_id} - Ran out of HL. Exiting...")

            effect = next((x for x in effects if x['m_equipment_effect_type_id'] == effect_id), None)

            if effect is None:
                continue

            effect_value = effect['effect_value']

            # If looking for unique innocent ignore value unless the effect contains a unique inno
            if unique_innocent and Constants.Unique_Innocent_Character_ID not in effect['m_character_ids']:
                effect_value = 0

            # if looking to have all effects unlocked, skip if less than 4 effects
            if all_effects_unlocked and len(effects) < 4:
                effect_value = 0

        self.log(
            f"{item_id} - Rolled {effect_value}% effect - Attempt count: {attempt_count} - "
            f"Priprism left: {prism_count}"
        )

        if item_type == 3:
            self.player_weapon_effects(True)
        else:
            self.player_equipment_effects(True)

    # This function re-rolls an item until a certain effect is rolled with max value
    # Specify and item ID, and a list of effects to roll for on the alchemy_effects list
    # Optional: all effects unlocked, unique innocent
    def etna_resort_roll_until_maxed_effect(self, item_id: int,
                                            alchemy_effects: set[int] = [],
                                            unique_innocent: bool = False,
                                            all_effects_unlocked: bool = True):

        if len(alchemy_effects) == 0:
            self.log(f"Please specify at least one effect to roll for. Exiting...")
            return

        if not self.etna_resort_can_item_be_rolled(item_id):
            self.log("{item_id} - Item has effects(s) locked and cannot be rolled. Exiting...")
            return

        e = self.pd.get_weapon_by_id(item_id)
        if e is not None:
            item_type = 3
            t_data_key = 'weapon_effects'
        else:
            item_type = 4
            t_data_key = 'equipment_effects'

        possible_effects = []
        for effect_id in alchemy_effects:
            if not self.etna_resort_can_effect_be_rolled_in_equipment(effect_id, item_type):
                effect = self.gd.get_alchemy_effect(effect_id)
                self.log(f"{effect['description']} cannot be rolled for this equipment type.")
            else:
                possible_effects.append(effect_id)

        if len(possible_effects) == 0:
            self.log(f"None of the specified effects can be rolled on this equipment. Exiting....")
            return

        attempt_count = 0

        prism_count = self.pd.get_item_by_m_item_id(ItemsC.PriPrism.value)['num']
        current_hl = self.pd.get_item_by_m_item_id(ItemsC.HL.value)['num']
        self.log(f"{item_id} - Rolling item - Priprism count: {prism_count} - Current HL: {current_hl}")

        roll = True

        while roll and prism_count > 0 and current_hl > Constants.Alchemy_Alchemize_Cost:
            res = self.client.etna_resort_add_alchemy_effects(item_type, item_id)
            effects = res['result']['after_t_data'][t_data_key]

            attempt_count += 1
            prism_count -= 1
            if prism_count == 0:
                self.log(f"{item_id} - Ran out of priprism.")
            current_hl -= Constants.Alchemy_Alchemize_Cost
            if current_hl < Constants.Alchemy_Alchemize_Cost:
                self.log(f"{item_id} - Ran out of HL")

            # if looking to have all effects unlocked, skip if less than 4 effects
            if all_effects_unlocked and len(effects) < 4:
                continue

            # Check if any of the sought after affects is maxed
            for e in effects:
                # look for effects specified in list
                if e['m_equipment_effect_type_id'] in possible_effects:
                    effect_data = self.gd.get_alchemy_effect(e['m_equipment_effect_type_id'])
                    is_max_effect = effect_data['effect_value_max'] == e['effect_value']
                    # if the effect is maxed
                    if is_max_effect:
                        # If looking for unique innocent ignore value unless the effect contains a unique inno
                        if unique_innocent and Constants.Unique_Innocent_Character_ID in e['m_character_ids']:
                            roll = False
                        if not unique_innocent:
                            roll = False

        self.log(f"{item_id} - Rolled - Attempt count: {attempt_count} - Priprism left: {prism_count}")

        if item_type == 3:
            self.player_weapons(True)
            self.player_weapon_effects(True)
        else:
            self.player_equipment(True)
            self.player_equipment_effects(True)
        self.pd.get_item_alchemy_effects(item_id)

    def etna_resort_reroll_effect(self, item_id: int,
                                  alchemy_effect_id: int,
                                  place_no: int,
                                  effect_target: int = 0,
                                  unique_innocent: bool = False):

        # verify value can be rolled
        if effect_target != 0:
            effect = self.gd.get_alchemy_effect(alchemy_effect_id)
            if effect is None or effect_target > effect['effect_value_max']:
                self.log(
                    f"The specified value is higher than the maximun possible roll ({effect['effect_value_max']}). Exiting...")
                return

        # verify slot is not locked
        if not self.etna_resort_can_effect_be_rerolled(item_id, place_no):
            self.log("The effect is locked and cannot be rerolled. Exiting...")
            return

        e = self.pd.get_weapon_by_id(item_id)
        if e is not None:
            item_type = 3
            t_data_key = 'weapon_effects'
        else:
            item_type = 4
            t_data_key = 'equipment_effects'

        # verify effect can be rerolled for that equipment
        if not self.etna_resort_can_effect_be_rolled_in_equipment(alchemy_effect_id, item_type):
            effect = self.gd.get_alchemy_effect(alchemy_effect_id)
            self.log(f"{effect['description']} cannot be rolled for this equipment type.")
            return

        # verify effect can be rolled in that slot
        if not self.etna_resort_can_effect_be_rolled_in_place(alchemy_effect_id, place_no):
            effect = self.gd.get_alchemy_effect(alchemy_effect_id)
            self.log(f"{effect['description']} cannot be rolled on slot {place_no}.")
            return

        # the same effect has already been rolled on that slot
        if self.etna_resort_is_effect_already_rolled(item_id=item_id, place_no=place_no, effect_id=alchemy_effect_id,
                                                     effect_target=effect_target):
            effect = self.gd.get_alchemy_effect(alchemy_effect_id)
            self.log(f"{effect['description']} is already rolled on slot {place_no} with a better or equal value.")
            return

        prilixir_count = self.pd.get_item_by_m_item_id(ItemsC.Prilixir.value)['num']
        current_hl = self.pd.get_item_by_m_item_id(ItemsC.HL.value)['num']
        self.log(f"{item_id} - Re-rolling item - Prilixir count: {prilixir_count} - Current HL: {current_hl}")

        roll = True
        attempt_count = 0

        while roll and prilixir_count > 0 and current_hl > Constants.Alchemy_Alchemize_Cost:
            res = self.client.etna_resort_reroll_alchemy_effect(item_type, item_id, place_no)

            effect = res['result']['after_t_data'][t_data_key][0]

            attempt_count += 1
            prilixir_count -= 1
            if prilixir_count == 0:
                self.log(f"{item_id} - Ran out of prilixir.")
            current_hl -= Constants.Alchemy_Realchemize_Cost
            if current_hl < Constants.Alchemy_Realchemize_Cost:
                self.log(f"{item_id} - Ran out of HL.")

            is_correct_effect = effect['m_equipment_effect_type_id'] == alchemy_effect_id
            is_max_effect = is_correct_effect and self.gd.get_alchemy_effect(alchemy_effect_id)['effect_value_max'] == effect['effect_value']

            # if effect is maxed finish rolling and overwrite
            # if effect target is manually specified
            if is_max_effect or (effect_target != 0 and effect['effect_value'] >= effect_target and is_correct_effect):
                # If looking for unique innocent ignore value unless the effect contains a unique inno
                if unique_innocent and Constants.Unique_Innocent_Character_ID not in effect['m_character_ids']:
                    r = self.client.etna_resort_update_alchemy_effect(False)
                else:
                    r = self.client.etna_resort_update_alchemy_effect(True)
                    roll = False
            else:
                r = self.client.etna_resort_update_alchemy_effect(False)

        self.log(
            f"{item_id} - Rolled {effect['effect_value']}%  - Attempt count: {attempt_count} - "
            f"Prilixir left: {prilixir_count}")

    def etna_resort_can_effect_be_rolled_in_place(self, alchemy_effect_id: int, place_no: int):
        if alchemy_effect_id in Constants.Place_1_Effects:
            return place_no == 1
        elif alchemy_effect_id in Constants.Place_2_Effects:
            return place_no == 2
        else:
            return place_no >= 3

    def get_caretaker_tickets(self, innocent_type_id):
        itype = self.gd.get_innocent_type(innocent_type_id)
        ticket_name = "%s Caretaker" % itype['name']
        for i in self.gd.items:
            if i['name'] == ticket_name:
                return self.pd.get_item_by_m_item_id(i['id'])
        return None

    # Will graze all innocents in an item so that they get the alchemy innocent boost
    # Item needs to have been alchemized
    def etna_resort_graze_item_innocents_for_innocent_boost(self, item_id):
        effects = self.pd.get_item_alchemy_effects(item_id)
        if len(effects) == 0:
            self.log(f"Please make sure alchemy is rolled on the item")
            return
        innocent_boost_effect = next(
            (x for x in effects if x['m_equipment_effect_type_id'] == Alchemy_Effect_Type.Innocent_Effect), None)
        if len(innocent_boost_effect['m_character_ids']) == 1 and innocent_boost_effect['m_character_ids'][0]:
            self.log(f"This item only has a unique innocent boost - Grazing is not possible")
            return
        # Get the type of the innocents that are boosted (skip unique)
        viable_boosted_innocents = [x for x in innocent_boost_effect['m_character_ids'] if x != 0]
        item_innocents = self.pd.get_item_innocents(item_id)

        for innocent in item_innocents:
            # If the innocent is not of the same type, graze
            if innocent['m_character_id'] not in viable_boosted_innocents and innocent['m_character_id'] != 0:
                # select one at random
                boost_innocent_type = random.choice(viable_boosted_innocents)
                self.etna_resort_graze(innocent=innocent['id'], target_character_id=boost_innocent_type)

    def etna_resort_max_train_innocent(self, innocent, min_initial_value:int=0):        
        
        starting_value = innocent['effect_values'][0]
        print(f"Training innocent. Starting value: {starting_value}")

        if starting_value  < min_initial_value:
            print(f"Starting value below minimum threshold. Skipping...")  
            return 

        inno_data = next((x for x in self.gd.innocent_types if x['id'] == innocent['m_innocent_id']),None)
        
        max_value = self.__get_innocent_max_effect(inno_data['effect_type'])
        if starting_value >= max_value:
             print(f"\tInnocent is already maxed")
             return
        
        attempts = 0   
        current_value = starting_value     
        while current_value < max_value:
            res = self.client.innocent_training(innocent['id'])
            if 'api_error' in res and 'message' in res['api_error'] and (res['api_error']['message'] == 'Insufficient Items' or res['api_error']['message'] == 'データが見つかりません'):
                print("No caretaker tickets left")
                break
            current_value = res['result']['after_t_data']['innocents'][0]['effect_values'][0]
            print(
                f"\tTrained innocent with result {self.innocent_get_training_result(res['result']['training_result'])} - Current value: {res['result']['after_t_data']['innocents'][0]['effect_values'][0]}")
            attempts += 1
        print(f"\tUpgraded innocent to Max Value. Total attempts: {attempts}")

    def __get_innocent_max_effect(self, effect_type:int):
       
       if effect_type >= 52  and effect_type <= 63:
        return 9
       
       type_max_values = {
            1: 6, # regular inno
            2: 2, # HL/EXP
            3: 1, # SPEED
            9 : 9, #Ancients
            48 : 0.1 # drop
       }

       return type_max_values[effect_type]