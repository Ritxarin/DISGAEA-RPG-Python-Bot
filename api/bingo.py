from abc import ABCMeta

from api.constants import Constants

class Bingo(metaclass=ABCMeta):
    
    def __init__(self):
        super().__init__()

    def bingo_index(self, bingo_id=Constants.Current_Bingo_ID):
        data = self.rpc('bingo/index', {"id":bingo_id})
        return data

    def bingo_lottery(self, bingo_id=Constants.Current_Bingo_ID, use_stone=False):
        data = self.rpc('bingo/lottery', {"id":bingo_id,"use_stone":use_stone})
        return data

    #ids takes an array like [57]
    def bingo_receive_reward(self, reward_id):
        data = self.rpc('bingo/receive', {"ids":reward_id})
        return data

    def bingo_is_spin_available(self):
        data = self.bingo_index()
        return  len(data['result']['t_bingo_data']['bingo_indexes']) < len(data['result']['t_bingo_data']['display_numbers']) and not data['result']['t_bingo_data']['drew_today']

    def bingo_claim_free_rewards(self):
        data = self.bingo_index()
        free_reward_positions = [0,3,6,9,12,15,18,21,24,27,30,33]
        bingo_rewards =  data['result']['rewards']
        free_rewards = [bingo_rewards[i] for i in free_reward_positions ]
        available_free_rewards = [x for x in free_rewards if x['status'] == 1] 
        if(len(available_free_rewards) > 0):
            print(f"Claiming {len(available_free_rewards)} free rewards...") 
        for reward in available_free_rewards:
            res = self.bingo_receive_reward([reward['id']])
        print("Finished claiming free rewards.")