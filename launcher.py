from panda3d.core import *
from direct.showbase.DirectObject import DirectObject
from direct.gui.DirectGui import *
from direct.interval.IntervalGlobal import *
import ast
from simpleeval import SimpleEval
import json
from direct.stdpy.file import listdir, exists
from my_zipfile import ZipFile, is_zipfile #2.7.4+ bugfree version
import os

#Helper functions
def _pos2d(x,y):
    return Point3(x,0,-y)
    
def _rec2d(width, height):
    return (-width, 0, 0, height)
    
def _resetPivot(frame):
    size=frame['frameSize']    
    frame.setPos(-size[0], 0, -size[3])        
    frame.flattenLight()

class Configer (object):
    def __init__(self, config_file):
        self.loadConfig(config_file)

    def getItem(self, key): 
        if key in self.cfg:
            return self.cfg[key]
        else:
            return self.getValueFromConfigVariable(key) 
        return None

    def __getitem__(self, key): 
        if key in self.cfg:
            return self.cfg[key]
        else:
            return self.getValueFromConfigVariable(key) 
        return None
                
    def __setitem__(self, key, value):
        self.cfg[key]=value
        
    def __contains__(self, item):        
        return item in self.cfg
        
    def getAllWords(self, var):
        """Returns all values of a config variable as a list
        or the first value if there only is one vaue in the variable
        """
        world_count=var.getNumWords()
        if world_count==1:
            return var.getValue()
        r=[]
        for i in range(world_count):
            r.append(var.getWord(i))   
        return r

    def getValueFromConfigVariable(self, var_name):
        """Returns the config variable value or values no matter what the
        type of the value is, returns list for multi word variables
        """
        var_type=ConfigVariable(var_name).getValueType()        
        #print "(",var_type,")", var_name
        
        if var_type ==ConfigFlags.VT_list:
            l=[]
            for i in range(ConfigVariableList(var_name).getNumValues()):
                l.append(ConfigVariableList(var_name).getStringValue (i))
            return l
        elif var_type ==ConfigFlags.VT_string:
            return self.getAllWords(ConfigVariableString(var_name))
        elif var_type ==ConfigFlags.VT_filename:
            return self.getAllWords(ConfigVariableFilename(var_name))
        elif var_type ==ConfigFlags.VT_double:
            return self.getAllWords(ConfigVariableDouble(var_name))
        elif var_type ==ConfigFlags.VT_bool:
            return self.getAllWords(ConfigVariableBool(var_name))    
        elif var_type ==ConfigFlags.VT_int:
            return self.getAllWords(ConfigVariableInt(var_name))
        elif var_type ==ConfigFlags.VT_enum:
            return self.getAllWords(ConfigVariableString(var_name))
        elif var_type ==ConfigFlags.VT_search_path:
            return ConfigVariableSearchPath(var_name).getValue ()
        elif var_type ==ConfigFlags.VT_int64:
            return self.getAllWords(ConfigVariableDouble(var_name))
        elif var_type ==ConfigFlags.VT_color:
            return ConfigVariableColor(var_name).getValue()
        else:        
            #the value is of unkonwn type, probably a custom value
            #load them as strings and then 
            #try to turn them into the right type one by one
            variables=self.getAllWords(ConfigVariableString(var_name, ''))   
            if len(variables)==0:
                return None      
            #is it one word?
            if ConfigVariableString(var_name).getNumWords()==1:
                try:
                   return ast.literal_eval(variables) 
                except:
                    #some special strings should be converted to bool
                    if variables in ("false", "#f"):
                        return False
                    if variables in ("true", "#t"):
                        return True    
                    return variables   
            r=[]        
            for var in variables:
                try:
                   r.append(ast.literal_eval(var)) 
                except:
                    #some special strings should be converted to bool
                    if variables in ("false", "#f"):
                        r.append(False) 
                    elif variables in ("true", "#t"):                    
                        r.append(True) 
                    else:    
                        r.append(var) 
            return r 
        return None    
            
    def loadConfig(self, config_file_name, load_all=False):
        self.cfg={}
        config_dict={}
        try:
            with open(config_file_name,'r') as f:        
                for row in f:
                    if not row.startswith("#"):
                        loadPrcFileData('',row)
                        var_name=row.split()[0]
                        var_value=self.getValueFromConfigVariable(var_name)
                        config_dict[var_name]=var_value
        except IOError:
            print "No config file"  
            
        if load_all:
            for i in range(ConfigVariableManager.getGlobalPtr().getNumVariables()):
                var_name=ConfigVariableManager.getGlobalPtr().getVariableName(i)
                var_value=self.getValueFromConfigVariable(var_name)
                config_dict[var_name]=var_value  
        self.cfg=config_dict                     
        return config_dict
                
    def saveConfig(self, config_file):
        #print "saving to:", config_file
        with open(config_file, "w") as out_file:
            out_file.write("#auto generated config file\n")
            for key in sorted(self.cfg):
                out_file.write(key+' '+self.getCfgValueAsString(key)+'\n')
                    
    def setCfgValueFromString(self, var_name, value):
        v=self.cfg[var_name]
        if isinstance(v, basestring): #string or unicode
            self.cfg[var_name]=value
        elif hasattr(v, "__iter__"):  #probaly list            
            r=[]
            for var in value.split(" "):
                try:
                   r.append(ast.literal_eval(var)) 
                except:
                    #some special strings should be converted to bool
                    if variables in ("false", "#f"):
                        r.append(False) 
                    elif variables in ("true", "#t"):                    
                        r.append(True) 
                    else:    
                        r.append(var) 
            self.cfg[var_name]=r
        else:
            try:
               self.cfg[var_name]=(ast.literal_eval(value)) 
            except:
                self.cfg[var_name]=value
            
    def getCfgValueAsString(self, var_name):
        if var_name not in self.cfg:
            v=self.getValueFromConfigVariable(var_name)            
            self.cfg[var_name]=v
            return self.getCfgValueAsString(var_name)        
        v=self.cfg[var_name]
        if isinstance(v, basestring): #string or unicode
            return v
        elif hasattr(v, "__iter__"):  #any type of sequence
            temp_string=""
            for item in v:
                temp_string+=str(item)+" "
            return  temp_string.strip()     
        else:
            return str(v)
    
