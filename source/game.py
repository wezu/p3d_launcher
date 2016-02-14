# A mode version of the "CarouselDemo" by Shao Zhang, Phil Saltzman, and Eddie Canaan
from panda3d.core import loadPrcFile
loadPrcFile(path+"autoconfig.prc")
from panda3d.core import *
from direct.showbase.DirectObject import DirectObject
from direct.interval.IntervalGlobal import *
from math import pi, sin

#make sure the loadscreen is displayed while we load things
for i in range(8):
    base.graphicsEngine.renderFrame() 
    
class Game(DirectObject):
    def __init__(self, app):    
        self.app=app
        
        #Luncher demo stuff...
        #reload the config values
        self.app.launcher.cfg.loadConfig(path+"autoconfig.prc")
        self.cfg=self.app.launcher.cfg
        
        #check if we can open a fullscreen window at the requested size
        if self.cfg['fullscreen']:
            mods=[]
            for mode in base.pipe.getDisplayInformation().getDisplayModes():
                mods.append([mode.width, mode.height])
            if self.cfg['win-size'] not in mods:
                self.cfg['fullscreen']=False
                print "Can't open fullscreen window at", self.cfg['win-size']    

        #the window props should be set by this time, but make sure 
        wp = WindowProperties.getDefault()                  
        wp.setUndecorated(self.cfg['undecorated'])          
        wp.setFullscreen(self.cfg['fullscreen'])     
        wp.setSize(self.cfg['win-size'][0],self.cfg['win-size'][1])   
        #these probably won't be in the config (?)
        wp.setOrigin(-2,-2)  
        wp.setFixedSize(self.cfg['win-fixed-size'])  
        wp.setTitle("Run update to download CarouselDemo")
        #kill the Launcher
        self.app.launcher.disable()
        #open the window
        base.openMainWindow(props = wp) 
        #exit event
        base.win.setCloseRequestEvent('exit_program')        
        self.accept('exit_program',self.exitGame)   
        
    def exitGame(self):
        self.app.exit()
