# -*- coding: utf-8 -*-
# myclouds.py
import sys,os,os.path,urllib,urllib2,urlparse,random,hashlib,re
import xbmcgui,xbmcplugin,xbmcaddon, xbmcvfs
import json,cookielib,gzip,time
#from StringIO import StringIO

reload(sys)
sys.setdefaultencoding('utf-8')

__addonid__ = "plugin.video.myclouds"
__addon__ = xbmcaddon.Addon(id=__addonid__)
__addonname__ = __addon__.getAddonInfo('name')
__cwd__ = __addon__.getAddonInfo('path')
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'lib' ) )
__profile__ = xbmc.translatePath( __addon__.getAddonInfo('profile')).decode('utf-8')
if not os.path.exists(__profile__):
    os.makedirs(__profile__)
    
sys.path.append (__resource__)
sys.path.append(os.path.join(__resource__, 'Clouds', 'Cloud115'))
sys.path.append(os.path.join(__resource__, 'Clouds', 'CloudBaidu'))
sys.path.append(os.path.join(__resource__, 'Clouds', 'CloudXunlei'))
import ChineseKeyboard
from Cloud115 import Cloud115
from CloudBaidu import CloudBaidu
from CloudXunlei import CloudXunlei

# Suggested view codes for each type from different skins (initial list thanks to xbmcswift2 library)
ALL_VIEW_CODES = {
    'list': {
        'skin.confluence': 50, # List
        'skin.aeon.nox': 50, # List
        'skin.droid': 50, # List
        'skin.quartz': 50, # List
        'skin.re-touched': 50, # List
    },
    'thumbnail': {
        'skin.confluence': 500, # Thumbnail
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 51, # Big icons
        'skin.re-touched': 500, #Thumbnail
        'skin.confluence-vertical': 500,
        'skin.jx720': 52,
        'skin.pm3-hd': 53,
        'skin.rapier': 50,
        'skin.simplicity': 500,
        'skin.slik': 53,
        'skin.touched': 500,
        'skin.transparency': 53,
        'skin.xeebo': 55,
    },
}

base_url = sys.argv[0]
try:
    addon_handle = int(sys.argv[1])
except ValueError:
    pass
args = urlparse.parse_qs(sys.argv[2][1:])
colors = {'back': '7FFF00','dir': '8B4513','video': 'FF0000','next': 'CCCCFF','bt': 'FF0066', 'audio': '0000FF', 'subtitle':'505050', 'image': '00FFFF', '-1':'FF0000','0':'8B4513','1':'CCCCFF','2':'7FFF00', 'menu':'FFFF00'}

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

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
        title = __addon__.getAddonInfo('name')
    xbmc.executebuiltin('XBMC.Notification("%s", "%s", "%s", "%s")' %
                        (msg, title, delay, image))

cloud_names = {Cloud115.full_name:Cloud115, CloudBaidu.full_name:CloudBaidu, CloudXunlei.full_name:CloudXunlei}

loadvideo = __addon__.getSetting('loadvideo')
loadaudio = __addon__.getSetting('loadaudio')
loadimage = __addon__.getSetting('loadimage')
loadsubtitle = __addon__.getSetting('loadsubtitle')
loadtorrent = __addon__.getSetting('loadtorrent')
loadother = __addon__.getSetting('loadotherfiles')
fileorder = __addon__.getSetting('fileorderby')
orderasc = int(__addon__.getSetting('orderasc'))
filtertype = __addon__.getSetting('filtertype')
videoqselect = __addon__.getSetting('videoquality')
imageqselect = __addon__.getSetting('imagequality')

##verq = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["version","name"]},"id":1}')
##verq = unicode(verq, 'utf-8', errors='ignore')
##verq = json.loads(verq)
##version_installed = verq['result']['version']

