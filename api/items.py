from api.shop import Shop


class Items(Shop):

    def can_item_be_sold(self, item, max_innocent_rank, max_item_rank, max_rarity):
        return self.pd.check_item(item, skip_max_lvl=True, max_innocent_rank=max_innocent_rank,
                                  max_item_rank=max_item_rank, max_rarity=max_rarity, only_max_lvl=False, skip_locked_innocent = False)

    def can_item_be_donated(self, item, max_innocent_rank, max_item_rank, max_rarity):
        return self.pd.check_item(item, skip_max_lvl=False, max_innocent_rank=max_innocent_rank,
                                  max_item_rank=max_item_rank, max_rarity=max_rarity, only_max_lvl=True, skip_locked_innocent = True)

