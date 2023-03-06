import datetime

from dateutil import parser

from api.player import Player


class Gatcha(Player):
    def __init__(self):
        super().__init__()

    def get_free_gacha(self):
        if self.is_free_gacha_available():
            res = self.client.gacha_do(is_gacha_free=True, price=0, item_type=2, num=1, m_gacha_id=100001, item_id=0, total_draw_count=self.get_gacha_pull_count())
            unit_obtained = self.gd.get_character(res['result']['gacha_result'][0]['item_id'])
            print(f"Obtained {res['result']['gacha_result'][0]['rarity']}★ character {unit_obtained['name']}")

    def is_free_gacha_available(self):
        player_data = self.client.player_index()
        last_free_gacha_at_string = player_data['result']['status']['last_free_gacha_at']
        last_free_gacha_at_string_date = parser.parse(last_free_gacha_at_string)
        time_delta = -4 if self.o.region == 2 else 9
        server_date_time = datetime.datetime.utcnow() + datetime.timedelta(hours=time_delta)
        return server_date_time.date() > last_free_gacha_at_string_date.date()

    def get_gacha_pull_count(self, m_gacha_id = 100001):
        gacha_data = self.client.gacha_sums()
        premium_banner = next((x for x in gacha_data['result']['_items'] if x['m_gacha_id'] == m_gacha_id),None)
        if premium_banner is not None:
            return premium_banner['total_draw_count']
        return 0

    def is_free_10pull_available(self, m_gacha_id, max_draws):
        banner_data = self.client.gacha_sums()
        banner = next((x for x in banner_data['result']['_items'] if x['m_gacha_id'] == m_gacha_id),None)
        if banner is  None:
            return True
        last_pull_at_string = banner['last_draw_at']
        last_pull_at_date = parser.parse(last_pull_at_string)
        time_delta = -4 if self.o.region == 2 else 9
        server_date_time = datetime.datetime.utcnow() + datetime.timedelta(hours=time_delta)
        return server_date_time.date() > last_pull_at_date.date() and banner['total_draw_count'] < max_draws

    def get_free_10pull(self, m_gacha_id, max_draws):
        if self.is_free_10pull_available(m_gacha_id, max_draws):
            res = self.client.gacha_do(is_gacha_free=False, price=0, item_type=2, num=10, m_gacha_id=m_gacha_id, item_id=0, total_draw_count=self.get_gacha_pull_count(m_gacha_id))
            for unit in res['result']['gacha_result']:
                unit_obtained = self.gd.get_character(unit['item_id'])
                print(f"Obtained {unit_obtained['base_rare']}★ character {unit_obtained['name']}")