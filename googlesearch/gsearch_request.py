# This source is modification of pytrends please refer below URL
## https://pypi.org/project/pytrends/
from __future__ import absolute_import, print_function, unicode_literals

import json
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests


from pandas.io.json._normalize import nested_to_record
from requests.packages.urllib3.util.retry import Retry

from pytrends import exceptions

if sys.version_info[0] == 2:  # Python 2
    from urllib import quote
else:  # Python 3
    from urllib.parse import quote


import requests_random_user_agent
from fake_headers import Headers

from bs4 import BeautifulSoup
import pandas as pd
import time
import platform as pltfrm
import os, sys
import re



class SearchReq(object):
    """
    Google Search API
    """
    GET_METHOD = 'get'
    POST_METHOD = 'post'
    GENRAL_URL = 'https://www.google.com'
    SEARCH_URL = 'https://www.google.com/search?'
    PARAMS_SET = {'sa': 'sa=X', 'source': 'source=lmns'}
    SEARCH_CAT = {'all':'', 'news':'nws', 'image':'isch', 'video':'vid', }

    """docstring for SearchReq"""
    def __init__(self, hl='en-US', lr=None, timeout=(10,30), proxies_itr=[], retries=0, backoff_factor=0, requests_args=None):
        """
        hl will be used in token
        """
        super(SearchReq, self).__init__()
        self.google_rl = 'Reached Quota Limit. Please try again later.'
        # External Parameters
        self.result = None
        self.hl = hl
        self.lr = lr
        self.timeout = timeout
        self.proxies = proxies_itr
        self.retries = retries
        self.backoff_factor = backoff_factor
        # Internal Parameters
        self.proxy_index = 0
        # Web Auth
        self.requests_args = requests_args or {}
        self.cookies = self.GetGoogleCookie()

        self.category = None


    def status(self):
        print('----------------------  SearchReq STATUS  ----------------------')
        print('hl:',self.hl)
        print('lr:',self.lr)
        print('timeout:',self.timeout)
        print('proxies:',self.proxies)
        print('retries:',self.retries)
        print('backoff_factor:',self.backoff_factor)
        print('proxy_index:',self.proxy_index)
        print('requests_args:',self.requests_args)
        print('================================================================')

    def GetGoogleCookie(self):
        """
        Gets google cookie (used for each and every proxy; once on init otherwise)
        Removes proxy from the list on proxy error
        """
        while True:
            if len(self.proxies) > 0:
                proxy = {'http': self.proxies[self.proxy_index]}
            else:
                proxy = ''
            try:
                return dict(filter(lambda i: i[0] == 'NID', requests.get(SearchReq.GENRAL_URL,
                    timeout=self.timeout,
                    proxies=proxy,
                    **self.requests_args
                ).cookies.items()))
            except requests.exceptions.ProxyError:
                print('Proxy error. Changing IP')
                if len(self.proxies) > 1:
                    self.proxies.remove(self.proxies[self.proxy_index])
                else:
                    print('No more proxies available. Bye!')
                    raise
                continue

    def searching(self, kywd, num=100, hl='', lr='', daterange='', category='all'):
        # update category
        self.category = category
        """Create the payload for related queries, interest over time and interest by region"""
        self.token_payload = SearchReq.PARAMS_SET
        self.token_payload['hl'] = self.hl[:2]
        if self.lr: self.token_payload['lr'] = lr or self.lr 
        self.token_payload['num'] = num + 1
        self.token_payload['tbm'] = SearchReq.SEARCH_CAT[category]
        if isinstance(kywd, (list, tuple)):
            self.token_payload['q'] = '+'.join(kywd)
        else:
            self.token_payload['q'] = kywd
        if isinstance(daterange, (tuple,list)):
            self.token_payload['tbs'] = ','.join(['tbs=crd:1','cd_min: {}'.format(min(daterange).strftime('%m/%d/%Y')), 'cd_min: {}'.format(max(daterange).strftime('%m/%d/%Y'))])
       
        # get tokens
        rslt = self._tokens()

        # parcing 
        parced_rslt = list(self.parse_results(rslt))
        return parced_rslt

    def _tokens(self):
        """Makes request to Google to get API tokens for interest over time, interest by region and related queries"""
        # make the request and parse the returned json
        rtn_src = self._get_data(url=SearchReq.SEARCH_URL,method=SearchReq.GET_METHOD,
            params=self.token_payload,trim_chars=0,)

        return rtn_src

    def _get_data(self, url, method=GET_METHOD, trim_chars=0, **kwargs):
        """Send a request to Google and return the JSON response as a Python object
        :param url: the url to which the request will be sent
        :param method: the HTTP method ('get' or 'post')
        :param trim_chars: how many characters should be trimmed off the beginning of the content of the response
            before this is passed to the JSON parser
        :param kwargs: any extra key arguments passed to the request builder (usually query parameters or data)
        :return:
        """
        usragt = Headers(os="windows", headers=False).generate()['User-Agent']


        s = requests.session()
        # Retries mechanism. Activated when one of statements >0 (best used for proxy)
        if self.retries > 0 or self.backoff_factor > 0:
            retry = Retry(total=self.retries, read=self.retries,
                          connect=self.retries,
                          backoff_factor=self.backoff_factor)

        s.headers.update({'accept-language': self.hl, 'User-Agent':usragt})

        if len(self.proxies) > 0:
            self.cookies = self.GetGoogleCookie()
            s.proxies.update({'http': self.proxies[self.proxy_index]})
        if method == SearchReq.POST_METHOD:
            response = s.post(url, timeout=self.timeout,
                              cookies=self.cookies, **kwargs, **self.requests_args)  # DO NOT USE retries or backoff_factor here
        else:
            response = s.get(url, timeout=self.timeout, cookies=self.cookies,
                             **kwargs, **self.requests_args)   # DO NOT USE retries or backoff_factor here


        # only for google search crowling, It doesn't matter what response form
        # check if the response contains json and throw an exception otherwise
        # Code 200 means success
        if response.status_code == 200:
            # trim initial characters
            # some responses start with garbage characters, like ")]}',"
            # these have to be cleaned before being passed to the json parser
            content = response.text[trim_chars:]

            return content
        else:
            # error
            raise exceptions.ResponseError(
                'The request failed: Google returned a '
                'response with code {0}.'.format(response.status_code),
                response=response)


    def parse_results(self, raw_html):
        soup = BeautifulSoup(raw_html, 'html.parser')
        if self.category == 'all':
            result_block = soup.find_all('div', attrs={'class': 'g'})
            for result in result_block:
                #print(result)
                link = result.find('a', href=True)
                title = result.find('h3')
                desc = result.find('span', attrs={'class': 'aCOpRe'})
                if self.bln_main:
                    print('>>link<<',link)
                    print('>>title<<',title)
                    print('>>desc<<',desc)
                #raise
                if link and title and desc:
                    print(title.text, desc.text, link['href'])
                    yield [title.text, desc.text, link['href']]
        elif self.category =='news':
            result_block = soup.find_all('g-card')
            for result in result_block:
                link = result.find('a', href=True)
                title = result.find('div', attrs={'class': re.compile('JheGif *')})
                desc = result.find('div', attrs={'class': 'Y3v8qd'})
                src = result.find('div', attrs={'class': 'XTjFC WF4CUc'})
                rel = result.find('span', attrs={'class': 'WG9SHc'})


                if link and title and desc:
                    #print('-----------------------------------------------')
                    #print(title.text, desc.text, link['href'], src.text)
                    #raise
                    yield [title.text, desc.text, src.text, link['href'], rel.text]




