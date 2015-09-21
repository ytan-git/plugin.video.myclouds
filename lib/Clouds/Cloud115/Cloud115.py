# -*- coding: utf-8 -*-
import sys,os,os.path,urllib,urllib2,urlparse,random,hashlib,re,threading
import json,cookielib,gzip,time
import xbmc, xbmcaddon, xbmcgui
from StringIO import StringIO

__addonid__ = "plugin.video.myclouds"
__addon__ = xbmcaddon.Addon(id=__addonid__)

def log(txt):
    message = '%s: %s' % ('Cloud115', txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGERROR)

class QRShower(xbmcgui.WindowDialog):
    def __init__(self):
        self.imgControl = xbmcgui.ControlImage((1280-218)/2, (720-218)/2, 218, 218, filename = '')
        self.addControl(self.imgControl)
        self.labelControl = xbmcgui.ControlLabel((1280-300)/2, (720+218)/2 + 10, 300, 10, '请用115手机客户端扫描二维码', alignment = 0x00000002)
        self.addControl(self.labelControl)

    def showQR(self, url):
        self.imgControl.setImage(url)
        self.doModal()
        #self.setFocus(self.imgControl)

    def changeLabel(self, label):
        self.labelControl.setLabel(label)
        
    def onAction(self,action):
        self.close()
    
