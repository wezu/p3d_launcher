import __builtin__ as builtins
from panda3d.core import loadPrcFileData
loadPrcFileData("", "window-type none")
from direct.showbase.AppRunnerGlobal import appRunner
if appRunner: #run from binary/p3d
    path=appRunner.p3dFilename.getDirname()+'/'
else:  #run from python 
    path=''
from panda3d.core import *
from direct.showbase import ShowBase
from launcher import Launcher
from collections import OrderedDict
import json
import sys

class App():
    def __init__(self):
        #init ShowBase
        base = ShowBase.ShowBase()        
        #make the path a builtin
        builtins.path=path 
        
        #the setup dict can be loaded from
        #-a json file
        #-a pickeled dict
        #-xml
        #-yaml
        #-any other file that can serialize a python dict
        #-or it could be here as a python dict
        #I used object_pairs_hook=OrderedDict to perserve the order of options
        with open(path+'setup.json') as f:  
            setup_data=json.load(f, object_pairs_hook=OrderedDict)
        #if some custom functions are needed you can add them here
        # and set the func value in the setup data e.g "func":"someCustomFunction(42)"
        functions={'someCustomFunction':self.someCustomFunction}        
        
        #launch the Launcher
        self.launcher=Launcher(self, setup_data, functions)
        
        #the Launcher also loads a prc file and puts it all in a nice dict like object
        #print self.launcher.cfg['win-size']
    
    def startGame(self):
        #print "app.startGame"
        sys.path.append(path+"source")
        from game import Game
        self.game=Game(self)    
    
    def someCustomFunction(self, arg=None):
        print "running someCustomFunction", arg
        
    def exit(self):
        print "APP EXIT!"
        base.userExit()
            
g=App()
base.run()        
        
        
