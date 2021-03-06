"""
Note: this file is very out of date, and is not current with the rest of the
library

"""
import threading
from pprint import pprint, pformat
import pytweener
import time


import StringIO
import sys
import os
from subprocess import Popen, call, STDOUT, PIPE

def sh(cmd):
    return Popen(cmd,shell=True,stdout=PIPE,stderr=PIPE)



class SceneSetter(object):

    def set_element_attr(self, target, mapping, value):
        if hasattr(target, "elements"):
            # is a group
            for e in self.target.elements:
                if hasattr(e, "elements"):
                    # recurse
                    self.set_element_attr(e, mapping, value)
                else:
                    try:
                        setattr(e,mapping,value)
                    except AttributeError:
                        print "error setting %s" % mapping
        else:
            try:
                setattr(target, mapping, value)
            # self.target.update_rgb()
            except AttributeError:
                print "error setting %s" % mapping

    def set_target_attr(self, mapping, value):
        print "setting %s on %s to %s" % (mapping, self.target.name, value)
        self.set_element_attr(self.target, mapping, value)
# TODO clean up below cruft
        # if hasattr(self.target, "elements"):
            # # is a group
            # for e in self.target.elements:
                # try:
                    # setattr(e,mapping,value)
                # except AttributeError:
                    # print "error setting %s" % mapping
        # else:
            # try:
                # setattr(self.target, mapping, value)
            # # self.target.update_rgb()
            # except AttributeError:
                # print "error setting %s" % mapping
        # print self.target.red, self.target.green, self.target.blue
        return

    def set_intensity(self, value):
        # print "intensity"
        self.set_target_attr('intensity', value)

    def set_hue(self, value):
        self.set_target_attr('hue', value)
        # print self.target.hue
        # print self.target.red, self.target.green, self.target.blue

    def set_saturation(self, value):
        self.set_target_attr('saturation', value)

    def get_val(self):
# TODO - create getters for mappings
        return 0

    intensity = property(get_val, set_intensity)
    hue = property(get_val, set_hue)
    saturation = property(get_val, set_saturation)


    def __init__(self, *args, **kwargs):
        super(SceneSetter, self).__init__(*args, **kwargs)

        self.mappings = {   (176,14): "intensity",
                            (176,15): "hue",
                            (176,16): "saturation"}
        self.target = None
        self.target_map =  {} #{ (144,41):somelightobj}
        self.highlight_signal = (144,48)
        self.print_scene_signal = (144,49)

    def highlight_target(self):
        """ show only the target light"""
        current_intensity = self.target.intensity
        for i in range(5):
            self.target.intensity = 0
            time.sleep(.1)
            self.target.intensity = 255
            time.sleep(.1)
        self.target.intensity = current_intensity

    def trigger(self, intensity, **kwargs):
        # print args
        # print kwargs
        # return
        # [[144, 42, 127, 0], 6463]
        message_key = kwargs.get('key')
        if message_key in self.target_map and not intensity:
            element = self.target_map[message_key]
            print "setting target: %s" % element.name
            # @@ temp hack - need to make mac os conditional
            sh('say %s' % element.name)
            # TODO remove previous target from dispatcher?
            self.target = element
            self.highlight_target()
            # TODO add element to dispatcher for mapping
            return
        if message_key == self.highlight_signal:
            self.highlight_target()
            return
        # if message_key in self.mappings:
            # if self.target:
                # mapping = self.mappings[message_key]
                # # if hasattr(self.target, mapping):
                # value = (message_data[0]/127.0) * 255
                # print "setting %s on %s to %s" % (mapping, self.target.name, value)
                # if hasattr(self.target, "elements"):
                    # # is a group
                    # for e in self.target.elements:
                        # setattr(e,mapping,value)
                # else:
                    # setattr(self.target, mapping, value)
                # # print self.target.red, self.target.green, self.target.blue
                # return
        if message_key == self.print_scene_signal and not intensity:
            self.print_scene()

    def get_scene(self):
        """exports code/text that can be used to create a scene"""
        scene_dict = {}
        for element in self.target_map.values():
            name = element.name
            if name in scene_dict:
                print "ERROR - each light must have a unique name"
                # @@
                # raise ValueError: "each light must have a unique name"
            element_dict = {}
            for key, attr in self.mappings.items():
                if hasattr(element,attr):
                    element_dict[attr] = getattr(element,attr)
            scene_dict[name] = element_dict
        return scene_dict

    def print_scene(self):
        scene = self.get_scene()
        pprint(scene)
        # more macos specific stuff @@
        # output = StringIO.StringIO()
        #
        #      # contents = output.getvalue()
        #      # print contents
        #      # sh('echo %s | pbcopy' % contents)
        #      p = Popen('pbcopy',shell=True,stdin=output,stdout=PIPE,stderr=PIPE)
        #      pprint(scene,stream=output)
        #      p.communicate()
        #      output.close()



