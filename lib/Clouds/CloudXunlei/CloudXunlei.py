# -*- coding: utf-8 -*-
import sys,os,os.path,urllib,urllib2,urlparse,random,hashlib,re
import json,cookielib,gzip,time
import captcha
import hashlib
import xbmc
from StringIO import StringIO

lxurlpre = 'http://dynamic.cloud.vip.xunlei.com'

class CloudXunlei(object):
    name = 'CloudXunlei'
    full_name = '迅雷离线'
    can_do_password_login = True
    can_do_search = False
    def __init__(self, cookiefile, username):
        self.max_server_files_per_page = 100
        self.user_name = username
        self.cachetime = int(time.time()*1000)
        self.cookiefile = cookiefile
        self.cookiejar = cookielib.LWPCookieJar()
        if os.path.exists(cookiefile):
            self.cookiejar.load(
                cookiefile, ignore_discard=True, ignore_expires=True)
        self.userid = self.getcookieatt('.xunlei.com', 'userid')
        self.sid = self.getcookieatt('.xunlei.com', 'sessionid')
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar))

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/28.0.1500.71 Safari/537.36',
            'Accept-encoding': 'gzip,deflate',
        }

    def get_name(self):
        return 'CloudXunlei'

    def get_full_name(self):
        return '迅雷离线'

    def get_user_name(self):
        return self.user_name

    def login(self, user, passwd):
        vfcodeurl = 'http://login.xunlei.com/check?u={0}&cachetime={1}'.format(user, self.cachetime)
        self.urlopen(vfcodeurl)
        vfcode = self.getcookieatt('.xunlei.com', 'check_result')[2:]

        if not vfcode:
            vfcode = self.getvfcode('http://verify.xunlei.com/image?cachetime=')
            if not vfcode:
                return {'state':False, 'message':'Error geting verify code'}

        # encoding password str
        if not re.match(r'^[0-9a-f]{32}$', passwd):
            passwd = md5(md5(passwd))

        passwd = md5(passwd+vfcode.upper())

        data = urllib.urlencode(
            {'u': user,
             'p': passwd,
             'verifycode': vfcode,
             'login_enable': '1',
             'login_hour': '720', }
        )

        self.urlopen('http://login.xunlei.com/sec2login/', data=data)

        self.userid = self.getcookieatt('.xunlei.com', 'userid')
        self.sid = self.getcookieatt('.xunlei.com', 'sessionid')

        # login lixian space
        self.urlopen(
            'http://dynamic.lixian.vip.xunlei.com/login?cachetime=%s' % self.cachetime)
        urlpre = '%s/%s' % (lxurlpre, 'interface/showtask_unfresh')
        rsp = self.urlopen('%s?type_id=2&tasknum=1&t=%s' % (urlpre, self.cachetime))
        data = json.loads(rsp[8:-1])
        if data['rtcode'] != 0:
            return {'stata':False, 'message':'登录失败，请检查用户名密码'}
        gdriveid = data['info']['user']['cookie']

        self.setcookie('.vip.xunlei.com', 'gdriveid', gdriveid)
        self.setcookie('.vip.xunlei.com', 'pagenum', '100')
        self.cookiejar.save(self.cookiefile, ignore_discard=True)

        blogresult = self.getcookieatt('.xunlei.com', 'blogresult')
        rst = int(blogresult)
        loginmsgs = ['登入成功', '验证码错误', '密码错误', '用户名不存在']
        if (rst == 0):
            return {'state':True, 'message':''}
        else:
            return {'state':False, 'message':loginmsgs[rst] if rst < 3 else '未知错误'}
        plugin.notify(msg=loginmsgs[rst] if rst < 3 else '未知错误')

    def get_file_list(self, items, cid, offset, filter_type, files_per_page, file_order, asc=0, searchstr=''):
        if searchstr != '':
            return {'state':True, 'totalcount':0, 'message':''}
        if cid != '/':
            urlpre = '%s/%s' % (lxurlpre, 'interface')
            (magnet, taskid) = cid.split(',')
            
            if magnet and 'torrent' in magnet:
                url = 'http://extratorrent.cc%s' % (magnet)
                rsp = self.urlopen(url)
                #print url
                magnetid = re.search(r'magnet:\?xt=urn:btih:\S{40}', rsp)
                #print magnetid.group(0)
                tid = gettaskid(magnetid.group(0))
                infoid = magnet[-40:]
            else:
                infoid = magnet
                tid = taskid
            url = '%s/%s&tid=%s&infoid=%s&g_net=1&p=1&uid=%s&noCacheIE=%s' % (
                urlpre, 'fill_bt_list?callback=fill_bt_list', tid, infoid,
                self.userid, self.cachetime)
            rsp = self.urlopen(url)
            if not self.getcookieatt('dynamic.cloud.vip.xunlei.com', 'PHPSESSID'):
                self.cookiejar.save(self.cookiefile, ignore_discard=True)
            try:
                data = json.loads(rsp[13:-1])
            except ValueError:
                return {'state':False, 'message':'该离线任务已删除,请重新添加'}
            for li in data['Result']['Record']:
                if li['percent'] == 100:
                    item = {}
                    item['n'] = li['title']
                    item['s'] = li['filesize']
                    item['pc'] = li['downurl']
                    item['ico'] = li['ext']
                    item['sha'] = 'sha'
                    item['cid'] = li['url']
                    items.append(item)
            return {'state':True, 'totalcount':len(items), 'message':''}

