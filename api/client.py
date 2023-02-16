import base64
import json
import os
import sys
import time
import uuid
from typing import List

import jwt
import requests
# noinspection PyUnresolvedReferences
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from api.constants import Constants
from api.game_data import GameData
from api.logger import Logger
# noinspection PyPep8Naming
from api.options import Options
from boltrend import boltrend
from codedbots import codedbots

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

head = {'version_check': 0, 'signup': 1, 'login': 1, '__rpc': 2}


class Client:
    def __init__(self, variables: Options):
        self.o: Options = variables
        self.c = codedbots()
        self.b = boltrend()
        self.s = requests.Session()
        self.s.verify = False
        self.gd = GameData()
        # self.s.proxies.update({'http': 'http://127.0.0.1:8080','https': 'http://127.0.0.1:8080',})
        # self.set_proxy('127.0.0.1:8080')

    def set_proxy(self, proxy):
        # noinspection HttpUrlsUsage
        tmp = 'http://' + proxy
        self.s.proxies.update({'http': tmp, 'https': tmp})

    def __rpc(self, method: str, prms: dict, current_iv=None):
        return self.__call_api(
            'rpc', {
                "rpc": {
                    "jsonrpc": "2.0",
                    "id": self.rndid(),
                    "prms": json.dumps(prms, separators=(',', ':')),
                    "method": method
                }
            }, current_iv=current_iv)

    def __call_api(self, url: str, data=None, current_iv=None):
        if self.o.wait >= 1:
            time.sleep(self.o.wait)

        if current_iv is None:
            current_iv = self.c.randomiv()

        self._set_headers(url, current_iv)
        if data is None:
            r = self.s.get(self.o.main_url + url)
        else:
            if data != '':
                cdata = self.c.encrypt(data, current_iv)
            else:
                cdata = data
            r = self.s.post(self.o.main_url + url, data=cdata)
        if 'X-Crypt-Iv' not in r.headers:
            r_method = data['rpc']['method'] if 'rpc' in data else url
            Logger.error('request: "%s" was missing iv!' % r_method)
            exit(1)
            return None
        res = self.c.decrypt(base64.b64encode(r.content), r.headers['X-Crypt-Iv'])
        if 'title' in res and 'Maintenance' in res['title']:
            Logger.info(res['content'])
            exit(1)
        if 'api_error' in res:
            if 'code' in res['api_error'] and res['api_error']['code'] == 30005:
                Logger.info(res['api_error'])
                if self.o.use_potions:
                    rr = self.item_use(use_item_id=301, use_item_num=1)
                    if 'api_error' in rr and rr['api_error']['code'] == 12009:
                        return None
                    return self.__call_api(url, data)
                else:
                    Logger.info('Potion usage disabled. Exiting...')
                    sys.exit()
            else:
                r_method = data['rpc']['method'] if 'rpc' in data else url
                if 'trophy' not in r:
                    Logger.error('request: "%s" server returned error: %s' % (r_method, res['api_error']['message']))
                # exit(1)
        if 'password' in res:
            self.o.password = res['password']
            self.o.uuid = res['uuid']
            Logger.info('found password:%s uuid:%s' % (self.o.password, self.o.uuid))
        if 'result' in res and 'newest_resource_version' in res['result']:
            self.o.newest_resource_version = res['result']['newest_resource_version']
            Logger.info('found resouce:%s' % self.o.newest_resource_version)
        if 'fuji_key' in res:
            if sys.version_info >= (3, 0):
                self.c.key = bytes(res['fuji_key'], encoding='utf8')
            else:
                self.c.key = bytes(res['fuji_key'])
            self.o.session_id = res['session_id']
            Logger.info('found fuji_key:%s' % self.c.key)
        if 'result' in res and 't_player_id' in res['result']:
            if 'player_rank' in res['result']:
                Logger.info(
                    't_player_id:%s player_rank:%s' % (res['result']['t_player_id'], res['result']['player_rank']))
            self.o.pid = res['result']['t_player_id']
        if 'result' in res and 'after_t_status' in res['result']:
            self.o.current_ap = int(res['result']['after_t_status']['act'])
            Logger.info('%s / %s rank:%s' % (
                res['result']['after_t_status']['act'], res['result']['after_t_status']['act_max'],
                res['result']['after_t_status']['rank']))
        if 'result' in res and 't_innocent_id' in res['result']:
            if res['result']['t_innocent_id'] != 0:
                Logger.info('t_innocent_id:%s' % (res['result']['t_innocent_id']))
                status = 0
                while status == 0:
                    status = self.item_world_persuasion()
                    Logger.info('status:%s' % status)
                    status = status['result']['after_t_innocent']['status']
        return res

    def _set_headers(self, url: str, iv: str):
        i = head[url] if url in head else None
        self.s.headers.clear()

        if i == 0:
            if self.o.region == 2:
                self.s.headers.update({
                    'X-Unity-Version': '2018.4.3f1',
                    'Accept-Language': 'en-us',
                    'X_CHANNEL': '1',
                    'Content-Type': 'application/x-haut-hoiski',
                    'User-Agent': 'en/17 CFNetwork/1206 Darwin/20.1.0',
                    'X-OS-TYPE': '1',
                    'X-APP-VERSION': self.o.version,
                    'X-Crypt-Iv': iv,
                    'Accept': '*/*'
                })
            else:
                self.s.headers.update({
                    'X-PERF-SCENE-TIME': '8619',
                    'X-PERF-APP-BUILD-NUMBER': '0',
                    'X-PERF-NETWORK-REQ-LAST': '1',
                    'X-PERF-DISC-FREE': '5395',
                    'X-PERF-FPS-LAST-MED': '59.99',
                    'X-APP-VERSION': self.o.version,
                    'X-PERF-OS-VERSION': 'iOS 14.2',
                    'X-PERF-CPU-SYS': '0',
                    'X-PERF-CPU-USER': '40.79',
                    'X-PERF-BUTTERY': '100',
                    'X-PERF-SCENE-TRACE':
                        'startup_scene,title_scene,startup_scene,title_scene',
                    'X-PERF-NETWORK-ERR-LAST': '0',
                    'X-PERF-NETWORK-REQ-TOTAL': '1',
                    'X-PERF-CPU-IDLE': '59.21',
                    'X-PERF-APP-VERSION': '2.11.2',
                    'X-PERF-FPS-LAST-AVG': '59.23',
                    'User-Agent':
                        'forwardworks/194 CFNetwork/1206 Darwin/20.1.0',
                    'X-PERF-MEM-USER': '1624',
                    'X-PERF-LAUNCH-TIME': '20210408T15:50:36Z',
                    'X-PERF-SCENE': 'title_scene',
                    'X-PERF-FPS': '59.99',
                    'X-Crypt-Iv': iv,
                    'X-PERF-MEM-AVAILABLE': '24',
                    'X-OS-TYPE': str(self.o.device),
                    'X-PERF-LAST-DELTA-TIMES': '16,17,16,17,21,13,16,17,17,17',
                    'X-PERF-NETWORK-ERR-TOTAL': '0',
                    'X-PERF-DEVICE': 'iPad7,5',
                    'Content-Type': 'application/x-haut-hoiski',
                    'X-PERF-OS': 'iOS 14.2',
                    'X-PERF-MEM-PYSIC': '1981',
                    'X-Unity-Version': '2018.4.20f1',
                    'X-PERF-TIME': '20210408T15:52:43Z',
                    'X-PERF-APP-ID': 'com.disgaearpg.forwardworks',
                    'X-PERF-LAUNCH-DURATION': '70363'
                })
        elif i == 1:
            if self.o.region == 2:
                self.s.headers.update({
                    'X-Unity-Version': '2018.4.3f1',
                    'X-Crypt-Iv': iv,
                    'Accept-Language': 'en-us',
                    'X_CHANNEL': '1',
                    'Content-Type': 'application/x-haut-hoiski',
                    'User-Agent': 'en/17 CFNetwork/1206 Darwin/20.1.0',
                    'X-OS-TYPE': '1',
                    'X-APP-VERSION': self.o.version
                })
            else:
                self.s.headers.update({
                    'X-Unity-Version': '2018.4.20f1',
                    'X-Crypt-Iv': iv,
                    'Accept-Language': 'en-us',
                    'Content-Type': 'application/x-haut-hoiski',
                    'User-Agent':
                        'forwardworks/194 CFNetwork/1206 Darwin/20.1.0',
                    'X-OS-TYPE': str(self.o.device),
                    'X-APP-VERSION': self.o.version
                })
        elif i == 2:
            self.s.headers.update({
                'X-Unity-Version': '2018.4.20f1',
                'X-Crypt-Iv': iv,
                'Accept-Language': 'en-us',
                'Content-Type': 'application/x-haut-hoiski',
                'User-Agent': 'iPad6Gen/iOS 14.2',
                'X-OS-TYPE': str(self.o.device),
                'X-APP-VERSION': self.o.version,
                'X-SESSION': self.o.session_id
            })
        else:
            self.s.headers.update({
                'X-Unity-Version': '2018.4.20f1',
                'X-Crypt-Iv': iv,
                'Accept-Language': 'en-us',
                'Content-Type': 'application/x-haut-hoiski',
                'User-Agent': 'forwardworks/194 CFNetwork/1206 Darwin/20.1.0',
                'X-OS-TYPE': str(self.o.device),
                'X-APP-VERSION': self.o.version
            })

    # noinspection SpellCheckingInspection
    def rndid(self):
        return self.c.rndid()

    def auto_login(self):
        account = os.getenv('DRPG_EMAIL')
        password = os.getenv('DRPG_PASS')
        sign = os.getenv('DRPG_SIGN')
        # noinspection DuplicatedCode
        request_id = str(uuid.uuid4())

        default_headers = {
            "Host": "p-public.service.boltrend.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "launcherId": "287",
            "lang": "en",
            "Origin": "https://p-public.service.boltrend.com"
        }

        r = requests.post(
            "https://p-public.service.boltrend.com/webapi/upc/user/authLogin",
            json.dumps({
                "appId": "287",
                "account": account,
                "password": password,
                "channel": 3,
                "captchaId": "", "validate": "", "sourceId": "",
                "sign": sign
            }),
            params={
                "requestid": request_id
            },
            headers=default_headers
        )

        if r.status_code != 200:
            Logger.error("Unable to perform authLogin")
            return

        d = json.loads(r.content)
        auth_ticket = d['data']['ticket']
        user_id = d['data']['userId']

        r = requests.post(
            "https://p-public.service.boltrend.com/webapi/npl-public/user/gameAuth",
            json.dumps({
                "launcherId": "287",
                "pubId": "287",
                "userId": user_id,
                "signature": "d1020d508cb737c56ac9d4d0ea991ec58468d102",
                "ticket": auth_ticket
            }),
            params={
                "requestid": request_id
            },
            headers=default_headers
        )
        if r.status_code != 200:
            Logger.error("Unable to perform gameAuth")
            return

        d = json.loads(r.content)

        self.o.sess = request_id
        self.o.uin = user_id
        return d['data']['ticket']

    def login(self):
        if self.o.region == 1 or hasattr(self, 'isReroll'):
            data = self.__call_api('login', {
                "password": self.o.password,
                "uuid": self.o.uuid
            })
        else:
            if self.o.platform == 'Steam':
                # Auto login
                if os.getenv('STEAM_LOGIN', '') == 'true':
                    ticket = self.auto_login()
                    Logger.info('Successfully auto logged in')
                    data = self.__call_api('steam/login', {'openId': self.o.uin, 'ticket': ticket})
                else:
                    data = self.__call_api('steam/login', {'openId': Constants.user_id, 'ticket': Constants.ticket})
            else:
                data = self.__call_api(
                    'sdk/login', {
                        "platform": self.o.platform,
                        "sess": self.o.sess,
                        "sdk": "BC4D6C8AE94230CC",
                        "region": "non_mainland",
                        "uin": self.o.uin
                    })
        return data

    def common_battle_result_jwt(self, iv, mission_status: str = '',
                                 killed_character_num: int = 0, steal_hl_num: int = 0,
                                 command_count: int = 1):
        data = {
            "hfbm784khk2639pf": mission_status,
            # max_once_damage
            "ypb282uttzz762wx": 9621642,
            # total_receive_damage
            "dppcbew9mz8cuwwn": 1572605948,
            "zacsv6jev4iwzjzm": killed_character_num,
            "kyqyni3nnm3i2aqa": 0,
            "echm6thtzcj4ytyt": 0,
            # steal_hl_num
            "ekusvapgppik35jj": steal_hl_num,
            # command_count
            "xa5e322mgej4f4yq": command_count
        }
        return jwt.encode(data, iv, algorithm="HS256")

    # Start API CALLS
    ####################

    #################
    # Trophy Endpoints
    #################

    def trophy_get_reward_daily(self, receive_all: int = 1, _id: int = 0):
        return self.__rpc('trophy/get_reward_daily', {"receive_all": receive_all, "id": _id})

    def trophy_get_reward_weekly(self, receive_all: int = 1, _id: int = 0):
        return self.__rpc('trophy/get_reward_weekly', {"receive_all": receive_all, "id": _id})

    def trophy_get_reward(self, receive_all: int = 1, _id: int = 0):
        return self.__rpc('trophy/get_reward', {"receive_all": receive_all, "id": _id})

    def trophy_get_reward_repetition(self, receive_all: int = 1, _id: int = 0):
        return self.__rpc('trophy/get_reward_repetition', {"receive_all": receive_all, "id": _id})

    def trophy_daily_requests(self):
        return self.__rpc('trophy/daily_requests', {})

    def trophy_character_missions(self, m_character_ids, updated_at):
        return self.__rpc('trophy/character_missions', {"m_character_ids": m_character_ids, "updated_at": updated_at})

    # Get rewards from etna resorts
    def trophy_get_reward_daily_request(self):
        # trophy/get_reward_daily_request
        return self.__rpc("trophy/get_reward_daily_request", {'receive_all': 1, 'id': 0})

    def trophy_beginner_missions(self, sheet_type=None):
        return self.__rpc('trophy/beginner_missions', {} if sheet_type is None else {'sheet_type': sheet_type})

    #################
    # Battle Endpoints
    #################

    def battle_status(self):
        return self.__rpc('battle/status', {})

    def battle_help_list(self):
        return self.__rpc('battle/help_list', {})

    def battle_skip_parties(self):
        return self.__rpc('battle/skip_parties', {})

    def battle_start(self, m_stage_id, help_t_player_id=None, help_t_character_id=0, act=0, help_t_character_lv=0,
                     deck_no=1, reincarnation_character_ids=[], raid_status_id=0, character_ids=None, memory_ids=[]):
        if help_t_player_id is None:
            help_t_player_id = []

        prms = {
            "t_deck_no": deck_no, "m_stage_id": m_stage_id,
            "m_guest_character_id": 0, "help_t_player_id": help_t_player_id,
            "t_raid_status_id": raid_status_id,
            "auto_rebirth_t_character_ids": reincarnation_character_ids,
            "act": act,
            "help_t_character_id": help_t_character_id,
            "help_t_character_lv": help_t_character_lv,
        }

        if len(memory_ids) >= 1:
            while len(memory_ids) < 5:
                memory_ids.append(0)
            prms['t_memory_ids'] = memory_ids

        if character_ids is not None:
            prms["t_character_ids"] = character_ids

        return self.__rpc('battle/start', prms)

    def battle_end(self, m_stage_id, battle_type, result=0, battle_exp_data=[], equipment_id: int = 0,
                   equipment_type: int = 0, m_tower_no: int = 0,
                   raid_status_id: int = 0, raid_battle_result: str = '',
                   skip_party_update_flg: bool = True, common_battle_result=None,
                   division_battle_result: str = None,
                   current_iv=None
                   ):

        if common_battle_result is None:
            common_battle_result = self.o.common_battle_result

        if raid_battle_result != '':
            prms = {
                "m_stage_id": m_stage_id,
                "m_tower_no": m_tower_no,
                "equipment_id": equipment_id,
                "equipment_type": equipment_type,
                "innocent_dead_flg": 0,
                "t_raid_status_id": raid_status_id,
                "raid_battle_result": raid_battle_result,
                "m_character_id": 0,
                "division_battle_result": "",
                "battle_type": battle_type,
                "result": result,
                "battle_exp_data": battle_exp_data,
                "common_battle_result": common_battle_result,
                "skip_party_update_flg": skip_party_update_flg,
            }
        else:
            prms = {
                "battle_exp_data": battle_exp_data,
                "equipment_type": equipment_type,
                "m_tower_no": m_tower_no,
                "raid_battle_result": raid_battle_result,
                "m_stage_id": m_stage_id,
                "equipment_id": equipment_id,
                "t_raid_status_id": 0,
                "battle_type": battle_type,
                "result": result,
                "innocent_dead_flg": 0,
                "skip_party_update_flg": skip_party_update_flg,
                "common_battle_result": common_battle_result,
            }

        if division_battle_result is not None:
            prms['division_battle_result'] = division_battle_result

        return self.__rpc('battle/end', prms, current_iv=current_iv)

    def battle_story(self, m_stage_id):
        return self.__rpc('battle/story', {"m_stage_id": m_stage_id})

    def axel_context_battle_end(self, m_character_id, battle_exp_data, common_battle_result: str = ''):
        return self.__rpc('battle/end', {
            "m_stage_id": 0,
            "m_tower_no": 0,
            "equipment_id": 0,
            "equipment_type": 0,
            "innocent_dead_flg": 0,
            "t_raid_status_id": 0,
            "raid_battle_result": "",
            "m_character_id": m_character_id,
            "division_battle_result": "",
            "battle_type": 7,
            "result": 1,
            "battle_exp_data": battle_exp_data,
            "common_battle_result": common_battle_result,
            "skip_party_update_flg": True
        })

    def battle_skip(self, m_stage_id, deck_no: int, skip_number: int, helper_player, reincarnation_character_ids=[]):

        stage = self.gd.get_stage(m_stage_id)
        return self.__rpc('battle/skip', {
            "m_stage_id": m_stage_id,
            "help_t_player_id": helper_player['t_player_id'],
            "help_t_character_id": helper_player['t_character']['id'],
            "help_t_character_lv": helper_player['t_character']['lv'],
            "t_deck_no": deck_no,
            "m_guest_character_id": 0,
            "t_character_ids": [],
            "skip_num": skip_number,
            "battle_type": 3,  # needs to be tested. It was an exp gate
            "act": stage['act'] * skip_number,
            "auto_rebirth_t_character_ids": reincarnation_character_ids,
            "t_memery_ids": []  # pass parameters?
        })

    def battle_skip_stages(self, m_stage_ids, deck_no: int, skip_number: int, helper_player, reincarnation_character_ids=[]):

        # calculate ap usage. Every stage is skipped 3 times
        act = 0
        for m_stage_id in m_stage_ids:
            stage = self.gd.get_stage(m_stage_id)
            act = act + (stage['act'] * skip_number)

        return self.__rpc('battle/skip_stages', {
            "m_stage_id": 0,
            "help_t_player_id": helper_player['t_player_id'],
            "help_t_character_id": helper_player['t_character']['id'],
            "help_t_character_lv": helper_player['t_character']['lv'],
            "t_deck_no": deck_no,
            "m_guest_character_id": 0,
            "t_character_ids": [],
            "skip_num": 0,
            "battle_type": 3,  # needs to be tested. It was an exp gate
            "act": act,
            "auto_rebirth_t_character_ids": reincarnation_character_ids,
            "t_memery_ids": [],  # pass parameters?
            "m_stage_ids": m_stage_ids
        })


    def pvp_battle_give_up(self):
        return self.__rpc('battle/end', {
            "m_stage_id": 0,
            "m_tower_no": 0,
            "equipment_id": 0,
            "equipment_type": 0,
            "innocent_dead_flg": 0,
            "t_raid_status_id": 0,
            "raid_battle_result": "",
            "m_character_id": 0,
            "division_battle_result": "",
            "arena_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJUeDJFQk5oWmNGNFlkOUIyIjoxNzQ1LCJSZzhQandZQlc3ZHNKdnVrIjo1LCJKNWdtVHA3WXI0SFU4dUFOIjpbXX0.oXH33OXjnaK18IcCpSR4MzrruG7mRg1G1GWLhdaaP8U",
            "battle_type": 9,
            "result": 0,
            "battle_exp_data": [],
            "common_battle_result": "eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MCwiZHBwY2JldzltejhjdXd3biI6MCwiemFjc3Y2amV2NGl3emp6bSI6MCwia3lxeW5pM25ubTNpMmFxYSI6MCwiZWNobTZ0aHR6Y2o0eXR5dCI6MCwiZWt1c3ZhcGdwcGlrMzVqaiI6MCwieGE1ZTMyMm1nZWo0ZjR5cSI6MH0.9DYl6QK2TkTIq81M98itbAqafdUE4nIPTYB_pp_NTd4",
            "skip_party_update_flg": True
        })




    #################
    # Raid Endpoints
    #################

    def raid_send_help_request(self, raid_id):
        return self.__rpc('raid/help', {"t_raid_status_id": raid_id})

    def raid_index(self):
        return self.__rpc('raid/index', {})

    def raid_ranking(self, raid_ID = Constants.Current_Raid_ID):
        data = self.__rpc('raid/ranking', {"m_event_id":raid_ID,"m_raid_boss_kind_id":0})
        return data
    
    def raid_ranking_player(self, t_player_id, raid_ID = Constants.Current_Raid_ID):
        data = self.rpc('raid/ranking_player', {"m_raid_id":raid_ID,"m_raid_boss_kind_id":0,"t_player_id":t_player_id})
        return data

    def raid_ranking_reward(self):
        return self.__rpc('raid/ranking_reward', {})

    def raid_give_up_boss(self, t_raid_status_id):
        return self.__rpc('raid/give_up', {"t_raid_status_id": t_raid_status_id})

    def raid_current(self):
        return self.__rpc('raid/current', {})

    def raid_history(self, raidID=Constants.Current_Raid_ID):
        return self.__rpc('raid/history', {"m_event_id": raidID})

    # reward for a specific boss battle
    def raid_reward(self, t_raid_status_id):
        return self.__rpc('raid/reward', {"t_raid_status_id": t_raid_status_id})

    def raid_gacha(self, m_event_gacha_id, lottery_num):
        return self.__rpc('event/gacha_do', {"m_event_gacha_id": m_event_gacha_id, "lottery_num": lottery_num})

    def raid_update(self, m_raid_boss_id, step):
        return self.__rpc('raid_boss/update', {"m_raid_boss_id": m_raid_boss_id, "step": step})

    def raid_exchange_surplus_points(self, points_to_exchange):
        data = self.__rpc('event/exchange_surplus_point',
                          {"m_event_id": Constants.Current_Raid_ID, "exchange_count": points_to_exchange})
        return data

    def raid_event_missions(self):
        return self.__rpc('event/missions', {"m_event_id":Constants.Current_Raid_ID})

    #################
    # Gacha Endpoints
    #################

    def gacha_available(self):
        return self.__rpc('gacha/available', {})

    def gacha_do(self, is_gacha_free, price, item_type, num, m_gacha_id, item_id, total_draw_count):
        return self.__rpc('gacha/do',
                          {"is_gacha_free": is_gacha_free, "price": price, "item_type": item_type, "num": num,
                           "m_gacha_id": m_gacha_id, "item_id": item_id, "total_draw_count": total_draw_count})

    def gacha_sums(self):
        return self.__rpc('gacha/sums', {})

    #################
    # Player Endpoints
    #################

    def player_sync(self):
        return self.__rpc('player/sync', {})

    def player_tutorial_gacha_single(self):
        return self.__rpc('player/tutorial_gacha_single', {})

    def player_tutorial_choice_characters(self):
        return self.__rpc('player/tutorial_choice_characters', {})

    def player_characters(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/characters', {
            "updated_at": updated_at,
            "page": page
        })

    def player_character_collections(self):
        return self.__rpc('player/character_collections', {})

    def player_weapons(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/weapons', {
            "updated_at": updated_at,
            "page": page
        })

    def player_weapon_effects(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/weapon_effects', {"updated_at": updated_at, "page": page})

    def player_equipments(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/equipments', {
            "updated_at": updated_at,
            "page": page
        })

    def player_equipment_effects(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/equipment_effects', {"updated_at": updated_at, "page": page})

    def player_equipment_decks(self, updated_at: int = 0, page: int = 1):
        data=self.__rpc('player/equipment_decks',{"updated_at": updated_at, "page": page})
        return data

    def player_innocents(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/innocents', {"updated_at": updated_at, "page": page})

    def player_clear_stages(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/clear_stages', {"updated_at": updated_at, "page": page})

    def player_stage_missions(self, updated_at: int, page: int):
        return self.__rpc('player/stage_missions', {"updated_at": updated_at, "page": page})

    def player_index(self):
        return self.__rpc('player/index', {})

    def player_agendas(self):
        return self.__rpc('player/agendas', {})

    def player_boosts(self):
        return self.__rpc('player/boosts', {})

    def player_decks(self):
        return self.__rpc('player/decks', {})

    def player_home_customizes(self):
        return self.__rpc('player/home_customizes', {})

    def player_items(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/items', {"updated_at": updated_at, "page": page})

    def player_stone_sum(self):
        return self.__rpc('player/stone_sum', {})

    def player_sub_tutorials(self):
        return self.__rpc('player/sub_tutorials', {})

    def player_gates(self):
        return self.__rpc('player/gates', {})

    def player_character_mana_potions(self):
        return self.__rpc('player/character_mana_potions', {})

    def player_tutorial(self, chara_id_list=None, step=None, chara_rarity_list=None, name=None, gacha_fix=None):
        if chara_id_list is None:
            data = self.__rpc('player/tutorial', {})
        else:
            data = self.__rpc('player/tutorial',
                              {"charaIdList": chara_id_list, "step": step, "charaRarityList": chara_rarity_list,
                               "name": name, "gacha_fix": gacha_fix})
        return data

    def player_update_device_token(self, device_token: str = ''):
        return self.__rpc('player/update_device_token',
                          {"device_token": device_token})

    def player_add(self):
        return self.__rpc('player/add', {})

    def player_badge_homes(self):
        return self.__rpc('player/badge_homes', {})

    def player_badges(self):
        return self.__rpc('player/badges', {})

    def player_update_equip_detail(self, e: dict, innocents: List[int] = []):
        equip_type = 1 if 'm_weapon_id' in e else 2
        return self.__rpc("player/update_equip_detail", {
            't_equip_id': e['id'],
            'equip_type': equip_type,
            'lock_flg': e['lock_flg'],
            'innocent_auto_obey_flg': e['innocent_auto_obey_flg'],
            'change_innocent_list': innocents
        })

    # {"deck_data":
    # {"selectDeckNo":4,
    # "charaIdList":["","","","","","","","",""], # example of each array "184027719,181611027,0,0,0"
    # "names":["","","","","","","","",""], # "Party 1","Party 2",.....
    # "t_memory_ids_list":["","","","","","","","",""] # 0,0,0,0,0
    # }}
    def player_update_deck(self, deck_data):
        data = self.__rpc('player/update_deck', {"deck_data": deck_data})
        return data

    #################
    # Kingdom Endpoints
    #################

    def kingdom_entries(self):
        return self.__rpc('kingdom/entries', {})

    def kingdom_weapon_equipment_entry(self, weap_ids: List[int] = [], equip_ids: List[int] = []):
        return self.__rpc("kingdom/weapon_equipment_entry", {'t_weapon_ids': weap_ids, 't_equipment_ids': equip_ids})

    def kingdom_innocent_entry(self, innocent_ids: List[int] = []):
        return self.__rpc("kingdom/innocent_entry", {'t_innocent_ids': innocent_ids})

    def etna_resort_refine(self, item_type, _id):
        return self.__rpc('weapon_equipment/rarity_up', {"item_type": item_type, "id": _id})

    def etna_resort_remake(self, item_type, id):
        data = self.__rpc('weapon_equipment/remake', {"item_type": item_type, "id": id})
        return data

    def etna_resort_add_alchemy_effects(self, item_type, id):
        data = self.__rpc('weapon_equipment/add_effects', {"item_type": item_type, "id": id})
        return data

    def etna_resort_reroll_alchemy_effect(self, item_type, item_id, place_no):
        data = self.__rpc('weapon_equipment/update_effect_lottery',
                          {"item_type": item_type, "id": item_id, "place_no": place_no})
        return data

    def etna_resort_lock_alchemy_effect(self, lock_flg: bool, t_weapon_effect_id=0, t_equipment_effect_id=0):
        data = self.__rpc('weapon_equipment/lock_effect',
                          {"t_weapon_effect_id": t_weapon_effect_id, "t_equipment_effect_id": t_equipment_effect_id,
                           "lock_flg": lock_flg})
        return data

    def etna_resort_update_alchemy_effect(self, overwrite: bool):
        data = self.__rpc('weapon_equipment/update_effect', {"overwrite":overwrite})
        return data

    #################
    # Shop Endpoints
    #################

    def shop_equipment_items(self):
        return self.__rpc('shop/equipment_items', {})

    def shop_equipment_shop(self):
        return self.__rpc('shop/equipment_shop', {})

    def shop_buy_equipment(self, item_type: int, itemid: List[int]):
        return self.__rpc('shop/buy_equipment', {"item_type": item_type, "ids": itemid})

    def shop_buy_item(self, itemid: int, quantity: int):
        return self.__rpc('shop/buy_item', {"id": itemid, "quantity": quantity})

    def shop_sell_item(self, item_ids: list[int], quantities: list[int]):
        return self.__rpc('item/sell', {"m_item_ids":item_ids,"item_nums":quantities})

    def shop_sell_equipment(self, sell_equipments):
        return self.__rpc('shop/sell_equipment', {"sell_equipments": sell_equipments})

    def shop_change_equipment_items(self, shop_rank: int = 32):
        update_number = self.shop_equipment_shop()['result']['lineup_update_num']
        if update_number < 5:
            data = self.__rpc('shop/change_equipment_items', {"shop_rank": shop_rank})
        else:
            Logger.warn('Free refreshes used up already')
            data = {}
        return data

    def shop_gacha(self):
        return self.__rpc('shop/garapon', {"m_garapon_id": 1})

    def shop_index(self):
        return self.__rpc('shop/index', {})

    #################
    # Friend Endpoints
    #################

    def friend_index(self):
        return self.__rpc('friend/index', {})

    def friend_send_act(self, target_t_player_id: int = 0):
        return self.__rpc('friend/send_act', {"target_t_player_id": target_t_player_id})

    def friend_receive_act(self, target_t_player_id: int = 0):
        return self.__rpc('friend/receive_act', {"target_t_player_id": target_t_player_id})

    def friend_send_sardines(self):
        data = self.__rpc('friend/send_act', {"target_t_player_id": 0})
        if data['error'] == 'You cannot send more sardine.':
            return data['error']
        Logger.info(f"Sent sardines to {data['result']['send_count_total']} friends")

    def friend_send_request(self, target_t_player_id):
        return self.__rpc('friend/send_request', {"target_t_player_id":target_t_player_id})

    # Use only one of the search params
    def friend_search(self, public_id:str='', name:str='', rank:int=0):
        return self.__rpc('friend/search', {"public_id":public_id,"name":name,"rank":rank})

    #################
    # Bingo Endpoints
    #################

    def bingo_index(self, bingo_id=Constants.Current_Bingo_ID):
        return self.__rpc('bingo/index', {"id": bingo_id})

    def bingo_lottery(self, bingo_id=Constants.Current_Bingo_ID, use_stone=False):
        return self.__rpc('bingo/lottery', {"id": bingo_id, "use_stone": use_stone})

    # ids takes an array like [57]
    def bingo_receive_reward(self, reward_id):
        return self.__rpc('bingo/receive', {"ids": reward_id})

    #################
    # Breeding Center Endpoints
    #################

    def breeding_center_list(self):
        return self.__rpc('breeding_center/list', {})

    # takes arrays with ids for weapons and equips to retrieve from ER Deposit
    def breeding_center_pick_up(self, t_weapon_ids, t_equipment_ids):
        return self.__rpc('breeding_center/pick_up', {"t_weapon_ids": t_weapon_ids, "t_equipment_ids": t_equipment_ids})

    # takes arrays with ids for weapons and equips to add to ER Deposit
    def breeding_center_entrust(self, t_weapon_ids, t_equipment_ids):
        return self.__rpc('breeding_center/entrust', {"t_weapon_ids": t_weapon_ids, "t_equipment_ids": t_equipment_ids})

    #################
    # Survey Endpoints
    #################

    def survey_index(self):
        return self.__rpc('survey/index', {})

    def survey_start(self, m_survey_id, hour, t_character_ids, auto_rebirth_t_character_ids=[]):
        return self.__rpc('survey/start', {"m_survey_id": m_survey_id, "hour": hour, "t_character_ids": t_character_ids,
                                           "auto_rebirth_t_character_ids": auto_rebirth_t_character_ids})

    def survey_end(self, m_survey_id, cancel):
        return self.__rpc('survey/end', {"m_survey_id": m_survey_id, "cancel": cancel})

    # bribe data [{"m_item_id":401,"num":4}]
    def survey_use_bribe_item(self, m_survey_id, bribe_data):
        return self.__rpc('survey/use_bribe_item', {"m_survey_id": m_survey_id, "bribe_data": bribe_data})

    #################
    # Trial Endpoints
    #################

    def trial_index(self):
        data = self.__rpc('division/index', {})
        return data

    def trial_ranking(self, m_division_battle_id):
        data = self.__rpc('division/ranking', {"m_division_battle_id":m_division_battle_id})
        return data


    # "result": {
    #   "after_t_division_battle_status": {
    #     "id": 7929,
    #     "t_player_id": 136974,
    #     "m_division_battle_id": 2,
    #     "m_stage_id": 0,
    #     "t_memory_ids": [],
    #     "killed_t_character_ids": [],
    #     "current_battle_count": 0,
    #     "current_turn_count": 0,
    #     "current_max_damage_rate": 0,
    #     "boss_hp": 0
    #   }
    # }
    def trial_reset(self, division_battle_id):
        return self.__rpc('division/reset', {"m_division_battle_id": division_battle_id})

    #################
    # Item World Survey Endpoints
    #################

    def item_world_survey_index(self):
        data = self.__rpc('item_world_survey/index', {})
        return data

    def item_world_survey_start(self, t_weapon_ids: List[int] = [], t_equipment_ids: List[int] = []):
        data = self.__rpc('item_world_survey/start', {"t_weapon_ids": t_weapon_ids, "t_equipment_ids": t_equipment_ids})
        return data

    def item_world_survey_end(self, t_weapon_ids: List[int] = [], t_equipment_ids: List[int] = [],
                              cancel: bool = False):
        data = self.__rpc('item_world_survey/end',
                          {"t_weapon_ids": t_weapon_ids, "t_equipment_ids": t_equipment_ids, "cancel": cancel})
        return data

    ##########################
    # Dark Assembly endpoints
    #########################

    def agenda_index(self,):
        return self.__rpc('agenda/index', {})

    def agenda_get_boost(self,):
        return self.__rpc('agenda/get_boost_agenda', {})

    def agenda_get_campaign(self,):
        return self.__rpc('agenda/get_agenda_campaign', {})

    # m_agenda_id: 28 for renaming generic characters
    def agenda_start(self, m_agenda_id):
        return self.__rpc('agenda/lowmaker_details', {"m_agenda_id": m_agenda_id})

    # [{"lowmaker_id":26776096,"item_id":402,"num":1},{"lowmaker_id":26776096,"item_id":401,"num":1}]
    def agenda_vote(self, m_agenda_id, bribe_data):
        return self.__rpc('agenda/vote', {"m_agenda_id": m_agenda_id, "bribe_data": bribe_data})

    #################
    # Misc Endpoints
    #################

    def login_update(self):
        return self.__rpc('login/update', {})

    def version_check(self):
        return self.__call_api('version_check', None)

    def signup(self):
        return self.__call_api('signup', '')

    def passport_index(self):
        return self.__rpc('passport/index', {})

    def sub_tutorial_read(self, m_sub_tutorial_id: int):
        return self.__rpc('sub_tutorial/read', {"m_sub_tutorial_id": m_sub_tutorial_id})

    def boltrend_exchange_code(self, code: str):
        return self.__rpc('boltrend/exchange_code', {"code": code})

    def app_constants(self):
        return self.__rpc('app/constants', {})

    def system_version_manage(self):
        return self.__rpc('system/version_manage', {})

    def present_history(self):
        return self.__rpc('present/history', {})

    def present_index(self, is_limit_notice=None, conditions=None, order=None):
        if is_limit_notice is not None:
            data = self.__rpc('present/index', {"is_limit_notice": is_limit_notice})
        else:
            data = self.__rpc('present/index', {"conditions": conditions, "order": order})
        return data

    def present_receive(self, receive_ids, conditions, order):
        return self.__rpc('present/receive', {"receive_ids": receive_ids, "conditions": conditions, "order": order})

    def adjust_add(self, event_id: int):
        return self.__rpc('adjust/add', {"event_id": event_id})

    def event_index(self, event_ids=None):
        if event_ids is None:
            return self.__rpc('event/index', {})
        else:
            return self.__rpc('event/index', {"m_event_ids": event_ids})

    def stage_boost_index(self):
        return self.__rpc('stage_boost/index', {})

    def information_popup(self):
        return self.__rpc('information/popup', {})

    def potential_current(self):
        return self.__rpc('potential/current', {})

    def potential_conditions(self):
        return self.__rpc('potential/conditions', {})

    def character_boosts(self):
        return self.__rpc('character/boosts', {})

    def update_admin_flg(self):
        return self.__rpc('debug/update_admin_flg', {})

    def weapon_equipment_update_effect_unconfirmed(self):
        return self.__rpc('weapon_equipment/update_effect_unconfirmed', {})

    def system_version_update(self):
        return self.__rpc('system/version_update', {
            "app_version": self.o.version,
            "resouce_version": self.o.newest_resource_version,
            "database_version": "0"
        })

    def memory_index(self):
        return self.__rpc('memory/index', {})

    def item_world_persuasion(self):
        return self.__rpc('item_world/persuasion', {})

    def item_world_start(self, equipment_id: int, equipment_type: int, deck_no: int, reincarnation_character_ids=[]):

        return self.__rpc('item_world/start', {
            "equipment_type": equipment_type,
            "t_deck_no": deck_no,
            "equipment_id": equipment_id,
            "auto_rebirth_t_character_ids": reincarnation_character_ids,
        })

    def item_use(self, use_item_id: int, use_item_num: int):
        return self.__rpc('item/use', {"use_item_id": use_item_id, "use_item_num": use_item_num})

    def item_use_gate_key(self, m_area_id, m_stage_id):
        data = self.__rpc('item/use_gate', {"m_area_id": m_area_id, "m_stage_id": m_stage_id, "m_item_id": 1401})
        return data

    def tower_start(self, m_tower_no: int, deck_no: int = 1):
        return self.__rpc('tower/start', {"t_deck_no": deck_no, "m_tower_no": m_tower_no})

    def axel_context_battle_start(self, act, m_character_id: int, t_character_ids):
        return self.__rpc('character_contest/start',
                          {"act": act, "m_character_id": m_character_id, "t_character_ids": t_character_ids})

    def apply_equipment_preset_to_team(self, team_number, equipment_preset):
        data = self.__rpc('weapon_equipment/change_deck_equipments', {"deck_no":team_number,"equipment_deck_no":equipment_preset})
        return data 

    # Sample consume data "consume_t_items":[{"m_item_id":4000001,"num":432},{"m_item_id":101,"num":580000}]
    def dispatch_prinny_from_prinny_prison(self, consume_item_data, dispatch_rarity, dispatch_num):
        data = self.__rpc('prison/shipment', {"consume_t_items":consume_item_data,"m_character_id":30001,"rarity":dispatch_rarity,"shipping_num":dispatch_num})
        return data 

    ## Use to get characters from gate events when enough shard are received
    def event_receive_rewards(self, event_id: int):
        return self.__rpc('event/receive_item_rewards', {"m_event_id":event_id})

    #########################
    # Innocent endpoints
    #########################
    
    def innocent_remove_all(self, ids, cost: int = 0):
        return self.__rpc("innocent/remove_all", {"t_innocent_ids": ids, "cost": cost})

    def innocent_training(self, t_innocent_id):
        return self.__rpc('innocent/training', {"t_innocent_id": t_innocent_id})

    def innocent_combine(self, m_innocent_recipe_id: int, t_innocent_ids: List[int]):
        return self.__rpc('innocent/combine', {
            "m_innocent_recipe_id": m_innocent_recipe_id,
            "t_innocent_ids": t_innocent_ids
        })

    def innocent_grazing(self, t_innocent_id: int, m_item_id: int):
        return self.__rpc('innocent/grazing', {"t_innocent_id": t_innocent_id, "m_item_id": m_item_id})

    ##########################
    # Hospital endpoints
    #########################

    def hospital_index(self):
        return self.__rpc('hospital/index', {})

    def hospital_roulette(self):
        data = self.__rpc('hospital/roulette', {})
        if 'api_error' in data and data['api_error']['message'] == 'Unable to restore yet':
            return
        Logger.info(f"Hospital Roulettte - Recovered {data['result']['recovery_num']} AP")
        return data

    def hospital_claim_reward(self, reward_id):
        return self.__rpc('hospital/receive_hospital', {"id":reward_id})

    ##########################
    # 4D Netherworld endpoints
    #########################
    
    def super_reincarnate(self,t_character_id:int, magic_element_num:int ):
        return self.__rpc('character/super_rebirth', {"t_character_id":t_character_id,"magic_element_num":magic_element_num})
    
    # status_up example (atk) [{"type":2,"num":1,"karma":340}]}
    def enhance_stats(self,t_character_id:int, status_ups ):
        return self.__rpc('character/status_up', {"t_character_id":t_character_id,"status_ups":status_ups})

    ##########################
    # Story event endpoints
    #########################
    
    def story_event_missions(self):
        return self.__rpc('event/missions', {"m_event_id":Constants.Current_Story_Event_ID})

    def story_event_daily_missions(self):
        return self.__rpc('event/mission_dailies', {"m_event_id":Constants.Current_Story_Event_ID})
        
    def story_event_claim_daily_missions(self, mission_ids: list[int] = []):
        return self.__rpc('event/receive_mission_daily', {"ids":mission_ids})

    def story_event_claim_missions(self, mission_ids: list[int] = []):
        return self.__rpc('event/receive_mission', {"ids":mission_ids})

    ##########################
    # PvP endpoints
    #########################
    
    def pvp_enemy_player_list(self):
        return self.__rpc('arena/enemy_players', {})

    def pvp_enemy_player_detail(self, t_player_id:int):
        return self.__rpc('arena/enemy_player_detail', {"t_player_id":t_player_id})
        
    def pvp_info(self):
        return self.__rpc('arena/current', {})

    def pvp_ranking(self):
        return self.__rpc('arena/ranking', {})

    def pvp_history(self, battle_at:int=0):
        return self.__rpc('arena/history', {"battle_at":battle_at})

    def pvp_start_battle(self, t_deck_no, enemy_t_player_id):
        return self.__rpc('arena/start', {"t_deck_no":t_deck_no,"enemy_t_player_id":enemy_t_player_id,"t_arena_battle_history_id":0,"act":1})

    def pvp_receive_rewards(self):
        return self.__rpc('arena/receive', {})


    ##########################
    # Sugoroku endpoints
    #########################
    
    def sugoroku_event_info(self):
        return self.__rpc('board/current', {"m_event_id":Constants.Current_Sugoroku_Event_ID})

    def sugoroku_battle_start(self, m_board_area_id:int, m_board_id:int, stage_no:int, t_character_ids: List[int], t_memory_ids :List[int], act:int=20):
        return self.__rpc('board/battle_start', {"m_event_id":Constants.Current_Sugoroku_Event_ID,"m_board_area_id":m_board_area_id,"m_board_id":m_board_id,"stage_no":stage_no,"t_character_ids":t_character_ids,"t_memory_ids":t_memory_ids,"act":act})

    def sugoroku_battle_end(self, m_board_area_id:int, m_board_id:int, stage_no:int, t_character_ids: List[int], t_memory_ids :List[int], act:int=20):
        return self.__rpc('battle/end', {
            "m_stage_id": 0,
            "m_tower_no": 0,
            "equipment_id": 0,
            "equipment_type": 0,
            "innocent_dead_flg": 0,
            "t_raid_status_id": 0,
            "raid_battle_result": "",
            "m_character_id": 0,
            "division_battle_result": "",
            "arena_battle_result" : "",
            "battle_type": 11,
            "result": 1,
            "battle_exp_data": [],
            "common_battle_result": "eyJhbGciOiJIUzI1NiJ9.eyJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MCwiZHBwY2JldzltejhjdXd3biI6MzQyNjgsInphY3N2NmpldjRpd3pqem0iOjUsImt5cXluaTNubm0zaTJhcWEiOjAsImVjaG02dGh0emNqNHl0eXQiOjAsImVrdXN2YXBncHBpazM1amoiOjAsInhhNWUzMjJtZ2VqNGY0eXEiOjJ9.u6onRDTkAeQLZ0EmIWrVOLxgJn8DJIIrDGYMtYOfplk",
            "skip_party_update_flg": True,
            "m_event_id" : Constants.Current_Sugoroku_Event_ID,
            "board_battle_result" : "eyJhbGciOiJIUzI1NiJ9.eyJjNFVkcFZ1WUV3NDVCZHhoIjpbeyJ0X2NoYXJhY3Rlcl9pZCI6OTg1Mzc5MjA4LCJocCI6MCwic3AiOjIwfSx7InRfY2hhcmFjdGVyX2lkIjo5ODUzNzkyOTUsImhwIjowLCJzcCI6MzB9LHsidF9jaGFyYWN0ZXJfaWQiOjk4NTM3OTIwMCwiaHAiOjAsInNwIjoyMH0seyJ0X2NoYXJhY3Rlcl9pZCI6OTg1Mzc5MjE5LCJocCI6MCwic3AiOjEwfSx7InRfY2hhcmFjdGVyX2lkIjo5ODUzNzkyMTcsImhwIjowLCJzcCI6MzB9XSwiZUsyVDQ5cVVqTDVNVm4zeiI6W3sid2F2ZSI6MSwicG9zIjoxLCJocCI6Mjc4N30seyJ3YXZlIjoxLCJwb3MiOjIsImhwIjoyNjI4fSx7IndhdmUiOjEsInBvcyI6MywiaHAiOjIzMjN9LHsid2F2ZSI6MSwicG9zIjo0LCJocCI6MjYyNn0seyJ3YXZlIjoxLCJwb3MiOjUsImhwIjoyNjMyfSx7IndhdmUiOjIsInBvcyI6MSwiaHAiOjIzMjN9LHsid2F2ZSI6MiwicG9zIjoyLCJocCI6Mjc4MX0seyJ3YXZlIjoyLCJwb3MiOjMsImhwIjoyNzgxfSx7IndhdmUiOjIsInBvcyI6NCwiaHAiOjI2MzJ9LHsid2F2ZSI6MiwicG9zIjo1LCJocCI6MjkzOH1dfQ.wjJaRp_gvrrVJ1bVEu3wgj6wX2FZPudz-WaXBdwfAeM"

        })

    ##########################
    # --------
    #########################


    def decrypt(self, content, iv):
        res = self.c.decrypt(content,iv)
        if 'fuji_key' in res:
            if sys.version_info >= (3, 0):
                self.c.key = bytes(res['fuji_key'], encoding='utf8')
            else:
                self.c.key = bytes(res['fuji_key'])
            self.session_id = res['session_id']
            print('found fuji_key:%s' % (self.c.key))  
    
    def raid_battle_finish_lvl50_boss(self,stage_id, raid_status_id, enemy_id):
        return self.__rpc('battle/end', 
            {
                "m_stage_id":stage_id,
                "m_tower_no":0,
                "equipment_id":0,
                "equipment_type":0,
                "innocent_dead_flg":0,
                "t_raid_status_id":raid_status_id,
                "raid_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJoamptZmN3Njc4NXVwanpjIjozNTM2NzgwODA2MywiczluZTNrbWFhbjVmcWR2dyI6ODQyLCJkNGNka253MjhmMmY1bm5sIjo1LCJyZ2o1b201cTljbmw2MXpiIjpbeyJjb21tYW5kX2NvdW50IjoxLCJjb21tYW5kX3R5cGUiOjIsIm1fY29tbWFuZF9pZCI6MzYwMDE1MSwiaXNfcGxheWVyIjpmYWxzZSwiY2hhcmFfcG9zaXRpb24iOjAsInJlbWFpbmluZ19mcmFtZSI6ODYzLCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NTIyLjYyNSwiaHAiOjIyMjM4NTM0LCJtX2NoYXJhY3Rlcl9pZCI6M30seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo0ODEuMCwiaHAiOjk4OTkyMjgsIm1fY2hhcmFjdGVyX2lkIjoxM30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo0OTQuODc1LCJocCI6NDY5NjA1ODMsIm1fY2hhcmFjdGVyX2lkIjoxNTJ9LHsiY2hhcmFfcG9zaXRpb24iOjMsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NjQyLjg3NSwiaHAiOjU5NDM1MTU3LCJtX2NoYXJhY3Rlcl9pZCI6MTQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjo0LCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMTUsMCw1LDAsMF0sInRpbWVsaW5lIjo0OTkuNSwiaHAiOjEwMjA4MjAwMywibV9jaGFyYWN0ZXJfaWQiOjE1MX1dLCJlbmVteV9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjowLjAsImhwIjozNzkwNjk5NCwibV9jaGFyYWN0ZXJfaWQiOjYwMDE1fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjg4MS4wLCJocCI6MTkwMTg4OSwibV9jaGFyYWN0ZXJfaWQiOjMwMDM3fSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjc4MS4wLCJocCI6MTkwMTg4OSwibV9jaGFyYWN0ZXJfaWQiOjMwMDM4fV0sImRhbWFnZV9jb21tYW5kIjp7ImF0a19wYXJhbSI6MzUyMTQsInNwZF9wYXJhbSI6NjAsImRhbWFnZV9saXN0IjpbeyJkZWZfcGFyYW0iOjMzMTE4MjkxLCJjaGFyYV9wb3NpdGlvbiI6NCwiZGFtYWdlX2xpc3QiOlswLDAsMCwwLDAsMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsZmFsc2UsZmFsc2UsZmFsc2UsdHJ1ZSxmYWxzZSxmYWxzZV19XX19LHsiY29tbWFuZF9jb3VudCI6MiwiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjExNywiaXNfcGxheWVyIjpmYWxzZSwiY2hhcmFfcG9zaXRpb24iOjEsInJlbWFpbmluZ19mcmFtZSI6ODUzLCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NjYzLjg3NSwiaHAiOjIyMjM4NTM0LCJtX2NoYXJhY3Rlcl9pZCI6M30seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo2MTEuMCwiaHAiOjk4OTkyMjgsIm1fY2hhcmFjdGVyX2lkIjoxM30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo2MjguNjI1LCJocCI6NDY5NjA1ODMsIm1fY2hhcmFjdGVyX2lkIjoxNTJ9LHsiY2hhcmFfcG9zaXRpb24iOjMsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6ODE2LjYyNSwiaHAiOjU5NDM1MTU3LCJtX2NoYXJhY3Rlcl9pZCI6MTQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjo0LCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMTUsMCw1LDAsMF0sInRpbWVsaW5lIjo2MzAuNzUsImhwIjoxMDIwODIwMDMsIm1fY2hhcmFjdGVyX2lkIjoxNTF9XSwiZW5lbXlfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMjUsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjEzNy41LCJocCI6Mzc5MDY5OTQsIm1fY2hhcmFjdGVyX2lkIjo2MDAxNX0seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwyNSwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MC4wLCJocCI6MTkwMTg4OSwibV9jaGFyYWN0ZXJfaWQiOjMwMDM3fSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDI1LDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo5MTEuMCwiaHAiOjE5MDE4ODksIm1fY2hhcmFjdGVyX2lkIjozMDAzOH1dLCJkYW1hZ2VfY29tbWFuZCI6eyJhdGtfcGFyYW0iOjE2NzM4LCJzcGRfcGFyYW0iOjU0LCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjoxODgyMTgxNCwiY2hhcmFfcG9zaXRpb24iOjMsImRhbWFnZV9saXN0IjpbMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZV19XX19LHsiY29tbWFuZF9jb3VudCI6MywiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjExOCwiaXNfcGxheWVyIjpmYWxzZSwiY2hhcmFfcG9zaXRpb24iOjIsInJlbWFpbmluZ19mcmFtZSI6ODQ2LCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NzYyLjc1LCJocCI6MjIyMzg1MzQsIm1fY2hhcmFjdGVyX2lkIjozfSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjcwMi4wLCJocCI6OTg5OTIyOCwibV9jaGFyYWN0ZXJfaWQiOjEzfSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlsyNSwwLDI1LDAsMCwwLDBdLCJ0aW1lbGluZSI6NzIyLjI1LCJocCI6NDY5NjA1ODMsIm1fY2hhcmFjdGVyX2lkIjoxNTJ9LHsiY2hhcmFfcG9zaXRpb24iOjMsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6OTM4LjI1LCJocCI6NTk0MzUxNTcsIm1fY2hhcmFjdGVyX2lkIjoxNDh9LHsiY2hhcmFfcG9zaXRpb24iOjQsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwxNSwwLDUsMCwwXSwidGltZWxpbmUiOjcyMi42MjUsImhwIjoxMDIwODIwMDMsIm1fY2hhcmFjdGVyX2lkIjoxNTF9XSwiZW5lbXlfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMjUsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjIzMy43NSwiaHAiOjM3OTA2OTk0LCJtX2NoYXJhY3Rlcl9pZCI6NjAwMTV9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMjUsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjkxLjAsImhwIjoxOTAxODg5LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMzd9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMjUsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjE5MDE4ODksIm1fY2hhcmFjdGVyX2lkIjozMDAzOH1dLCJkYW1hZ2VfY29tbWFuZCI6eyJhdGtfcGFyYW0iOjE2NzM4LCJzcGRfcGFyYW0iOjU0LCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjoxMTc5MDkyNywiY2hhcmFfcG9zaXRpb24iOjIsImRhbWFnZV9saXN0IjpbMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZV19XX19LHsiY29tbWFuZF9jb3VudCI6NCwiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjEwMDAzNiwiaXNfcGxheWVyIjp0cnVlLCJjaGFyYV9wb3NpdGlvbiI6MywicmVtYWluaW5nX2ZyYW1lIjo4NDIsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo4MTkuMjUsImhwIjoyMjIzODUzNCwibV9jaGFyYWN0ZXJfaWQiOjN9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NzU0LjAsImhwIjo5ODk5MjI4LCJtX2NoYXJhY3Rlcl9pZCI6MTN9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzI1LDAsMjUsMCwwLDAsMF0sInRpbWVsaW5lIjo3NzUuNzUsImhwIjo0Njk2MDU4MywibV9jaGFyYWN0ZXJfaWQiOjE1Mn0seyJjaGFyYV9wb3NpdGlvbiI6MywiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjowLjAsImhwIjo1OTQzNTE1NywibV9jaGFyYWN0ZXJfaWQiOjE0OH0seyJjaGFyYV9wb3NpdGlvbiI6NCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDE1LDAsNSwwLDBdLCJ0aW1lbGluZSI6Nzc1LjEyNSwiaHAiOjEwMjA4MjAwMywibV9jaGFyYWN0ZXJfaWQiOjE1MX1dLCJlbmVteV9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbXSwiZGVidWZmX3ZhbHVlX2xpc3QiOltdLCJ0aW1lbGluZSI6MC4wLCJocCI6MCwibV9jaGFyYWN0ZXJfaWQiOjYwMDE1fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDI1LDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjoxNDMuMCwiaHAiOjE5MDE4ODksIm1fY2hhcmFjdGVyX2lkIjozMDAzN30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwyNSwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NTIuMCwiaHAiOjE5MDE4ODksIm1fY2hhcmFjdGVyX2lkIjozMDAzOH1dLCJkYW1hZ2VfY29tbWFuZCI6eyJhdGtfcGFyYW0iOjQyMjQxNjU5LCJzcGRfcGFyYW0iOjg5LCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjozMTMyMywiY2hhcmFfcG9zaXRpb24iOjAsImRhbWFnZV9saXN0IjpbMTc1MjUzNDQ2MjEsMTc4NDI0NjM0NDJdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2VdfV19fV19.aBNNahtjDaq1bEcvntBY-SrDIACPJ6tWsxdESfCsJhY",
                "m_character_id":0,
                "division_battle_result":"",
                "arena_battle_result":"",
                "battle_type":1,
                "result":0,
                "battle_exp_data":[{"m_enemy_id":enemy_id,"finish_type":2,"finish_member_ids":[197923696]}],
                "common_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJhODNiY2ZiODdhMmQ5MzQ5Ijo1LCJiYmVjNmUzMjA5OGQ2YjUyIjowLCJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MzUzNjc4MDgwNjMsImRwcGNiZXc5bXo4Y3V3d24iOjAsInphY3N2NmpldjRpd3pqem0iOjAsImt5cXluaTNubm0zaTJhcWEiOjAsImVjaG02dGh0emNqNHl0eXQiOjAsImVrdXN2YXBncHBpazM1amoiOjAsInhhNWUzMjJtZ2VqNGY0eXEiOjF9.kWs1hSovRXeeFX0lulbKJ1HIUB6JT3u3-5adYW5OYWE",
                "skip_party_update_flg":True
            })

    def raid_battle_finish_lvl100_boss(self,stage_id, raid_status_id, enemy_id):
        return self.__rpc('battle/end', 
            {
                "m_stage_id":stage_id,
                "m_tower_no":0,
                "equipment_id":0,
                "equipment_type":0,
                "innocent_dead_flg":0,
                "t_raid_status_id":raid_status_id,
                "raid_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJoamptZmN3Njc4NXVwanpjIjoxOTI4MTQwOTUxNDE0LCJzOW5lM2ttYWFuNWZxZHZ3Ijo4NDIsImQ0Y2RrbncyOGYyZjVubmwiOjUsInJnajVvbTVxOWNubDYxemIiOlt7ImNvbW1hbmRfY291bnQiOjEsImNvbW1hbmRfdHlwZSI6MiwibV9jb21tYW5kX2lkIjozNjAwMTUxLCJpc19wbGF5ZXIiOmZhbHNlLCJjaGFyYV9wb3NpdGlvbiI6MCwicmVtYWluaW5nX2ZyYW1lIjo4NjMsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo1MjIuNjI1LCJocCI6MjIyMzg1MzQsIm1fY2hhcmFjdGVyX2lkIjozfSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMTUsMCw1LDAsMF0sInRpbWVsaW5lIjo0ODEuMCwiaHAiOjk4OTkyMjgsIm1fY2hhcmFjdGVyX2lkIjoxM30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo0OTQuODc1LCJocCI6NDY5NjA1ODMsIm1fY2hhcmFjdGVyX2lkIjoxNTJ9LHsiY2hhcmFfcG9zaXRpb24iOjMsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NjQyLjg3NSwiaHAiOjU5NDM1MTU3LCJtX2NoYXJhY3Rlcl9pZCI6MTQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjo0LCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjQ5OS41LCJocCI6MTAyMDgyMDAzLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjE0MDk5MTcsIm1fY2hhcmFjdGVyX2lkIjo2MDAxNn0seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo4ODEuMCwiaHAiOjM4MjEzLCJtX2NoYXJhY3Rlcl9pZCI6MzAwMzd9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NzgxLjAsImhwIjozODIxMywibV9jaGFyYWN0ZXJfaWQiOjMwMDM4fV0sImRhbWFnZV9jb21tYW5kIjp7ImF0a19wYXJhbSI6NTgyLCJzcGRfcGFyYW0iOjYwLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjoyMDcxMzUwLCJjaGFyYV9wb3NpdGlvbiI6MSwiZGFtYWdlX2xpc3QiOlswLDAsMCwwLDAsMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsZmFsc2UsZmFsc2UsdHJ1ZSxmYWxzZSxmYWxzZSxmYWxzZV19XX19LHsiY29tbWFuZF9jb3VudCI6MiwiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjExNywiaXNfcGxheWVyIjpmYWxzZSwiY2hhcmFfcG9zaXRpb24iOjEsInJlbWFpbmluZ19mcmFtZSI6ODUzLCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NjYzLjg3NSwiaHAiOjIyMjM4NTM0LCJtX2NoYXJhY3Rlcl9pZCI6M30seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDE1LDAsNSwwLDBdLCJ0aW1lbGluZSI6NjA3LjI1LCJocCI6OTg5OTIyOCwibV9jaGFyYWN0ZXJfaWQiOjEzfSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjYyOC42MjUsImhwIjo0Njk2MDU4MywibV9jaGFyYWN0ZXJfaWQiOjE1Mn0seyJjaGFyYV9wb3NpdGlvbiI6MywiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo4MTYuNjI1LCJocCI6NTk0MzUxNTcsIm1fY2hhcmFjdGVyX2lkIjoxNDh9LHsiY2hhcmFfcG9zaXRpb24iOjQsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NjM0LjUsImhwIjoxMDIwODIwMDMsIm1fY2hhcmFjdGVyX2lkIjoxNTF9XSwiZW5lbXlfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMjUsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjEzNy41LCJocCI6MTQwOTkxNywibV9jaGFyYWN0ZXJfaWQiOjYwMDE2fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDI1LDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjowLjAsImhwIjozODIxMywibV9jaGFyYWN0ZXJfaWQiOjMwMDM3fSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDI1LDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo5MTEuMCwiaHAiOjM4MjEzLCJtX2NoYXJhY3Rlcl9pZCI6MzAwMzh9XSwiZGFtYWdlX2NvbW1hbmQiOnsiYXRrX3BhcmFtIjozNzgsInNwZF9wYXJhbSI6NTQsImRhbWFnZV9saXN0IjpbeyJkZWZfcGFyYW0iOjYwMzM2MjQsImNoYXJhX3Bvc2l0aW9uIjowLCJkYW1hZ2VfbGlzdCI6WzBdLCJpc19jcml0aWNhbF9saXN0IjpbdHJ1ZV19XX19LHsiY29tbWFuZF9jb3VudCI6MywiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjExOCwiaXNfcGxheWVyIjpmYWxzZSwiY2hhcmFfcG9zaXRpb24iOjIsInJlbWFpbmluZ19mcmFtZSI6ODQ2LCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NzYyLjc1LCJocCI6MjIyMzg1MzQsIm1fY2hhcmFjdGVyX2lkIjozfSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlsyNSwwLDQwLDAsNSwwLDBdLCJ0aW1lbGluZSI6Njk1LjYyNSwiaHAiOjk4OTkyMjgsIm1fY2hhcmFjdGVyX2lkIjoxM30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo3MjIuMjUsImhwIjo0Njk2MDU4MywibV9jaGFyYWN0ZXJfaWQiOjE1Mn0seyJjaGFyYV9wb3NpdGlvbiI6MywiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo5MzguMjUsImhwIjo1OTQzNTE1NywibV9jaGFyYWN0ZXJfaWQiOjE0OH0seyJjaGFyYV9wb3NpdGlvbiI6NCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo3MjkuMCwiaHAiOjEwMjA4MjAwMywibV9jaGFyYWN0ZXJfaWQiOjE1MX1dLCJlbmVteV9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwyNSwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MjMzLjc1LCJocCI6MTQwOTkxNywibV9jaGFyYWN0ZXJfaWQiOjYwMDE2fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDI1LDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo5MS4wLCJocCI6MzgyMTMsIm1fY2hhcmFjdGVyX2lkIjozMDAzN30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwyNSwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MC4wLCJocCI6MzgyMTMsIm1fY2hhcmFjdGVyX2lkIjozMDAzOH1dLCJkYW1hZ2VfY29tbWFuZCI6eyJhdGtfcGFyYW0iOjM3OCwic3BkX3BhcmFtIjo1NCwiZGFtYWdlX2xpc3QiOlt7ImRlZl9wYXJhbSI6MjA3MTM1MCwiY2hhcmFfcG9zaXRpb24iOjEsImRhbWFnZV9saXN0IjpbMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZV19XX19LHsiY29tbWFuZF9jb3VudCI6NCwiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjEwMDAzNiwiaXNfcGxheWVyIjp0cnVlLCJjaGFyYV9wb3NpdGlvbiI6MywicmVtYWluaW5nX2ZyYW1lIjo4NDIsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo4MTkuMjUsImhwIjoyMjIzODUzNCwibV9jaGFyYWN0ZXJfaWQiOjN9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzI1LDAsNDAsMCw1LDAsMF0sInRpbWVsaW5lIjo3NDYuMTI1LCJocCI6OTg5OTIyOCwibV9jaGFyYWN0ZXJfaWQiOjEzfSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjc3NS43NSwiaHAiOjQ2OTYwNTgzLCJtX2NoYXJhY3Rlcl9pZCI6MTUyfSx7ImNoYXJhX3Bvc2l0aW9uIjozLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjU5NDM1MTU3LCJtX2NoYXJhY3Rlcl9pZCI6MTQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjo0LCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjc4My4wLCJocCI6MTAyMDgyMDAzLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOltdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6W10sInRpbWVsaW5lIjowLjAsImhwIjowLCJtX2NoYXJhY3Rlcl9pZCI6NjAwMTZ9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMjUsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjE0My4wLCJocCI6MzgyMTMsIm1fY2hhcmFjdGVyX2lkIjozMDAzN30seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwyNSwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6NTIuMCwiaHAiOjM4MjEzLCJtX2NoYXJhY3Rlcl9pZCI6MzAwMzh9XSwiZGFtYWdlX2NvbW1hbmQiOnsiYXRrX3BhcmFtIjo0MjI0MTY1OSwic3BkX3BhcmFtIjo4OSwiZGFtYWdlX2xpc3QiOlt7ImRlZl9wYXJhbSI6NTgyLCJjaGFyYV9wb3NpdGlvbiI6MCwiZGFtYWdlX2xpc3QiOls5MzUxNzQ0MTMxOTMsOTkyOTY2NTM4MjIxXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlLGZhbHNlXX1dfX1dfQ.0y_V8wFyJkRL0L5glcgn9QiK2Bwd79S-2tW7zwPe9uU",
                "m_character_id":0,
                "division_battle_result":"",
                "arena_battle_result":"",
                "battle_type":1,
                "result":0,
                "battle_exp_data":[{"m_enemy_id":enemy_id,"finish_type":2,"finish_member_ids":[197923696]}],
                "common_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJhODNiY2ZiODdhMmQ5MzQ5Ijo1LCJiYmVjNmUzMjA5OGQ2YjUyIjowLCJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MTkyODE0MDk1MTQxNCwiZHBwY2JldzltejhjdXd3biI6MCwiemFjc3Y2amV2NGl3emp6bSI6MCwia3lxeW5pM25ubTNpMmFxYSI6MCwiZWNobTZ0aHR6Y2o0eXR5dCI6MCwiZWt1c3ZhcGdwcGlrMzVqaiI6MCwieGE1ZTMyMm1nZWo0ZjR5cSI6MX0.6N3rGgAQ_c6TDygKsf7u6tl5PD93A_WwmlvS9UqrFYg",
                "skip_party_update_flg":True
            })