from abc import ABCMeta

from api.constants import Constants, Innocent_ID, EquipmentType, ErrorMessages, JP_ErrorMessages
from api.player import Player


class Shop(Player, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def remove_innocents(self, e):
        innos = self.pd.get_item_innocents(e)
        if len(innos) > 0:
            ids = []
            for i in innos:
                ids.append(i['id'])

            retry = True
            # execute once - repeat if there was an exception retrieving equipment
            while retry:
                retry = False
                data = self.client.innocent_remove_all(ids, 0)
                if 'error' in data and data['error'] == ErrorMessages.Innocent_Full_Error or data['error'] == JP_ErrorMessages.Innocent_Full_Error:                    
                    self.etna_donate_innocents(max_innocent_rank=5, max_innocent_type = Innocent_ID.RES)
                    self.player_innocents(True)
                    retry = True
            self.check_resp(data)
            if data['result']['after_t_data']:
                self.player_update_equip_detail(e)
            return data
        return {}

    def buy_daily_items_from_shop(self):
        product_data = self.client.shop_index()['result']['shop_buy_products']['_items']
        self.logger.info("Buying daily AP Pots and bribe items...")
        # 50% AP Pot
        self.__buy_shop_item(product_data, 102, 2)
        # Golden candy
        self.__buy_shop_item(product_data, 107, 3)
        # Golden Bar
        self.__buy_shop_item(product_data, 108, 2)
        # Skip ticket
        self.__buy_shop_item(product_data, 1121, 1)
        # BP refill
        self.__buy_shop_item(product_data, 111, 3)

    def __buy_shop_item(self, product_data, product_id, quantity):
        items = [x for x in product_data if x['m_product_id'] == product_id]
        if len(items) > 0:
            item = items[0]
            if item['buy_num'] == 0:
                self.client.shop_buy_item(product_id, quantity)

    def buy_all_equipment_with_innocents(self, shop_rank):
        self.log("Buying all equipment with innocents...")
        buy = True

        while buy:
            equipment_items = self.client.shop_equipment_items()['result']['_items']
            for i in equipment_items:
                if i['sold_flg']: continue
                if i['innocent_num'] > 0:
                    item_ids = [i['id']]
                    res = self.client.shop_buy_equipment(item_type=i['item_type'], itemid=item_ids)
                    if res['error'] == ErrorMessages.Armor_Full_Error or res['error'] == ErrorMessages.Weapon_Full_Error or res['error'] == JP_ErrorMessages.Armor_Full_Error or res['error'] == JP_ErrorMessages.Weapon_Full_Error:
                        buy=False
                        break
            if buy:
                update_number = self.client.shop_equipment_shop()['result']['lineup_update_num']
                if update_number < Constants.Shop_Max_Free_Refresh:
                    self.logger.info(f"Refreshing Shop. Current Refresh: {update_number}")
                    self.client.shop_change_equipment_items(shop_rank=shop_rank)
                else:
                    self.log(f"Free shop refreshes used up. Finished buying all equipment.")
                    buy = False

    def sell_r40_commons_with_no_innocents(self, item_count: int = 0):
        self.log("Looking for r40 equipment with no innocents to sell...")
        selling = []
        wc = 0
        ec = 0

        self.player_equipment(True)
        self.player_weapons(True)
        self.player_innocents(True)

        items, skipping = self.pd.filter_items(
            min_item_rank=40, max_item_rank=40,
            max_item_level=1,
            skip_equipped=True, skip_locked=True,
            max_rarity=39, max_innocent_count=0
        )
        if item_count > 0:
            items = items[:item_count]

        for item in items:
            _id = item['id']
            equip_type = self.pd.get_equip_type(item)
            if len(self.pd.get_item_innocents(_id)) == 0:
                if equip_type == EquipmentType.ARMOR:
                    ec += 1
                    selling.append(item)
                else:
                    wc += 1
                selling.append(item)

        self.log(f'Weapons to sell: {wc} - Equipment to sell: {ec}')
        if len(selling) > 0:
            sell_list = []
            for x in selling:
                self.log_sell(x)
                sell_list.append({'eqtype': self.pd.get_equip_type(x), 'eqid': x['id']})
            self.client.shop_sell_equipment(sell_list)

    # Sell items (to make sure depository can be emptied) that have no innocent or 1 common
    def shop_free_inventory_space(self, sell_weapons=False, sell_equipment=False, items_to_sell=20):
        self.log("Selling items to free inventory space...")
        selling = []
        wc = 0
        ec = 0

        if sell_equipment == True:
            self.player_equipment(True)
        if sell_weapons == True:
            self.player_weapons(True)
        self.player_innocents(True)

        items, skipping = self.pd.filter_items(
            max_item_rank=40, max_rarity=39, max_item_level=1,
            skip_equipped=True, skip_locked=True,
            max_innocent_rank=6, max_innocent_type=Innocent_ID.SPD
        )

        for item in items:
            _id = item['id']
            equip_type = self.pd.get_equip_type(item)
            if equip_type == EquipmentType.ARMOR and sell_equipment:
                ec += 1
                selling.append(item)
            if equip_type == EquipmentType.WEAPON and sell_weapons:
                wc += 1
                selling.append(item)

            if len(selling) == items_to_sell:
                break

        self.log(f"Weapons to sell: {wc} - Equipment to sell: {ec}")
        if len(selling) > 0:
            sell_list = []
            for x in selling:
                self.log_sell(x)
                sell_list.append({'eqtype': self.pd.get_equip_type(x), 'eqid': x['id']})
            self.client.shop_sell_equipment(sell_list)

    def innocent_safe_sell_items(self, max_innocent_rank:int=5, max_item_rank:int=32):
        self.player_equipment(True)
        self.player_weapons(True)

        selling = []

        items, skipping = self.pd.filter_items(
            max_item_level=1, max_item_rank=max_item_rank,
            skip_equipped=True, skip_locked=True,
            skip_max_lvl=True,
            max_innocent_rank=max_innocent_rank
        )
        for item in items:
            _id = item['id']
            equip_type = self.pd.get_equip_type(item)
            selling.append({'eqtype': equip_type, 'eqid': _id})

        if len(selling) > 0:
            self.log(f"Selling {len(selling)} items...")
            self.client.shop_sell_equipment(selling)

    def shop_use_lottery_tickets(self, ticket_to_use:int = 0):
        tickets_left = True
        # if 0 use all tickets
        if ticket_to_use == 0:
            ticket_to_use = 10000
        while tickets_left and ticket_to_use > 0:
            ticket_to_use -=1
            data = self.client.shop_gacha()
            item = None
            if data['result']['item_type'] == 4:
                item = self.gd.get_equipment(data['result']['item_id'])
            if data['result']['item_type'] == 3:
                item = self.gd.get_weapon(data['result']['item_id'])
            if data['result']['item_type'] not in (3, 4):
                item = self.gd.get_item(data['result']['item_id'])

            if item is None:
                raise Exception("Unknown item type %s" % data['result']['item_type'])

            self.log(
                f"Obtained {data['result']['m_garapon_lot_id']} prize: {data['result']['item_num']} x {item['name']}")
            if data['result']['t_item_garapon']['num'] <= 0:
                tickets_left = False

    def sell_items(self, max_rarity=40, max_item_rank=100, skip_max_lvl=False, only_max_lvl=False, max_innocent_rank=10,
                   max_innocent_type=Innocent_ID.HL, remove_innocents: bool = False, limit=None, item_type=None):
        self.player_equipment(True)
        self.player_weapons(True)

        # if we are removing innocents then it doesn't matter about the innocent filter
        if remove_innocents:
            max_innocent_rank = 10
            max_innocent_type = Innocent_ID.HL

        selling, skipping = self.pd.filter_items(
            skip_max_lvl=skip_max_lvl, skip_equipped=True,
            max_innocent_rank=max_innocent_rank, max_innocent_type=max_innocent_type,
            max_item_rank=max_item_rank, max_rarity=max_rarity,
            only_max_lvl=only_max_lvl, skip_locked=True,
            item_type=item_type
        )

        if limit is not None and limit < len(selling):
            skipping = skipping + len(selling) - limit
            selling = selling[0:limit]

        self.log('skipping %s items, selling %s items' % (skipping, len(selling)))
        if len(selling) >= 1:
            data = self.sell_item_list(selling, remove_innocents)
            # self.player_weapons(True)
            # self.player_equipment(True)
            return data

    def sell_item_list(self, selling: list, remove_innocents: bool = True):
        sell_list = []
        for i in selling:
            sell_list.append({'eqtype': self.pd.get_equip_type(i), 'eqid': i['id']})
            if remove_innocents:
                self.remove_innocents(i)

            self.log_sell(i)
        data = self.client.shop_sell_equipment(sell_list)
        self.check_resp(data)
        return data

    def log_sell(self, w):
        self.log_item("[-] sell item", w)

    def log_item(self, msg, w):
        item = self.gd.get_weapon(w['m_weapon_id']) if 'm_weapon_id' in w else self.gd.get_equipment(
            w['m_equipment_id'])
        self.logger.debug(
            '%s: "%s" rarity: %s rank: %s lv: %s lv_max: %s locked: %s' %
            (msg, item['name'], w['rarity_value'], self.gd.get_item_rank(w), w['lv'],
             w['lv_max'], w['lock_flg'])
        )