from rtmplite3.rtmp import FlashServer, Event
import rtmplite3.multitask as multitask
import time

def start():
    _verbose = False
    _recording = False
    _debug = False
    agent = FlashServer()
    agent.root = "./"
    agent.start("0.0.0.0", 1935)
    multitask.run()
    agent.stop()
    
def test_event1():
    def handler(client, *args):
        print("Connected")
    Event.add_handler("onConnect", handler)

def test_event2():
    @Event.add("onDisconnect")
    def handler(client):
        print("Disconnected")

def test_event3():
    @Event.onPublish
    def handler(client, stream):
        print("Publishing")