class SceneElement(object):
    def __init__(self, light=None, values={}, delay=0, duration=3):
        self.light = light
        # values is a dict of property names and end values
        # if you want different delay or duration values for some properties, create multiple elements
        # for the same light object
        self.values = values
        self.delay = delay
        self.duration = duration
        self.tween = 'linear'

class Scene(object):
    """ contains a list of lights and their various values"""
    def __init__(self, *args, **kwargs):
        self.elements = kwargs.get("elements",[])
        self.name = kwargs.get("name","scene")


    def add_element(self,light=None, values={}, delay=0, duration=3):
        E = SceneElement(light=light, values=values, delay=delay, duration=duration)
        self.elements.append(E)

def tween_done_logger(*args, **kwargs):
    # print "tween done"
    # print args
    # print kwargs
    pass

class SceneManager(object):
    """ manages the transition from one scene to another

    sets up a tween for each value from current value to new value

    need to determine whether a single scene has a single duration - no each change

    option to dip to black for some amount of time

    For whena simple transition is needed, it can be generated on the fly - all same, all linear

    todo:
    signals and triggers for scene switch?
    scenes are a funciton of the show

    """
    def __init__(self):
        self.tweener = pytweener.Tweener()
        self.switching = False
        self.last_update = 0
        self.cues = {}

    def switch_to_scene(self,scene):
        # set up tweens between values
        # @@ what should we do if we are already running a switch?
        print scene.name
        for element in scene.elements:
            # @@ TODO - remove this debug code:
            if element.light.name == "floorscr1":
                pass
                # print
                # print "%s scene values:" % element.light.name
                # print element.values
            # could gang all properties for light into a single tween... @@
            tween = getattr(self.tweener,element.tween.upper())
            changes = {}
            for k, v in element.values.items():
                if not hasattr(element.light,k): continue
                current_value = getattr(element.light, k)
                if v == current_value:
                    if element.light.name == "floorscr1":
                        pass
                        # print "skipping %s.%s already %s" % (element.light.name, k,v)
                    continue # no need to tween
                else:
                    if element.light.name == "floorscr1":
                        pass
                        # print "current value of %s.%s : %s" % (element.light.name,
                                # k, current_value)
                changes[k] = v - current_value
            if element.light.name == "floorscr1":
                pass
                # print "changes:"
                # print changes
            if changes:

                new_tween = self.tweener.addTween(
                                        element.light,
                                        tweenTime=element.duration,
                                        tweenDelay=element.delay,
                                        tweenType=tween,
                                        onCompleteFunction=tween_done_logger,
                                        **changes)
                if element.light.name == "floorscr1":
                    pass
                    # print "currently have %s tweens" % len(self.tweener.currentTweens)
                    # print "tweenables:"
                    # print new_tween.tweenables
                self.switching = True

    def set_cue(self, message_key, scene):
        self.cues[message_key] = scene

    def update(self,show):
        if not self.switching:
            self.last_update = 0
            return False
        if not self.tweener.hasTweens():
            print "scene tweens done"
            self.switching = False
            return False
        if not self.last_update:
            # in doing this, we may be 1 frame behind till next update
            # alternative is to assume timedelta of one frame
            self.last_update = show.timecode
            return False
        time_delta = show.timecode - self.last_update
        self.last_update = show.timecode
        # print "updating"
        # print time_delta
        self.tweener.update(time_delta)
        return True

    def signal(self, message):
        message_key = tuple(message[0][:2])
        vel = message[0][2]
        if vel and message_key in self.cues:
            self.switch_to_scene(self.cues[message_key])

    def trigger(self, vel, key=None):
        if vel and key in self.cues:
            self.switch_to_scene(self.cues[key])
