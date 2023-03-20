from bot import Bot
from main import API

DRY_RUN = False

a = API()
bot = Bot(a)

# a.setProxy("127.0.0.1:8080")
a.o.wait = 0
a.o.set_region(2)
a.o.set_device(3)

if DRY_RUN:
    bot.load_from_file()
else:
    a.quick_login()

r_ids = [
    # Base stats
    # 1, 4, 7, 10, 13,
    # 2, 5, 8, 11, 14,
    3, 6, 9, 12, 15,
    # WM Enhancer
    16,
    # Super SKill
    19,
    # ATK&DEF
    # 22, 25, 28,
    # INT&RES
    # 31, 34, 37,
    # HP&DEF
    40, 43, 46,
    # HP&RES
    49, 52, 55,
    # Tutor
    58, 61, 64,
    # Almighty
    67
]


inno_blacklist = [x['id'] for x in a.find_recipe_innocents(True, recipe_ids=r_ids)]
tickets_used = {}
tickets_to_buy = {}
completed = {}


def complete_recipes(skip_equipped: bool = True, skip_advanced: bool = True, dry_run: bool = False,
                     recipe_ids=None):
    total_completed = 0
    recipes = []
    for recipe in a.gd.innocent_recipes:
        if recipe_ids is not None and recipe['id'] not in recipe_ids:
            continue

        if skip_advanced and recipe['id'] > 15:
            continue

        # if recipe['id'] != 1:
        #     continue

        recipes.append(recipe)
    conversions = []
    for recipe in recipes:
        conversions = check_recipe(recipe_id=recipe['id'], skip_equipped=skip_equipped)
        conversions = conversions + check_recipe(recipe_id=recipe['id'], skip_equipped=skip_equipped,
                                                 override_min_rank=True)
        for data in conversions:
            check_innocent_rank_and_train(data, dry_run)
            log_conversion(data)
            if not dry_run:
                a.etna_resort_graze(data['subject_id'], data['target_character_id'])

    for recipe in recipes:
        missing_mats, iids = check_recipe_mats(recipe, skip_equipped=skip_equipped)
        if len(iids) > 0:
            # a.log('complete %s' % recipe['name'])
            if recipe['name'] not in completed:
                completed[recipe['name']] = 0
            if not dry_run:
                a.etna_resort_complete_recipe(recipe['id'], iids)
                completed[recipe['name']] += 1
                total_completed += 1
    return total_completed


def check_innocent_rank_and_train(data, dry_run: bool = False):
    min_r = data['min_r']
    iid = data['subject_id']
    innocent = a.pd.get_innocent_by_id(iid=iid)
    i = a.pd.get_innocent_by_id(iid)
    subject_char_name = a.gd.get_innocent_name(i)

    if innocent['effect_rank'] < min_r:
        a.log('[%s] - lvl innocent from %s to %s' % (subject_char_name, innocent['effect_rank'], min_r))
        if not dry_run:
            bot.train_innocents(
                innocents=[innocent],
                innocent_type=None,
                max_innocent_rank=min_r
            )


def check_recipe(recipe_id: int, skip_equipped: bool = True, override_min_rank: bool = False):
    conversions = []
    recipe = a.gd.get_innocent_recipe(recipe_id)
    missing_mats, iids = check_recipe_mats(recipe, skip_equipped=skip_equipped)

    # If there is no missing mats, it can be completed
    if missing_mats is None:
        return conversions

    # gather all the possible conversions
    innocent_conversions = innocents_to_convert(missing_mats, override_min_rank=override_min_rank)

    # override min rank is false - we will graze without training - pick innocent with lowest value
    if not override_min_rank:
        innocent_conversions.sort(key=lambda x: x['subject_effect_values'], reverse=False)
    # otherwise, pick the one with the highest value to reduce training needed
    else:
        innocent_conversions.sort(key=lambda x: x['subject_effect_values'], reverse=True)
        
    for mat in missing_mats:
        for data in innocent_conversions:
            i = a.pd.get_innocent_by_id(data['subject_id'])
            # Skip equipped if true and on an equipment
            if skip_equipped and i['place_id'] > 0:
                continue

            # skip if it's not the right material
            if data['material_id'] != mat['id']:
                continue

            # Skip if it's in the blacklist
            if data['subject_id'] in inno_blacklist:
                continue

            # Check if we have tickets
            ticket_item_def = a.gd.get_ranch_ticket(data['target_character_id'])
            ticket_item = a.pd.get_item_by_id(data['ticket_id'])
            if ticket_item['id'] not in tickets_used:
                tickets_used[ticket_item['id']] = 0
            # Skip if we are out of tickets to convert
            if tickets_used[ticket_item['id']] >= ticket_item['num']:
                if ticket_item_def['id'] not in tickets_to_buy:
                    tickets_to_buy[ticket_item_def['id']] = 0
                tickets_to_buy[ticket_item_def['id']] += 1
                continue

            # If we are here we can do this conversion
            conversions.append(data)
            inno_blacklist.append(data['subject_id'])
            tickets_used[ticket_item['id']] += 1
            break
    return conversions