def index(content_type):
    totalaccts = 0
    username = None
    cloudname = None
    for name in cloud_names:
        accounts = load_account_settings(name)
        for user in accounts:
            username = user
            cloudname = name
            totalaccts = totalaccts + 1
    if totalaccts <= 1:
        if username is not None:
            items = []
            cid = '/'
            offset = '0'
            files_per_page = get_files_perpage()
            if filtertype != '0' and files_per_page > 1000:
                files_per_page = 1000
            cloud = get_cloud(cloudname, username)
            result = get_file_list(items, cloud, cid, offset, files_per_page, '')
            add_items_to_directory(cloud, items, content_type, result, cid, offset, files_per_page, '')
    else:
        for cloudname in sorted(cloud_names):
            accounts = load_account_settings(cloudname)
            for username in sorted(accounts):
                item = xbmcgui.ListItem('[%s][%s]' %(cloudname, username))
                item.addContextMenuItems([('删除','RunScript(special://home/addons/plugin.video.myclouds/myclouds.py,RemoveAccount,%s,%s)' % (cloudname,username),),
                                          ('重新登录','RunScript(special://home/addons/plugin.video.myclouds/myclouds.py,ReloginAccount,%s,%s)' % (cloudname,username),)])
                xbmcplugin.addDirectoryItem(addon_handle,
                                            build_url({'mode':'CloudFolder', 'content_type':content_type, 'cloud_name':cloudname, 'user_name':username}),
                                            item, isFolder=True)
    if totalaccts == 0:
        items = []
    elif totalaccts == 1:
        items = [{'label': colorize_label('搜索', 'menu'), 'url': {'mode':'Search', 'cloud_name':'', 'user_name':'', 'cid':'/', 'content_type':content_type}, 'isFolder':True},]
    else:
        items = [{'label': colorize_label('统一搜索', 'menu'), 'url': {'mode':'Search', 'cloud_name':'', 'user_name':'', 'cid':'/', 'content_type':content_type}, 'isFolder':True},]
    items.extend([
        {'label': colorize_label('账号管理', 'menu'), 'url': {'mode':'ManageAccounts','content_type':content_type}, 'isFolder':True},
        {'label': colorize_label('设置', 'menu'), 'url': {'mode':'setting'},'isFolder':False},
        ])
    for item in items:
        li = xbmcgui.ListItem(item['label'])
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=build_url(item['url']), listitem=li, isFolder=item['isFolder'])
    xbmcplugin.endOfDirectory(addon_handle)
    
def do_setting():
    __addon__.openSettings()
   
def do_nothing():
    pass

def do_login_cloud_password(cloud, user, passwd):
    msg = ''
    if user != '':
        result = cloud.login(user, passwd)
        try:
            result = cloud.login(user, passwd)
            if result['state']:
                notify(cloud.get_full_name() + '用户' + user + '登录成功 ')
                return {'state':True, 'message':''}
            else:
                msg = result['message']
        except Exception as e:
            msg = '登录异常'
    else:
        msg = '用户名不能为空'
    return {'state':False, 'message':msg}
    
def do_manage_accounts(content_type):
    for name in sorted(cloud_names):
        li = xbmcgui.ListItem(name + '账号管理')
        xbmcplugin.addDirectoryItem(addon_handle,  build_url({'mode':'ManageCloudAccounts', 'cloud_name':name, 'content_type':content_type}), li, isFolder = True)
    xbmcplugin.endOfDirectory(addon_handle)

def do_manage_cloud_accounts(cloudname, content_type):
    accounts = load_account_settings(cloudname)
    for username in accounts.keys():
        item = xbmcgui.ListItem(username)
        item.addContextMenuItems([('删除','RunScript(special://home/addons/plugin.video.myclouds/myclouds.py,RemoveAccount,%s,%s)' % (cloudname,username),),
                                  ('重新登录','RunScript(special://home/addons/plugin.video.myclouds/myclouds.py,ReloginAccount,%s,%s)' % (cloudname,username),)], True)
        xbmcplugin.addDirectoryItem(addon_handle,  build_url({'mode':'CloudFolder','cloud_name':cloudname, 'user_name':username, 'content_type':content_type}), item, isFolder = True)
    xbmcplugin.addDirectoryItem(addon_handle,  build_url({'mode':'AddAccount','cloud_name':cloudname}), xbmcgui.ListItem('增加'), isFolder = False)
    xbmcplugin.endOfDirectory(addon_handle)