##            mitems = [(i['title'],
##                       i['size'],
##                       i['percent'],
##                       i['cid'],
##                       re.sub(r'.*?&g=', '', i['downurl'])[:40],
##                       i['downurl'],
##                       i['url'])
##                      for i in data['Result']['Record'] if 'movie' in i['openformat']
##                      and i['percent'] == 100]
##
##            if not mitems:
##                plugin.notify('离线下载进行中，请稍候从离线空间播放')
##                return
##
##            if len(mitems) > 1:
##                sel = dialog.select(
##                    '播放选择',
##                    ['[%s]%s[%s]' % (i[2], i[0], i[1]) for i in mitems])
##                if sel is -1:
##                    return
##                mov = mitems[sel]
##            else:
##                mov = mitems[0]
##
##            (name, _, _, cid, gcid, downurl, bturl) = mov
##            videos = []
##            # videos = getcloudvideourl(bturl, name.encode('utf-8'))
##            videos.insert(0, ('源码', downurl))
##            selitem = dialog.select('清晰度', [v[0] for v in videos])
##            if selitem is -1:
##                return
##            v = videos[selitem]
##            player(v[1], gcid, cid, name, True)
##
##            return {'state':True, 'message':''}
    


        
        filesperpage = files_per_page
        if filesperpage > self.max_server_files_per_page:
            server_files_per_page = self.max_server_files_per_page
        else:
            server_files_per_page = files_per_page
        
        server_offset = offset
        while True:
            
            data = self.get_data_from_server(searchstr, cid, filter_type, get_file_order_by(file_order), asc, server_offset, server_files_per_page)
            if data['rtcode'] != 0:
                #notify(msg='数据获取失败,错误信息:'+str(data['error']))
                return {'state':False, 'message':'请重新登录'}
            for it in data['info']['tasks']:
                item = {}
                #item['n'] = '[{0}%][{1}]{2}'.format(it['progress'], it['openformat'], it['taskname'].encode('utf-8')),
                item['n'] = '[' + str(it['progress'])+'%][' + it['openformat']+ ']' + it['taskname'].encode('utf-8')
                item['s'] = it['file_size']
                item['cid'] = it['cid']+','+it['id']
                if it['lixian_url']:
                    item['sha'] = 'sha'
                    item['ico'] = os.path.splitext(it['taskname'])[1].replace('.', '')
                item['pc'] =it['lixian_url'] if it['lixian_url'] else 'bt'
                items.append(item)
            if int(data['info']['user']['total_num']) <= server_offset + server_files_per_page:
                break
            elif server_offset + len(data['info']['tasks']) >= offset + files_per_page:
                break
            else:
                server_offset = server_offset + len(data['info']['tasks'])
                server_files_per_page = int(offset) + files_per_page - server_offset
                if server_files_per_page > self.max_server_files_per_page: server_files_per_page = self.max_server_files_per_page
        
        return {'state':True, 'totalcount':int(data['info']['user']['total_num']), 'message':''}

                      
    def get_image_url(self, quality, pc, largeimgurl=''):
        return self.get_file_download_url(pc)

    def get_video_quality_selection(self, pc):
        sels = []
        return sels

    def get_file_download_url(self, pc):
        if pc.startswith('http'):
            url = self.urlopen(pc, redirect=False)
            cks = ['%s=%s' % (ck.name, ck.value) for ck in self.cookiejar]
            movurl = '%s|%s&Cookie=%s' % (
                url, urllib.urlencode(self.headers), urllib2.quote('; '.join(cks)))
            return movurl
       
        return ''

    def getvfcode(self, url):
        cdg = captcha.CaptchaDialog(url)
        cdg.doModal()
        confirmed = cdg.isConfirmed()
        if not confirmed:
            return
        info = cdg.getText()
        # del cdg
        vfcode, vfcookie = info.split('||')
        k, v = vfcookie.split('; ')[0].split('=')
        self.setcookie('.xunlei.com', k, v)
        return vfcode
    

    def setcookie(self, domain, k, v):
        c = cookielib.Cookie(
            version=0, name=k, value=v, comment_url=None, port_specified=False,
            domain=domain, domain_specified=True, path='/', secure=False,
            domain_initial_dot=True, path_specified=True, expires=None,
            discard=True, comment=None, port=None, rest={}, rfc2109=False)
        self.cookiejar.set_cookie(c)
        self.cookiejar.save(self.cookiefile, ignore_discard=True)

    class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            infourl = urllib.addinfourl(fp, headers, req.get_full_url())
            infourl.status = code
            infourl.code = code
            return infourl
        http_error_301 = http_error_303 = http_error_307 = http_error_302
        
    def urlopen(self, url, redirect=True, **args):
        if 'data' in args and type(args['data']) == dict:
            args['data'] = json.dumps(args['data'])
            self.headers['Content-Type'] = 'application/json'
        if not redirect:
            self.opener = urllib2.build_opener(
                self.SmartRedirectHandler(),
                urllib2.HTTPCookieProcessor(self.cookiejar))
        rs = self.opener.open(
            urllib2.Request(url, headers=self.headers, **args), timeout=30)
        if 'Location' in rs.headers:
            return rs.headers.get('Location', '')
        if rs.headers.get('content-encoding', '') == 'gzip':
            content = gzip.GzipFile(fileobj=StringIO(rs.read())).read()
        else:
            content = rs.read()
        return content

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



    def get_data_from_server(self, searchstr, cid, filtertype, fileorder, asc, server_offset, server_files_per_page):
        urlpre = '%s/%s' % (lxurlpre, 'interface/showtask_unfresh')
        server_page = (server_offset /server_files_per_page) + 1
        rsp = self.urlopen(
            '%s?t=%s&type_id=4&page=%s&tasknum=%s&p=1' % (urlpre, self.cachetime, server_page, server_files_per_page))
        data = json.loads(rsp[8:-1])
        return data

    def gettaskid(self, magnet):
        '''
        add magnet link to lixian space.
        http://verify.xunlei.com/image?t=MVA&cachetime=1392381968052
        '''
        urlpre = '%s/%s' % (lxurlpre, 'interface')
        if True: #magnet not in magnets:
            url = '%s/url_query?callback=queryUrl&u=%s&random=%s&tcache=%s' % (
                urlpre, urllib2.quote(magnet), randomtime, cachetime)
            rsp = self.urlopen(url)
            success = re.search(r'queryUrl(\(1,.*\))\s*$', rsp, re.S)
            if not success:
                already_exists = re.search(r"queryUrl\(-1,'([^']{40})", rsp, re.S)
                if already_exists:
                    return already_exists.group(1)
                raise NotImplementedError(repr(rsp))
            args = success.group(1).decode('utf-8')
            args = eval(args.replace('new Array', ''))
            _, cid, tsize, btname, _, names, sizes_, sizes, _, types, \
                findexes, _, timestamp, _ = args

            def toList(x):
                if type(x) in (list, tuple):
                    return x
                else:
                    return [x]
            data = {'uid': self.userid, 'btname': btname, 'cid': cid, 'tsize': tsize,
                    'findex': ''.join(x+'_' for x in toList(findexes)),
                    'size': ''.join(x+'_' for x in toList(sizes)),
                    'from': '0'}
            jsonp = 'jsonp%s' % cachetime
            commiturl = '%s/bt_task_commit?callback=%s' % (urlpre, jsonp)
            rsp = self.urlopen(commiturl, data=urllib.urlencode(data))
            while '"progress":-11' in rsp or '"progress":-12' in rsp:
                vfcode = self.getvfcode(
                    'http://verify2.xunlei.com/image?t=MVA&cachetime')
                if not vfcode:
                    return
                data['verify_code'] = vfcode
                rsp = self.urlopen(commiturl, data=urllib.urlencode(data))
            tids = re.findall(r'"id":"(\d+)"', rsp)
            if not tids:
                return
        tid = tids[0]
        return tid

def md5(s):
    return hashlib.md5(s).hexdigest().lower()

def log(txt):
    message = 'CloudXunlei: %s' % (txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGERROR)
    
def get_file_order_by(choice):
    orders = {'0':'', '1':'file_name', '2':'user_ptime', '3':'file_size'}
    return orders.get(choice)