def check_recipe_mats(recipe, skip_equipped: bool = True, ):
    materials = recipe['materials']
    mat_map = {material['id']: a.find_recipe_material_innocents(material, skip_equipped=skip_equipped) for material in
               materials}
    missing = 0
    missing_mats = []
    for mat in materials:
        # if we are missing mats, lets see if we can find an innocent to convert
        if len(mat_map[mat['id']]) == 0:
            missing += 1
            missing_mats.append(mat)
    # if there are none missing, then recipe can be completed
    if missing == 0:
        a.log('recipe %s can be completed!' % recipe['name'])
        iids = []
        for mat in materials:
            iids.append(mat_map[mat['id']][0]['id'])
        return None, iids
    else:
        a.log('recipe %s is missing %d materials' % (recipe['name'], missing))
        return missing_mats, []


def sort_data(e):
    return e['target_character_id']


def log_conversion(data):
    i = a.pd.get_innocent_by_id(data['subject_id'])

    # Grab human-readable names
    target_type_name = a.gd.get_innocent_type(data['target_innocent_id'])['name']
    subject_char_name = a.gd.get_innocent_name(i)
    ticket_item_def = a.gd.get_ranch_ticket(data['target_character_id'])

    a.log('ticket: "%s" -> "%s" : "%s" %s' % (
        ticket_item_def['name'], target_type_name, subject_char_name, i['effect_values'][0]))


# will provide a list of innocents that could be converted to complete recipe
# if loose_check is True it will ignore the innocents rank, so it can be leveled up later
def innocents_to_convert(missing_mats, override_min_rank: bool = False):
    conversions = []

    for mat in missing_mats:
        # if we are missing mats, lets see if we can find an innocent to convert
        min_r, max_r = a.gd.get_innocent_rank_min_max(mat['rank'])
        m_character_id = mat['m_character_id']
        m_innocent_id = mat['m_innocent_id']

        # Gather ticket info for conversion
        ticket_item_def = a.gd.get_ranch_ticket(m_character_id)
        ticket_item = a.pd.get_item_by_m_item_id(ticket_item_def['id'])

        # a.log('complete_recipes - %s - missing materials, mat_id: %s' % (recipe['name'], mat['id']))
        # look for an innocent with matching rank and type
        for i in a.player_innocents():
            if i['m_innocent_id'] == m_innocent_id and bot.check_innocent_rank(i, mat['rank'], override_min_rank):
                conversions.append({
                    'material_id': mat['id'],
                    'target_character_id': m_character_id,
                    'target_innocent_id': m_innocent_id,
                    'subject_id': i['id'],
                    'subject_character_id': i['m_character_id'],
                    'subject_innocent_id': m_innocent_id,
                    'subject_effect_values': i['effect_values'],
                    'ticket_id': ticket_item['id'],
                    'min_r': min_r,
                    'max_r': max_r,
                })

    return conversions


def print_results():
    print("Completed:")
    for name in completed:
        print('\t"%s" => %d' % (name, completed[name]))

    print('Tickets Needed:')
    for tid in tickets_to_buy:
        item = a.gd.get_item(tid)
        print('\t"%s" => %d' % (item['name'], tickets_to_buy[tid]))
    exit(0)


# recipes = range(40, 69)
while True:
    # # Uncomment to remove all innocents from all equipment
    # try:
    #     matches, skipping = a.pd.filter_items(min_innocent_count=1, skip_locked=False,
    #                                           max_rarity=999, max_item_rank=99)
    #     for e in matches:
    #         a.log('removing innocents from %s' % e['id'])
    #         a.remove_innocents(e)
    # except:
    #     a.log('Max innocents reached')

    total = complete_recipes(skip_advanced=False, dry_run=DRY_RUN, recipe_ids=r_ids)

    if not DRY_RUN:
        bot.train_recipe_innocents()

    if total == 0:
        print_results()

# a.dump_player_data("./player_data.json")
