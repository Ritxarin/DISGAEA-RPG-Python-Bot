# -*- coding: utf-8 -*-
import datetime
import random

from api.CustomExceptions import NoAPLeftException
from api.constants import Item_World_Mode

from dateutil import parser

from api import BaseAPI
from api.constants import Constants, Battle_Finish_Mode, Character_Gate
from api.constants import Items as ItemsC


class API(BaseAPI):
    def __init__(self):
        super().__init__()

    def config(self, sess: str, uin: str, wait: int = 0, region: int = 1, device: int = 1):
        self.o.sess = sess
        self.o.uin = uin
        self.o.wait = wait
        self.o.set_region(region)
        self.o.set_device(device)
        self.gd.__init__(self.o.region)

    def get_mail_and_rewards(self):
        self.client.trophy_get_reward_daily()
        for i in range(5):
            self.client.trophy_get_reward()
        for i in range(5):
            self.get_mail()

    ################################################################
    ###########      LOGIN METHODS   ###############################
    ################################################################

    def quick_login(self):
        self.client.login()
        self.player_characters(True)
        self.player_weapons(True)
        self.player_weapon_effects(True)
        self.player_equipment(True)
        self.player_equipment_effects(True)
        self.player_items(True)
        self.player_innocents(True)

        data = self.client.player_index()
        if 'result' in data:
            self.o.current_ap = int(data['result']['status']['act'])

        self.player_character_collections()
        self.player_decks()
        self.player_get_equipment_presets()
        self.player_stone_sum()

    # Use for JP
    def dologin(self,public_id=None,inherit_code=None):
        self.client.version_check()
        if public_id and inherit_code:
            public_id=str(public_id)
            inherit_code=str(inherit_code)
            self.client.signup()
            self.client.login()
            self.client.player_add(tracking_authorize=2)
            self.client.inherit_check()
            self.client.auth_providers()
            if not self.client.inherit_conf_inherit(public_id=public_id,inherit_code=inherit_code):
                self.log('wrong password or public_id')
                exit(1)
            self.client.inherit_exec_inherit(public_id=public_id,inherit_code=inherit_code)
            self.client.version_check()
        self.client.login()
        self.client.app_constants()
        self.client.player_tutorial()
        self.client.battle_status()
        # player/profile
        # player/sync
        self.player_characters(True)
        self.player_weapons(True)
        self.player_weapon_effects(True)
        self.player_equipment(True)
        self.player_equipment_effects(True)
        self.player_items(True)
        # self.client.player_clear_stages(updated_at=0, page=1)
        # self.client.player_stage_missions(updated_at=0, page=1)
        self.player_innocents(True)
        data = self.client.player_index()
        if 'result' in data:
            self.o.current_ap = int(data['result']['status']['act'])
        self.client.player_agendas()
        self.client.player_boosts()
        self.player_character_collections()
        self.player_decks()
        self.client.friend_index()
        self.client.player_home_customizes()
        self.client.passport_index()
        self.player_stone_sum()
        self.client.player_sub_tutorials()
        self.client.system_version_manage()
        self.client.player_gates()
        self.client.event_index()
        self.client.stage_boost_index()
        self.client.information_popup()
        self.client.player_character_mana_potions()
        self.client.potential_current()
        self.client.potential_conditions()
        self.client.character_boosts()
        self.client.survey_index()
        self.client.kingdom_entries()
        self.client.breeding_center_list()
        self.client.trophy_daily_requests()
        self.client.weapon_equipment_update_effect_unconfirmed()
        self.client.memory_index()
        self.client.battle_skip_parties()
        # boltrend/subscriptions
        self.client.login_update()
        self.player_get_equipment_presets()
        if self.o.region==1:
            self.client.auth_providers()
            code=self.client.inherit_get_code()['result']
            self.log('public_id: %s inherit_code: %s'%(code['public_id'],code['inherit_code']))
            with open('transfercode.txt', 'w') as f:
                f.write(code['inherit_code'])

    # Reads from logindata.json. Avoids new login (prevents issues with JP code transfer)
    def loginfromcache(self):
        self.client.login_from_cache()
        self.client.app_constants()
        self.player_characters(True)
        self.player_weapons(True)
        self.player_weapon_effects(True)
        self.player_equipment(True)
        self.player_equipment_effects(True)
        self.player_items(True)
        self.player_innocents(True)

        data = self.client.player_index()
        if 'result' in data:
            self.o.current_ap = int(data['result']['status']['act'])

        self.player_character_collections()
        self.player_decks()
        self.player_get_equipment_presets()
        self.player_stone_sum()

    ################################################################
    ###########      MAIL METHODS   ################################
    ################################################################

    def get_mail(self):
        did = set()
        while 1:
            ids = self.client.present_index(conditions=[0, 1, 2, 3, 4, 99],
                                            order=1)['result']['_items']
            msgs = []
            for i in ids:
                if i['id'] in did: continue
                msgs.append(i['id'])
                did.add(i['id'])
            if len(msgs) >= 1:
                self.client.present_receive(
                    receive_ids=msgs[0:len(msgs) if len(msgs) <= 20 else 20],
                    conditions=[0, 1, 2, 3, 4, 99],
                    order=1)
            else:
                break

    def present_receive_ap(self):
        present_data = self.client.present_index(conditions=[4], order=0)
        ap = next((x for x in present_data['result']['_items'] if x['present_id'] == 2501), None)
        if ap is not None:
            self.client.present_receive(receive_ids=[ap['id']], order=0, conditions=[4])
            print(f"Claimed {ap['present_num']} AP")
            self.o.current_ap += int(ap['present_num'])

    def present_receive_equipment(self):
        claim_presents = True
        while claim_presents:
            present_data = self.client.present_index(conditions=[2], order=0)
            if len(present_data['result']['_items']) == 0:
                claim_presents = False
            item_ids = []
            for item in present_data['result']['_items']:
                item_ids.append(item['id'])
            for batch in (item_ids[i:i + 20] for i in range(0, len(item_ids), 20)):
                res = self.client.present_receive(receive_ids=batch, order=0, conditions=[2])
                print(f"Claimed {len(res['result']['received_ids'])} items")
                if len(res['result']['received_ids']) == 0 and len(batch):
                    self.log("Cannot claim more items.")
                    claim_presents = False
                    break
        self.log("Finished claiming items.")

    def present_receive_all_except_equip_and_AP(self):
        initial_nq = self.player_stone_sum()['result']['_items'][0]['num']
        current_nq = initial_nq
        present_data = self.client.present_index(conditions=[0, 1, 3, 99], order=0)
        claim = True
        while claim:
            item_ids = []
            for item in present_data['result']['_items']:
                item_ids.append(item['id'])
            if len(item_ids) > 0:
                for batch in (item_ids[i:i + 20] for i in range(0, len(item_ids), 20)):
                    data = self.client.present_receive(receive_ids=batch, order=0, conditions=[0, 1, 3, 99])
                    self.log(f"Claimed {len(data['result']['received_ids'])} presents")
                    if 'stones' in data['result']:
                        current_nq = data['result']['stones'][0]['num']
                    if len(data['result']['received_ids']) == 0:
                        self.log(f"Could not claim any presents. Item box is probably full...")
                        claim = False
                        break
            if claim:
                present_data = self.client.present_index(conditions=[0, 1, 3, 99], order=0)
                claim = len(present_data['result']['_items']) > 0
        if current_nq > initial_nq:
            self.log(f"Total Nether Quartz gained: {current_nq - initial_nq}")
        self.log("Finished claiming presents.")

    ################################################################
    ###########      QUEST METHODS    ##############################
    ################################################################

    def doQuest(self, m_stage_id=101102, team_num=None, auto_rebirth: bool = None,
                help_t_player_id: int = 0, send_friend_request: bool = False,
                finish_mode: Battle_Finish_Mode = Battle_Finish_Mode.Random_Finish,
                randomize_helper:bool=False):
        if auto_rebirth is None:
            auto_rebirth = self.o.auto_rebirth

        stage = self.gd.get_stage(m_stage_id)
        if stage is None:
            self.log(f"No stage with id {m_stage_id} found")
            return
        self.log('doing quest:%s [%s]' % (stage['name'], m_stage_id))
        if stage['exp'] == 0:
            return self.client.battle_story(m_stage_id)

        if stage['act'] > self.current_ap:
            if self.o.use_potions:
                self.log('not enough ap. using potion')
                item_id = ItemsC.AP_Pot
                ap_pot = self.pd.get_item_by_m_item_id(ItemsC.AP_Pot)
                if ap_pot is None or ap_pot['num_total'] == 0:
                    self.log('No AP potions left')
                    item_id = ItemsC.AP_Pot_50
                    ap_pot = self.pd.get_item_by_m_item_id(ItemsC.AP_Pot_50)
                    if ap_pot is None or ap_pot['num_total'] == 0:
                        self.log('No 50% AP potions left. Trying to claim AP from mail')
                        self.present_receive_ap()
                        if self.o.current_ap < stage['act']:
                            self.log('No AP left on mail. Exiting....')
                            raise NoAPLeftException
                        return
                rr = self.client.item_use(use_item_id=item_id, use_item_num=1)
                if 'api_error' in rr and rr['api_error']['code'] == 12009:
                    self.log_err('unable to use potion')
                    raise NoAPLeftException
            else:
                self.log('not enough ap')
                raise NoAPLeftException

        if team_num is None:
            team_num = self.o.team_num

        auto_rebirth_character_ids = []
        if auto_rebirth:
            if len(self.o.auto_rebirth_character_ids) > 0:
                auto_rebirth_character_ids = self.o.auto_rebirth_character_ids
            else:
                auto_rebirth_character_ids = self.pd.deck(team_num)

        if help_t_player_id != 0:
            help_player = self.battle_help_get_friend_by_id(help_t_player_id)
        else:
            helper_data = self.client.battle_help_list()['result']['help_players']   
            if randomize_helper:                         
                help_player = helper_data[random.randint(0, len(helper_data)-1)]
            else:
                help_player = helper_data[0]

        start = self.client.battle_start(
            m_stage_id=m_stage_id, help_t_player_id=help_player['t_player_id'],
            help_t_character_id=help_player['t_character']['id'], act=stage['act'],
            help_t_character_lv=help_player['t_character']['lv'],
            deck_no=team_num, reincarnation_character_ids=auto_rebirth_character_ids,
        )

        if 'result' not in start:
            return

        if finish_mode == Battle_Finish_Mode.Tower_Finish:
            exp_data = self.get_battle_exp_data_tower_finish(start)
        elif finish_mode == Battle_Finish_Mode.Single_Character:
            exp_data = self.get_battle_exp_data_single_unit_finish(start)
        else:
            exp_data = self.get_battle_exp_data(start)

        end = self.client.battle_end(
            battle_exp_data=exp_data, m_stage_id=m_stage_id,
            battle_type=1, result=1)
        res = self.parseReward(end)
        self.check_resp(end)

        if send_friend_request and not self.is_helper_in_friend_list(help_player['t_player_id']):
            self.log(f"Send friend request to {help_player['name']} - Rank {help_player['rank']}")
            self.client.friend_send_request(help_player['t_player_id'])

        return res

    def do_conquest_battle(self, m_stage_id=101102, t_character_ids=[]):
        stage = self.gd.get_stage(m_stage_id)
        self.log('doing conquest battle:%s [%s]' % (stage['name'], m_stage_id))
        start = self.client.battle_start(
            m_stage_id=m_stage_id,
            help_t_player_id=0,
            help_t_character_id=0,
            act=stage['act'],
            help_t_character_lv=0,
            character_ids=t_character_ids)
        if 'result' not in start:
            return
        end = self.client.battle_end(battle_exp_data=self.get_battle_exp_data(start),
                                     m_stage_id=m_stage_id,
                                     battle_type=1,
                                     result=1)
        res = self.parseReward(end)
        return res

    def Complete_Overlord_Tower(self, team_no: int = 1):
        tower_level = 1
        while tower_level <= Constants.Highest_Tower_Level:
            self.log(f"Clearing Overlord Tower level {tower_level}...")
            start = self.client.tower_start(m_tower_no=tower_level, deck_no=team_no)
            end = self.client.battle_end(battle_exp_data=self.get_battle_exp_data(start), m_tower_no=tower_level,
                                         m_stage_id=0,
                                         battle_type=4, result=1)
            tower_level += 1
        self.log("Completed Overlod Tower")

    def completeStory(self, m_area_id=None, limit=None, raid_team=None, send_friend_request:bool=False, team_to_use:int=1):
        ss = []
        for s in self.gd.stages:
            ss.append(s['id'])
        ss.sort(reverse=False)
        i = 0
        blacklist = set()

        cleared_stages = self.get_cleared_stages()
        ranks = [1, 2, 3, 4 ,5 ,6] if self.is_carnage_unlocked() else [1, 2, 3]
        for rank in ranks:
            for s in ss:
                if limit is not None and i >= limit:
                    return False
                stage = self.gd.get_stage(s)
                if m_area_id is not None and m_area_id != stage['m_area_id']:
                    continue
                if stage['rank'] != rank: continue

                # Skip non story areas, but do anecdote
                if m_area_id is None and stage['m_area_id']> 1000:
                    if stage['m_area_id'] < 200000 or stage['m_area_id'] > 200315: 
                        continue

                if self.is_stage_3starred(s):
                    self.log('Stage already 3 starred - area: %s stage: %s rank: %s name: %s' % (
                        stage['m_area_id'], s, rank, stage['name']
                    ))
                    continue

                if stage['act'] == 0 and s in cleared_stages:
                    self.log('Story stage already completed - area: %s stage: %s rank: %s name: %s' % (
                        stage['m_area_id'], s, rank, stage['name']
                    ))
                    continue

                if not stage['appear_m_stage_id'] in cleared_stages and stage['appear_m_stage_id'] != 0:
                    self.log('not unlocked - area: %s stage: %s rank: %s name: %s' % (
                        stage['m_area_id'], s, rank, stage['name']
                    ))
                    continue

                if stage['m_area_id'] in blacklist:
                    continue
                try:
                    self.doQuest(m_stage_id=s, team_num=team_to_use, auto_rebirth=self.o.auto_rebirth, send_friend_request=send_friend_request, randomize_helper=True)
                    cleared_stages.add(s)                    
                    if raid_team is not None:
                        self.raid_share_own_boss(raid_team)
                        self.raid_farm_shared_bosses(raid_team)
                except KeyboardInterrupt:
                    return False
                except NoAPLeftException:
                    return
                except:
                    self.log_err('failed stage: %s area: %s' % (s, stage['m_area_id']))
                    blacklist.add(stage['m_area_id'])
                    continue
                self.player_stone_sum()
                self.player_items()
                i += 1

    ################################################################
    ##############      IW METHODS    ##############################
    ################################################################

    def upgrade_items(self, item_limit: int = None, items=None):
        if items is None:
            items = self.items_to_upgrade()
        if item_limit is not None and len(items) > int(item_limit):
            items = items[0:item_limit]
        self.upgrade_item_list(items)

    def upgrade_item_list(self, items):
        if len(items) == 0:
            self.log_err('No items found to upgrade')

        for w in items:

            if self.is_item_in_iw_survey(w['id']):
                continue
            if self.etna_resort_is_item_in_depository(w['id']):
                continue

            self.client.trophy_get_reward_repetition()
            self.log_upgrade_item(w)
            while 1:
                if not self.doItemWorld(
                        equipment_id=w['id'],
                        equipment_type=self.pd.get_equip_type(w)
                ):
                    break

    # Will return a list of items that match the upgrade options filter
    def items_to_upgrade(self):
        weapons = self.player_weapons(False)
        equipments = self.player_equipment(False)

        if self.options.item_world_mode == Item_World_Mode.Run_Weapons_Only:
            items = weapons
        elif self.options.item_world_mode == Item_World_Mode.Run_Equipment_Only:
            items = equipments
        else:
            items = equipments + weapons

        item_list = []
        for w in filter(self.__item_filter, items):
            item_list.append(w)

        return item_list

    def __item_filter(self, e, i_filter=None):
        if i_filter is None:
            i_filter = {
                'min_item_rank': self.o.min_item_rank,
                'min_item_rarity': self.o.min_item_rarity,
                'min_item_level': self.o.min_item_level,
                'lv_max': False,
            }

        if self.gd.get_item_rank(e) < i_filter['min_item_rank']:
            return False
        if e['rarity_value'] < i_filter['min_item_rarity']:
            return False
        if e['lv_max'] < i_filter['min_item_level']:
            return False
        if i_filter['lv_max'] is False and e['lv'] >= e['lv_max']:
            return False
        return True

    def log_upgrade_item(self, w):
        item = self.gd.get_weapon(w['m_weapon_id']) if 'm_weapon_id' in w else self.gd.get_equipment(
            w['m_equipment_id'])
        if item is not None:
            self.log(
                '[*] upgrade item: "%s" rarity: %s rank: %s lv: %s lv_max: %s locked: %s' %
                (item['name'], w['rarity_value'], self.gd.get_item_rank(w), w['lv'],
                w['lv_max'], w['lock_flg'])
            )

    def doItemWorld(self, equipment_id=None, equipment_type=1):
        if equipment_id is None:
            self.log_err('missing equip')
            return
        start, result = self.__start_item_world(equipment_id, equipment_type)

        # Loop until we get a good result, should also prevent too deep recursion
        while result != 1:
            if start is None:
                return False
            stage = start['result']['stage']
            self.log('stage: %s - did not drop anything good, retrying..' % stage)
            self.client.battle_end(
                m_stage_id=0,
                result=result,
                battle_type=start['result']['battle_type'],
                equipment_type=start['result']['equipment_type'],
                equipment_id=start['result']['equipment_id'],
            )
            start, result = self.__start_item_world(equipment_id, equipment_type)

        # End the battle and keep the equipment
        end = self.client.battle_end(
            battle_exp_data=self.get_battle_exp_data(start),
            m_stage_id=0,
            result=result,
            battle_type=start['result']['battle_type'],
            equipment_type=start['result']['equipment_type'],
            equipment_id=start['result']['equipment_id'],
        )

        res = self.get_weapon_diff(end)
        if res:
            self.log(res)
        return res

    def __start_item_world(self, equipment_id, equipment_type):
        start = self.client.item_world_start(equipment_id, equipment_type=equipment_type,
                                             deck_no=self.o.team_num,
                                             reincarnation_character_ids=self.pd.deck(
                                                 self.o.team_num) if self.o.auto_rebirth else [])
        if start is None or 'result' not in start:
            return None, None

        result = self.parse_start(start)

        return start, result

    def getGain(self, t):
        for j in self.pd.items:
            if j['m_item_id'] == t['m_item_id']:
                return t['num'] - j['num']

    def parseReward(self, end):
        drop_result = end
        event_points = drop_result['result']['after_t_event']['point'] if drop_result['result']['after_t_event'] else 0
        drop_result = drop_result['result']['drop_result']
        for e in drop_result:
            if e == 'after_t_item':
                for t in drop_result[e]:
                    i = self.gd.get_item(t['m_item_id'])
                    if i is not None: self.log('%s +%s' % (i['name'], self.getGain(t)))
            elif e == 'drop_character':
                for t in drop_result[e]:
                    self.log('unit:%s lv:%s rarity:%s*' % (
                        self.gd.get_character(t['m_character_id'])['name'], t['lv'], t['rarity']))
            elif e == 'stones':
                self.log('+%s nether quartz' % (drop_result[e][0]['num'] - self.pd.gems))
        if event_points > 0:
            self.log('%s event points' % event_points)

        return drop_result

    ################################################################
    ###########      STAGE METHODS   ###############################
    ################################################################

    def get_cleared_stages(self, refresh:bool=False):
        stages = set()
        r = self.player_clear_stages(refresh=refresh)
        if len(r) <= 0:
            return
        for i in r:
            if i['clear_num'] >= 1:
                stages.add(i['m_stage_id'])
        return stages
    
    def is_stage_cleared(self, stage_id:int):
        stages = self.get_cleared_stages(False)
        return stage_id in stages
    
    def get_3starred_stages(self, refresh:bool=False):
        stages = []
        r = self.player_stage_missions(refresh)
        if len(r) <= 0:
            return
        for i in r:
            if i['clear_flg_1'] == 1 and i['clear_flg_2'] == 1 and i['clear_flg_3'] == 1:
                stages.append(i['m_stage_id'])
        return stages
    
    def is_stage_3starred(self, stage_id:int):
        stages = self.get_3starred_stages(False)
        return stage_id in stages

    def getAreaStages(self, m_area_id):
        ss = []
        for s in self.gd.stages:
            if s['m_area_id'] == m_area_id:
                ss.append(s)
        return ss

    ################################################################
    ##############      IW METHODS    ##############################
    ################################################################
    
    def useCodes(self, codes):
        for c in codes:
            self.client.boltrend_exchange_code(c)
        self.get_mail()

    def spin_hospital(self):
        # Server time is utc -4. Spins available every 8 hours
        last_roulete_time_string = self.client.hospital_index()['result']['last_hospital_at']
        last_roulette_time = parser.parse(last_roulete_time_string)
        time_delta = -4 if self.o.region == 2 else 9
        server_date_time = datetime.datetime.utcnow() + datetime.timedelta(hours=time_delta)
        if server_date_time > last_roulette_time + datetime.timedelta(hours=8):
            self.client.hospital_roulette()

    def is_helper_in_friend_list(self, player_id):
        resp = self.client.friend_index()
        self.check_resp(resp)
        all_friends = resp['result']['friends']
        friend = next((x for x in all_friends if x['id'] == player_id), None)
        return friend is not None

    def dump_player_data(self, file_path: str):
        self.player_stone_sum()
        self.player_decks(True)
        self.player_items(True)
        self.player_weapons(True)
        self.player_equipment(True)
        self.player_innocents(True)
        self.player_characters(True)
        self.player_character_collections(True)
        self.get_cleared_stages(True)
        self.player_stage_missions(True)
        self.pd.dump_to_file(file_path, {
            "app_constants": self.client.app_constants()['result'],
        })

    def complete_dark_assembly_mission(self, agenda_id=138):
        self.client.agenda_start(agenda_id)
        self.client.agenda_vote(agenda_id, [])
        self.client.agenda_get_campaign()

    def is_carnage_unlocked(self):
        agendas = self.client.agenda_index()
        carnage = next((x for x in agendas['result']['t_agendas'] if x['m_agenda_id'] == 59), None)
        return carnage is not None and carnage['status'] == 1

    def player_get_deck_data(self):
        deck_data = self.client.player_decks()
        charaIdList = []
        names = []
        t_memory_ids_list = []

        for team in deck_data['result']['_items']:
            team_characters = team['t_character_ids']
            character_ids = ""
            sorted_keys = sorted(team_characters)
            for key in sorted_keys:
                unit_id = team_characters[key]
                if (character_ids == ""):
                    character_ids = unit_id
                else:
                    character_ids = "{character_ids},{unit_id}".format(character_ids=character_ids, unit_id=unit_id)

            if len(team_characters) < 5:
                zeroes_to_add = 5 - len(team_characters)
                i = 0
                while i < zeroes_to_add:
                    character_ids = "{character_ids},0".format(character_ids=character_ids)
                    i += 1

            charaIdList.append(character_ids)
            names.append(team['name'])

            memories = ""
            for memory in team['t_memory_ids']:
                if (memories == ""):
                    memories = memory
                else:
                    memories = "{memories},{memory}".format(memories=memories, memory=memory)
            t_memory_ids_list.append(memories)

        deck_data = {"selectDeckNo": 1, "charaIdList": charaIdList, "names": names,
                     "t_memory_ids_list": t_memory_ids_list}
        return deck_data

    # team_no index starts at 0 Deduct 1 to offset. Character ids: '149980157,115286421,86661270,181611027,0'
    def update_team(self, team_no:int, character_ids):
        x = character_ids.split(",")
        if len(x) != 5:
            print(f"You need to specify 5 character ids")
            return
        if x[0] == '0' and next((r for r in x if r != '0'), None) is not None:
            print(f"Leader slot cannot be empty")
            return
        deck_data = self.player_get_deck_data()
        deck_data['charaIdList'][team_no - 1] = character_ids
        self.client.player_update_deck(deck_data)
        self.player_decks(refresh=True)


    ################################################################
    ###########     FRIEND METHODS   ###############################
    ################################################################

    # Search friend by public ID and send request
    def add_friend_by_public_id(self, public_id):
        if isinstance(public_id, int):
            public_id = str(public_id)
        friend_data = self.client.friend_search(public_id=public_id)
        if len(friend_data['result']['friends']) == 0:
            self.log(f"No user found with public id {public_id}")
            return
        self.log(
            f"Sending request to user {friend_data['result']['friends'][0]['name']} - Rank {friend_data['result']['friends'][0]['rank']}")
        self.client.friend_send_request(friend_data['result']['friends'][0]['id'])

    def add_friend_by_name(self, user_name):
        friend_data = self.client.friend_search(name=user_name)
        if len(friend_data['result']['friends']) == 0:
            self.log(f"No user found with public name {user_name}")
            return
        self.log(
            f"Sending request to user {friend_data['result']['friends'][0]['name']} - Rank {friend_data['result']['friends'][0]['rank']}")
        self.client.friend_send_request(friend_data['result']['friends'][0]['id'])


    def super_reincarnate(self, character_id, log:bool=True):
        unit = self.pd.get_character_by_id(character_id)
        if unit is None:
            self.log(f"No character with id {character_id} found")
            return
        if unit['lv'] < 9999:
            if log: self.log(f"Unit needs to be level 9999 to be able to Super Reincarnate")
            return
        sr_count = unit['super_rebirth_num']
        from data import data as gamedata
        sr_data = gamedata['super_rebirth_data']
        next_sr = next((x for x in sr_data if x['super_rebirth_num'] == sr_count + 1), None)
        ne_count = self.pd.get_item_by_m_item_id(ItemsC.Nether_Essence)['num']
        if next_sr['magic_element'] > ne_count:
            self.log(f"SR costs {next_sr['magic_element']}, you only have {ne_count} Nether Essence")
            return
        res = self.client.super_reincarnate(t_character_id=character_id, magic_element_num=next_sr['magic_element'])
        char = self.gd.get_character(unit['m_character_id'])
        self.log(
            f"Super Reincarnated {char['name']}. SR Count: {next_sr['super_rebirth_num']} - Karma Gained: {next_sr['karma']}")

    def clear_character_gates(self):
        events = self.client.event_index()
        gate_id_list = [Character_Gate.Majin_Etna, Character_Gate.Pure_Flonne, Character_Gate.Bloodis,
                        Character_Gate.Sister_Artina, Character_Gate.Killidia, Character_Gate.Pringer_X]
        for event in events['result']['events']:
            event_id = event['m_event_id']
            if event_id in gate_id_list:
                self.clear_character_gate(event_id)

    def clear_character_gate(self, character_gate: Character_Gate):
        run_count = 0
        area_id = 0
        if character_gate == Character_Gate.Majin_Etna:
            area_id = 1002101
        elif character_gate == Character_Gate.Pure_Flonne:
            area_id = 1014101
        elif character_gate == Character_Gate.Bloodis:
            area_id = 1027101
        elif character_gate == Character_Gate.Sister_Artina:
            area_id = 1034101
        elif character_gate == Character_Gate.Killidia:
            area_id = 1045101
        elif character_gate == Character_Gate.Pringer_X:
            area_id = 1084101

        event_data = self.client.event_index(event_ids=[character_gate])
        run_count = event_data['result']['events'][0]['challenge_num']
        if run_count == 3:
            return
        stages = self.gd.stages
        event_stages = [x for x in stages if x["m_area_id"] == area_id]
        event_stages.sort(key=lambda x: x['sort'], reverse=True)

        # initial run, 3 star event first
        for event_stage in event_stages:
            if self.is_stage_3starred(stage_id=event_stage['id']):
                continue
            self.doQuest(m_stage_id=event_stage['id'])
            run_count +=1
            if run_count == 3:
                return
        # If there are runs left, do them on the highest stagge
        while run_count < 3:
            self.doQuest(m_stage_id=event_stages[0]['id'])
            run_count +=1

        event_data = self.client.event_index(event_ids=[character_gate])
        if event_data['result']['events'][0]['is_item_reward_receivable']:
            self.log(f"Claiming character copy")
            r = self.client.event_receive_rewards(event_id=character_gate)