def do_add_account(cloud_name, default_username = '', default_password = '' ):
    accounts = load_account_settings(cloud_name)
    if cloud_names[cloud_name].can_do_password_login == False:
        cloud = cloud_names[cloud_name](__profile__, '')
        r = cloud.do_login()
        if r['state']:
            user_name = r['user_name']
            accounts[user_name] = 'NONE'
            save_account_settings(cloud_name, accounts)
            xbmc.executebuiltin('Container.Refresh')
        else:
            notify('登录失败：' + r['message'])
        return
    #keyboard = xbmc.Keyboard(default_username, '输入'+cloud_name+'账号', False)
    keyboard = ChineseKeyboard.Keyboard(default_username, '输入'+cloud_name+'账号')
    keyboard.doModal()
    if keyboard.isConfirmed():
        username = keyboard.getText()
        if accounts.has_key(username):
            ret =  xbmcgui.Dialog().yesno(cloud_name + '已经存在', '是否重新设置密码？')
            if ret == False:
                return
        keyboard = xbmc.Keyboard(default_password, '输入密码', True)
        keyboard.doModal()
        if keyboard.isConfirmed():
            password = keyboard.getText()
            #accounts.append({'username':username, 'password':password})
            accounts[username] = password
            cookiefile = os.path.join(__profile__, 'cookie_%s_%s.dat' %(cloud_name, username))
            cloud = cloud_names[cloud_name](cookiefile, username)
            r = do_login_cloud_password(cloud, username, password)
            if r['state']:
                save_account_settings(cloud_name, accounts)
            elif xbmcgui.Dialog().yesno('登录失败：'+r['message'], '是否重新登录？'):
                do_add_account(cloud_name, username, password)
            else:
                if xbmcvfs.exists(cookiefile):
                    xbmcvfs.delete(cookiefile)
                notify('login failed:' + r['message'])
            #__addon__.setSetting(cloud_name, username + ':'+ password)
            xbmc.executebuiltin('Container.Refresh')

def do_remove_account(cloudname, username):
    if xbmcgui.Dialog().yesno('', '是否删除'+cloudname+'账号'+username+'？') == False:
        return
    accounts = load_account_settings(cloudname)
    if accounts.has_key(username):
        del accounts[username]
        save_account_settings(cloudname, accounts)
        cookiefile = os.path.join(__profile__, 'cookie_%s_%s.dat' %(cloudname, username))
        xbmcvfs.delete(cookiefile)
        xbmc.executebuiltin('Container.Refresh')

def do_relogin(cloudname, username):
    if cloud_names[cloudname].can_do_password_login == False:
        cloud = cloud_names[cloudname](__profile__, '')
        r = cloud.do_login()
    else:
        cloud = get_cloud(cloudname, username)
        accounts = load_account_settings(cloudname)
        password = accounts.get(username, None)
        if password is None:
            notify('无法获得账户密码，请删除账号后重新添加')
        r = do_login_cloud_password(cloud, username, password)
    if r['state'] != True:
        if xbmcgui.Dialog().yesno('重新登录失败：'+r['message'], '重试一次？'):
            return do_relogin(cloudname, username)
        else:
            return False
    return True


def do_search(cloudname, username, cid, content_type):
    keyboard = ChineseKeyboard.Keyboard('', '输入要搜索的内容')
    keyboard.doModal()
    if keyboard.isConfirmed():
        searchfor = keyboard.getText()
    else:
        return
    
    offset = '0'
    files_per_page = get_files_perpage()
    if ( searchfor!= '' or filtertype != '0') and files_per_page > 1000:
        files_per_page = 1000
    for cname in sorted(cloud_names):
        if cloudname == '' or cloudname == cname:
            for uname in load_account_settings(cname):
                if username == '' or username == uname:
                    items = []
                    cloud = get_cloud(cname, uname)
                    if searchfor == '' or cloud.can_do_search:
                        result = get_file_list(items, cloud, cid, offset, files_per_page, searchfor)
                        add_items_to_directory(cloud, items, content_type, result, cid,  offset, files_per_page, searchfor, True)
    xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=True)
    