if __name__ == '__main__':
    strt_date = datetime.strptime('20191201','%Y%m%d')
    tmnt_date = datetime.strptime('20201216','%Y%m%d')
    
    SR = SearchReq()

    out = SR.searching(kywd = 'CJ대한통운', hl='ko-KR',daterange=[strt_date, tmnt_date], category = 'news')
    print(out)
    #searching(self, kywd, num=100, hl='', lr='', daterange='', category='all')
"""

  https://www.google.com/search?q=대한항공 
  &sxsrf=ALeKk01C_ErzxqvOJ615vu07mUmb1cYAXQ:1607663867128 
  &source=lnms 
  &tbm=isch 
  &sa=X 
  &ved=2ahUKEwinlt_NlsXtAhVBa94KHQybAiAQ_AUoAnoECAcQBA 
  &biw=1280 
  &bih=824

https://www.google.com/search?hl=en&tbm=nws&sa=X&hl=en&q=Korean+Air
# ALL
&hl=en         &source=lmns&bih=824&biw=1280&sa=X         &ved=2ahUKEwjuk6LknsXtAhVL6JQKHTDBA2MQ_AUoAHoECAEQAA
# NEWS
&hl=en&tbm=nws &source=lnms&bih=824&biw=1280&sa=X         &ved=2ahUKEwi2kZTQn8XtAhWL7GEKHSZyBKAQ_AUoAXoECAcQAw &sxsrf=ALeKk02Egm5VqO1nyqC-nIp-M9rbyvJKUg:1607666288107
# Images
&hl=en&tbm=isch&source=lnms&bih=824&biw=1280&sa=X &dpr=1  &ved=0ahUKEwiPwbjfnsXtAhWLfXAKHSQaCWwQ_AUIDCgC       &sxsrf=ALeKk03Ll7rxkrST_TQCYhdT2vAiMD81WA:1607666051728
# Video
&hl=en&tbm=vid &source=lmns&bih=824&biw=1280&sa=X         &ved=2ahUKEwin0PjOlsXtAhUHXJQKHTJFBfEQ_AUoA3oECAEQAw
"""