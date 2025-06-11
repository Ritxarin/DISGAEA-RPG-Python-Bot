import random
import time
from abc import ABCMeta

from api.constants import Item_World_Drop_Mode

from api.constants import Battle_Finish_Type
from api.player import Player


class Battle(Player, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()

    def battle_help_get_friend_by_id(self, help_t_player_id):
        friend = None
        self.log("Looking for friend")
        while friend is None:
            help_players = self.client.battle_help_list()['result']['help_players']
            friend = next((x for x in help_players if x['t_player_id'] == help_t_player_id), None)
            # time.sleep(1)
        return friend

    def battle_skip(self, m_stage_id:int, skip_number:int, help_t_player_id: int = 0):

        if help_t_player_id == 0:
            helper_player = self.client.battle_help_list()['result']['help_players'][0]
        else:
            helper_player = self.battle_help_get_friend_by_id(help_t_player_id)

        reincarnation_character_ids = []
        if self.o.auto_rebirth:            
            if len(self.o.auto_rebirth_character_ids) > 0:
                 reincarnation_character_ids = self.o.auto_rebirth_character_ids
            else:
                reincarnation_character_ids = self.pd.deck(self.o.team_num)
        return self.client.battle_skip(m_stage_id=m_stage_id, deck_no=self.o.team_num, skip_number=skip_number,
                                       helper_player=helper_player, reincarnation_character_ids=reincarnation_character_ids)

    # m_stage_ids [5010711,5010712,5010713,5010714,5010715] for monster reincarnation
    def battle_skip_stages(self, m_stage_ids:list[int], help_t_player_id:int=0, skip_number:int=3):
        if help_t_player_id == 0:
            helper_player = self.client.battle_help_list()['result']['help_players'][0]
        else:
            helper_player = self.battle_help_get_friend_by_id(help_t_player_id)
        reincarnation_character_ids = []
        if self.o.auto_rebirth:            
            if len(self.o.auto_rebirth_character_ids) > 0:
                 reincarnation_character_ids = self.o.auto_rebirth_character_ids
            else:
                reincarnation_character_ids = self.pd.deck(self.o.team_num)
        return self.client.battle_skip_stages(
            m_stage_ids=m_stage_ids, helper_player=helper_player,
            deck_no=self.o.team_num, reincarnation_character_ids=reincarnation_character_ids, skip_number=skip_number)

    ## Finish battle, kills will be distributed randomly
    def get_battle_exp_data(self, start):
        res = []
        for d in start['result']['enemy_list']:
            for r in d:
                if d[r] != 0:
                    res.append({
                        "finish_member_ids": self.get_random_deck_member(start['result']['t_deck_no']),
                        "finish_type": random.randint(Battle_Finish_Type.Normal_Attack, Battle_Finish_Type.Special_Move),
                        "m_enemy_id": d[r]
                    })
        return res

    def get_random_deck_member(self, deck_no):
        character = []
        characters_count = len(self.pd.deck(deck_no))
        rand_char = self.pd.deck(deck_no)[random.randint(0, characters_count-1)]
        character.append(rand_char)
        return character

    # Finish battle using tower attacks. Exp will be shared evenly
    def get_battle_exp_data_tower_finish(self, start):
        res = []
        for d in start['result']['enemy_list']:
            for r in d:
                if d[r] != 0:
                    res.append({
                        "finish_member_ids": self.pd.deck(start['result']['t_deck_no']),
                        "finish_type": Battle_Finish_Type.Tower_Attack.value,
                        "m_enemy_id": d[r]
                    })
        return res

    ## Finish battle, leader unit kills all enemies thus grabbing all bonus exp
    def get_battle_exp_data_single_unit_finish(self, start):
        active_party = start['result']['t_deck_no']
        team = self.player_decks()[active_party-1] 
        leader_unit = team['leader_t_character_id']
        res = []
        for d in start['result']['enemy_list']:
            for r in d:
                if d[r] != 0:
                    res.append({
                        "finish_member_ids": [leader_unit],
                        "finish_type": Battle_Finish_Type.Special_Move,
                        "m_enemy_id": d[r]
                    })
        return res

    def do_tower(self, m_tower_no=1):
        start = self.client.tower_start(m_tower_no)
        end = self.client.battle_end(battle_exp_data=self.get_battle_exp_data(start),
                                     m_tower_no=m_tower_no,
                                     m_stage_id=0,
                                     battle_type=4,
                                     result=1)
        return end

    def parse_start(self, start):
        if 'result' in start and 'reward_id' in start['result']:
            # reward_id = start['result']['reward_id'][10]
            # reward_type = start['result']['reward_type'][10]
            # reward_rarity = start['result']['reward_rarity'][10]
            reward_id = start['result']['reward_id'][0]
            reward_type = start['result']['reward_type'][0]
            reward_rarity = start['result']['reward_rarity'][0]

            # stage with no drops or ensure_drops is false, continue
            if start['result']['stage'] % 10 != 0 or not self.options.item_world_ensure_drops:
                return 1

            # no drop, ensuring drops, retry
            if reward_id == 101:
                return 5

            item = self.gd.get_weapon(reward_id) if reward_type == 3 else self.gd.get_equipment(reward_id)
            reward_rank = self.gd.get_item_rank(item)

            # drop, no Item General/King/God stage, continue
            if start['result']['stage'] not in {30, 60, 90, 100}:
                self.log('[+] found item: %s with rarity: %s rank: %s' % (item['name'], reward_rarity, reward_rank))
                return 1

            # drop, rarity less than min_rarity, retry
            if reward_rarity < self.o.min_drop_item_rarity:
                return 5

            # equipment drop, but farming only weapons, retry
            if reward_type == 4 and self.options.item_world_drop_mode == Item_World_Drop_Mode.Drop_Weapons_Only:
                return 5

            item = self.gd.get_weapon(reward_id) if reward_type == 3 else self.gd.get_equipment(reward_id)

            # drop, rank less than min_rank, retry
            # FIXME: should check to see if the rank can even be found from the item
            if self.o.min_rank > 0 and reward_rank < self.o.min_rank:
                return 5

            if item is None:
                item = {'name': ''}

            self.log('[+] found item: %s with rarity: %s rank: %s' % (item['name'], reward_rarity, reward_rank))
            return 1
        else:
            return 1
