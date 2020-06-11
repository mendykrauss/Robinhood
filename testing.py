from __future__ import print_function
import robin_stocks as rs
#import login
import requests as rq
import json as j
from slack import WebClient
from slack import RTMClient
from slack.errors import SlackApiError
import os
import re
import time
#import utils as _utils
import traceback
import sys
#import schedule
from robin_stocks import account

rs.logout
rs.login('mendyk@idtechsolutionns.com', 'Abcd1290.*')
client = WebClient(token='xoxp-598678183767-598678184535-1161644462661-440b8f9f94b5c2f3d75fe01419ade10f')

#response = rq.get('https://api.robinhood.com/')

#
def checkStocks():
    myStocks = rs.build_holdings()
    for key, value in myStocks.items():
        quantity_int = str(int(float(value['quantity'])))
        #print(quantity_int)
        name = value['name']
        price = value['price']
        #quantity = quantity_int
        equity = value['equity']
        #print('-----')
        #print('')
        print(value['name'] + ' | ' + value['price'] + ' | ' + quantity_int + ' | ' + value['equity'])
        #print(value['name'] + '|' + value['price'] + '|' + value['equity'])
        '''quantity_int = value['quantity']
        print(value['name'])
        print(value['price'])
        print(int(float(quantity_int)))
        print(value['equity'])
        print('-----')
        print('')'''

output = ':moneybag: Total equity | $' + rs.account.build_user_profile()['extended_hours_equity'] + ' :moneybag:'
print(output)

if __name__ == '__main__':
    channel_id = "#robinhood"
    user_id = "robinhood_iw"
else:
    channel_id = "C0XXXXXX"
    user_id = "C0155166R8R"

response = client.chat_postMessage(
    channel=channel_id,
    text=output
)
#schedule.every(10).seconds.do(checkStocks)

#while True:
    #schedule.run_pending()
    #time.sleep(1)