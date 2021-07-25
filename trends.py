import pandas as pd 
from pytrends.request import TrendReq
import requests
from urllib.parse import quote
import datetime
import json


import os

BOT_API_KEY = os.environ['BOT_API_KEY']
CHAT_ID = os.environ['CHAT_ID']

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = ''
    bot_chatID = ''
    send_text = 'https://api.telegram.org/' + BOT_API_KEY+'/sendMessage?chat_id=' + CHAT_ID +'&parse_mode=Markdown&text=' + quote(bot_message)
    response = requests.get(send_text)
    return response.json()

def chunkIt(seq):
    print('len', len(seq), len(seq)/5)
    chunky = int(len(seq)/5)
    return [seq[i*5:(i+1)*5] for i in range(chunky + 1)]

def read_in_keywords():
    keywords = open('keywords.csv').read().strip().split(',')
    return keywords

def read_in_proxies():
    try:
        proxies = open('proxies.csv').read().strip().split(',')
        return proxies
    except:
        return []

while True:
    try:
        with open('config.json', 'r') as config_file:
            config_data = json.load(config_file)

        option = config_data['option']

        avg_multiplier = config_data['avg_multiplier']
        alert_threshold = config_data['alert_threshold']
        time_scale = config_data['time_scale']
        hours_to_compare = config_data['hours_to_compare']

        pytrends = TrendReq(hl='en-US', tz=360, proxies=read_in_proxies())
        done = False
        total = ''
        for chunk in chunkIt(read_in_keywords()):
            print('Fetching trends for ',chunk)
            pytrends.build_payload(chunk, timeframe='now 7-d')
            if not done:
                total = pytrends.interest_over_time().drop('isPartial', 1)
                done = True
            else:
                total = total.join(pytrends.interest_over_time().drop('isPartial', 1))
        print(telegram_bot_sendtext('\"Starting trends scrape at ' + str(datetime.datetime.now()) + ' with config avg multiplier ' + str(avg_multiplier) + ' alert threshold ' + str(alert_threshold) + ' time scale ' + str(time_scale) + ' hours compare ' + str(hours_to_compare) + '\"'))
        total.to_csv('trends.csv')
        for column in total:
            vals = total[column].values[-time_scale-hours_to_compare:]
            print(column, 'values ', hours_to_compare, 'before time scale which equals', time_scale, vals[:-time_scale])
            avg = vals[:-time_scale].mean()
            max_vals = vals[:-time_scale].max()
            if option == 'a':
                print(column, 'values in the time scale', vals[- time_scale:])
                vals_above_max = [i for i in vals[- time_scale:] if i > max_vals]
                print('For column', column, ' there are at least', len(vals_above_max), ' against threshold', alert_threshold, 'values bigger than max in the timescale, which equals=', max_vals)
                if len(vals_above_max) >= alert_threshold:
                    print(telegram_bot_sendtext('%s is currently trending, max %s in last %s hours was breached %s times' % (str(column), max_vals, str(time_scale), str(len(vals_above_max)))))
            else:
                print('For column', column, ' average in the last', time_scale, 'is equal to',vals[-time_scale:].mean(), 'in the timescale equals=', avg * avg_multiplier)
                if avg * avg_multiplier <= vals[-time_scale:].mean():
                    print(telegram_bot_sendtext('%s is currently trending, average in last %s hours = %s is bigger than average outside time scale %s x average multiplier %s = %s' % (str(column), str(time_scale), vals[-time_scale:].mean(), str(avg), str(avg_multiplier), str(avg * avg_multiplier))))
        import time
        print('Scraped', len(read_in_keywords()), 'keywords, repeating in an hour')
        time.sleep(3600)
    except Exception as e:
        print(e)
        print('Stopping')
        exit(0)
