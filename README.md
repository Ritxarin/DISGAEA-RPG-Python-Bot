# DISGAEA RPG Bot written in Python

requirements:

- Python v3.10+
- `pip install requests`
- `pip install python-dateutil`
- `pip install jwt`
- license key (get it from https://disgaea.codedbots.com, once you have the license key either create a BOT_TOKEN environmental variable or put it into `codedbots.py` on line 15. )

![bot running](https://raw.github.com/Mila432/DISGAEA-RPG-Python-Bot/master/1.png)

features:

- use serial codes
- finish all quests
- farm single quests
- farm full EPs
- every quest is finished with 3\*
- buy rare items from shop
- use free summons
- overlords tower supported
- farm item world for both weapons & armor
- catching innocents while farming item world
- multi region support gl & jp
- proxy support
- leech raid bosses
- run Axel contest
- automate fish fleet and item survey

## Auto login

1. go to <https://p-public.service.boltrend.com/oauthOs?appid=287&lang=en>
2. open developer tools -> network (ensure persist logs is on)
3. login via webpage
4. inspect the first requests payload, it should look something like:

   ```json
   {
     "appId": "287",
     "account": "<string>",
     "password": "<string>",
     "channel": 3,
     "captchaId": "",
     "validate": "",
     "sourceId": "",
     "sign": "<string>"
   }
   ```

5. Using the variables above set the following environmental variables:
   ```shell
   export STEAM_LOGIN='true'
   export DRPG_EMAIL="<account value>"
   export DRPG_PASS="<password value>"
   export DRPG_SIGN="<sign value>"
   ```
6. be sure to set your device to 3
   ```python
   a = API()
   a.o.wait = 0
   a.o.set_region(2)
   a.o.set_device(3)
   a.quick_login()
   ```

### Set envs using python

If you dont know how to set envs or are on window or w/e use this at the start of your bot script:

```python
import os

os.environ["STEAM_LOGIN"] = 'true'
os.environ["DRPG_EMAIL"] = "<account value>"
os.environ["DRPG_PASS"] = "<password value>"
os.environ["DRPG_SIGN"] = "<sign value>"

from main import API

a = API()
a.o.wait = 0
a.o.set_region(2)
a.o.set_device(3)
a.quick_login()
```

## Using the bot for JP

1. Create an account for JP (preferrably on DMM)
2. Get a transfer code
3. Set region to 1
4. Use jp_reroll_example.py Call the dologin method with the user id and one time code from the transfer. Paste the code in line 18.

```python
   code = 'TRANSFER CODE GOES HERE THE FIRST TIME YOU USE THE BOT'
```

5. The bot generates a new transfer code every time. It will be stored in transfercode.txt
6. After a few uses, you will run into the following error:

   ```json
      server returned error: undefined method `correct_signature?' for nil:NilClass for battle_status
   ```

When you do, open DRPG JP on a different device and use the transfer code there. You do not need to log in afterwards, once you've used the code you can use the bot once again.

8. Once you've succesfulyl logged in, you can use loginfromcache() instead of dologin. Instead of logging in again, it will resume the previous session. It will reduce the number og logins, thus making it so that the transfer code will break less often.
9. After logging in to the game (dmm/phone) or after a daily reset you will need to use a.dologin(user_id, one_time_code) before you can use loginfromcache() again.
10. If you want to reroll, copy the new transfer code into transfercode.txt, and use the new player id