class Launcher (DirectObject):
    def __init__(self, app, setup_data, custom_functions={}):         
        #we keep the 'main' application class to call some functions there
        self.app=app            
        #load the config
        self.setup_data=setup_data
        self.cfg=Configer(path+self.setup_data['basic']['config_file'])        
        
        #setup the window for the launcher
        wp = WindowProperties.getDefault() 
        wp.setFixedSize(True)  
        wp.setFullscreen(False)
        wp.setUndecorated(self.setup_data['basic']['undecorated'])
        wp.setOrigin(-2,-2)  
        wp.setTitle(self.setup_data['basic']['title'])  
        wp.setSize(self.setup_data['basic']['window_size'][0],self.setup_data['basic']['window_size'][1])        
        base.openMainWindow(props = wp)
        base.win.setCloseRequestEvent('exit_program')
        
        #a root node for ell the widgets
        self.root=pixel2d.attachNewNode('launcher_root')
        
        #set the bacground image
        self.background=DirectFrame(frameSize=_rec2d(self.setup_data['basic']['window_size'][0],self.setup_data['basic']['window_size'][1]),
                                 frameColor=(1,1,1, 1), 
                                 frameTexture=path+self.setup_data['basic']['background'],                    
                                 parent=self.root)
        _resetPivot(self.background) 
        self.background.setPos(_pos2d(0,0))                         
        
        #some vars used later
        self.last_click_time=0.0
        self.shouldExit =False
        self.last_button=None
        self.last_select_button=None
        self.last_select=None
        self.last_button_group=0            
        self.fonts={}        
        self.buttons=[]
        self.last_slider_config_name=None
        self.last_slider_name=None
        #make the needed buttons
        #needed for the updater part...
        self.update_label=self.makeLabel("", 'wait')   
        x=self.setup_data['basic']["window_size"][0]/2
        x-=self.setup_data['style']['default']["size"][0]/2  
        y=self.setup_data['basic']["window_size"][1]-self.setup_data['style']['default']["size"][1]*1.5
        pos=[x,y]   
        self.update_done_button=self.makeButton(self.setup_data['basic']['msg']['ok'], {"style": "default","pos": pos,"func": "updateDone()"})
        self.update_done_button.hide()
        #needed for the loadscreen
        self.loading_label=self.makeLabel(self.setup_data['basic']['msg']['loading'], 'loading') 
        #needed for the slider screen
        self.slider = DirectSlider(frameSize=_rec2d(self.setup_data['style']['slider']["size"][0]*0.8, self.setup_data['style']['slider']["size"][1]),
                                range=(0.0,1.0),
                                value=0.5,
                                thumb_relief=DGG.FLAT,
                                thumb_frameTexture=path+self.setup_data['style']['slider']['thumb_img'],
                                thumb_frameSize=(self.setup_data['style']['slider']['thumb_size'][0]/2,
                                                -self.setup_data['style']['slider']['thumb_size'][0]/2,
                                                -self.setup_data['style']['slider']['thumb_size'][1]/2,
                                                 self.setup_data['style']['slider']['thumb_size'][1]/2),
                                frameTexture=path+self.setup_data['style']['slider']['img'],
                                frameVisibleScale=(1.25,1), 
                                command=self.setSliderValue,
                                parent=self.root)
        x=self.setup_data['basic']["window_size"][0]/2
        x+=(self.setup_data['style']['slider']["size"][0]*0.8)/2  
        y=self.setup_data['basic']["window_size"][1]/2
        y+=self.setup_data['style']['slider']["size"][1]/2
        self.slider.setPos(_pos2d(x,y))                        
        self.slider.setTransparency(TransparencyAttrib.MDual)
        self.slider.hide()
        self.slider_done_button=self.makeButton(self.setup_data['basic']['msg']['ok'], {"style": "default","pos": pos,"func": "sliderDone()"})
        self.slider_done_button.hide()
        self.slider_label=self.makeLabel("")
        #needed for key input
        self.key_input_label=self.makeLabel("")
        self.key_input_current_label=self.makeLabel("", "key_input")
        self.key_input_done=self.makeButton(self.setup_data['basic']['msg']['ok'], {"style": "default","pos": pos,"func": "keyInputDone()"})
        self.key_input_done.hide()
        #the rest
        self.select_screens={}        
        self.select_names={}
        self.select_labels={}
        for select_group in self.setup_data["select"]:
            self.select_screens[select_group]=[]
            self.select_names[select_group]={}
            for label in self.setup_data["select"][select_group]:                
                self.select_names[select_group][self.setup_data["select"][select_group][label]]=label
                self.select_screens[select_group].append(self.makeSelectButton(label))                
            self.packSelectButtons(self.select_screens[select_group])
        i=0
        for button_group in self.setup_data["buttons"]:
            self.buttons.append({})
            for button_name in button_group:
                self.buttons[i][button_name]=self.makeButton(button_name, button_group[button_name])
                if i != 0:
                    self.buttons[i][button_name].hide()
            i+=1       
        #SimpleEval stuff
        names={'None': None}
        functions={ 
                    'Vec3':Vec3,
                    'startGame':self.startGame,
                    'exitGame':self.exitGame,
                    'updateGame':self.updateGame,
                    'updateDone':self.updateDone,
                    'toggleButtonGroup':self.toggleButtonGroup,
                    'showButton':self.showButton,
                    'select':self.showSelectScreen,
                    'slide':self.showSlideScreen,
                    'key':self.showKeyInputScreen,
                    'keyInputDone':self.keyInputDone,
                    'sliderDone':self.sliderDone,
                    'selectItem':self.selectItem,
                    'saveConfig':self.saveConfig                    
                    }   
        for key in  custom_functions:
            functions[key]=custom_functions[key]                
        self.simple_eval = SimpleEval(names=names, functions=functions)   
         
        #events 
        self.accept('exit_program',self.exitGame) 
        base.buttonThrowers[0].node().setButtonDownEvent('buttonDown')
        self.accept('buttonDown', self.getKey)
        
        #tasks
        taskMgr.add(self.update, 'launcher_update')
    
    def disable(self):
        #destroy all buttons
        for button_group in self.buttons:            
            for button_name in button_group:
                button_group[button_name].destroy()
        for button_group in  self.select_screens:       
            for button in self.select_screens[button_group]:            
                button.destroy()        
        for label in self.select_labels:
            self.select_labels[label].destroy()        
        self.key_input_label.destroy()
        self.key_input_current_label.destroy()
        self.key_input_done.destroy()
        self.update_done_button.destroy()
        self.loading_label.destroy()
        self.update_label.destroy()
        self.background.destroy() 
               
        #ignore all events
        self.ignoreAll()
        #remove task
        taskMgr.remove('launcher_update')
        #remove root node
        self.root.removeNode()
        #clear data
        del self.select_names
        del self.setup_data
        del self.last_click_time
        del self.shouldExit
        del self.last_button
        del self.last_select_button
        del self.last_select
        del self.last_button_group
        del self.fonts
        del self.buttons
        del self.last_slider_config_name
        del self.last_slider_name
        
    def getKey(self, keyname):
        self.last_key=keyname
        self.key_input_current_label['text']=keyname
        
    def renderSomeFrames(self, frames=1):
        for i in range(frames):
            base.graphicsEngine.renderFrame() 
            
    def startGame(self):
        self.toggleButtonGroup(-1)
        self.loading_label.show()
        #print "starting game"
        self.app.startGame()
    
    def hide(self):
        self.root.hide()
   
    def updateDone(self):
        self.toggleButtonGroup(0)
        self.update_done_button.hide()
        self.update_label['text']=""
        self.update_label.hide()
        
    def updateGame(self, wait_txt):
        url=self.setup_data['basic']['update_url']
        self.downloadUpdates(url)
        self.toggleButtonGroup(-1)
        self.update_label.show()
        self.update_label['text']
        
    def downloadUpdates(self, url):
        self.files_to_download=[]
                
        self.http = HTTPClient()
        self.channel = self.http.makeChannel(True)        
        
        self.files_to_download.append({'url':url, 'target':path+'update.json'})
        self.channel.beginGetDocument(DocumentSpec(url))
        self.channel.downloadToFile(Filename(path+'update.json')) 
        self.update_label['text']+=self.setup_data['basic']['msg']['collect']
        
        #add a task that will do the lifting
        taskMgr.add(self.downloadTask, 'downloadTask')    
            
    def downloadTask(self, task):
        if self.files_to_download:
            if self.channel.run():
                #print 'running...'
                return task.cont
            else:    
                if not self.channel.isDownloadComplete():      
                    #print "Error downloading file."
                    self.update_label['text']+=self.setup_data['basic']['msg']['download_error']
                    self.update_label['text']+="\n"+str(self.channel.getStatusString())
                else:
                    #if the downloaded file is named 'update.json'
                    #we get the files and urls there and add them to
                    #the download quene
                    last_file=self.files_to_download[0]['target']
                    #print "downloaded", last_file
                    self.update_label['text']+=self.setup_data['basic']['msg']['download_ok'] +last_file
                    self.renderSomeFrames(8)
                    if last_file == path+'update.json':
                        with open(path+'update.json') as f: 
                            try: 
                                file_list=json.load(f)
                                #print "loaded json file"
                            except:
                                #print "Error reading file" 
                                self.update_label['text']+=self.setup_data['basic']['msg']['read_error']   
                        #we only download files on the list that we don't have (by name)    
                        for f in file_list:
                            #print f 
                            if not os.path.exists(path+f['target']):
                                self.files_to_download.append({'url':f['url'], 'target':path+f['target']})
                    #if it's a zipfile we extract
                    elif is_zipfile(last_file):
                        #print "extracting"
                        self.update_label['text']+=self.setup_data['basic']['msg']['unzip']
                        self.renderSomeFrames(8)
                        with ZipFile(last_file) as zf:
                            zf.extractall(Filename(path).toOsSpecific())   
                        #remove zero sized files
                        self.update_label['text']+=self.setup_data['basic']['msg']['clean_up']
                        self.renderSomeFrames(8)                                               
                        for dirpath, dirs, files in os.walk(path):
                            for file in files: 
                                full_path = Filename(os.path.join(dirpath, file)).toOsSpecific()
                                #print full_path
                                if os.stat(full_path).st_size == 0:
                                    os.remove(full_path)
                    else:
                        self.update_label['text']+=path+last_file               
                        self.update_label['text']+="\n - not a zip file!"
                    #remove the last file from the list and get a next one        
                    self.files_to_download.pop(0) 
                    if self.files_to_download:
                        next_file=self.files_to_download[0]
                        #print "next_file", next_file
                        self.channel.beginGetDocument(DocumentSpec(next_file['url']))
                        self.channel.downloadToFile(Filename(next_file['target']))    
                        return task.cont                    
        #print "done" 
        self.update_label['text']+=self.setup_data['basic']['msg']['done']
        self.update_done_button.show()               
        return task.done
    
        
    def update(self, task):
        #calling exit from a sequence will crash the game
        if self.shouldExit:
            self.app.exit()
        return task.cont 
              
    def exe(self, command):
        if command:                        
            command=command.split(";")
            for cmd in command:
                try:  
                    #print cmd     
                    self.simple_eval.eval(cmd.strip())
                except Exception as e:
                    print e
    
    
    def runClickAnim(self, button):
        old_pos=button.getPos()
        new_pos=old_pos+_pos2d(0, 3)
        Sequence(LerpPosInterval(button, 0.05,new_pos),LerpPosInterval(button, 0.05,old_pos)).start()
        
            
    def onButtonClick(self, button, func, event=None): 
        time=globalClock.getFrameTime()
        if (time-self.last_click_time) >0.11:            
            self.last_button=button
            self.runClickAnim(button)                 
            Sequence(Wait(0.1),Func(self.exe, func)).start()            
        self.last_click_time=time
        
    def doNothing(self, arg=None):
        print "nop"    
    
    def saveConfig(self):        
        self.toggleButtonGroup(0)        
        config_file=path+self.setup_data['basic']['config_file']
        self.cfg.saveConfig(config_file)
    
    def exitGame(self):
        #self.app.exit()
        self.shouldExit=True
    
    def showButton(self, group, button_name):
        self.buttons[group][button_name].show()
    
    def selectItem(self, button_name):
        #set the new value in the cfg
        self.cfg.setCfgValueFromString(self.last_select, self.setup_data['select'][self.last_select][button_name])        
        #print self.cfg[self.last_select] 
        #update the button
        self.last_select_button['text']=self.last_select_button.getPythonTag("name")+" "+button_name        
        #hide the select screen
        self.hideSelectScreen()
        #show the last group
        self.toggleButtonGroup(self.last_button_group)
    
    def setSliderValue(self):
        if self.last_slider_config_name:
            round_to=self.setup_data['slide'][self.last_slider_config_name]["round"]
            mini=self.setup_data['slide'][self.last_slider_config_name]["min"]
            maxi=self.setup_data['slide'][self.last_slider_config_name]["max"]
            self.slider_value=mini+self.slider['value']*(maxi-mini)
            if round_to==0:
                self.slider_value=int(self.slider_value)
            else:
                self.slider_value=round(self.slider_value,round_to) 
            self.slider_label['text']=self.last_slider_name+'\n'+str(self.slider_value)
        
    def sliderDone(self):
        self.toggleButtonGroup(self.last_button_group)
        self.slider_label.hide()
        self.slider.hide()        
        self.slider_done_button.hide()
        self.buttons[self.last_button_group][self.last_slider_name]['text']=self.last_slider_name+str(self.slider_value)
        self.cfg[self.last_slider_config_name]=self.slider_value
        cmd="slide('"+self.last_slider_config_name+"', '"+self.last_slider_name+"', "+str(self.slider_value)+")"
        self.buttons[self.last_button_group][self.last_slider_name].bind(DGG.B1PRESS, self.onButtonClick, [self.buttons[self.last_button_group][self.last_slider_name], cmd])    
        
    def showSlideScreen(self, config_name, name, value):
        self.last_slider_config_name=config_name
        self.last_slider_name=name
        for button_group in self.buttons:            
            for button_name in button_group:
                button_group[button_name].hide()        
        self.slider_label.show()
        self.slider_label['text']=name
        self.slider.show()        
        self.slider_done_button.show()
        
        mini=self.setup_data['slide'][self.last_slider_config_name]["min"]
        maxi=self.setup_data['slide'][self.last_slider_config_name]["max"]
        
        self.slider['value']=float(value)/float(maxi-mini)
        
        self.setSliderValue()
        
    def showSelectScreen(self, screen): 
        self.last_select=screen  
        self.last_select_button=self.last_button
        for button_group in self.buttons:            
            for button_name in button_group:
                button_group[button_name].hide()                
        for button in self.select_screens[screen]:            
            button.show()        
        for label in self.select_labels:
            if label == screen:
                self.select_labels[label].show()
            else:    
                self.select_labels[label].hide()
    
    def keyInputDone(self):
        self.toggleButtonGroup(self.last_button_group)
        self.key_input_label.hide()
        self.key_input_current_label.hide()
        self.key_input_done.hide()
        self.buttons[self.last_button_group][self.last_key_name]['text']=self.last_key_name+self.last_key
        self.cfg[self.last_key_config_name]=self.last_key
        cmd="key('"+self.last_key_config_name+"', '"+self.last_key_name+"', '"+self.last_key+"')"
        self.buttons[self.last_button_group][self.last_key_name].bind(DGG.B1PRESS, self.onButtonClick, [self.buttons[self.last_button_group][self.last_key_name], cmd])    
                
    def showKeyInputScreen(self, config_name, name, value):    
        self.last_key_config_name=config_name
        self.last_key_name=name
        for button_group in self.buttons:            
            for button_name in button_group:
                button_group[button_name].hide()
        self.key_input_label.show()
        self.key_input_current_label.show()
        self.key_input_done.show()        
        self.key_input_label['text']=self.setup_data['basic']['msg']['new_key'].format(name)
        self.key_input_current_label['text']=value
                
    def hideSelectScreen(self):
        for screen in self.select_screens:
            for button in self.select_screens[screen]:            
                button.hide()    
        for label in self.select_labels:            
            self.select_labels[label].hide()
                    
    def toggleButtonGroup(self, group):
        self.last_button_group=group
        i=0
        for button_group in self.buttons:            
            for button_name in button_group:
                if i==group:
                    button_group[button_name].show()
                else:    
                    button_group[button_name].hide()
            i+=1          
    
    def getFont(self, font_name, font_size):
        if font_name in self.fonts:
            if font_size in self.fonts[font_name]:            
                font=self.fonts[font_name][font_size]
            else:
                font=self.addFontSize(font_name, font_size)
        else:
            font=self.addFont(font_name, font_size)
        return font    
    
    def addFont(self, font_name, font_size):        
        font=loader.loadFont(path+font_name)     
        font.setPixelsPerUnit(font_size)
        font.setMinfilter(Texture.FTNearest )
        font.setMagfilter(Texture.FTNearest )        
        self.fonts[font_name]={font_size:font}
        return font
        
    def addFontSize(self, font_name, font_size):
        #a bit of a hack to get a font of any size
        font=self.fonts[font_name].itervalues().next()
        new_font=font.makeCopy()        
        new_font.setPixelsPerUnit(font_size)
        self.fonts[font_name][font_size]=new_font        
        return new_font
    
    def getTextAlign(self, align):
        a=align.strip().lower()
        if a == 'center':
            return TextNode.ACenter
        elif a == 'left':
            return TextNode.ALeft    
        elif a == 'right':
            return TextNode.ARight  
        elif a == 'boxed_left':
            return TextNode.ABoxedLeft  
        elif a == 'boxed_right':
            return TextNode.ABoxedRight  
        elif a == 'boxed_center':
            return TextNode.ABoxedCenter  
        else:
            return TextNode.ALeft

    def packSelectButtons(self, button_list):        
        label_y=self.setup_data['style']["label"]["size"][1]
        x_offset=0
        y_offset=0
        button_x=self.setup_data['style']["select"]["size"][0]
        button_y=self.setup_data['style']["select"]["size"][1]
        window_x=self.setup_data['basic']["window_size"][0]
        window_y=self.setup_data['basic']["window_size"][1]+label_y
        button_count=len(button_list)   
        last_row_x_offset=0        
        #how many buttons can I fit side by side?
        buttons_per_row=window_x/button_x
        #how much space is left unused?
        x_offset=(window_x%button_x)/2
        #can all the buttons fit in one row?
        if button_count <= buttons_per_row:
            y_offset=window_y/2-button_y/2
            row_count=1            
            x_offset+=(window_x-(button_count*button_x))/2
        else:
            row_count=button_count/buttons_per_row
            if button_count%buttons_per_row != 0:
                row_count+=1
            y_offset=(window_y-((row_count)*button_y))/2
        if y_offset<0 or x_offset<0:
            print "(warning) Select buttons can't fit the window" 
        #is the last row full?
        if row_count > 1 and buttons_per_row*row_count >  button_count:            
            last_row_x_offset=(buttons_per_row*row_count-button_count)*button_x/2
        #start packing the buttons
        i=0
        row=-1
        for button in button_list:   
            column=i%buttons_per_row  
            if column==0:
                row+=1          
            x=x_offset+button_x*column
            y=y_offset+button_y*row
            if row==row_count-1: #this is the last row
                x+=last_row_x_offset
            button.setPos(_pos2d(x,y))            
            i+=1
                
    def makeLabel(self, name, style_name="label"):
        style=self.setup_data['style'][style_name]
        button=self.makeStyleButton(style)        
        button['state'] = DGG.DISABLED
        button['text']=name        
        x=self.setup_data['basic']["window_size"][0]/2
        x-=style["size"][0]/2
        button.setPos(_pos2d(x,0))
        button.hide()
        return button
            
    def makeSelectButton(self, name):
        style=self.setup_data['style']["select"]
        button=self.makeStyleButton(style)        
        button['text']=name
        button.bind(DGG.B1PRESS, self.onButtonClick, [button, "selectItem('"+name+"')"])
        button.hide()
        return button
        
    def makeButton(self, name, config):
        style=self.setup_data['style'][config["style"]]
        button=self.makeStyleButton(style)        
        button['text']=name
        button.setPos(_pos2d(config["pos"][0], config["pos"][1]))
        if "select" in config:            
            self.select_labels[config["select"]]=self.makeLabel(name)
            current_value=self.cfg.getCfgValueAsString(config["select"])
            if current_value in self.select_names[config["select"]]:
                label_txt=self.select_names[config["select"]][current_value]            
            else:
                label_txt=current_value +"*"    
            button['text']=name+" "+label_txt
            button.bind(DGG.B1PRESS, self.onButtonClick, [button, "select('"+config["select"]+"')"])
            button.setPythonTag("name", name)
        elif "slide" in config:
            current_value=self.cfg.getCfgValueAsString(config["slide"])
            if current_value == "None":
                current_value=str(self.setup_data['slide'][config["slide"]]['default'])
                self.cfg[config["slide"]]=self.setup_data['slide'][config["slide"]]['default']
            button['text']+=current_value
            button.bind(DGG.B1PRESS, self.onButtonClick, [button, "slide('"+config["slide"]+"', '"+name+"', "+current_value+")"])    
        elif "key" in config:
            current_value=self.cfg.getCfgValueAsString(config["key"])
            if current_value == "None":
                current_value=str(self.setup_data['key'][config["key"]])
                self.cfg[config["key"]]=current_value
            button['text']+=current_value
            button.bind(DGG.B1PRESS, self.onButtonClick, [button, "key('"+config["key"]+"', '"+name+"', '"+current_value+"')"])            
        elif "func" in config:
            button.bind(DGG.B1PRESS, self.onButtonClick, [button,config["func"] ])
        return button    
            
    def makeStyleButton(self, config):
        align=self.getTextAlign(config["text_align"])
        if align in (TextNode.ACenter, TextNode.ABoxedCenter):
            text_offset=[
                    -config["size"][0]/2+config["text_offset"][0], 
                    config["size"][1]/2+config["text_offset"][1]
                    ]
        elif align in (TextNode.ALeft, TextNode.ABoxedLeft):
            text_offset=[
                    -config["size"][0]+config["text_offset"][0], 
                    config["size"][1]/2+config["text_offset"][1]
                    ]  
        else:
            text_offset=[
                    +config["text_offset"][0], 
                    config["size"][1]/2+config["text_offset"][1]
                    ]                      
        button=DirectFrame(frameSize=_rec2d(config["size"][0],config["size"][1]),
                           frameColor=(1,1,1, 1), 
                           frameTexture=path+config["img"],
                           text_font=self.getFont(config["font"],config["text_size"]),
                           text=" ",
                           text_scale=config["text_size"],                           
                           text_align=align,
                           text_pos=text_offset,
                           text_fg=config["text_color"],                           
                           state=DGG.NORMAL, 
                           parent=self.root)
        _resetPivot(button)
        button.setTransparency(TransparencyAttrib.MDual)
        return button                 
      
    
