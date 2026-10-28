import os
import requests
import requests_cache
from datetime import date,timedelta
from langdetect import detect
from dotenv import load_dotenv
import smtplib


def send_mail(message):
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user=MY_EMAIL, password=MY_PASSWORD)
        connection.sendmail(from_addr=MY_EMAIL, to_addrs=SEND_TO, msg=message.encode('utf-8'))


def get_nws(parameters):
    articles = []
    nws_response = requests.get(url=NWS_API_ENDPOINT, params=parameters)
    nws_response.raise_for_status()
    len_articles = len(articles)
    index = 0
    while len(articles) < 3:

        news = nws_response.json()['articles'][index]
        title = news['title']
        try:
            if detect(title) == 'en':
                description= news['description']
                nws_url = news['url']
                content = news['content']
                index +=1
                articles.append(news)
            else:
                index +=1
        except:
            index +=1
    return articles

# print(get_nws())
def get_stk_info(parameters: dict, day_of):
    stk_info = []
    day_before = day_of-timedelta(days=1)
    keys = [day_of,day_before]
    for key in keys:
        url: str = STK_API_ENDPOINT
        try:
            # print(key)
            response = requests.get(url,params=parameters)
            response.raise_for_status()
            data = response.json().get('Time Series (Daily)',{})
            source: str = 'CACHE' if getattr(response, 'from_cache', False) else 'API'

            keep_trying = True
            while keep_trying:
                try:
                    new_data = data[str(key)]
                    keep_trying = False
                except KeyError:

                    new_key = key - timedelta(days=1)
                    keys[1] = new_key - timedelta(days=1)
                    key = new_key
                    keep_trying = True

                else:
                    stk_info.append({
                        'day':str(key),
                        'symbol': parameters['symbol'] ,
                        'source': source,
                        'info': new_data
                    })


        except Exception as e:
            return {'Error': f'{e}'}
    return stk_info



def check_last_two_days(*args):
    msg = f"Subject: Stock News\nMIME-Version: 1.0\nContent-Type: text/html; charset=utf-8\n\n"

    for company in args:

        stk_params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': company['symbol'],
            'apikey': STK_API_KEY
        }

        nws_params = {
            'q':  company['name'],
            'from': '2026-10-21',
            'sortBy': 'relevancy',
            'apiKey': NWS_API_KEY
        }

        day = date.today() - timedelta(days=1)
        data = get_stk_info(stk_params, day_of=day)
        opn = float(data[0]['info']['1. open'])
        cls = float(data[0]['info']['4. close'])
        opn_prv = float(data[1]['info']['1. open'])
        cls_prv = float(data[1]['info']['4. close'])
        print(data)
        difference = cls- cls_prv
        pct = difference/cls *100


        if  pct > 3:

            news = get_nws(nws_params)
            msg += f"""
            <div>
                    <hr>
                    <h2>{company['name']} 🔺{round(pct, 2)}%</h2>
                    <hr>
            </div>
            """
            for i in range(len(news)):
                msg += f"""
                <div>
                    <h3>{news[i]['title']}</h3>
                    <p>{news[i]['description']}</p>
                    <p><a href='{news[i]['url']}'>Read full article</a></p>
                    
                </div>
                """

        elif pct < -3:

            news = get_nws(nws_params)
            msg += f"""
            <div>
                    <hr>
                    <h2>{company['name']} 🔻{round(pct, 2)}%</h2>
            </div>
            """
            for i in range(len(news)):
                msg+= f"""
                <div>
                    <h3>{news[i]['title']}</h3>
                    <p>{news[i]['description']}</p>
                    <p><a href='{news[i]['url']}'>Read full article</a></p>
                    
                </div>
                """
        else:
            print(f"{company} else case")

    if len(msg) > len('Subject: Stock News\n\n'):
        send_mail(msg)



load_dotenv()
date = date.today()
requests_cache.install_cache('stk_cache')

STK_API_ENDPOINT = "https://www.alphavantage.co/query"
NWS_API_KEY = os.environ.get("NWS_API_KEY")

NWS_API_ENDPOINT = "https://newsapi.org/v2/everything"
STK_API_KEY = os.environ.get("STK_API_KEY")

MY_EMAIL=os.environ.get("MY_EMAIL")
MY_PASSWORD=os.environ.get("MY_PASSWORD")
SEND_TO=os.environ.get("SEND_TO")

delta = {'symbol':"DAL", 'name':"Delta Air Lines"}
tesla = {'symbol':'TSLA','name':"Tesla"}
nvidia = {'symbol':'NVDA', 'name':'Nvidia'}


check_last_two_days(delta, tesla, nvidia)