def do_cloud_folder(content_type, cloud_name, user_name, searchfor=''):
    cid = '/'
    offset = '0'
    if searchfor == 'nEeDInPT':
        keyboard = ChineseKeyboard.Keyboard('', '输入要搜索的内容')
        keyboard.doModal()
        if keyboard.isConfirmed():
            searchfor = keyboard.getText()
        if searchfor == 'nEeDInPT':
            return
    files_per_page = get_files_perpage()
    if ( searchfor!= '' or filtertype != '0') and files_per_page > 1000:
        files_per_page = 1000
    items = []
    cloud = get_cloud(cloudname, username)
    result = get_file_list(items, cloud, cid, offset, files_per_page, searchfor)
    if result['state']:
        add_items_to_directory(cloud, items, content_type, result, cid, offset, files_per_page, searchfor)
        if searchfor == '':
            xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'Search', 'cloud_name':cloud_name,
                                                                 'user_name':user_name, 'cid':cid, 'content_type':content_type}),
                                        xbmcgui.ListItem(colorize_label('搜索','menu')), isFolder = True)
    xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=True)

def do_folder(cloud_name, user_name, cid, offset, content_type, searchfor):
    #xbmcplugin.addSortMethod(addon_handle,xbmcplugin.SORT_METHOD_NONE)
    if searchfor == 'nEeDInPT':
        keyboard = ChineseKeyboard.Keyboard('', '输入要搜索的内容')
        keyboard.doModal()
        if keyboard.isConfirmed():
            searchfor = keyboard.getText()
        if searchfor == 'nEeDInPT':
            return
    cloud = get_cloud(cloud_name, user_name)
    files_per_page = get_files_perpage()
    if ( searchfor!= '' or filtertype != '0') and files_per_page > 1000:
        files_per_page = 1000
    items = []
    result = get_file_list(items, cloud, cid, offset, files_per_page, searchfor)
    add_items_to_directory(cloud, items, content_type, result, cid, offset, files_per_page, searchfor)
    xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=True)

    
def get_file_list(items, cloud, cid, offset, files_per_page, searchstr=''):
    try:
        result = cloud.get_file_list(items, cid, int(offset), filtertype, files_per_page, fileorder, orderasc, searchstr)
        if result['state'] != True:
            notify(cloud.get_full_name() + '数据获取失败,错误信息:'+ result['message'])
    except Exception, e:
        result = {'state':False, 'message':str(e)}
    if result['state']:
        return result
    elif xbmcgui.Dialog().yesno(result['message'], '重新登录'+cloud.get_full_name()+'账号'+cloud.get_user_name()+'？'):
        if do_relogin(cloud.get_full_name(), cloud.get_user_name()):
            cloud = get_cloud(cloud.get_full_name(), cloud.get_user_name())
            return get_file_list(items, cloud, cid, offset, files_per_page, searchstr)
    return result