class Cloud115(object):
    name = 'Cloud115'
    full_name = '115网盘'
    can_do_password_login = False
    can_do_search = True
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:38.0) Gecko/20100101 Firefox/38.0'
    bad_servers = ['fscdnuni-vip.115.com', 'fscdntel-vip.115.com']
    def __init__(self, cookiefile, username):
        self.prefer_server = get_prefer_server(__addon__.getSetting('prefer115server'))
        self.max_server_files_per_page = 200
        self.cookiejar = cookielib.LWPCookieJar()
        
        if username != '':
            self.user_name = username
            self.cookiefile = cookiefile
            if os.path.exists(cookiefile):
                self.cookiejar.load(
                    cookiefile, ignore_discard=True, ignore_expires=True)
        else:
            self.cookiefile_path = cookiefile
        
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar))

        self.headers = {
            'User-Agent': self.user_agent,
            'Accept-encoding': 'gzip,deflate',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'http://web.api.115.com/bridge_2.0.html?namespace=Core.DataAccess&api=UDataAPI&_t=v5',
        }

        # set cookies.
        self.set_cookie('115_lang', 'zh')
        

    def get_name(self):
        return 'Cloud115'

    def get_full_name(self):
        return '115网盘'

    def get_user_name(self):
        return self.user_name

    def get_cookie_string(self):
        result = ''
        i = 1
        count = len(self.cookiejar)
        for cookie in self.cookiejar:
            result += cookie.name + '=' + cookie.value
            if i < count:
                result += '; '
                i = i+1
        return result

    def get_user_agent(self):
        return self.user_agent
    
    def do_login(self):
        self.cookiejar.clear()
        data = self.urlopen('http://www.115.com/?ct=login&ac=qrcode_token')
        data = self.fetch(data)
        data = json.loads(data[data.index('{'):])
        uid = data['uid']
        data = self.urlopen('http://msg.115.com/proapi/anonymous.php?ac=signin&user_id='+uid+'&sign='+data['sign']+'&time='+str(data['time'])+'&_='+str(time.time()))
            
        data = self.fetch(data)
        data = json.loads(data[data.index('{'):])
        imserver = data['server']
        sessionid = data['session_id']

        qrurl = 'http://www.115.com/scan/?ct=scan&ac=qrcode&uid='+uid+'&_t='+str(time.time())
        qrShower = QRShower()
        qthread = threading.Thread(target=qrShower.showQR, args=(qrurl,))
        qthread.start()

        for i in range(2):
            try:
                data = self.urlopen('http://' + imserver +'/chat/r?VER=2&c=b0&s='+sessionid+'&_t='+str(time.time()))
            except Exception, e:
                qrShower.close()
                qthread.join()
                return {'state':False, 'message':'手机客户端扫描超时'}
            data = self.fetch(data)
            data = data.replace('\n','').replace('\r','')
            #ll = eval(data)
            ll = json.loads(data[data.index('[{'):])
            for l in ll:
                for p in l['p']:
                    if p.has_key('key') == False:
                        qrShower.changeLabel('请在手机客户端点击登录确认')
                        continue
                    key = p['key']
                    v = p['v']
                    break;
        if key is None:
            return {'state':False, 'message':'Login Error'}
        #data = self.urlopen('http://www.115.com/?ct=login&ac=qrcode&key=' + key + '&v=' + v + '&goto=https%3A%2F%2Fpassport.115.com%2F%3Fct%3Dlogin%26ac%3Dempty_page%26is_ssl%3D1')
        data = self.urlopen('http://www.115.com/?ct=login&ac=qrcode&key=' + key + '&v=' + v)
        data = self.fetch(data)

        data = self.urlopen('http://www.115.com/?ct=login&ac=is_login&_=' + str(time.time()))
        data = self.fetch(data)
        data = json.loads(data[data.index('{'):])
        qrShower.close()
        qthread.join()

        if data['state'] != True:
            return {'state':False, 'message':data['msg']}
        if data['data'].has_key('USER_NAME'):
            self.user_name = data['data']['USER_NAME']
        else:
            self.user_name = data['data']['USER_ID']
        self.cookiefile = os.path.join(self.cookiefile_path, 'cookie_%s_%s.dat' % (self.full_name, self.user_name))
        self.cookiejar.save(self.cookiefile, ignore_discard=True)
        return {'state':True, 'user_name':self.user_name}
        

    def login(self, user, passwd):
        vcode=self.encodes()
        data = urllib.urlencode({'login[ssoent]': 'A1', 'login[version]': '2.0', 'login[ssoext]': vcode,
                                 'login[ssoln]':user, 'login[ssopw]':self.depass(user,passwd,vcode),'login[ssovcode]':vcode,
                                 'login[safe]':'1','login[time]':'1','login[safe_login]':'1','goto':'http://m.115.com/?ac=home'})
        self.cookiejar.clear()
        #login_page = self.urlopen('http://passport.115.com/?ct=login&ac=ajax&is_ssl=1', data=data)
        login_page = self.urlopen('http://passport.115.com/?ct=open_login&t=qq', data=data)
        msgs=json.loads(self.fetch(login_page))
        if msgs['state']==True:
            self.cookiejar.save(self.cookiefile, ignore_discard=True)
            return {'state':True, 'message':''}
        else:
            return {'state':False, 'message':str(msgs['err_msg'])}

    def get_file_list(self, items, cid, offset, filter_type, files_per_page, file_order, asc=0, searchstr=''):
        if cid == '/':
            cid = '0'
        filesperpage = files_per_page
        if asc > 0:
            order_asc = '1' if asc == 1 else '0'
        else:
            order_asc = ''
        if (searchstr != '' or filter_type != '0' )and files_per_page > 1000:
            filesperpage = 1000
        if filesperpage > self.max_server_files_per_page:
            server_files_per_page = self.max_server_files_per_page
        else:
            server_files_per_page = files_per_page
        server_offset = offset
        
        
        while True:
            data = self.get_data_from_server(searchstr, cid, filter_type, get_file_order_by(file_order), order_asc, str(server_offset), server_files_per_page)
            if data['state'] != True:
                #notify(msg='数据获取失败,错误信息:'+str(data['error']))
                return {'state':False, 'message':str(data['error'])}
            items.extend(data['data'])
            if data['count'] <= int(server_offset) + server_files_per_page:
                break
            elif server_offset + len(data['data']) >= int(offset) + files_per_page:
                break
            else:
                server_offset = server_offset + len(data['data'])
                server_files_per_page = int(offset) + files_per_page - server_offset
                if server_files_per_page > self.max_server_files_per_page: server_files_per_page = self.max_server_files_per_page

        return {'state':True, 'totalcount':data['count'], 'message':''}

                      
    def get_image_url(self, quality, pc, largeimgurl=''):
        if quality == '0':
            data=self.urlopen("http://web.api.115.com/files/image?pickcode="+pc+"&_="+str(time.time()))
            data=self.fetch(data)
            data=json.loads(data[data.index('{'):])
            if data['state'] and data['data'].has_key('url'):
                return data['data']['url']
        return self.get_file_download_url(pc)

    def get_video_quality_selection(self, pc):
        sels = []
        data=self.urlopen('http://115.com/api/video/m3u8/'+pc+'.m3u8')
        data=self.fetch(data)
        sels= re.compile(r'http:(.*?)\r', re.DOTALL).findall(data)
        return sels

    def get_file_download_url(self, pc):
        data=self.urlopen("http://web.api.115.com/files/download?pickcode="+pc+"&_="+str(time.time()))
        data=self.fetch(data)
        data=json.loads(data[data.index('{'):])
        bad_server = ''
        result = ''
        if data['state']:
            result = data['file_url']
            #return data['file_url'].replace(self.bad_server, self.prefer_server)
        else:
            data=self.urlopen("http://proapi.115.com/app/chrome/down?method=get_file_url&pickcode="+pc)
            data=self.fetch(data)
            data=json.loads(data[data.index('{'):])
            if data['state']:
                for value in data['data'].values():
                    if value.has_key('url'):
                        result = value['url']['url']
                        break
                    #return value['url']['url'].replace(self.bad_server, self.prefer_server)
                #return data['file_url']
            else:
                #notify('get file error:' + data['msg'])
                return ''
        for bs in self.bad_servers:
            if result.find(bs) != -1:
                bad_server = bs
                break
        if bad_server != '':
            result = result.replace(bad_server, self.prefer_server)
        return result


    

    def set_cookie(self, name, value):
        ck = cookielib.Cookie(version=0, name=name, value=value, port=None, port_specified=False, domain='.115.com', domain_specified=False, domain_initial_dot=False,
                              path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        self.cookiejar.set_cookie(ck)

    def urlopen(self, url, **args):
        #plugin.log.error(url)
        #update ck: _115_curtime=1434809478
        self.set_cookie('_115_curtime', str(time.time()))
        self.set_cookie('tjj_id', str(time.time())) #115' new API uses tjj_id instead of _115_curtime in cookie

        if 'data' in args and type(args['data']) == dict:
            args['data'] = json.dumps(args['data'])
            self.headers['Content-Type'] = 'application/json'
        else:
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        rs = self.opener.open(
            urllib2.Request(url, headers=self.headers, **args), timeout=60)
        #urlcache[url] = rs
        return rs

    def fetch(self,wstream):
        if wstream.headers.get('content-encoding', '') == 'gzip':
            content = gzip.GzipFile(fileobj=StringIO(wstream.read())).read()
        else:
            content = wstream.read()
        return content

    def getcookieatt(self, domain, attr):
        if domain in self.cookiejar._cookies and attr in \
           self.cookiejar._cookies[domain]['/']:
            return self.cookiejar._cookies[domain]['/'][attr].value
    def depass(self,ac,ps,co):
        eac=hashlib.sha1(ac).hexdigest()
        eps=hashlib.sha1(ps).hexdigest()
        return hashlib.sha1(hashlib.sha1(eps+eac).hexdigest()+co.upper()).hexdigest()
    def encodes(self):
        prefix = ""
        phpjs=int(random.random() * 0x75bcd15)
        retId = prefix
        retId += self.encodess(int(time.time()),8)
        retId += self.encodess(phpjs, 5)
        return retId
    def encodess(self,seed, reqWidth):
        seed = hex(int(seed))[2:]
        if (reqWidth < len(seed)):
            return seed[len(seed) - reqWidth:]
        if (reqWidth >  len(seed)):
            return (1 + (reqWidth - seed.length)).join('0') + seed
        return seed

    def get_data_from_server(self, searchstr, cid, filtertype, fileorder, asc, server_offset, server_files_per_page):
        if searchstr != '':
            data=self.urlopen('http://web.api.115.com/files/search?search_value=' + urllib.quote_plus(searchstr) + '&type='+filtertype+'&star=0&o='+fileorder+'&asc='+asc+'&offset='+str(server_offset)+'&show_dir=1&natsort=1&limit='+str(server_files_per_page)+'&format=json')
            data= self.fetch(data).replace('\n','').replace('\r','')
            data=json.loads(data[data.index('{'):])
        else:
            data=self.urlopen('http://web.api.115.com/files?aid=1&cid='+str(cid)+'&type='+filtertype+'&star=0&o='+fileorder+'&asc='+asc+'&natsort=1&offset='+str(server_offset)+'&show_dir=1&limit='+str(server_files_per_page)+'&format=json')
            data= self.fetch(data).replace('\n','').replace('\r','')
            data=json.loads(data[data.index('{'):])
            if data['state'] == False:
                data=self.urlopen('http://aps.115.com/natsort/files.php?aid=1&cid='+str(cid)+'&type='+filtertype+'&star=0&o='+fileorder+'&asc='+asc+'&offset='+str(server_offset)+'&show_dir=1&natsort=1&limit='+str(server_files_per_page)+'&format=json')
                data= self.fetch(data).replace('\n','').replace('\r','')
                data=json.loads(data[data.index('{'):])
        return data


def get_file_order_by(choice):
    orders = {'0':'', '1':'file_name', '2':'user_ptime', '3':'file_size'}
    return orders.get(choice)

def get_prefer_server(choice):
    servers = {'0':'vipcdntel.115.com', '1':'vipcdnuni.115.com', '2':'vipcdnctt.115.com', '3':'vipcdngwbn.115.com'}
    return servers.get(choice)

