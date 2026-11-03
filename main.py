import os
import requests
import requests_cache
from requests_cache import DO_NOT_CACHE
from datetime import date,timedelta
from langdetect import detect
from dotenv import load_dotenv
import smtplib
import time
from typing import Any


def send_mail(message):
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user=MY_EMAIL, password=MY_PASSWORD)
        connection.sendmail(from_addr=MY_EMAIL, to_addrs=SEND_TO, msg=message.encode('utf-8'))


def get_nws(parameters, num_articles: int = 3):
    articles = []
    nws_response = requests.get(url=NWS_API_ENDPOINT, params=parameters)
    nws_response.raise_for_status()
    nws = nws_response.json()
    len_articles = len(articles)
    index = 0
    while len(articles) < num_articles:
        if index >= len(nws['articles']):
            break
        news = nws['articles'][index]

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
    if not articles:
        articles = []
    return articles

# print(get_nws())
def get_stk_info(parameters: dict, day_of, size: int = 2) -> list[dict[str, Any]]:
    stk_info = []

    if size < 2:
        raise ValueError(f"Size must be greater than 1")


    url: str = STK_API_ENDPOINT
    try:

        response = requests.get(url, params=parameters)
        # print(response)

        response.raise_for_status()
        print(f"Error status of {parameters['symbol']}: ", response.raise_for_status())

        data = response.json().get('Time Series (Daily)', {})

        print(f'Response from cache: {response.from_cache}, Response created at: {response.created_at}, Respnse Expires on: {response.expires}')


        source: str = 'CACHE' if getattr(response, 'from_cache', False) else 'API'
        day = day_of

        if source == 'API':
            time.sleep(3)
        attempt = 0
        if 'Information' in response.json():

            return [{'Error':response.json()['Information']}]
        while  len(stk_info)<size:
            attempt +=1
            if attempt == 10:
                break
            try:
                new_data = data[str(day)]
            except KeyError:
                day = day - timedelta(days=1)

            else:
                stk_info.append({
                    'day':str(day),
                    'symbol': parameters['symbol'] ,
                    'source': source,
                    'info': new_data
                })
                day = day - timedelta(days=1)

        return stk_info
    except Exception as e:
        print(response.text)



        return [{'Error': f'{e}'}]












def check_last_two_days(*args, number_of_articles, w_target: float = 0.3):
    header = f"Subject: Stock News\nMIME-Version: 1.0\nContent-Type: text/html; charset=utf-8\n\n"
    msg = header

    # print(f"companies: {args[0]['symbol']},{args[1]['symbol']},{args[2]['symbol']}")
    for company in args:
        print("company", company['symbol'])

        stk_params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': company['symbol'],
            'apikey': STK_API_KEY
        }

        day = date.today()
        stk_info = get_stk_info(stk_params, day_of=day)
        print("stk_info: ", stk_info)
        if stk_info  and 'Error' in stk_info[0]:
            print(f"{stk_info[0]['Error']}")
        else:
            try:
                print("temp debug", stk_info[0])
                # opn = float(stk_info[0]['info']['1. open'])
                cls = float(stk_info[0]['info']['4. close'])
                # opn_prv = float(stk_info[1]['info']['1. open'])
                cls_prv = float(stk_info[1]['info']['4. close'])
                difference = cls- cls_prv
                pct = difference/cls_prv *100

                nws_params = {
                    'q': company['name'],
                    'from': stk_info[1]['day'],
                    'sortBy': 'relevancy',
                    'apiKey': NWS_API_KEY
                }

                if  pct > w_target:
                    print(f"Difference of {pct}% with {company['name']}\n{'#'*100}\n")
                    news = get_nws(nws_params, num_articles = number_of_articles)
                    msg += f"""
                    <div>
                            <hr>
                            <h2>{company['name']} 🔺{round(pct, 2)}%</h2>
                            <hr>
                    </div>
                    """
                    if news:
                        for i in range(len(news)):
                            msg += f"""
                            <div>
                                <h3>{news[i]['title']}</h3>
                                <p>{news[i]['description']}</p>
                                <p><a href='{news[i]['url']}'>Read full article</a></p>
                                
                            </div>
                            """
                    else:
                        msg+=f"""<p>No English news article found for {company['name']}</p>"""


                elif pct < -1* w_target:
                    print(f"Difference of {pct}% with {company['name']}\n{'#'*100}\n")

                    news = get_nws(nws_params,  num_articles = number_of_articles)
                    msg += f"""
                    <div>
                            <hr>
                            <h2>{company['name']} 🔻{round(pct, 2)}%</h2>
                            <hr>
                    </div>
                    """
                    if news:
                        for i in range(len(news)):
                            msg+= f"""
                            <div>
                                <h3>{news[i]['title']}</h3>
                                <p>{news[i]['description']}</p>
                                <p><a href='{news[i]['url']}'>Read full article</a></p>
                                
                            </div>
                            """
                    else:
                        msg+=f"""<p>No English news article found for {company['name']}</p>"""
                else:
                    print(f"Difference less than {w_target}% with {company['name']}\n{'#'*100}\n")
            except Exception as e:
                print(f"Error: {e}")

    if len(msg) > len(header):
        send_mail(msg)



load_dotenv()
def valid_stk_response(response):
    try:
        return 'Time Series (Daily)' in response.json()
    except ValueError:
        return False

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


requests_cache.install_cache(
    'stk_cache',
    backend='sqlite',
    expire_after= timedelta(hours=24),
    urls_expire_after={
        NWS_API_ENDPOINT:DO_NOT_CACHE
    },
    filter_fn=valid_stk_response
)

check_last_two_days( tesla, nvidia, delta, w_target = 1,number_of_articles=6)