def add_items_to_directory(cloud, items, content_type, result, cid, offset, files_per_page, searchstr, add_cloudname_prefix = False):
    image_count = 0;
    subtitle_files = []
    cover_file_pc = ''
    for item in items:
        if item.has_key('sha'):
            if is_subtitle(item['ico']):
                subtitle_files.append({'name':item['n'], 'pc':item['pc']})
            if item['n'].lower() in ['cover.jpg', 'folder.jpg', 'front.jpg']:
                cover_file_pc = item['pc']
    def get_subtitlelist(name):
        sublist = []
        filename, _, ext = name.rpartition('.')
        for subitem in subtitle_files:
            if (subitem['name'].startswith(filename + '.')):# and '.' not in subitem['name'][len(filename) + 1:]):
                sublist.append(cloud.get_file_download_url(subitem['pc']))
        return sublist
    for item in items:
        if add_cloudname_prefix:
            item['n'] = '[' + cloud.get_full_name() + ']' +'[' + cloud.get_user_name() + ']' + item['n']
        if item.has_key('sha'):
            if (loadvideo == 'true' or content_type == 'video') and (item.has_key('iv') or is_video(item['ico'])):
                listitem = xbmcgui.ListItem(colorize_label(item['n'],'video'))
                if item.has_key('u'):
                    listitem.setThumbnailImage(item['u'])
                listitem.setInfo('video', {'size': item['s']})
                #if version_installed['major'] > 13:
                listitem.setSubtitles(get_subtitlelist(item['n']))
                listitem.setProperty('IsPlayable', 'true')
                listitem.setProperty('PlayableInList', 'true')
                listitem.setProperty('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:38.0) Gecko/20100101 Firefox/38.0')
                xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'VideoFile', 'pc':item['pc'], 'cloud_name':cloud.get_full_name(), 'user_name':cloud.get_user_name()}), listitem)
            elif (loadaudio == 'true' or content_type == 'audio') and is_audio(item['ico']):
                listitem = xbmcgui.ListItem(colorize_label(item['n'], 'audio'))
                if cover_file_pc != '':
                    cover_file_url = cloud.get_file_download_url(cover_file_pc)
                    listitem.setArt({'thumb':cover_file_url})
                listitem.setInfo('audio', {'size': item['s']})
                listitem.setProperty('IsPlayable', 'true')
                listitem.setProperty('PlayableInList', 'true')
                xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'AudioFile', 'pc':item['pc'], 'cloud_name':cloud.get_full_name(), 'user_name':cloud.get_user_name()}), listitem, isFolder=False)
            elif (loadimage == 'true' or content_type == 'image') and is_image(item['ico']):
                image_count = image_count + 1
                listitem = xbmcgui.ListItem(colorize_label(item['n'], 'image'))
                if item.has_key('u'):
                    listitem.setThumbnailImage(item['u'])
                if item.has_key('largeimage'):
                    largeimgurl = item['largeimage']
                else:
                    largeimgurl = ' '
                if content_type == 'image':
                    listitem.setInfo('image', {'size':item['s']})
                    listitem.setProperty('IsPlayable', 'false')
                    xbmcplugin.addDirectoryItem(addon_handle, cloud.get_image_url(imageqselect, item['pc'], largeimgurl), listitem, isFolder=False)
                else:
                    #listitem.setInfo('image', {'size':item['s']})
                    listitem.setProperty('IsPlayable', 'false')
                    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'ImageFile', 'pc':item['pc'], 'large_image_url':largeimgurl, 'cloud_name':cloud.get_full_name(), 'user_name':cloud.get_user_name()}), listitem, isFolder=False)
            elif loadsubtitle == 'true' and is_subtitle(item['ico']):
                listitem = xbmcgui.ListItem(colorize_label(item['n'], 'subtitle'))
                listitem.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(addon_handle,  build_url({'mode':'DoNothing', 'pc':item['pc']}), listitem, isFolder = False)
            elif loadother == 'true' :
                listitem = xbmcgui.ListItem(colorize_label(item['n'], 'subtitle'))
                listitem.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(addon_handle,  build_url({'mode':'DoNothing', 'pc':item['pc']}), listitem, isFolder = False)
        else:
            listitem = xbmcgui.ListItem(colorize_label(item['n'], 'dir'))
            #listitem.addContextMenuItems([("SlideShow", "SlideShow(%s)" % build_url({'mode':'folder', 'cid':item['cid'], 'offset':'0','content_type':content_type, 'cloud_type':cloud.get_name()}),)])
            xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'folder', 'cid':item['cid'], 'offset':'0','content_type':content_type, 'cloud_name':cloud.get_full_name(), 'user_name':cloud.get_user_name()}), listitem, isFolder=True)
    if (result.has_key('totalcount') and result['totalcount']>int(offset)+files_per_page) or (result.has_key('finished') and result['finished'] != True):
        npitem = xbmcgui.ListItem(colorize_label('下一页', 'video'))
        if searchstr == '':
            xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'folder', 'cid':str(cid), 'offset':str(int(offset)+files_per_page),'content_type':content_type, 'cloud_name':cloud.get_full_name(), 'user_name':cloud.get_user_name()}), npitem, isFolder = True)
        else:
            xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'folder', 'cid':str(cid), 'offset':str(int(offset)+files_per_page),'content_type':content_type, 'cloud_name':cloud.get_full_name(), 'user_name':cloud.get_user_name(), 'searchfor':searchstr}), npitem, isFolder = True)
    #xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=True)
    viewmode = get_view_mode()
    if viewmode == '':
        if image_count >= 10 and image_count * 2 > len(items):
            viewmode = 'thumbnail'
        else:
            viewmode = 'list'
    if ALL_VIEW_CODES[viewmode].has_key(xbmc.getSkinDir()):
        xbmc.executebuiltin("Container.SetViewMode(%s)" % ALL_VIEW_CODES[viewmode][xbmc.getSkinDir()])
    return

