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
    def __init__(self, hl='en-US', lr=None, timeout=(10,30)
                , proxies_itr=[], retries=0, backoff_factor=0, requests_args=None):
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
        self.proxy_idx = 0
        # Web Auth
        self.requests_args = requests_args or {}
        self.cookies = self.GetGoogleCookie()


    def GetGoogleCookie(self):
        """
        Gets google cookie (used for each and every proxy; once on init otherwise)
        Removes proxy from the list on proxy error
        """
        while True:
            if len(self.proxies) > 0:
                proxy = {'https': self.proxies[self.proxy_index]}
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

    def GetNewProxy(self):
        """
        Increment proxy INDEX; zero on overflow
        """
        if self.proxy_index < (len(self.proxies) - 1):
            self.proxy_index += 1
        else:
            self.proxy_index = 0

    def build_payload(self, kywd, num=100, hl='', lr='', category='all'):
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

        print(self.token_payload)
        
        # get tokens
        self._tokens()
        return

    def _tokens(self):
        """Makes request to Google to get API tokens for interest over time, interest by region and related queries"""
        # make the request and parse the returned json
        widget_dict = self._get_data(
            url=SearchReq.SEARCH_URL,
            method=SearchReq.GET_METHOD,
            params=self.token_payload,
            trim_chars=0,
        )['widgets']
        # order of the json matters...
        first_region_token = True
        # clear self.related_queries_widget_list and self.related_topics_widget_list
        # of old keywords'widgets
        self.related_queries_widget_list[:] = []
        self.related_topics_widget_list[:] = []
        # assign requests
        for widget in widget_dict:
            if widget['id'] == 'TIMESERIES':
                self.interest_over_time_widget = widget
            if widget['id'] == 'GEO_MAP' and first_region_token:
                self.interest_by_region_widget = widget
                first_region_token = False
            # response for each term, put into a list
            if 'RELATED_TOPICS' in widget['id']:
                self.related_topics_widget_list.append(widget)
            if 'RELATED_QUERIES' in widget['id']:
                self.related_queries_widget_list.append(widget)
        return


    def _get_data(self, url, method=GET_METHOD, trim_chars=0, **kwargs):
        """Send a request to Google and return the JSON response as a Python object
        :param url: the url to which the request will be sent
        :param method: the HTTP method ('get' or 'post')
        :param trim_chars: how many characters should be trimmed off the beginning of the content of the response
            before this is passed to the JSON parser
        :param kwargs: any extra key arguments passed to the request builder (usually query parameters or data)
        :return:
        """
        usragt = Headers(os="random_os", headers=True).generate()['User-Agent']


        s = requests.session()
        # Retries mechanism. Activated when one of statements >0 (best used for proxy)
        if self.retries > 0 or self.backoff_factor > 0:
            retry = Retry(total=self.retries, read=self.retries,
                          connect=self.retries,
                          backoff_factor=self.backoff_factor)

        s.headers.update({'accept-language': self.hl, 'User-Agent':usragt})

        if len(self.proxies) > 0:
            self.cookies = self.GetGoogleCookie()
            s.proxies.update({'https': self.proxies[self.proxy_index]})
        if method == SearchReq.POST_METHOD:
            response = s.post(url, timeout=self.timeout,
                              cookies=self.cookies, **kwargs, **self.requests_args)  # DO NOT USE retries or backoff_factor here
        else:
            response = s.get(url, timeout=self.timeout, cookies=self.cookies,
                             **kwargs, **self.requests_args)   # DO NOT USE retries or backoff_factor here
        print(url)
        print(response.text)
        raise
        # check if the response contains json and throw an exception otherwise
        # Google mostly sends 'application/json' in the Content-Type header,
        # but occasionally it sends 'application/javascript
        # and sometimes even 'text/javascript
        if response.status_code == 200 and 'application/json' in \
                response.headers['Content-Type'] or \
                'application/javascript' in response.headers['Content-Type'] or \
                'text/javascript' in response.headers['Content-Type']:
            # trim initial characters
            # some responses start with garbage characters, like ")]}',"
            # these have to be cleaned before being passed to the json parser
            content = response.text[trim_chars:]
            # parse json
            self.GetNewProxy()
            return json.loads(content)
        else:
            # error
            raise exceptions.ResponseError(
                'The request failed: Google returned a '
                'response with code {0}.'.format(response.status_code),
                response=response)



if __name__ == '__main__':
    SR = SearchReq()
    SR.build_payload('jhlee@korea.ac.kr')
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