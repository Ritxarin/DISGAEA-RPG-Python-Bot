import base64
from collections import OrderedDict
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

head = {'version_check': 0, 'signup': 1, 'login': 1, 'rpc': 2}


class Client:
    def __init__(self, variables: Options):
        self.o: Options = variables
        self.c = codedbots()
        self.b = boltrend()
        self.s = requests.Session()
        self.s.verify = False
        self.gd = GameData(self.o.region)
        # self.s.proxies.update({'http': 'http://127.0.0.1:8080','https': 'http://127.0.0.1:8080',})
        # self.set_proxy('127.0.0.1:8080')

    def set_proxy(self, proxy):
        # noinspection HttpUrlsUsage
        tmp = 'http://' + proxy
        self.s.proxies.update({'http': tmp, 'https': tmp})

    def __rpc(self, method: str, prms: dict, current_iv=None):
        rpc=OrderedDict([('jsonrpc', "2.0"), ('id', self.rndid()), ('method', method), ('prms', json.dumps(prms,separators=(',',':')))])
        return self.__call_api('rpc',{"rpc":rpc})

    def __call_api(self, url: str, data=None, current_iv=None):
        if self.o.wait >= 1:
            time.sleep(self.o.wait)

        if current_iv is None:
            current_iv = self.c.randomiv()

        if 'version_check' in url and not hasattr(self,'oldkey'):
            self.oldkey=self.c.key
        if 'version_check' in url and hasattr(self,'oldkey'):
            self.c.key=self.oldkey
                        
        self._set_headers(url, current_iv)
        if data is None:
            r = self.s.get(self.o.main_url + url)
        else:
            if data != '':
                cdata = self.c.encrypt(data, current_iv, self.o.region)
            else:
                cdata = data
            r = self.s.post(self.o.main_url + url, data=cdata)
        if 'X-Crypt-Iv' not in r.headers:
            r_method = data['rpc']['method'] if 'rpc' in data else url
            Logger.error('request: "%s" was missing iv!' % r_method)
            exit(1)
            return None
        res = self.c.decrypt(base64.b64encode(r.content), r.headers['X-Crypt-Iv'], self.o.region)
        if res is None: return
        if 'title' in res and 'Maintenance' in res['title']:
            Logger.info(res['content'])
            exit(1)
        if 'api_error' in res:
            if 'code' in res['api_error'] and res['api_error']['code'] == 1002:
                Logger.info('Date has changed. Please log in again.')
                sys.exit()
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
            
            ## Cache login data
            login_data =  []
            login_data.append({
                'fuji_key': res['fuji_key'],
                "session_id": res['session_id']
                })
            f = open("logindata.json", "w")
            f.write(json.dumps(login_data, indent=2, sort_keys=True))
            f.close()

        if 'result' in res and 't_player_id' in res['result']:
            if 'player_rank' in res['result']:
                Logger.info(
                    't_player_id:%s player_rank:%s' % (res['result']['t_player_id'], res['result']['player_rank']))
            self.o.pid = res['result']['t_player_id']
        if 'result' in res and 'after_t_status' in res['result']:
            if res['result']['after_t_status'] is not None and 'act' in res['result']['after_t_status']:
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
                    'X-PERF-SCENE-TIME':'8619',
                    'X-PERF-APP-BUILD-NUMBER':'0',
                    'X-PERF-NETWORK-REQ-LAST':'1',
                    'X-PERF-DISC-FREE':'5395',
                    'X-PERF-FPS-LAST-MED':'59.99',
                    'X-APP-VERSION':self.o.version,
                    'X-PERF-OS-VERSION':'iOS 14.2',
                    'X-PERF-CPU-SYS':'0','X-PERF-CPU-USER':
                    '40.79','X-PERF-BUTTERY':'100',
                    'X-PERF-SCENE-TRACE':'startup_scene,title_scene,startup_scene,title_scene',
                    'X-PERF-NETWORK-ERR-LAST':'0',
                    'X-PERF-NETWORK-REQ-TOTAL':'1',
                    'X-PERF-CPU-IDLE':'59.21',
                    'X-PERF-APP-VERSION':'2.11.2',
                    'X-PERF-FPS-LAST-AVG':'59.23',
                    'User-Agent':'RPG/282 CFNetwork/1197 Darwin/20.0.0',
                    'X-PERF-MEM-USER':'1624',
                    'X-PERF-LAUNCH-TIME':'20210408T15:50:36Z',
                    'X-PERF-SCENE':'title_scene',
                    'X-PERF-FPS':'59.99',
                    'X-Crypt-Iv':iv,
                    'X-PERF-MEM-AVAILABLE':'24',
                    'X-PERF-LAST-DELTA-TIMES':'16,17,16,17,21,13,16,17,17,17',
                    'X-PERF-NETWORK-ERR-TOTAL':'0',
                    'X-PERF-DEVICE':'iPad7,5',
                    'Content-Type':'application/x-haut-hoiski',
                    'X-PERF-OS':'iOS 14.2',
                    'X-PERF-MEM-PYSIC':'1981',
                    'X-Unity-Version':'2019.4.29f1',
                    'X-PERF-TIME':'20210408T15:52:43Z',
                    'X-PERF-APP-ID':'com.disgaearpg.forwardworks',
                    'X-PERF-LAUNCH-DURATION':'70363',
                    'x-jvhpdr5cvhahu5zp':'Sj3guMhsn6TRzhmg',
                    'accept':'*/*',
                    'accept-encoding':'gzip, deflate, br'})
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
                    'X-Unity-Version':'2019.4.29f1',
                    'X-Crypt-Iv':iv,
                    'Accept-Language':'en-us',
                    'Content-Type':'application/x-haut-hoiski',
                    'User-Agent':'RPG/282 CFNetwork/1197 Darwin/20.0.0',
                    'X-APP-VERSION':self.o.version,
                    'x-jvhpdr5cvhahu5zp':'Sj3guMhsn6TRzhmg',
                    'accept':'*/*',
                    'accept-encoding':'gzip, deflate, br'})
        elif i == 2:
            if self.o.region==2:
                self.s.headers.update({
                    'X-Unity-Version':'2018.4.3f1',
                    'X-Crypt-Iv':iv,
                    'Accept-Language':'en-us',
                    'X_CHANNEL':'1',
                    'Content-Type':'application/x-haut-hoiski',
                    'User-Agent':'en/17 CFNetwork/1206 Darwin/20.1.0',
                    'X-OS-TYPE':'1',
                    'X-APP-VERSION':self.o.version
                    })
            else:
                self.s.headers.update({
                    'X-Unity-Version':'2019.4.29f1',
                    'X-Crypt-Iv':iv,
                    'Accept-Language':'en-us',
                    'Content-Type':'application/x-haut-hoiski',
                    'User-Agent':'iPad6Gen/iOS 14.2',
                    'X-OS-TYPE':self.o.device,
                    'X-APP-VERSION':self.o.version,
                    'X-SESSION':self.o.session_id,
                    'x-jvhpdr5cvhahu5zp':'Sj3guMhsn6TRzhmg',
                    'accept':'*/*',
                    'accept-encoding':'gzip, deflate, br'})
        else:
            if self.o.region==2:
                self.s.headers.update({
                    'X-Unity-Version':'2018.4.20f1',
                    'X-Crypt-Iv':iv,
                    'Accept-Language':'en-us',
                    'Content-Type':'application/x-haut-hoiski',
                    'User-Agent':'forwardworks/194 CFNetwork/1206 Darwin/20.1.0',
                    'X-OS-TYPE':self.o.device,
                    'X-APP-VERSION':self.o.version})
            else:
                self.s.headers.update({
                    'X-Unity-Version':'2019.4.29f1',
                    'X-Crypt-Iv':iv,
                    'Accept-Language':'en-us',
                    'Content-Type':'application/x-haut-hoiski',
                    'User-Agent':'RPG/282 CFNetwork/1197 Darwin/20.0.0',
                    'X-APP-VERSION':self.o.version,
                    'x-jvhpdr5cvhahu5zp':'Sj3guMhsn6TRzhmg',
                    'accept':'*/*',
                    'accept-encoding':'gzip, deflate, br',
                    'X-SESSION':self.o.session_id})

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

    def login_from_cache(self):
        login_file = open("logindata.json")
        login_data = json.load(login_file)
        self.c.key = bytes(login_data[0]['fuji_key'], encoding='utf8')
        self.o.session_id = login_data[0]['session_id']

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
                     deck_no=1, reincarnation_character_ids=[], raid_status_id=0, character_ids=None, memory_ids=[],
                     use_item_id:int = 0, use_item_num:id=0):
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
            "use_item_id":use_item_id,
            "use_item_num":use_item_num
        }

        if len(memory_ids) >= 1:
            while len(memory_ids) < 5:
                memory_ids.append(0)
            prms['t_memory_ids'] = memory_ids
        else:
            prms['t_memory_ids'] = memory_ids
            
        if character_ids is not None:
            prms["t_character_ids"] = []

        return self.__rpc('battle/start', prms)

    def battle_end(self, m_stage_id, battle_type, result=0, battle_exp_data=[], equipment_id: int = 0,
                   equipment_type: int = 0, m_tower_no: int = 0,
                   raid_status_id: int = 0, raid_battle_result: str = '',
                   skip_party_update_flg: bool = True, common_battle_result=None,
                   division_battle_result: str = None,
                   innocent_dead_flg: int = 0,
                   travel_battle_result=''
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
                "arena_battle_result":"",
                "battle_type": battle_type,
                "result": result, 
                "battle_exp_data": battle_exp_data,                                        
                "common_battle_result": common_battle_result,
                "skip_party_update_flg": skip_party_update_flg,
                "m_event_id":0,
                "board_battle_result":""
            }
        else:
            prms = {
                "m_stage_id": m_stage_id,
                "m_tower_no": m_tower_no,
                "equipment_id": equipment_id, 
                "equipment_type": equipment_type,
                "innocent_dead_flg": innocent_dead_flg,
                "t_raid_status_id": 0, 
                "raid_battle_result": raid_battle_result, 
                "m_character_id": 0,
                "arena_battle_result":"",
                "battle_type": battle_type,
                "result": result,
                "battle_exp_data": battle_exp_data,
                "common_battle_result": common_battle_result,                        
                "skip_party_update_flg": skip_party_update_flg,
                "m_event_id":0,
                "board_battle_result":"",
                "tournament_score":0,
                "tournament_battle_result":"",
                "travel_battle_result" : travel_battle_result             
            }

        if division_battle_result is not None:
            prms['division_battle_result'] = division_battle_result

        return self.__rpc('battle/end', prms)

    def battle_end_end_with_payload(self, parameters):
        return self.__rpc('battle/end', parameters)
    
    def battle_story(self, m_stage_id):
        return self.__rpc('battle/story', {"m_stage_id": m_stage_id})

    def battle_reset(self):
        return self.__rpc('battle/reset', {})

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
            "skip_party_update_flg": True,
            "m_event_id":0,
            "board_battle_result":""
        })

    def battle_skip(self, m_stage_id, deck_no: int, skip_number: int, helper_player,  ap_cost:int,
                    reincarnation_character_ids=[], battle_type:int=3):

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
            "battle_type": battle_type,
            "act": ap_cost,
            "auto_rebirth_t_character_ids": reincarnation_character_ids,
            "t_memery_ids": [],
            "use_item_id":0,
            "use_item_num":0
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
            "skip_party_update_flg": True,
            "m_event_id":0,
            "board_battle_result":""
        })


    #################
    # Raid Endpoints
    #################

    def raid_send_help_request(self, raid_id):
        return self.__rpc('raid/help', {"t_raid_status_id": raid_id})

    def raid_index(self):
        return self.__rpc('raid/index', {})

    def raid_ranking(self, raid_ID:int=0):
        if raid_ID == 0:
            raid_ID = Constants.Current_Raid_ID_GL if self.o.region == 2 else Constants.Current_Raid_ID_JP
        data = self.__rpc('raid/ranking', {"m_event_id":raid_ID,"m_raid_boss_kind_id":0})
        return data
    
    def raid_ranking_player(self, t_player_id, raid_ID:int=0):
        if raid_ID == 0:
            raid_ID = Constants.Current_Raid_ID_GL if self.o.region == 2 else Constants.Current_Raid_ID_JP
        data = self.__rpc('raid/ranking_player', {"m_raid_id":raid_ID,"m_raid_boss_kind_id":0,"t_player_id":t_player_id})
        return data

    def raid_ranking_reward(self):
        return self.__rpc('raid/ranking_reward', {})

    def raid_give_up_boss(self, t_raid_status_id):
        return self.__rpc('raid/give_up', {"t_raid_status_id": t_raid_status_id})

    def raid_current(self):
        return self.__rpc('raid/current', {})

    def raid_history(self, raid_ID:int=0):
        if raid_ID == 0:
            raid_ID = Constants.Current_Raid_ID_GL if self.o.region == 2 else Constants.Current_Raid_ID_JP
        return self.__rpc('raid/history', {"m_event_id": raid_ID})

    # reward for a specific boss battle
    def raid_reward(self, t_raid_status_id):
        return self.__rpc('raid/reward', {"t_raid_status_id": t_raid_status_id})

    def raid_gacha(self, m_event_gacha_id, lottery_num):
        return self.__rpc('event/gacha_do', {"m_event_gacha_id": m_event_gacha_id, "lottery_num": lottery_num})

    def raid_update(self, m_raid_boss_id, step):
        return self.__rpc('raid_boss/update', {"m_raid_boss_id": m_raid_boss_id, "step": step})

    def raid_exchange_surplus_points(self, points_to_exchange):
        raid_ID = Constants.Current_Raid_ID_GL if self.o.region == 2 else Constants.Current_Raid_ID_JP
        data = self.__rpc('event/exchange_surplus_point',
                          {"m_event_id": raid_ID, "exchange_count": points_to_exchange})
        return data

    def raid_event_missions(self, raid_ID:int=0):
        if raid_ID == 0:
            raid_ID = Constants.Current_Raid_ID_GL if self.o.region == 2 else Constants.Current_Raid_ID_JP
        return self.__rpc('event/missions', {"m_event_id":raid_ID})
    
    def raid_start_special_stage(self, raid_dtage_id:int, team_number:int):
        return self.__rpc('raid/start_special_stage', {"m_raid_special_stage_id":raid_dtage_id,"t_deck_no":team_number})

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

    def player_character_collections(self, updated_at: int = 0, page: int = 1):
        return self.__rpc('player/character_collections', {
            "updated_at": updated_at,
            "page": page
        })

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

    def player_add(self,tracking_authorize=2):
        data=self.__rpc('player/add',{"uuid": self.o.uuid, "pw": self.o.password, "tracking_authorize": tracking_authorize})

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
    
    # material_t_character_ids = [220159023,220159708,220159706,220159047,220159046]
    def player_awakening(self, t_character_id:int, material_t_character_ids:list[int], material_m_item_id:int=0):
        data = self.__rpc('player/awakening', {"t_character_id":t_character_id,"material_t_character_ids":material_t_character_ids,"material_m_item_id":material_m_item_id})
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
        if 'error' in data:
            return
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

    def event_index(self, event_ids:list[int]=None):
        if event_ids is None:
            return self.__rpc('event/index', {})
        else:
            return self.__rpc('event/index', {"m_event_ids": event_ids})
    
    def event_update_read_flg(self, event_id:int, flag_type:str):
        return self.__rpc('event/update_read_flg', {"m_event_id":event_id,"type":flag_type})
    
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
            "database_version": ""
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
    
    def award_index(self,updated_at,page):
        data=self.__rpc('award/index',{"updated_at": updated_at, "page": page})
        return data

    def inherit_check(self):
        data=self.__rpc('inherit/check',{})
        return data

    def inherit_conf_inherit(self,public_id,inherit_code):
        data=self.__rpc('inherit/conf_inherit',{"public_id": public_id, "inherit_code": inherit_code})
        return data

    def inherit_exec_inherit(self,public_id,inherit_code):
        data=self.__rpc('inherit/exec_inherit',{"public_id": public_id, "inherit_code": inherit_code})
        return data

    def player_character_commands(self,updated_at,page):
        data=self.__rpc('player/character_commands',{"updated_at": updated_at, "page": page})
        return data

    def auth_providers(self):
        data=self.__call_api('auth/providers',None)
        return data

    def inherit_get_code(self):
        data=self.__rpc('inherit/get_code',{})
        return data
    
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
        if 'api_error' in data:
            return
        Logger.info(f"Hospital Roulettte span - Current AP: {data['result']['after_t_status']['act']}")
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
        m_event_id = Constants.Current_Story_Event_ID_GL if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
        return self.__rpc('event/missions', {"m_event_id":m_event_id})

    def story_event_daily_missions(self):
        m_event_id = Constants.Current_Story_Event_ID_GL if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
        return self.__rpc('event/mission_dailies', {"m_event_id":m_event_id})
    
    def story_event_mission_repetitions(self):
        m_event_id = Constants.Current_Story_Event_ID_GL if self.o.region == 2 else Constants.Current_Story_Event_ID_JP
        return self.__rpc('event/mission_repetitions', {"m_event_id":m_event_id})
        
    def story_event_claim_daily_missions(self, mission_ids: list[int] = []):
        return self.__rpc('event/receive_mission_daily', {"ids":mission_ids})

    def story_event_claim_missions(self, mission_ids: list[int] = []):
        return self.__rpc('event/receive_mission', {"ids":mission_ids})
    
    def story_event_claim_mission_repetitions(self, mission_ids: list[int] = []):
        return self.__rpc('event/receive_mission_repetitions', {"ids":mission_ids})

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
    # Netherworld Travel Endpoint
    #########################
    
    def netherworld_travel_index(self):
        return self.__rpc('travel/current', {})
    
    def netherworld_travel_start(self, m_travel_id:int, t_character_ids:List[int]):
        return self.__rpc('travel/travel_start', {"m_travel_id":m_travel_id,"t_character_ids":t_character_ids,"t_memory_ids":[0,0,0,0,0],"appear_event_area_flg":True})
    
    def netherworld_travel_battle_start(self):
        return self.__rpc('travel/battle_start', {})
    
    def netherworld_travel_receive_reward(self, m_travel_benefit_id:int):
        return self.__rpc('travel/select_benefit', {'m_travel_benefit_id':m_travel_benefit_id})
    
    def netherworld_travel_select_negative_effect(self, t_character_id:int, effect_id:int):
        return self.__rpc('travel/select_negative_effect', {"t_character_id":t_character_id,"m_travel_negative_effect_id":effect_id})

    ##########################
    # --------
    #########################

    def decrypt(self, content, iv, region):
        res = self.c.decrypt(content,iv, region)
        if res != None and 'fuji_key' in res:
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
                "raid_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJoamptZmN3Njc4NXVwanpjIjoyNDc3ODk5MjYwOTM2LCJzOW5lM2ttYWFuNWZxZHZ3Ijo4NDEsImQ0Y2RrbncyOGYyZjVubmwiOjUsInJnajVvbTVxOWNubDYxemIiOlt7ImNvbW1hbmRfY291bnQiOjEsImNvbW1hbmRfdHlwZSI6MiwibV9jb21tYW5kX2lkIjozNjAwMzczLCJpc19wbGF5ZXIiOmZhbHNlLCJjaGFyYV9wb3NpdGlvbiI6MCwicmVtYWluaW5nX2ZyYW1lIjo4NjAsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMjUsMCwyNSwwLDAsMCwwXSwidGltZWxpbmUiOjU0NS4wLCJocCI6MjQxMjg2NTAsIm1fY2hhcmFjdGVyX2lkIjozfSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlsyNSwwLDI1LDAsMCwwLDBdLCJ0aW1lbGluZSI6NTEwLjAsImhwIjo0OTE3LCJtX2NoYXJhY3Rlcl9pZCI6MjAwNDh9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzI1LDAsMjUsMCwwLDAsMF0sInRpbWVsaW5lIjo1MzUuMCwiaHAiOjcwNTMxMzc0LCJtX2NoYXJhY3Rlcl9pZCI6MTUyfSx7ImNoYXJhX3Bvc2l0aW9uIjozLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlsyNSwwLDI1LDAsMCwwLDBdLCJ0aW1lbGluZSI6Njk1LjAsImhwIjo2NDg2NDQwMiwibV9jaGFyYWN0ZXJfaWQiOjE0OH0seyJjaGFyYV9wb3NpdGlvbiI6NCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMjUsMCwyNSwwLDAsMCwwXSwidGltZWxpbmUiOjU0MC4wLCJocCI6MTExNTEzMTcyLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjQ1MzA5NywibV9jaGFyYWN0ZXJfaWQiOjYwMDM3fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjkwNS4wLCJocCI6MTk5MTUsIm1fY2hhcmFjdGVyX2lkIjozMDAxMH0seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo4MDUuMCwiaHAiOjE5OTE1LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9XSwiZGFtYWdlX2NvbW1hbmQiOnsiYXRrX3BhcmFtIjoyODUsInNwZF9wYXJhbSI6NTAsImRhbWFnZV9saXN0IjpbeyJkZWZfcGFyYW0iOjU2MTUzODUsImNoYXJhX3Bvc2l0aW9uIjowLCJkYW1hZ2VfbGlzdCI6WzBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2VdfSx7ImRlZl9wYXJhbSI6MTA0NCwiY2hhcmFfcG9zaXRpb24iOjEsImRhbWFnZV9saXN0IjpbNTIxXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlXX0seyJkZWZfcGFyYW0iOjE4MDEzMTUyLCJjaGFyYV9wb3NpdGlvbiI6MiwiZGFtYWdlX2xpc3QiOlswXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlXX0seyJkZWZfcGFyYW0iOjE2NjU1Mzc0LCJjaGFyYV9wb3NpdGlvbiI6MywiZGFtYWdlX2xpc3QiOlswXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlXX0seyJkZWZfcGFyYW0iOjIxMzEzNjMxLCJjaGFyYV9wb3NpdGlvbiI6NCwiZGFtYWdlX2xpc3QiOlswXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlXX1dfX0seyJjb21tYW5kX2NvdW50IjoyLCJjb21tYW5kX3R5cGUiOjIsIm1fY29tbWFuZF9pZCI6MjI2LCJpc19wbGF5ZXIiOmZhbHNlLCJjaGFyYV9wb3NpdGlvbiI6MSwicmVtYWluaW5nX2ZyYW1lIjo4NTIsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNDAsMCwyNSwxNSwxMCwwLDBdLCJ0aW1lbGluZSI6NjU0LjAsImhwIjoyNDEyODY1MCwibV9jaGFyYWN0ZXJfaWQiOjN9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzQwLDAsMjUsMTUsMTAsMCwwXSwidGltZWxpbmUiOjYxMi4wLCJocCI6NDkxNywibV9jaGFyYWN0ZXJfaWQiOjIwMDQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls0MCwwLDI1LDE1LDEwLDAsMF0sInRpbWVsaW5lIjo2NDIuMCwiaHAiOjcwNTMxMzc0LCJtX2NoYXJhY3Rlcl9pZCI6MTUyfSx7ImNoYXJhX3Bvc2l0aW9uIjozLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls0MCwwLDI1LDE1LDEwLDAsMF0sInRpbWVsaW5lIjo4MzQuMCwiaHAiOjY0ODY0NDAyLCJtX2NoYXJhY3Rlcl9pZCI6MTQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjo0LCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls0MCwwLDI1LDE1LDEwLDAsMF0sInRpbWVsaW5lIjo2NDguMCwiaHAiOjExMTUxMzE3MiwibV9jaGFyYWN0ZXJfaWQiOjE1MX1dLCJlbmVteV9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjoxMDAuMCwiaHAiOjQ1MzA5NywibV9jaGFyYWN0ZXJfaWQiOjYwMDM3fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjE5OTE1LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6OTA2LjAsImhwIjoxOTkxNSwibV9jaGFyYWN0ZXJfaWQiOjMwMDEwfV0sImRhbWFnZV9jb21tYW5kIjp7ImF0a19wYXJhbSI6MjMyLCJzcGRfcGFyYW0iOjUxLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjo2MjkzMjM5LCJjaGFyYV9wb3NpdGlvbiI6MCwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19LHsiZGVmX3BhcmFtIjoxNTAzLCJjaGFyYV9wb3NpdGlvbiI6MSwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOlt0cnVlLGZhbHNlLGZhbHNlXX0seyJkZWZfcGFyYW0iOjE3OTQzMzM5LCJjaGFyYV9wb3NpdGlvbiI6MiwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19LHsiZGVmX3BhcmFtIjoyMDgwMzcyOSwiY2hhcmFfcG9zaXRpb24iOjMsImRhbWFnZV9saXN0IjpbMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsZmFsc2VdfSx7ImRlZl9wYXJhbSI6MzYwODkzNjEsImNoYXJhX3Bvc2l0aW9uIjo0LCJkYW1hZ2VfbGlzdCI6WzAsMCwwXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlLGZhbHNlLGZhbHNlXX1dfX0seyJjb21tYW5kX2NvdW50IjozLCJjb21tYW5kX3R5cGUiOjIsIm1fY29tbWFuZF9pZCI6MjI2LCJpc19wbGF5ZXIiOmZhbHNlLCJjaGFyYV9wb3NpdGlvbiI6MiwicmVtYWluaW5nX2ZyYW1lIjo4NDQsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNTAsMCwyNSwzMCwyMCwwLDBdLCJ0aW1lbGluZSI6NzU3LjAsImhwIjoyNDEyODY1MCwibV9jaGFyYWN0ZXJfaWQiOjN9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjcwOC4wLCJocCI6NDkxNywibV9jaGFyYWN0ZXJfaWQiOjIwMDQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls1MCwwLDI1LDMwLDIwLDAsMF0sInRpbWVsaW5lIjo3NDMuMCwiaHAiOjcwNTMxMzc0LCJtX2NoYXJhY3Rlcl9pZCI6MTUyfSx7ImNoYXJhX3Bvc2l0aW9uIjozLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls1MCwwLDI1LDMwLDIwLDAsMF0sInRpbWVsaW5lIjo5NjQuMCwiaHAiOjY0ODY0NDAyLCJtX2NoYXJhY3Rlcl9pZCI6MTQ4fSx7ImNoYXJhX3Bvc2l0aW9uIjo0LCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls1MCwwLDI1LDMwLDIwLDAsMF0sInRpbWVsaW5lIjo3NTAuMCwiaHAiOjExMTUxMzE3MiwibV9jaGFyYWN0ZXJfaWQiOjE1MX1dLCJlbmVteV9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjoyMDAuMCwiaHAiOjQ1MzA5NywibV9jaGFyYWN0ZXJfaWQiOjYwMDM3fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjEwMS4wLCJocCI6MTk5MTUsIm1fY2hhcmFjdGVyX2lkIjozMDAxMH0seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjowLjAsImhwIjoxOTkxNSwibV9jaGFyYWN0ZXJfaWQiOjMwMDEwfV0sImRhbWFnZV9jb21tYW5kIjp7ImF0a19wYXJhbSI6MjMyLCJzcGRfcGFyYW0iOjUxLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjo2MjkzMjM5LCJjaGFyYV9wb3NpdGlvbiI6MCwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSx0cnVlXX0seyJkZWZfcGFyYW0iOjE1MDMsImNoYXJhX3Bvc2l0aW9uIjoxLCJkYW1hZ2VfbGlzdCI6WzAsMCwwXSwiaXNfY3JpdGljYWxfbGlzdCI6W3RydWUsZmFsc2UsZmFsc2VdfSx7ImRlZl9wYXJhbSI6MTc5NDMzMzksImNoYXJhX3Bvc2l0aW9uIjoyLCJkYW1hZ2VfbGlzdCI6WzAsMCwwXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlLGZhbHNlLGZhbHNlXX0seyJkZWZfcGFyYW0iOjIwODAzNzI5LCJjaGFyYV9wb3NpdGlvbiI6MywiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19LHsiZGVmX3BhcmFtIjozNjA4OTM2MSwiY2hhcmFfcG9zaXRpb24iOjQsImRhbWFnZV9saXN0IjpbMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsZmFsc2VdfV19fSx7ImNvbW1hbmRfY291bnQiOjQsImNvbW1hbmRfdHlwZSI6MiwibV9jb21tYW5kX2lkIjoxMDAwMzYsImlzX3BsYXllciI6dHJ1ZSwiY2hhcmFfcG9zaXRpb24iOjMsInJlbWFpbmluZ19mcmFtZSI6ODQxLCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc5My4zNzUsImhwIjoyNDEyODY1MCwibV9jaGFyYWN0ZXJfaWQiOjN9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc0Mi4xMjUsImhwIjo0OTE3LCJtX2NoYXJhY3Rlcl9pZCI6MjAwNDh9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc3OC42MjUsImhwIjo3MDUzMTM3NCwibV9jaGFyYWN0ZXJfaWQiOjE1Mn0seyJjaGFyYV9wb3NpdGlvbiI6MywiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNTAsMCwyNSwzMCwyMCwwLDBdLCJ0aW1lbGluZSI6MC4wLCJocCI6NDg2NDgzMDEsIm1fY2hhcmFjdGVyX2lkIjoxNDh9LHsiY2hhcmFfcG9zaXRpb24iOjQsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc4Ni4wLCJocCI6MTExNTEzMTcyLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOltdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6W10sInRpbWVsaW5lIjowLjAsImhwIjowLCJtX2NoYXJhY3Rlcl9pZCI6NjAwMzd9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MTM4Ljg3NSwiaHAiOjE5OTE1LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MzcuODc1LCJocCI6MTk5MTUsIm1fY2hhcmFjdGVyX2lkIjozMDAxMH1dLCJkYW1hZ2VfY29tbWFuZCI6eyJhdGtfcGFyYW0iOjI4Njc1NTM4LCJzcGRfcGFyYW0iOjcxLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjoyNzUsImNoYXJhX3Bvc2l0aW9uIjowLCJkYW1hZ2VfbGlzdCI6WzEyMjkzNjU3MTAzMzAsMTI0ODUzMzU1MDYwNl0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZV19XX19XX0.F00X5BCP2TcRzYq_RgGoOEopuOFLE28sd--CJoduZdU",
                "m_character_id":0,
                "division_battle_result":"",
                "arena_battle_result":"",
                "battle_type":1,
                "result":0,
                "battle_exp_data":[{"m_enemy_id":enemy_id,"finish_type":2,"finish_member_ids":[197923696]}],
                "common_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJhODNiY2ZiODdhMmQ5MzQ5Ijo0LCJiYmVjNmUzMjA5OGQ2YjUyIjoxLCJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MjQ3Nzg5OTI2MDkzNiwiZHBwY2JldzltejhjdXd3biI6NTIxLCJ6YWNzdjZqZXY0aXd6anptIjowLCJreXF5bmkzbm5tM2kyYXFhIjowLCJlY2htNnRodHpjajR5dHl0IjowLCJla3VzdmFwZ3BwaWszNWpqIjowLCJ4YTVlMzIybWdlajRmNHlxIjoxfQ.NWfLAzcDGIL5mInbdkX8DW0lKMeN1f-NFSo3ldZnw_c",
                "skip_party_update_flg":True,
                "m_event_id":0,
                "board_battle_result":""
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
                "raid_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJoamptZmN3Njc4NXVwanpjIjoxMTA4MDQ1ODE1Mjg5LCJzOW5lM2ttYWFuNWZxZHZ3Ijo4NDEsImQ0Y2RrbncyOGYyZjVubmwiOjUsInJnajVvbTVxOWNubDYxemIiOlt7ImNvbW1hbmRfY291bnQiOjEsImNvbW1hbmRfdHlwZSI6MiwibV9jb21tYW5kX2lkIjozNjAwMzgzLCJpc19wbGF5ZXIiOmZhbHNlLCJjaGFyYV9wb3NpdGlvbiI6MCwicmVtYWluaW5nX2ZyYW1lIjo4NjAsInBsYXllcl9saXN0IjpbeyJjaGFyYV9wb3NpdGlvbiI6MCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMjUsMCwyNSwwLDAsMCwwXSwidGltZWxpbmUiOjU0NS4wLCJocCI6MjQxMjg2NTAsIm1fY2hhcmFjdGVyX2lkIjozfSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlsyNSwwLDI1LDAsMCwwLDBdLCJ0aW1lbGluZSI6NTEwLjAsImhwIjozNzY0LCJtX2NoYXJhY3Rlcl9pZCI6MjAwNDh9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzI1LDAsMjUsMCwwLDAsMF0sInRpbWVsaW5lIjo1MzUuMCwiaHAiOjcwNTMxMzc0LCJtX2NoYXJhY3Rlcl9pZCI6MTUyfSx7ImNoYXJhX3Bvc2l0aW9uIjozLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlsyNSwwLDI1LDAsMCwwLDBdLCJ0aW1lbGluZSI6Njk1LjAsImhwIjo2NDg2NDQwMiwibV9jaGFyYWN0ZXJfaWQiOjE0OH0seyJjaGFyYV9wb3NpdGlvbiI6NCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMjUsMCwyNSwwLDAsMCwwXSwidGltZWxpbmUiOjU0MC4wLCJocCI6MTExNTEzMTcyLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjE0MDk5MTcsIm1fY2hhcmFjdGVyX2lkIjo2MDAzOH0seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sInRpbWVsaW5lIjo5MDUuMCwiaHAiOjM5ODg4LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6ODA1LjAsImhwIjozOTg4OCwibV9jaGFyYWN0ZXJfaWQiOjMwMDEwfV0sImRhbWFnZV9jb21tYW5kIjp7ImF0a19wYXJhbSI6NjMwLCJzcGRfcGFyYW0iOjUwLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjo1NjE1Mzg1LCJjaGFyYV9wb3NpdGlvbiI6MCwiZGFtYWdlX2xpc3QiOlswXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlXX0seyJkZWZfcGFyYW0iOjEwNDQsImNoYXJhX3Bvc2l0aW9uIjoxLCJkYW1hZ2VfbGlzdCI6WzE2NzRdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2VdfSx7ImRlZl9wYXJhbSI6MTgwMTMxNTIsImNoYXJhX3Bvc2l0aW9uIjoyLCJkYW1hZ2VfbGlzdCI6WzBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2VdfSx7ImRlZl9wYXJhbSI6MTY2NTUzNzQsImNoYXJhX3Bvc2l0aW9uIjozLCJkYW1hZ2VfbGlzdCI6WzBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2VdfSx7ImRlZl9wYXJhbSI6MjEzMTM2MzEsImNoYXJhX3Bvc2l0aW9uIjo0LCJkYW1hZ2VfbGlzdCI6WzBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2VdfV19fSx7ImNvbW1hbmRfY291bnQiOjIsImNvbW1hbmRfdHlwZSI6MiwibV9jb21tYW5kX2lkIjoyMjYsImlzX3BsYXllciI6ZmFsc2UsImNoYXJhX3Bvc2l0aW9uIjoxLCJyZW1haW5pbmdfZnJhbWUiOjg1MiwicGxheWVyX2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls0MCwwLDI1LDE1LDEwLDAsMF0sInRpbWVsaW5lIjo2NTQuMCwiaHAiOjI0MTI4NjUwLCJtX2NoYXJhY3Rlcl9pZCI6M30seyJjaGFyYV9wb3NpdGlvbiI6MSwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNDAsMCwyNSwxNSwxMCwwLDBdLCJ0aW1lbGluZSI6NjEyLjAsImhwIjozNjk3LCJtX2NoYXJhY3Rlcl9pZCI6MjAwNDh9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzQwLDAsMjUsMTUsMTAsMCwwXSwidGltZWxpbmUiOjY0Mi4wLCJocCI6NzA1MzEzNzQsIm1fY2hhcmFjdGVyX2lkIjoxNTJ9LHsiY2hhcmFfcG9zaXRpb24iOjMsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzQwLDAsMjUsMTUsMTAsMCwwXSwidGltZWxpbmUiOjgzNC4wLCJocCI6NjQ4NjQ0MDIsIm1fY2hhcmFjdGVyX2lkIjoxNDh9LHsiY2hhcmFfcG9zaXRpb24iOjQsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzQwLDAsMjUsMTUsMTAsMCwwXSwidGltZWxpbmUiOjY0OC4wLCJocCI6MTExNTEzMTcyLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjEwMC4wLCJocCI6MTQwOTkxNywibV9jaGFyYWN0ZXJfaWQiOjYwMDM4fSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjM5ODg4LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6OTA2LjAsImhwIjozOTg4OCwibV9jaGFyYWN0ZXJfaWQiOjMwMDEwfV0sImRhbWFnZV9jb21tYW5kIjp7ImF0a19wYXJhbSI6MzcxLCJzcGRfcGFyYW0iOjUxLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjo2MjkzMjM5LCJjaGFyYV9wb3NpdGlvbiI6MCwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19LHsiZGVmX3BhcmFtIjoxNTAzLCJjaGFyYV9wb3NpdGlvbiI6MSwiZGFtYWdlX2xpc3QiOlsyMywyMiwyMl0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19LHsiZGVmX3BhcmFtIjoxNzk0MzMzOSwiY2hhcmFfcG9zaXRpb24iOjIsImRhbWFnZV9saXN0IjpbMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsZmFsc2VdfSx7ImRlZl9wYXJhbSI6MjA4MDM3MjksImNoYXJhX3Bvc2l0aW9uIjozLCJkYW1hZ2VfbGlzdCI6WzAsMCwwXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlLGZhbHNlLGZhbHNlXX0seyJkZWZfcGFyYW0iOjM2MDg5MzYxLCJjaGFyYV9wb3NpdGlvbiI6NCwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19XX19LHsiY29tbWFuZF9jb3VudCI6MywiY29tbWFuZF90eXBlIjoyLCJtX2NvbW1hbmRfaWQiOjIyNiwiaXNfcGxheWVyIjpmYWxzZSwiY2hhcmFfcG9zaXRpb24iOjIsInJlbWFpbmluZ19mcmFtZSI6ODQ0LCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc1Ny4wLCJocCI6MjQxMjg2NTAsIm1fY2hhcmFjdGVyX2lkIjozfSx7ImNoYXJhX3Bvc2l0aW9uIjoxLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOls1MCwwLDI1LDMwLDIwLDAsMF0sInRpbWVsaW5lIjo3MDguMCwiaHAiOjM2MjcsIm1fY2hhcmFjdGVyX2lkIjoyMDA0OH0seyJjaGFyYV9wb3NpdGlvbiI6MiwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNTAsMCwyNSwzMCwyMCwwLDBdLCJ0aW1lbGluZSI6NzQzLjAsImhwIjo3MDUzMTM3NCwibV9jaGFyYWN0ZXJfaWQiOjE1Mn0seyJjaGFyYV9wb3NpdGlvbiI6MywiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNTAsMCwyNSwzMCwyMCwwLDBdLCJ0aW1lbGluZSI6OTY0LjAsImhwIjo2NDg2NDQwMiwibV9jaGFyYWN0ZXJfaWQiOjE0OH0seyJjaGFyYV9wb3NpdGlvbiI6NCwiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNTAsMCwyNSwzMCwyMCwwLDBdLCJ0aW1lbGluZSI6NzUwLjAsImhwIjoxMTE1MTMxNzIsIm1fY2hhcmFjdGVyX2lkIjoxNTF9XSwiZW5lbXlfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MjAwLjAsImhwIjoxNDA5OTE3LCJtX2NoYXJhY3Rlcl9pZCI6NjAwMzh9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MTAxLjAsImhwIjozOTg4OCwibV9jaGFyYWN0ZXJfaWQiOjMwMDEwfSx7ImNoYXJhX3Bvc2l0aW9uIjoyLCJidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwiZGVidWZmX3ZhbHVlX2xpc3QiOlswLDAsMCwwLDAsMCwwXSwidGltZWxpbmUiOjAuMCwiaHAiOjM5ODg4LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9XSwiZGFtYWdlX2NvbW1hbmQiOnsiYXRrX3BhcmFtIjozNzEsInNwZF9wYXJhbSI6NTEsImRhbWFnZV9saXN0IjpbeyJkZWZfcGFyYW0iOjYyOTMyMzksImNoYXJhX3Bvc2l0aW9uIjowLCJkYW1hZ2VfbGlzdCI6WzAsMCwwXSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlLGZhbHNlLGZhbHNlXX0seyJkZWZfcGFyYW0iOjE1MDMsImNoYXJhX3Bvc2l0aW9uIjoxLCJkYW1hZ2VfbGlzdCI6WzIzLDIzLDI0XSwiaXNfY3JpdGljYWxfbGlzdCI6W2ZhbHNlLGZhbHNlLGZhbHNlXX0seyJkZWZfcGFyYW0iOjE3OTQzMzM5LCJjaGFyYV9wb3NpdGlvbiI6MiwiZGFtYWdlX2xpc3QiOlswLDAsMF0sImlzX2NyaXRpY2FsX2xpc3QiOltmYWxzZSxmYWxzZSxmYWxzZV19LHsiZGVmX3BhcmFtIjoyMDgwMzcyOSwiY2hhcmFfcG9zaXRpb24iOjMsImRhbWFnZV9saXN0IjpbMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsdHJ1ZV19LHsiZGVmX3BhcmFtIjozNjA4OTM2MSwiY2hhcmFfcG9zaXRpb24iOjQsImRhbWFnZV9saXN0IjpbMCwwLDBdLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2UsZmFsc2VdfV19fSx7ImNvbW1hbmRfY291bnQiOjQsImNvbW1hbmRfdHlwZSI6MiwibV9jb21tYW5kX2lkIjoxMDAwMzYsImlzX3BsYXllciI6dHJ1ZSwiY2hhcmFfcG9zaXRpb24iOjMsInJlbWFpbmluZ19mcmFtZSI6ODQxLCJwbGF5ZXJfbGlzdCI6W3siY2hhcmFfcG9zaXRpb24iOjAsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc5My4zNzUsImhwIjoyNDEyODY1MCwibV9jaGFyYWN0ZXJfaWQiOjN9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc0Mi4xMjUsImhwIjozNjI3LCJtX2NoYXJhY3Rlcl9pZCI6MjAwNDh9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc3OC42MjUsImhwIjo3MDUzMTM3NCwibV9jaGFyYWN0ZXJfaWQiOjE1Mn0seyJjaGFyYV9wb3NpdGlvbiI6MywiYnVmZl92YWx1ZV9saXN0IjpbMCwwLDAsMCwwLDAsMF0sImRlYnVmZl92YWx1ZV9saXN0IjpbNTAsMCwyNSwzMCwyMCwwLDBdLCJ0aW1lbGluZSI6MC4wLCJocCI6NjQ4NjQ0MDIsIm1fY2hhcmFjdGVyX2lkIjoxNDh9LHsiY2hhcmFfcG9zaXRpb24iOjQsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzUwLDAsMjUsMzAsMjAsMCwwXSwidGltZWxpbmUiOjc4Ni4wLCJocCI6MTExNTEzMTcyLCJtX2NoYXJhY3Rlcl9pZCI6MTUxfV0sImVuZW15X2xpc3QiOlt7ImNoYXJhX3Bvc2l0aW9uIjowLCJidWZmX3ZhbHVlX2xpc3QiOltdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6W10sInRpbWVsaW5lIjowLjAsImhwIjowLCJtX2NoYXJhY3Rlcl9pZCI6NjAwMzh9LHsiY2hhcmFfcG9zaXRpb24iOjEsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MTM4Ljg3NSwiaHAiOjM5ODg4LCJtX2NoYXJhY3Rlcl9pZCI6MzAwMTB9LHsiY2hhcmFfcG9zaXRpb24iOjIsImJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJkZWJ1ZmZfdmFsdWVfbGlzdCI6WzAsMCwwLDAsMCwwLDBdLCJ0aW1lbGluZSI6MzcuODc1LCJocCI6Mzk4ODgsIm1fY2hhcmFjdGVyX2lkIjozMDAxMH1dLCJkYW1hZ2VfY29tbWFuZCI6eyJhdGtfcGFyYW0iOjI4Njc1NTM4LCJzcGRfcGFyYW0iOjcxLCJkYW1hZ2VfbGlzdCI6W3siZGVmX3BhcmFtIjo1ODIsImNoYXJhX3Bvc2l0aW9uIjowLCJkYW1hZ2VfbGlzdCI6WzU0ODA2Njk2MDQ3Miw1NTk5Nzg4NTQ4MTddLCJpc19jcml0aWNhbF9saXN0IjpbZmFsc2UsZmFsc2VdfV19fV19.0QZxfPP4ZeoPbJgZG_O7RxLv_g5rSk72V95XBmKN-y0",
                "m_character_id":0,
                "division_battle_result":"",
                "arena_battle_result":"",
                "battle_type":1,
                "result":0,
                "battle_exp_data":[{"m_enemy_id":enemy_id,"finish_type":2,"finish_member_ids":[197923696]}],
                "common_battle_result":"eyJhbGciOiJIUzI1NiJ9.eyJhODNiY2ZiODdhMmQ5MzQ5Ijo0LCJiYmVjNmUzMjA5OGQ2YjUyIjoxLCJoZmJtNzg0a2hrMjYzOXBmIjoiIiwieXBiMjgydXR0eno3NjJ3eCI6MTEwODA0NTgxNTI4OSwiZHBwY2JldzltejhjdXd3biI6MTgxMSwiemFjc3Y2amV2NGl3emp6bSI6MCwia3lxeW5pM25ubTNpMmFxYSI6MCwiZWNobTZ0aHR6Y2o0eXR5dCI6MCwiZWt1c3ZhcGdwcGlrMzVqaiI6MCwieGE1ZTMyMm1nZWo0ZjR5cSI6MX0.D4kxdQFOzgoTQKvLKzUb7v7cmGBuNnHfMFgH0ldLmgI",
                "skip_party_update_flg":True,
                "m_event_id":0,
                "board_battle_result":""
            })