def play_video(cloud_name, user_name, pc):
    '''
    if clearunplayable:
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        i = 0
        while i < playlist.size():
            li = playlist[i]
            if li.getProperty('PlayableInList') == '':
                playlist.remove(li.getfilename())
            else:
                i = i+1
        #clearunplayable = False
    '''
    cloud = get_cloud(cloud_name, user_name)
    qselect = int(videoqselect) - 1
    sel_len = 4
    sels = []
    if qselect != -1:
        sels = cloud.get_video_quality_selection(pc)
        sel_len = len(sels)
    if videoqselect == '5':
        qsels = [('原码', '0'),('标清', '1'),('高清', '2'),('超清', '3'),('1080P', '4')]
        dialog = xbmcgui.Dialog()
        sel = dialog.select('视频质量', [q[0] for q in qsels[:(sel_len+1)]])
        if sel is -1:
            return
        qselect = int(sel) -1
    if qselect >= sel_len : qselect = sel_len -1
    if qselect == -1:
        url = cloud.get_file_download_url(pc)
    else:
        url = 'http:'+sels[qselect]

    xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=url))

def play_audio(cloud_name, user_name, pc):
    '''
    if clearunplayable:
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        i = 0
        while i < playlist.size():
            li = playlist[i]
            if li.getProperty('PlayableInList') == '':
                playlist.remove(li.getfilename())
            else:
                i = i+1
    '''
    cloud = get_cloud(cloud_name, user_name)
    xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=cloud.get_file_download_url(pc)))

def show_image(cloud_name, user_name, pc, largeimgurl):
    cloud = get_cloud(cloud_name, user_name)
    xbmc.executebuiltin('ShowPicture(%s)' % cloud.get_image_url(imageqselect, pc, largeimgurl))
    #xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=cloud.get_file_download_url(pc)))

 
def colorize_label(label, _class=None, color=None):
    color = color or colors.get(_class)

    if not color:
        return label

    if len(color) == 6:
        color = 'FF' + color

    return '[COLOR %s]%s[/COLOR]' % (color, label)

    
def is_video(ext):
    return ext.lower() in ['mkv', 'mp4', 'm4v', 'mov', 'flv', 'wmv', 'asf', 'avi', 'm2ts', 'mts', 'm2t', 'ts', 'mpg', 'mpeg', '3gp', 'rmvb', 'rm', 'iso']

def is_ext_video(ext):
    return ext.lower() in ['iso', 'm2ts', 'mts', 'm2t']

def is_subtitle(ext):
    return ext.lower() in ['srt', 'sub', 'ssa', 'smi', 'ass']

def is_audio(ext):
    return ext.lower() in ['wav', 'flac', 'mp3', 'ogg', 'm4a', 'ape', 'dff', 'dsf', 'wma', 'ra']

