import json

from api.constants import EquipmentType, Innocent_ID, Fish_Fleet_Survey_Duration
from main import API


def get_event_areas(event_id):
    tmp = event_id * 1000
    return [tmp + 101, tmp + 102, tmp + 103, tmp + 104, tmp + 105]


class Bot:
    def __init__(self, api: API | None = None):
        if api is None:
            api = API()
            api.o.wait = 0
            api.o.set_region(2)
            api.o.set_device(3)

        self.api: API = api

    def farm_event_stage(self, times: int, stage_id: int, team: int, rebirth: bool, raid_team=None):
        for _ in range(times):
            self.do_quest(stage_id, team_num=team, auto_rebirth=rebirth, raid_team=raid_team)

    def farm_item_world(self, team=1, min_rarity=0, min_rank=0, min_item_rank=0, min_item_level=0, item_limit=None):
        # Change the party: 1-9
        self.api.o.team_num = team
        # This changes the minimum rarity of equipments found in the item-world. 1 = common, 40 = rare, 70 = Legendary
        self.api.o.min_rarity = min_rarity
        # This changes the min rank of equipments found in the item-world
        self.api.o.min_rank = min_rank
        # Only upgrade items that have this # of levels or greater
        self.api.o.min_item_level = min_item_level
        # Only upgrade items with the following rank
        self.api.o.min_item_rank = min_item_rank

        items = self.api.items_to_upgrade()
        if len(items) == 0:
            # self.remake_items()
            self.refine_items(min_rarity=90, min_item_rank=40, limit=5)
            items = self.api.items_to_upgrade()

        if len(items) == 0:
            self.api.log_err('No items to farm! Where they all at?')
            exit(1)

        self.api.log('found %s items to upgrade' % len(items))

        # This runs item-world to level all your items.
        self.api.upgrade_items(item_limit=item_limit, items=items)

    def do_gate(self, gate, team, rebirth, raid_team=None):
        self.api.log("[*] running gate {}".format(gate['m_stage_id']))
        current = int(gate['challenge_num'])
        _max = int(gate['challenge_max'])
        while current < _max:
            self.do_quest(gate['m_stage_id'], team_num=team, auto_rebirth=rebirth, raid_team=raid_team)
            current += 1

    def do_gates(self, gates_data, gem_team=7, hl_team=8, exp_team=None, raid_team=None, use_potions=False):
        orig_potions_val = self.api.o.use_potions
        self.api.o.use_potions = use_potions
        self.api.log("- checking gates")
        for data in gates_data:
            self.api.log("- checking gate {}".format(data['m_area_id']))
            if data['m_area_id'] == 50102:
                team = hl_team
                rebirth = False
            elif data['m_area_id'] == 50107 or data['m_area_id'] == 50108:
                team = gem_team
                rebirth = False
            else:
                team = exp_team
                rebirth = True

            if team is None:
                continue

            for gate in data['gate_stage_data']:
                if self.api.current_ap < 10:
                    self.api.log('Too low on ap to do gates')
                    return
                if team is not None and rebirth is not None:
                    self.do_gate(gate, team, rebirth, raid_team=raid_team)
                else:
                    self.api.log_err('no team or rebirth defined for: %s' % gate['m_stage_id'])
        self.api.o.use_potions = orig_potions_val

    def daily(self, gem_team: int = 22, hl_team: int = 21, exp_team=None):
        self.api.get_mail_and_rewards()
        self.send_sardines()

        self.api.vote_dark_assembly_agenda(110016)

        # Buy items from HL shop
        self.api.buy_daily_items_from_shop()

        # Do gates
        gates_data = self.api.client.player_gates()['result']
        self.do_gates(gates_data, gem_team=gem_team, hl_team=hl_team, exp_team=exp_team, use_potions=True)

    # Will return an array of event area ids based on the event id.
    # clear_event([1132101, 1132102, 1132103, 1132104, 1132105])

    def clear_event(self, area_lt, team_num, raid_team: int | None = None):
        self.api.o.use_potions = True
        dic = self.api.gd.stages
        rank = [1, 2, 3]
        for k in rank:
            for i in area_lt:
                new_lt = [x for x in dic if x["m_area_id"] == i and x["rank"] == k]
                for c in new_lt:
                    self.do_quest(c['id'], team_num, True, raid_team=raid_team)
        self.api.o.use_potions = False

    def use_ap(self, stage_id, event_team: int = 1, raid_team=None):
        self.api.log("[*] using ap")

        self.complete_story(team_num=event_team, raid_team=raid_team)

        if stage_id is None:
            for i in range(1, 5):
                for unit_id in self.api.pd.deck(i):
                    self.api.do_axel_contest(unit_id, 1000)
        else:
            times = int(self.api.current_ap / 30)
            self.farm_event_stage(stage_id=stage_id, team=event_team, times=times, rebirth=True, raid_team=raid_team)

    def clear_inbox(self):
        self.api.log("[*] clearing inbox")
        self.clean_inv()
        ids = self.api.client.present_index(conditions=[0, 1, 2, 3, 4, 99], order=1)['result']['_items']
        last_id = None

        while len(ids) > 0:
            self.api.get_mail()

            ids = self.api.client.present_index(conditions=[0, 1, 2, 3, 4, 99], order=1)['result']['_items']
            if len(ids) == 0:
                break
            new_last_id = ids[-1]
            if new_last_id == last_id:
                self.api.log("- inbox is empty or didnt change")
                break
            else:
                self.api.sell_items(max_rarity=39, max_item_rank=40, skip_max_lvl=True, only_max_lvl=False,
                                    max_innocent_rank=4, max_innocent_type=Innocent_ID.RES)
                self.api.sell_items(max_rarity=80, max_item_rank=40, skip_max_lvl=True, only_max_lvl=False,
                                    max_innocent_rank=4, max_innocent_type=Innocent_ID.RES)
            last_id = new_last_id

    def do_quest(self, stage_id, team_num=None, auto_rebirth=None, raid_team=None):
        if auto_rebirth is None:
            auto_rebirth = self.api.o.auto_rebirth

        self.api.doQuest(stage_id, team_num=team_num, auto_rebirth=auto_rebirth)
        if raid_team is not None:
            self.api.raid_share_own_boss(party_to_use=raid_team)
            self.api.raid_farm_shared_bosses(party_to_use=raid_team)

    def remake_items(self):
        items, skipped = self.api.pd.filter_items(
            min_rarity=90,
            max_rarity=100,
            min_item_rank=40,
            only_max_lvl=True,
            # item_type=EquipmentType.WEAPON,
            max_item_rank=99,
            skip_equipped=False,
            skip_locked=False,
        )
        for i in items:
            # print(i['id'])
            self.api.etna_resort_remake_item(i['id'])

    def refine_items(self, max_rarity: int = 99, max_item_rank: int = 9999, min_rarity: int = 90,
                     min_item_rank: int = 40,
                     limit=None):
        self.api.log('[*] looking for items to refine')
        weapons = []
        equipments = []

        items, skipped = self.api.pd.filter_items(max_rarity=max_rarity, max_item_rank=max_item_rank,
                                                  min_rarity=min_rarity, min_item_rank=min_item_rank,
                                                  skip_max_lvl=False, only_max_lvl=True,
                                                  skip_equipped=False, skip_locked=False,
                                                  max_innocent_rank=99, max_innocent_type=99,
                                                  min_innocent_rank=0, min_innocent_type=0)

        if limit is not None:
            items = items[0:limit]

        for item in items:
            equip_type = self.api.pd.get_equip_type(item)
            if equip_type == EquipmentType.WEAPON:
                weapons.append(item)
            else:
                equipments.append(item)

        self.api.log('[*] refine_items: found %s weapons and %s equipment to refine' % (len(weapons), len(equipments)))

        for i in weapons:
            self.api.etna_resort_refine_item(i['id'])
        for i in equipments:
            self.api.etna_resort_refine_item(i['id'])

    def train_innocents(self, innocent_type: int | None, initial_innocent_rank: int = 0, max_innocent_rank: int = 9,
                        innocents=None):
        innocents_trained = 0
        tickets_finished = False
        if innocents is None:
            innocents = self.api.pd.innocent_get_all_of_type(innocent_type, only_unequipped=True)

        if len(innocents) == 0:
            return

        for innocent in innocents:
            if tickets_finished:
                break
            innocent_type = innocent['m_innocent_id']
            innocent_rank = innocent['effect_rank']
            if innocent_rank < initial_innocent_rank or innocent_rank >= max_innocent_rank:
                continue
            self.api.log(
                f"Found innocent (type: {innocent_type}) to train. Starting value: {innocent['effect_values'][0]}")
            attempts = 0
            innocents_trained += 1
            tickets = self.api.get_caretaker_tickets(innocent_type)
            while tickets != None and innocent_rank < max_innocent_rank:
                if tickets['num'] <= 0:
                    self.api.log("No caretaker tickets left")
                    break

                res = self.api.client.innocent_training(innocent['id'])
                if ('self.api.error' in res and 'message' in res['self.api.error'] and
                        (
                                res['self.api.error']['message'] == 'Not enough item.' or
                                res['self.api.error']['message'] == 'Insufficient Items'
                        )):
                    self.api.log("No caretaker tickets left")
                    tickets_finished = True
                    break
                if 'result' not in res:
                    break
                innocent_rank = res['result']['after_t_data']['innocents'][0]['effect_rank']
                self.api.log(
                    f"Trained innocent (type: {str(innocent_type)}) with result"
                    f" {self.api.innocent_get_training_result(res['result']['training_result'])} "
                    f"- Current value: {res['result']['after_t_data']['innocents'][0]['effect_values'][0]}"
                )
                attempts += 1
            self.api.log(
                f"Upgraded innocent (type: {innocent_type}) to rank {self.api.gd.get_innocent_rank(innocent_rank)} "
                f"({innocent_rank}). "
                f"Finished training. Total attempts: {attempts}"
            )
        self.api.log(
            f"No innocents (type: {innocent_type}) left to train. Total innocents trained: {innocents_trained}")

    def send_sardines(self):
        # Send sardines
        player_data = self.api.client.player_index()
        if player_data['result']['act_give_count']['act_send_count'] == 0:
            self.api.client.friend_send_sardines()

    def complete_story(self, team_num=9, raid_team=None):
        self.api.o.team_num = team_num
        self.api.o.auto_rebirth = True
        self.api.o.use_potions = True
        # for i in range(141, 175):
        self.api.completeStory(raid_team=raid_team)
        self.api.o.use_potions = False

    def raid_claim(self):
        self.api.raid_claim_all_point_rewards()
        self.api.raid_claim_all_boss_rewards()
        # a.raid_exchange_surplus_points()
        self.api.raid_spin_innocent_roulette()

    def loop(self, team=9, rebirth: bool = False, farm_stage_id=None,
             iw_team: int = None, raid_team: int = None, event_team: int = None,
             gem_team: int = None, hl_team: int = None, exp_team: int = None,
             pvp_team: int = None, ap_limit: int = 6000,
             ):
        # Set defaults
        self.api.o.auto_rebirth = rebirth
        self.api.o.team_num = team

        if iw_team is None:
            iw_team = team
        if event_team is None:
            event_team = team
        if gem_team is None:
            gem_team = team
        if hl_team is None:
            hl_team = team

        # if exp_team is None:
        #     exp_team = team
        # if raid_team is None:
        #     raid_team = team

        if self.api.current_ap >= ap_limit:
            self.use_ap(stage_id=farm_stage_id, raid_team=raid_team)

        while True:
            if pvp_team is not None:
                self.api.pvp_do_battle(pvp_team)

            self.api.log("- claiming rewards and hospital")
            self.api.get_mail_and_rewards()
            self.api.spin_hospital()

            # self.api.log("- checking item world survey")
            # self.api.item_survey_complete_and_start_again(min_item_rank_to_deposit=40, auto_donate=True)

            self.api.log("- checking expeditions")
            self.api.survey_complete_all_expeditions_and_start_again(use_bribes=True,
                                                                     hours=Fish_Fleet_Survey_Duration.HOURS_24)

            self.api.log("- checking raids")
            self.api.raid_farm_shared_bosses(party_to_use=raid_team)
            self.raid_claim()

            # self.api.log("- train innocents")
            # self.train_recipe_innocents()

            # Train innocents
            # for i in a.gd.innocent_types:
            #     train_innocents(i["id"])
            # Train all EXP innocents to max level
            # train_innocents(Innocent_ID.EXP, initial_innocent_rank=0, max_innocent_rank=10)
            # Train all SPD innocents to max level
            # train_innocents(Innocent_ID.SPD, initial_innocent_rank=0, max_innocent_rank=10)

            self.clean_inv()

            if self.api.current_ap >= ap_limit:
                self.api.log("- doing gates")
                gates_data = self.api.client.player_gates()['result']
                self.do_gates(gates_data, gem_team=gem_team, hl_team=hl_team, exp_team=exp_team, raid_team=raid_team)
                self.use_ap(stage_id=farm_stage_id, event_team=event_team)

            self.api.log("- farming item world")
            # Go through rank 41+ items first
            items, skipped = self.api.pd.filter_items(min_item_rank=41, max_item_rank=49, max_item_level=0)
            self.api.upgrade_items(items=items)

            # Then do normal farm
            self.farm_item_world(
                team=iw_team,
                min_rank=40,
                min_item_rank=40
            )

            # self.remake_items()
            # self.clear_inbox()

    def train_recipe_innocents(self):
        for i in self.api.find_recipe_innocents(override_min_rank=True):
            inno_type_id = i['m_innocent_id']
            char_id = i['m_character_id']
            ranks = self.api.gd.innocent_recipe_map[inno_type_id][char_id]
            for target_rank in ranks:
                min_r, max_r = self.api.gd.get_innocent_rank_min_max(target_rank)
                # Skip if the innocent is already the required rarity
                if self.check_innocent_rank(i, target_rank):
                    continue
                if i['effect_rank'] > max_r:
                    self.api.log('innocent too high for recipe')
                    continue
                self.train_innocents(innocents=[i],
                                     innocent_type=inno_type_id,
                                     initial_innocent_rank=i['effect_rank'],
                                     max_innocent_rank=min_r)

    def check_innocent_rank(self, i: int | dict, target_rank: int, override_min_rank: bool = False):
        if type(i) is int:
            i = self.api.pd.get_innocent_by_id(i)
        min_r, max_r = self.api.gd.get_innocent_rank_min_max(target_rank)
        if override_min_rank and i['effect_rank'] < min_r:
            return True
        return min_r <= i['effect_rank'] <= max_r

    def check_innocent_mat_match(self, i: int | dict, mat: dict, override_min_rank: bool = False):
        if type(i) is int:
            i = self.api.pd.get_innocent_by_id(i)
        min_r, max_r = self.api.gd.get_innocent_rank_min_max(mat['rank'])
        m_innocent_id = mat['m_innocent_id']
        if i['m_innocent_id'] == m_innocent_id:
            if override_min_rank and i['effect_rank'] < min_r:
                return True
            return min_r <= i['effect_rank'] <= max_r
        return False

    def clean_inv(self):
        self.api.log("- donate equipment/innocents")
        # inno_blacklist = [x['id'] for x in self.api.find_recipe_innocents()]
        inno_blacklist = []
        self.api.etna_donate_innocents(max_innocent_rank=8, max_innocent_type=Innocent_ID.RES,
                                       blacklist=inno_blacklist)
        self.api.etna_donate_innocents(max_innocent_rank=8, innocent_types=[Innocent_ID.SPD, Innocent_ID.HL],
                                       blacklist=inno_blacklist)
        self.api.etna_resort_donate_items(max_item_rarity=69, remove_innocents=True)
        self.api.etna_resort_get_all_daily_rewards()
        self.api.log("- selling excess items")
        self.api.sell_items(max_item_rank=39, skip_max_lvl=True, only_max_lvl=False, remove_innocents=True)
        # self.api.sell_items(max_item_rank=40, max_rarity=85, max_innocent_rank=7, max_innocent_type=Innocent_ID.HL,  only_max_lvl=False,)
        self.api.sell_r40_commons_with_no_innocents()

    def use_codes(self, codes: list[str]):
        for code in codes:
            self.api.client.boltrend_exchange_code(code)

    def load_from_file(self):
        f = open('player_data.json', 'r')
        data = json.loads(str(f.read()))
        f.close()

        self.api.pd.decks = data['decks']
        self.api.pd.gems = data['gems']
        self.api.pd.items = data['items']
        self.api.pd.weapons = data['weapons']
        self.api.pd.equipment = data['equipment']
        self.api.pd.innocents = data['innocents']
        self.api.pd.characters = data['characters']
        self.api.pd.character_collections = data['character_collections']
        self.api.pd.clear_stages = data['clear_stages']
        self.api.pd.stage_missions = data['stage_missions']
        self.api.pd.weapon_effects = data['weapon_effects']
        self.api.pd.equipment_effects = data['equipment_effects']

    # Example
    ###############

    # a = API()
    # a.o.wait = 0
    # a.o.set_region(2)
    # a.o.set_device(3)
    # a.quick_login()
    #
    # codes = []
    #
    # bot = Bot(api=a)
    # bot.use_codes(codes)
    #
    # # Daily tasks
    # bot.daily(gem_team=22, hl_team=21, exp_team=None)
    #
    # # Full loop
    # bot.loop(
    #     team=9, rebirth=True, farm_stage_id=None,
    #     raid_team=23, iw_team=9, event_team=9,
    #     gem_team=22, hl_team=21, exp_team=None,
    #     ap_limit=5000,
    # )
