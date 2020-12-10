import requests 
from fake_headers import Headers

# if Tor is available
tor_is_available = False
try:
    import psutil as ps
    import socket
    import socks
    from stem import Signal
    from stem.control import Controller
    import json
    tor_is_available = True
except:
    pass
#from seleniumrequests import Firefox
from selenium import webdriver as driver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


from bs4 import BeautifulSoup
import pandas as pd
import time
import platform as pltfrm
import os, sys
import re




"""
This Part is for If and only If you use Tor relations and set the torrc properry
"""
if pltfrm.system() == 'Windows':
  print('[tor.global] this system is Windows')
  __tor__ = 'tor.exe'
  __pw__ = ''
elif pltfrm.system() == 'Linux':
  print('[tor.global] this system is Linux')
  __tor__ = 'tor'
  __pw__ = ''

def check_tor_running():
  bln_tor_exec = False
  procs = ps.process_iter(attrs=None, ad_value=None)

  for proc in procs:
    if proc.name() == __tor__ :
      if proc.status()=='running':
        bln_tor_exec = True
        print('[tor.check_tor_running] tor is running')
      elif 'tor-browser' in proc.exe():
        bln_tor_exec = True
        print('[tor.check_tor_running] tor is running')
  if not bln_tor_exec:
    print('[tor.check_tor_running] tor is NOT running')

  return bln_tor_exec

def get_tor_session(header=None):
    session = requests.Session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {'http':  'socks5://127.0.0.1:9150',
                       'https': 'socks5://127.0.0.1:9150'}
    if header != None:
        session.headers = header
    tor_IP = json.loads(session.get("http://httpbin.org/ip").text)['origin']
    print('Tor Session is opend on %s'%tor_IP)
    return session

# signal TOR for a new connection 
def renew_connection():
    frm_IP = json.loads(get_tor_session().get("http://httpbin.org/ip").text)['origin']
    socks.setdefaultproxy()
    """Change IP using TOR"""
    with Controller.from_port(port=9151) as controller:
        controller.authenticate(password='0000')
        #socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050, True)
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9150, True)
        socket.socket = socks.socksocket
        controller.signal(Signal.NEWNYM)
    tto_IP = json.loads(get_tor_session().get("http://httpbin.org/ip").text)['origin']
    print('IP is changed from %s -> %s'%(frm_IP, tto_IP) )

"""
This Part is for If and only If you use Selenium Marionette
"""
from pathlib import Path as Path_

if hasattr(sys, "frozen"):
  main_dir = os.path.dirname(sys.executable)
else:
  main_dir = os.path.dirname(os.path.realpath(sys.argv[0]))


parent_path = Path_(main_dir).parent

sys.path.append(os.path.join(parent_path, 'eco'))
sys.path.append(os.path.join(parent_path, 'xx_geckodriver/*'))

exec_path = 'D:/local_git/xx_geckodriver/geckodriver-v0.28.0-win64/geckodriver.exe'




def header_tune(base_header, random_header):
    intersections = list(set(list(base_header.keys()))&set(list(random_header.keys())))

    for intsec in intersections:
        #if intsec != 'Accept':
        base_header[intsec] = random_header[intsec]
    return base_header


