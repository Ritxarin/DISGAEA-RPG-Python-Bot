from abc import ABCMeta

from api.base import Base
from api.constants import Constants


class Dark_Assembly(Base, metaclass=ABCMeta):

    def __init__(self):
        super().__init__()

    def vote_dark_assembly_agenda(self, agenda_id=138, use_bribes=False):
        agendas = self.client.agenda_index()
        agenda = next((x for x in agendas['result']['t_agendas'] if x['m_agenda_id'] == agenda_id), None)
        if agenda is None:
            self.log(f"Agenda with id {agenda_id} is not found")
            return

        if agenda['status'] != 0:
            self.log(f"Agenda has already been passed.")
            return
        r1 = self.client.agenda_start(agenda_id)
        if 'api_error' in r1:
            return
        
        bribe_data = []
        #[{"lowmaker_id":26776096,"item_id":402,"num":1},{"lowmaker_id":26776096,"item_id":401,"num":1}]
        if use_bribes:
            senators_to_bribe = [x for x in r1['result']['t_lowmakers'] if x['power'] >= 9]
            for senator in senators_to_bribe:
                if senator['fav_rate'] >=6:
                    continue
                bribe_data.append(
                    {"lowmaker_id":senator['id'],"item_id":401,"num":6-senator['fav_rate']}
                )
        r2 = self.client.agenda_vote(agenda_id, bribe_data)
        self.log(r2['result']['result_message'])
        self.client.agenda_get_campaign()
        
    def has_agenda_been_passed(self, agenda_id):
        agendas = self.client.agenda_index()
        agenda = next((x for x in agendas['result']['t_agendas'] if x['m_agenda_id'] == agenda_id), None)
        if agenda is None:
            self.log(f"Agenda with id {agenda_id} is not found")
            return None

        if agenda['status'] != 0:
            return True
        return False
    
    def pass_agendas_of_type(self, agenda_type):
        all_agendas = self.client.agenda_index()['result']['t_agendas']
        all_available_agendas = [a for a in all_agendas if a['status'] == 0]
        no_points_left = False
        for agenda in all_available_agendas:
            if no_points_left == True:
                break
            agenda_data = next((x for x in self.gd.agendas if x['id'] == agenda['m_agenda_id']),None)
            if agenda_data is not None and agenda_data['agenda_type']== agenda_type: 
                player_status = self.client.player_index()
                retry = True
                while retry:
                    agenda_points = player_status['result']['status']['agenda_point']
                    if agenda_points >= agenda_data['point']:
                        self.vote_dark_assembly_agenda(agenda_id=agenda_data['id'], use_bribes=False)
                        player_status = self.client.player_index()
                        if self.has_agenda_been_passed(agenda_id=agenda_data['id']) == False:
                            retry = True
                        else:
                            retry = False
                    else:
                        retry = False
                        no_points_left = True