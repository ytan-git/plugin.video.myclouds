# -*- coding: utf-8 -*-
import sys,os
import json,time
import xbmc, xbmcaddon
from urllib import quote_plus
from client_api import ClientAPI, PCSApiError, ClientApiError, TRANSCODE_TYPES
from CaptchaDialog import CaptchaDialog
from utils import fetch_url
from simple_rsa import get_public_key
from storage import TimedStorage

__addonid__ = "plugin.video.myclouds"
addon = xbmcaddon.Addon(id=__addonid__)
__addonname__ = addon.getAddonInfo('name')
__cwd__ = addon.getAddonInfo('path')
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'lib' ) )
lib_path = os.path.join(__resource__, 'Clouds', 'CloudBaidu')

sys.path[0:0] = [lib_path,
                 os.path.join(lib_path, 'poster-0.4-py2.6.egg'),
                 os.path.join(lib_path, 'rsa_x509_pem-0.1.0.egg')]


class CloudBaidu(object):
    name = 'CloudBaidu'
    full_name = '百度云'
    can_do_password_login = True
    can_do_search = True
    def __init__(self, cookiefile, username):
        self.user_name = username
        self.storage = TimedStorage(cookiefile)
        
    def get_name(self):
        return 'CloudBaidu'

    def get_full_name(self):
        return '百度云'

    def get_user_name(self):
        return self.user_name

    def login(self, user, passwd):
        api = create_api_with_publickey(self.storage, forceGetCert = True)
        try:
            login_info = api.try_login(user, passwd, on_verifycode)
        except Exception as e:
            msg = 'unknown error'
            if isinstance(e, ClientApiError):
                msg = e.get_errmsg()
            return {'state':False,  'message':msg}
        if not login_info:
            return {'state':False, 'message':'Login failed'}
        self.username = user
        
        save_user_info(user, login_info, api, self.storage)
        return {'state':True, 'message':''}
        

    def get_file_list(self, items, cid, offset, filter_type, files_per_page, file_order, asc=0, searchstr=''):
        #if cid == '/':
        #    addon.setSetting('baidu_cert', '')
        #log('baidu getfilelist, username = '+self.username + ' prefix='+self.settingPrefix)
        api = get_api(self.storage)
        if api is None:
            return {'state':False, 'message':'请先登录'}
        filesperpage = files_per_page
        if (searchstr != '' or filter_type != '0' )and files_per_page > 1000:
            filesperpage = 1000
        server_page = (offset / filesperpage) + 1
        order = get_file_order_by(file_order)
        if asc == 2:
            desc = 1
        else:
            desc = 0
        if filter_type != '0':
            filtertype = get_filter_type(filter_type)
            entries = api.category_list(filtertype, page = server_page, num = filesperpage, order = order, desc = desc)
        elif searchstr == '':
            entries = api.list_dir(cid, page = server_page, num = filesperpage, order = order, desc = desc)
        else:
            entries = api.search_dir(searchstr, remote_dir = cid, page = server_page, num = filesperpage, order = order, desc = desc)
        for entry in entries:
            item = {}
            item['n'] = entry['server_filename']
            item['s'] = entry['size']
            if entry['isdir'] == 0:
                item['sha'] = 'sha'
            else:
                item['cid'] = entry.get('path').encode('utf-8')
            item['ico'] = os.path.splitext(entry['server_filename'])[1].replace('.', '')
            item['pc'] = entry.get('path').encode('utf-8')
            item['md5'] = entry.get('md5')
            if 'thumbs' in entry and 'url1' in entry['thumbs']:
                item['u'] = entry['thumbs']['url1'].replace('size=c140_u90', 'size=c300_u300')
                item['largeimage'] = item['u'].replace('size=c300_u300', 'size=c10000_u10000')
            items.append(item)
        return {'state':True, 'finished':len(items) < filesperpage, 'message':''}

                      
    def get_image_url(self, quality, pc, largeimgurl):
        if quality == '0' and largeimgurl.startswith('http'):
            return largeimgurl
        return self.get_file_download_url(pc)
    
    def get_video_quality_selection(self, pc):
        api = get_api(self.storage)
        if api is None:
            return ''
        sels = []
        transtypes = ['M3U8_AUTO_360', 'M3U8_AUTO_480', 'M3U8_AUTO_720']
        for transtype in transtypes:
           sels.append(api.get_transcode_url(pc, transtype).lstrip('http:'))
        return sels
    
    def get_file_download_url(self, pc):
        api = get_api(self.storage)
        if api is None:
            return ''
        info = api.get_filemetas(pc)['info']
        return info[0]['dlink'] + '|User-Agent=netdisk;5.3.6.0;PC;PC-Windows;6.2.9200;WindowsBaiduYunGuanJia'
        #return info[0]['dlink'] + '|User-Agent=AppleCoreMedia/1.0.0.9B206 (iPad; U; CPU OS 5_1_1 like Mac OS X; zh_cn)'
        #return pc + '|User-Agent=Mozilla/5.0%20%28Windows%20NT%206.1%3B%20rv%3A25.0%29%20Gecko/20100101%20Firefox/25.0&Referer=http%3A//pan.baidu.com/disk/home'

