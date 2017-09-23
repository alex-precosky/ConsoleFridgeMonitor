#!/usr/bin/env python
import paho.mqtt.client as paho
import urwid
from threading import Thread
import os
import pickle

tempTopicName = "/home/fridge/XBeeSensor/temperature"
batteryTopicName = "/home/fridge/XBeeSensor/batteryVoltage"

mqtt_server = "localhost"


class mqtt_listener(Thread):
    def on_connect(self, client, userdata, flags, rc):
        pass

    def on_message(self, client, userdata, msg):      
        if msg.topic==tempTopicName:
            tempBuffer = str(float(msg.payload))
            os.write( self.temperature_write_pipe, pickle.dumps(tempBuffer) )

        elif msg.topic==batteryTopicName:
            voltageBuffer = str(float(msg.payload))
            os.write( self.voltage_write_pipe, pickle.dumps(voltageBuffer) )

    def __init__(self, temperature_write_pipe, voltage_write_pipe):
        Thread.__init__(self)

        # Set up the Mqtt client and subscribe to topics
        self.pahoClient = paho.Client()
        self.pahoClient.on_connect = self.on_connect
        self.pahoClient.on_message = self.on_message
        self.pahoClient.connect(mqtt_server, 1883, 60)
        self.pahoClient.subscribe(tempTopicName,2)
        self.pahoClient.subscribe(batteryTopicName,2)
        
        self.temperature_write_pipe = temperature_write_pipe
        self.voltage_write_pipe = voltage_write_pipe

    def run(self):
        while(True):
            self.pahoClient.loop(timeout=1.0)


        
class TUI:


    def temperature_pipe_event(self, pipe_data):
        temperature = pickle.loads(pipe_data)
        self.txtTemperature.set_text(temperature + " C")
        self.insert_plot_point( float(temperature) )

    def voltage_pipe_event(self, pipe_data):
        voltage = pickle.loads(pipe_data)
        self.set_voltage(voltage)


    def set_voltage(self, voltage):
        self.batteryVoltage = voltage
        self.set_footer()

    def set_footer(self):
        self.txtFooter.set_text(("header", "MQTT Host: %s          Battery Voltage: %s V" % (self.mqttHost, self.batteryVoltage)))

    def insert_plot_point(self, plot_point):
        self.plotData.append((plot_point-5.7,))
        self.BarGraph.set_data(self.plotData, 1)

    def __init__(self):

        # Variables used to build status line
        self.batteryVoltage = 0.00
        self.mqttHost = mqtt_server


        # Data list where points are put for bar graph plotting
        self.plotData = []

            # name,          foreground,    background,  mono         , foreground_high, background_high
        palette = [
            ('body',         'black',      'light gray', 'standout'),
            ('header',       'white',      'dark red',   'bold'),
            ('screen edge',  'light blue', 'dark cyan'),
            ('main shadow',  'dark gray',  'black'),
            ('line',         'black',      'light gray', 'standout'),
            ('bg background','light gray', 'black'),
            ('bg 1',         'black',      'dark blue', 'standout'),
            ('bg 1 smooth',  'dark blue',  'black'),
            ('bg 2',         'black',      'dark cyan', 'standout'),
            ('bg 2 smooth',  'dark cyan',  'black'),
            ('button normal','light gray', 'dark blue', 'standout'),
            ('button select','white',      'dark green'),
            ('line',         'black',      'light gray', 'standout'),
            ('pg normal',    'white',      'black', 'standout'),
            ('pg complete',  'white',      'dark magenta'),
            ('pg smooth',    'dark magenta','black'),
            ('bigtext',      'dark green',      'dark red' )
            ]

        # Title
        txtTitle = urwid.BigText(("bigtext", "@alexmaswarrior fridge"), urwid.font.Thin6x6Font())
        txtTitleBox = urwid.Padding(txtTitle, "center", width="clip")
        txtTitleBox = urwid.Filler(txtTitleBox, "bottom")
        txtTitleBox = urwid.BoxAdapter(txtTitleBox, 7)
        titlePile = urwid.Pile([txtTitleBox])

        # Big temperature numerals
        self.txtTemperature = urwid.BigText("", urwid.font.HalfBlock7x7Font())
        txtTemperatureBox = urwid.Padding(self.txtTemperature, "center", width="clip")
        txtTemperatureBox = urwid.Filler(txtTemperatureBox, "bottom")
        txtTemperatureBox = urwid.BoxAdapter(txtTemperatureBox, 7)

        # Footer
        self.txtFooter = urwid.Text("MQTT Host:     Battery Voltage:")

        # History graph
        self.BarGraph = urwid.BarGraph(['bg background','bg 1','bg 2'])
        self.BarGraph.set_data([(0,),(1,),(2,)], 8)
        self.BarGraph.set_bar_width(1)
        BarGraphBox = urwid.Columns([("weight",2,self.BarGraph)])
        BarGraphBox = urwid.Padding(self.BarGraph, ("fixed left",1))
        BarGraphBox = urwid.BoxAdapter(BarGraphBox,25)

        # put it together
        cols = urwid.Columns([txtTemperatureBox, BarGraphBox])
        fill = urwid.Filler(cols, "middle")
                             

        frame=urwid.Frame(fill, header=titlePile, footer=self.txtFooter)
        frameLineBox = urwid.LineBox(frame, title="Refrigerator Display Thing", tlcorner="\u2554", tline="\u2550", lline="\u2551", trcorner="\u2557", blcorner="\u255A", rline="\u2551", bline="\u2550", brcorner="\u255d")

        screen = urwid.raw_display.Screen()
        screen.register_palette(palette)
        self.loop = urwid.MainLoop(frameLineBox, palette, screen=screen)

        # Gets the writing end of pipes to the UI event loop
        self.temperature_write_pipe = self.loop.watch_pipe( self.temperature_pipe_event )
        self.voltage_write_pipe = self.loop.watch_pipe( self.voltage_pipe_event )

    def get_temperature_write_pipe(self):
        return self.temperature_write_pipe

    def get_voltage_write_pipe(self):
        return self.voltage_write_pipe


    def go(self):
        self.loop.run()


if __name__=="__main__":

    my_tui = TUI()
    temperature_write_pipe = my_tui.get_temperature_write_pipe()
    voltage_write_pipe = my_tui.get_voltage_write_pipe()
    
    # Start the mqtt listener thread, giving it the write pipe so it can write to the UI event loop
    lstnr = mqtt_listener( temperature_write_pipe, voltage_write_pipe )
    lstnr.start()

    # Start the UI event loop. Blocks forever
    try:
        my_tui.go()
    except KeyboardInterrupt:
        exit()
    