def is_image(ext):
    return ext.lower() in ['jpg', 'jpeg', 'bmp', 'tif', 'tiff', 'png', 'gif']

def get_files_perpage():
    pages = {'0':25, '1':50, '2':100, '3':150, '4':200, '5':500, '6':1000, '7':99999}
    return pages.get(__addon__.getSetting('filesperpage'))

def get_view_mode():
    modes = {'0':'', '1':'list', '2':'thumbnail'}
    return modes.get(__addon__.getSetting('viewmode'))

def get_cloud(cloudname, username):
    cookiefile = cookiefile = os.path.join(__profile__, 'cookie_%s_%s.dat' %(cloudname, username))
    return cloud_names[cloudname](cookiefile, username)

def save_account_settings(cloudname, accounts):
    r = ''
    for username in accounts.keys():
        if r == '':
            r = username +':' + accounts[username]
        else:
            r = r + ',' + username + ':' + accounts[username]
    __addon__.setSetting('ACCOUNT:'+cloudname, r)

def load_account_settings(cloudname):
    r = __addon__.getSetting('ACCOUNT:'+cloudname)
    if r == '':
        return {}
    accounts = {}
    accstrs = r.split(',')
    for accstr in accstrs:
        acc = accstr.split(':')
        if len(acc) == 2:
            accounts[acc[0]] = acc[1]
    return accounts

mode = args.get('mode', None)

if sys.argv[1] == 'RemoveAccount':
    do_remove_account(sys.argv[2], sys.argv[3])
elif sys.argv[1] == 'ReloginAccount':
    do_relogin(sys.argv[2], sys.argv[3])
elif mode is None:
    cts = args.get('content_type', None)
    if cts is not None:
        ct = cts[0]
    else:
        ct = 'video'
    index(ct)
elif mode[0] == 'folder':
    cid = args['cid'][0]
    offset = args['offset'][0]
    contenttype = args['content_type'][0]
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    searchfor = args.get('searchfor', None)
    if searchfor is not None:
        searchforstr = args['searchfor'][0]
    else:
        searchforstr = ''
    do_folder(cloudname, username, cid, offset, contenttype, searchforstr)
elif mode[0] == 'CloudFolder':
    contenttype = args['content_type'][0]
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    searchfor = args.get('searchfor', None)
    if searchfor is not None:
        searchforstr = args['searchfor'][0]
    else:
        searchforstr = ''
    do_cloud_folder(contenttype, cloudname, username, searchforstr)
elif mode[0] == 'Search':
    contenttype = args['content_type'][0]
    cloudname = '' if args.get('cloud_name', None) is None else args['cloud_name'][0]
    username = '' if args.get('user_name', None) is None else args['user_name'][0]
    cid = args['cid'][0]
    do_search(cloudname, username, cid, contenttype)
elif mode[0] == 'VideoFile':
    pc = args['pc'][0]
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    play_video(cloudname, username, pc)
elif mode[0] == 'AudioFile':
    pc = args['pc'][0]
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    play_audio(cloudname, username, pc)
elif mode[0] == 'ImageFile':
    pc = args['pc'][0]
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    largeimgurl = args['large_image_url'][0]
    show_image(cloudname, username, pc, largeimgurl)
elif mode[0] == 'setting':
    do_setting()
elif mode[0] == 'ManageAccounts':
    contenttype = args['content_type'][0]
    do_manage_accounts(contenttype)
elif mode[0] == 'ManageCloudAccounts':
    cloudname = args['cloud_name'][0]
    contenttype = args['content_type'][0]
    do_manage_cloud_accounts(cloudname, contenttype)
elif mode[0] == 'AddAccount':
    cloudname = args['cloud_name'][0]
    do_add_account(cloudname)
elif mode[0] == 'ReloginAccount':
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    do_relogin(cloudname, username)
elif mode[0] == 'RemoveAccount':
    cloudname = args['cloud_name'][0]
    username = args['user_name'][0]
    do_remove_account(cloudname, username)
elif mode[0] == 'DoNothing':
    do_nothing()
