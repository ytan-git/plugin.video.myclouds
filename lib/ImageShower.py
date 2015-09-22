class ImageShower(xbmcgui.Window):
    def __init__(self):
        self.imgControl = xbmcgui.ControlImage(0,0,1280,720, filename = '', aspectRatio=2)
        self.addControl(self.imgControl)
    def showImage(self, image_list, cur_position):
        self.image_count = len(image_list)
        self.image_list = image_list
        self.cur_position = cur_position
        self.showCurrentImage()
    def showCurrentImage(self):
        url = get_image_url(self.image_list[self.cur_position])
        self.imgControl.setImage(url) #get_image_url(self.image_list[self.cur_position]))
    def onAction(self,action):
        if action.getId() in [xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_GESTURE_SWIPE_RIGHT] and self.cur_position > 0:
            self.cur_position = self.cur_position -1
            self.showCurrentImage()
        elif action.getId() in [xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_GESTURE_SWIPE_LEFT] and self.cur_position < len(self.image_list) - 1:
            self.cur_position = self.cur_position + 1
            self.showCurrentImage()
        elif action.getId() in [xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP, xbmcgui.ACTION_GESTURE_SWIPE_DOWN] and self.cur_position > 0:
            self.cur_position = self.cur_position - 10
            if self.cur_position < 0 : self.cur_position = 0
            self.showCurrentImage()
        elif action.getId() in [xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_GESTURE_SWIPE_UP] and self.cur_position < self.image_count - 1:
            self.cur_position = self.cur_position + 10
            if self.cur_position > self.image_count - 1: self.cur_position = self.image_count - 1
            self.showCurrentImage()
        elif action.getId() in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_PARENT_DIR, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_SELECT_ITEM,
                                xbmcgui.ACTION_STOP]:
            self.close()
            return
        
    def onClick(self, controlID):
        self.close()
    def onControl(self, controlID):
        self.close()

imageShower = ImageShower()

def show_image(pc, img_pc_list):
    xbmc.executebuiltin('ShowPicture(%s)' % get_image_url(pc))
    return
    curpos = -1
    i = 0
    for item in img_pc_list:
        if item == pc:
            curpos = i
            break;
        i = i + 1
    if curpos == -1:
        return

xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode':'ImageFile', 'pc':item['pc'], 'image_pc_list':image_pc_files}), listitem, isFolder=False)
imageShower.showImage(img_pc_list, curpos)
imageShower.doModal()

imgliststr = args['image_pc_list'][0].replace("u'", "").replace("[", "").replace("]", "").replace("'", "").replace(" ", "")
imglist = imgliststr.split(',')
show_image(pc, imglist)
