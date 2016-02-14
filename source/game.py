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
        
        #"CarouselDemo" stuff
        base.disableMouse()  # Allow manual positioning of the camera
        camera.setPosHpr(0, -8, 2.5, 0, -9, 0)  # Set the cameras' position
                                                # and orientation

        self.loadModels()  # Load and position our models
        self.setupLights()  # Add some basic lighting
        self.startCarousel()  # Create the needed intervals and put the
                              # carousel into motion
        
        
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
        wp.setTitle("CarouselDemo")
        #kill the Launcher
        self.app.launcher.disable()
        #open the window
        base.openMainWindow(props = wp) 
        #exit event
        base.win.setCloseRequestEvent('exit_program')        
        self.accept('exit_program',self.exitGame)   
        
    def exitGame(self):
        self.app.exit()

    def loadModels(self):
        # Load the carousel base
        self.carousel = loader.loadModel(path+"models/carousel_base.egg.pz")
        self.carousel.reparentTo(render)  # Attach it to render

        # Load the modeled lights that are on the outer rim of the carousel
        # (not Panda lights)
        # There are 2 groups of lights. At any given time, one group will have
        # the "on" texture and the other will have the "off" texture.
        self.lights1 = loader.loadModel(path+"models/carousel_lights.egg.pz")
        self.lights1.reparentTo(self.carousel)

        # Load the 2nd set of lights
        self.lights2 = loader.loadModel(path+"models/carousel_lights.egg.pz")
        # We need to rotate the 2nd so it doesn't overlap with the 1st set.
        self.lights2.setH(36)
        self.lights2.reparentTo(self.carousel)

        # Load the textures for the lights. One texture is for the "on" state,
        # the other is for the "off" state.
        self.lightOffTex = loader.loadTexture(path+"models/carousel_lights_off.jpg")
        self.lightOnTex = loader.loadTexture(path+"models/carousel_lights_on.jpg")

        # Create an list (self.pandas) with filled with 4 dummy nodes attached
        # to the carousel.
        # This uses a python concept called "Array Comprehensions."  Check the
        # Python manual for more information on how they work
        self.pandas = [self.carousel.attachNewNode("panda" + str(i))
                       for i in range(4)]
        self.models = [loader.loadModel(path+"models/carousel_panda.egg.pz")
                       for i in range(4)]
        self.moves = [0] * 4

        for i in range(4):
            # set the position and orientation of the ith panda node we just created
            # The Z value of the position will be the base height of the pandas.
            # The headings are multiplied by i to put each panda in its own position
            # around the carousel
            self.pandas[i].setPosHpr(0, 0, 1.3, i * 90, 0, 0)

            # Load the actual panda model, and parent it to its dummy node
            self.models[i].reparentTo(self.pandas[i])
            # Set the distance from the center. This distance is based on the way the
            # carousel was modeled in Maya
            self.models[i].setY(.85)

        # Load the environment (Sky sphere and ground plane)
        self.env = loader.loadModel(path+"models/env.egg.pz")
        self.env.reparentTo(render)
        self.env.setScale(7)

    # Panda Lighting
    def setupLights(self):
        # Create some lights and add them to the scene. By setting the lights on
        # render they affect the entire scene
        # Check out the lighting tutorial for more information on lights
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.4, .4, .35, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(LVector3(0, 8, -2.5))
        directionalLight.setColor((0.9, 0.8, 0.9, 1))
        render.setLight(render.attachNewNode(directionalLight))
        render.setLight(render.attachNewNode(ambientLight))

        # Explicitly set the environment to not be lit
        self.env.setLightOff()

    def startCarousel(self):
        # Here's where we actually create the intervals to move the carousel
        # The first type of interval we use is one created directly from a NodePath
        # This interval tells the NodePath to vary its orientation (hpr) from its
        # current value (0,0,0) to (360,0,0) over 20 seconds. Intervals created from
        # NodePaths also exist for position, scale, color, and shear

        self.carouselSpin = self.carousel.hprInterval(20, LVector3(360, 0, 0))
        # Once an interval is created, we need to tell it to actually move.
        # start() will cause an interval to play once. loop() will tell an interval
        # to repeat once it finished. To keep the carousel turning, we use
        # loop()
        self.carouselSpin.loop()

        # The next type of interval we use is called a LerpFunc interval. It is
        # called that becuase it linearly interpolates (aka Lerp) values passed to
        # a function over a given amount of time.

        # In this specific case, horses on a carousel don't move contantly up,
        # suddenly stop, and then contantly move down again. Instead, they start
        # slowly, get fast in the middle, and slow down at the top. This motion is
        # close to a sine wave. This LerpFunc calls the function oscillatePanda
        # (which we will create below), which changes the height of the panda based
        # on the sin of the value passed in. In this way we achieve non-linear
        # motion by linearly changing the input to a function
        for i in range(4):
            self.moves[i] = LerpFunc(
                self.oscillatePanda,  # function to call
                duration=3,  # 3 second duration
                fromData=0,  # starting value (in radians)
                toData=2 * pi,  # ending value (2pi radians = 360 degrees)
                # Additional information to pass to
                # self.oscialtePanda
                extraArgs=[self.models[i], pi * (i % 2)]
            )
            # again, we want these to play continuously so we start them with
            # loop()
            self.moves[i].loop()

        # Finally, we combine Sequence, Parallel, Func, and Wait intervals,
        # to schedule texture swapping on the lights to simulate the lights turning
        # on and off.
        # Sequence intervals play other intervals in a sequence. In other words,
        # it waits for the current interval to finish before playing the next
        # one.
        # Parallel intervals play a group of intervals at the same time
        # Wait intervals simply do nothing for a given amount of time
        # Func intervals simply make a single function call. This is helpful because
        # it allows us to schedule functions to be called in a larger sequence. They
        # take virtually no time so they don't cause a Sequence to wait.

        self.lightBlink = Sequence(
            # For the first step in our sequence we will set the on texture on one
            # light and set the off texture on the other light at the same time
            Parallel(
                Func(self.lights1.setTexture, self.lightOnTex, 1),
                Func(self.lights2.setTexture, self.lightOffTex, 1)),
            Wait(1),  # Then we will wait 1 second
            # Then we will switch the textures at the same time
            Parallel(
                Func(self.lights1.setTexture, self.lightOffTex, 1),
                Func(self.lights2.setTexture, self.lightOnTex, 1)),
            Wait(1)  # Then we will wait another second
        )

        self.lightBlink.loop()  # Loop this sequence continuously

    def oscillatePanda(self, rad, panda, offset):
        # This is the oscillation function mentioned earlier. It takes in a
        # degree value, a NodePath to set the height on, and an offset. The
        # offset is there so that the different pandas can move opposite to
        # each other.  The .2 is the amplitude, so the height of the panda will
        # vary from -.2 to .2
        panda.setZ(sin(rad + offset) * .2)
