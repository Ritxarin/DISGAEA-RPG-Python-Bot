from abc import ABC

from api.axel_contest import AxelContest
from api.base import Base
from api.battle import Battle
from api.bingo import Bingo
from api.etna_resort import EtnaResort
from api.fish_fleet import FishFleet
from api.gatcha import Gatcha
from api.items import Items
from api.player import Player
from api.raid import Raid
from api.shop import Shop
from api.spar_space import SparSpace
from api.item_survey import ItemSurvey
from api.Event import Event
from api.PvP import PvP
from api.sugoroku import Sugoroku
from api.dark_assembly import Dark_Assembly
from api.final_boss_lab import FinalBossLab

class BaseAPI(Bingo, Raid, AxelContest, SparSpace, FishFleet, Gatcha, Battle, EtnaResort, ItemSurvey, Event, PvP, Sugoroku, Dark_Assembly, FinalBossLab, ABC):
    def __init__(self):
        super().__init__()