def _get_public_key(storage, forceGetCert = False):
    cert = storage.get('cert', '')
    if forceGetCert or cert == '':
        cert = ClientAPI().get_cert()[0]
        storage['cert'] = cert
    return get_public_key(cert)

def create_api_with_publickey(storage, forceGetCert = False):
    api = ClientAPI()
    api.set_public_key(*_get_public_key(storage, forceGetCert))
    return api

def get_api(storage, forceGetCert = False):
    session = storage['session']
    #session_uid = addon.getSetting(settingPrefix + 'uid')
    #session_uid = login_info['uid']
    #if (session_uid == ''):
    #    return None
    _api = create_api_with_publickey(storage, forceGetCert)
    #session = (addon.getSetting(settingPrefix + 'bduss'),
    #           int(session_uid),
    #           addon.getSetting(settingPrefix + 'ptoken'),
    #           addon.getSetting(settingPrefix + 'stoken'))
    _api.set_login_info(session)
    return _api

def save_user_info(user, login_info, api, storage):
    ss = (login_info['bduss'], login_info[
          'uid'], login_info['ptoken'], login_info['stoken'])

    api.set_login_info(ss)
    storage['session'] = ss
    storage['session_time'] = time.time()
    storage.sync()
##    addon.setSetting(settingPrefix + 'bduss', login_info['bduss'])
##    addon.setSetting(settingPrefix + 'uid', str(login_info['uid']))
##    addon.setSetting(settingPrefix + 'ptoken', login_info['ptoken'])
##    addon.setSetting(settingPrefix + 'stoken', login_info['stoken'])
##    addon.setSetting(settingPrefix + 'time', str(time.time()))

def on_verifycode(imgurl, captcha_error=False):
    notify('open verifycode window')
    if captcha_error:
        notify('验证码不正确，请重新输入', delay=2000)

    win = CaptchaDialog('captcha.xml', __cwd__, imgurl=imgurl)
    try:
        win.doModal()
        input_text = win.get_text()
        if input_text:
            return input_text
    finally:
        del win

def get_file_order_by(choice):
    orders = {'0':'time', '1':'name', '2':'time', '3':'size'}
    return orders.get(choice)

def get_filter_type(filter_type):
    types = {'0':0, '1':6, '2':3, '3':2, '4':1}
    return types.get(filter_type)

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGERROR)
    
def notify(msg='', title=None, delay=3000, image=''):
    '''Displays a temporary notification message to the user. If
    title is not provided, the plugin name will be used. To have a
    blank title, pass '' for the title argument. The delay argument
    is in milliseconds.
    '''
    if not msg:
        log.warning('Empty message for notification dialog')
    if title is None:
        title = addon.getAddonInfo('name')
    xbmc.executebuiltin('XBMC.Notification("%s", "%s", "%s", "%s")' %
                        (msg, title, delay, image))
    
