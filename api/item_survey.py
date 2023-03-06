import datetime
from abc import ABCMeta

from dateutil import parser

from api import Shop
from api.constants import Constants, EquipmentType, Innocent_ID, ErrorMessages, JP_ErrorMessages


class ItemSurvey(Shop, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def item_survey_complete_and_start_again(self, min_item_rank_to_deposit=40, auto_donate=True):
        time_delta = -4 if self.o.region == 2 else 9
        server_date_time = datetime.datetime.utcnow() + datetime.timedelta(hours=time_delta)
        weapons_finished = []
        equipments_finished = []
        iw_survey_data = self.client.item_world_survey_index()

        for item in iw_survey_data['result']['t_weapons']:
            item_survey_end_time = self.item_world_survey_get_item_return_time(item)
            if server_date_time > item_survey_end_time:
                weapons_finished.append(item['id'])

        for item in iw_survey_data['result']['t_equipments']:
            item_survey_end_time = self.item_world_survey_get_item_return_time(item)
            if server_date_time > item_survey_end_time:
                equipments_finished.append(item['id'])

        retry = True
        # execute once - repeat if there was an exception retrieving equipment
        while retry:
            retry = False
            if len(weapons_finished) > 0 or len(equipments_finished) > 0:
                self.log(f"\tRetrieving {len(weapons_finished)} weapons and {len(equipments_finished)} items")
                result = self.client.item_world_survey_end(weapons_finished, equipments_finished, False)
                if result['error'] == ErrorMessages.Armor_Full_Error or result['error'] == ErrorMessages.Weapon_Full_Error or result['error'] == JP_ErrorMessages.Armor_Full_Error or result['error'] == JP_ErrorMessages.Weapon_Full_Error:
                    sell_equipments = result['error'] == ErrorMessages.Armor_Full_Error or JP_ErrorMessages.Armor_Full_Error
                    sell_weapons = result['error'] == ErrorMessages.Weapon_Full_Error or JP_ErrorMessages.Weapon_Full_Error
                    self.shop_free_inventory_space(sell_weapons, sell_equipments, 10)
                    retry = True
        if auto_donate and (len(weapons_finished) > 0 or len (equipments_finished)> 0):
            self.client.kingdom_weapon_equipment_entry(weap_ids=weapons_finished, equip_ids=equipments_finished)

        iw_survey_data = self.client.item_world_survey_index()
        free_slots = Constants.Item_Survey_Deposit_Size - len(iw_survey_data['result']['t_weapons']) - len(
            iw_survey_data['result']['t_equipments'])
        if free_slots > 0:
            self.item_world_survey_fill(free_slots, min_item_rank_to_deposit)

    def item_world_survey_get_return_time(self):
        iw_survey_data = self.client.item_world_survey_index()
        # If available slots
        if (len(iw_survey_data['result']['t_equipments']) + len(
                iw_survey_data['result']['t_weapons']) < Constants.Item_Survey_Deposit_Size):
            return datetime.datetime.min

        closest_survey_end_time = datetime.datetime.max
        for item in iw_survey_data['result']['t_weapons']:
            item_survey_end_time = self.item_world_survey_get_item_return_time(item)
            if item_survey_end_time < closest_survey_end_time:
                closest_survey_end_time = item_survey_end_time

        for item in iw_survey_data['result']['t_equipments']:
            item_survey_end_time = self.item_world_survey_get_item_return_time(item)
            if item_survey_end_time < closest_survey_end_time:
                closest_survey_end_time = item_survey_end_time

        return closest_survey_end_time

    def item_world_survey_get_item_return_time(self, item):
        end_time_string = item['item_world_survey_end_at']
        if end_time_string != '':
            end_time_datetime = parser.parse(end_time_string)
            return end_time_datetime
        return datetime.datetime.min

    # Will first try to fill the depository with items with rare innocents (any rank)
    # Rest of spots will be filled with any item of specified rank (r40 by default)
    def item_world_survey_fill(self, free_slots=10, min_item_rank_to_deposit=40):
        if free_slots == 0:
            iw_survey_data = self.client.item_world_survey_index()
            free_slots = Constants.Item_Survey_Deposit_Size - len(iw_survey_data['result']['t_weapons']) - len(
                iw_survey_data['result']['t_equipments'])

        if free_slots > 0:
            self.log(f"\tSearching for {free_slots} items for item world survey...")

            self.player_weapons(True)
            self.player_equipment(True)
            equipments_to_deposit = []
            weapons_to_deposit = []
            etd, _ = self.pd.filter_items(
                max_item_rank=40, max_rarity=39, max_item_level=1,
                skip_locked=True, skip_equipped=True,
                max_innocent_rank=4,
                min_item_rank=min_item_rank_to_deposit,
                item_type=EquipmentType.ARMOR
            )

            # If deposit cannot be filled with only equipment, find weapons to finish filling
            if len(etd) < free_slots:
                free_slots = free_slots - len(etd)
                wtd, _ = self.pd.filter_items(
                    max_item_rank=40, max_rarity=39, max_item_level=1,
                    skip_locked=True, skip_equipped=True,
                    max_innocent_rank=4, max_innocent_type=Innocent_ID.RES,
                    min_item_rank=min_item_rank_to_deposit,
                    item_type=EquipmentType.WEAPON
                )
                weapons_to_deposit = wtd[0:free_slots]
            else:
                equipments_to_deposit = etd[0:free_slots]

            equipment_ids = []
            weapons_ids = []
            for equipment in equipments_to_deposit:
                equipment_ids.append(equipment['id'])
            for weapon in weapons_to_deposit:
                weapons_ids.append(weapon['id'])

            if len(weapons_ids) > 0 or len(equipment_ids) > 0:
                self.log(
                    'found %s armor and %s weapons for survey' % (len(equipment_ids), len(weapons_ids)))
                self.client.item_world_survey_start(weapons_ids, equipment_ids)
            else:
                self.log('unable to find items for survey')