class gSearch(object):
    """docstring for gSearch"""
    def __init__(self, arg, bln_main=False):
        super(gSearch, self).__init__()
        try:
            self.num_results = arg['num_results']
        except:
            self.num_results = 10
        try:
            self.lang = arg['lang']
        except:
            self.lang = 'en'
        try:
            self.cate = arg['cate']
        except:
            self.cate = 'all'

        self.chnnl = arg['chnl']
        self.get_base_url()

        self.driver = None

        self.headers_base = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", 
            "Accept-Encoding": "gzip, deflate", 
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8", 
            "Dnt": "1", 
            "Host": "httpbin.org", 
            "Upgrade-Insecure-Requests": "1", 
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36", 
            }

        # check chnnl is available
        self.avail_tor = False
        if self.chnnl == 'tor':
            self.avail_tor = check_tor_running()
        self.avail_gck = False
        if self.chnnl == 'gck':
            self.avail_gck = True


        self.bln_main = bln_main

    def get_base_url(self):
        if self.cate == 'all':
            self.base_url = 'https://www.google.com/search?q={}&num={}&hl={}' 

        elif self.cate == 'news':
            self.base_url = 'https://www.google.com/search?q={}&num={}&hl={}&tbm=nws' 

    def url_generator(self, search_term):
        if isinstance(search_term, (list, tuple)):
            escaped_search_term = '+'.join(search_term)
        else:
            escaped_search_term = search_term.replace(' ', '+')

        google_url = self.base_url.format(escaped_search_term, self.num_results+1,self.lang)

        return google_url

    def marionette(self, google_url, header):
        # if google cut the IP, you can try firefox marionette mote
        if self.driver == None:
                #try:
                rtn_drvr = driver.Firefox(executable_path = exec_path)
                profile = driver.FirefoxProfile()
                profile.set_preference("network.proxy.type", 1)
                profile.set_preference("network.proxy.socks", '127.0.0.1')
                profile.set_preference("network.proxy.socks_port", 9150)
                profile.set_preference("network.proxy.socks_remote_dns", False)
                profile.update_preferences()
                #except:
                #rtn_drvr = driver.Firefox()
                self.driver = rtn_drvr


        self.driver.get(google_url)
        time.sleep(10) 

        return self.driver.page_source

    def fetch_results(self, google_url, headers):
        #print(google_url)
        if self.avail_tor == False:
            response = requests.get(google_url)
        else:
            if self.bln_main:
                print('Use Proxy')
                renew_connection()
            session = get_tor_session(headers)
            if self.bln_main:
                print(session.headers)
            response = session.get(google_url, timeout=30.0)

        response.raise_for_status()

        return response.text

    def parse_results(self, raw_html):
        soup = BeautifulSoup(raw_html, 'html.parser')
        if self.cate == 'all':
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
        elif self.cate =='news':
            result_block = soup.find_all('g-card')
            for result in result_block:
                link = result.find('a', href=True)
                title = result.find('div', attrs={'class': re.compile('JheGif *')})
                desc = result.find('div', attrs={'class': 'Y3v8qd'})
                src = result.find('div', attrs={'class': 'XTjFC WF4CUc'})
                rel = result.find('span', attrs={'class': 'WG9SHc'})
                if self.bln_main:
                    print('>> link <<',link['href'])
                    print('>> title <<',title.text)
                    print('>> desc <<',desc.text)
                    print('>> src <<', src.text)


                if link and title and desc:
                    #print('-----------------------------------------------')
                    #print(title.text, desc.text, link['href'], src.text)
                    #raise
                    yield [title.text, desc.text, src.text, link['href'], rel.text]

    def search(self, term, outform='df'):
        # to avoid captch every fetch will be done fake header
        header = Headers(os="random_os", headers=True).generate()
        random_header = header_tune(self.headers_base, header)
        random_header = header

        # search API generate
        search_url = self.url_generator(term)

        # This gives multiple ways to avoid captcha
        if self.avail_tor == True:
            html = self.fetch_results(search_url, random_header)
        elif self.avail_gck == True:
            html = self.marionette(search_url, random_header)
        else:
            html = self.fetch_results(search_url, random_header)
        records = list(self.parse_results(html))
        #print('////////////////////////////////////////////////////////////////////////////////////')
        #print(records)

        if outform == 'df':
            if self.cate == 'all':
                rtn = pd.DataFrame(records, columns = ['TITLE','DESC','LINK'])
            elif self.cate == 'news':
                rtn = pd.DataFrame(records, columns = ['TITLE','DESC','SRC','LINK','RELEASE'])
        else:
            rtn = records
        return rtn
    def close(self):
        self.driver.close()


if __name__ == '__main__':
    """
    # for test
    rtn = search('Google', num_results = 30)
    print(rtn)
    #"""
    header = Headers(os="windows", headers=True).generate()
    #session = get_tor_session(header)
    #renew_connection()

    conditions = {
        'num_results': 100,
        'lang': 'en',
        'cate': 'news',
        'chnl': 'gck'
    }
    gs = gSearch(conditions, bln_main=True)
    out = gs.search('ANA')
    print(out)
