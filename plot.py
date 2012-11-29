#!/usr/bin/python

import csv
import difflib
import glob
import itertools
import traceback
import re
import wx
import wxmpl

from collections import defaultdict, OrderedDict
from matplotlib import cm
from pylab import amin, amax, array, append, arange, linspace, mean, median, reshape, shape, std, sqrt
from sys import argv

stats = []
title = ""

PLOT_TYPES = OrderedDict([("Mean",  "mean"),
                          ("Median", "median")])

ERRORBAR_TYPES = OrderedDict([("None",  None),
                              ("Standard Deviation", "std"),
                              ("Standard Error", "ste"),
                              ("Min/Max", "minmax")])

DATA = {"mean" : defaultdict(dict), "median" : defaultdict(dict),
        "std" : defaultdict(dict), "ste": defaultdict(dict),
        "min" : defaultdict(dict), "max" : defaultdict(dict)}

""" return the union of two lists """
def union(a, b):
    return list(set(a) | set(b))

"""Extracts columns of data from csv rows
"""
def csvExtractAllCols(csvinput):
    data = defaultdict(list)

    csvDict = csv.DictReader(csvinput, delimiter=' ', quotechar='"')
    keys = csvDict.fieldnames

    if keys[-1] is "":  #Bug in div files: space at eol causes extra key
        keys.pop()

    for row in csvDict:
        for key in keys:
            data[key].append(float(row[key]))

    return keys, data

"""Reads a directory of dat and div files and calculates mean and
standard deviation values, storing them in global meanData stdData.

If the key/directory hasn't been read already, read the data in and
calculate mean values. The first line of each file is read to build
the list of statistics that can be plotted.
"""
def readDatDirectory(key, directory):
    global stats
    #Don't read data in if it's already read
    if not key in DATA["mean"]:
        data = defaultdict(array)

        #Process the dat files
        for datfile in glob.glob(directory + "/*.dat"):
            fileHandle = open(datfile, 'rb')
            keys, dataDict = csvExtractAllCols(fileHandle)
            stats = union(stats, keys)
            for aKey in keys:
                if not aKey in data:
                    data[aKey] = reshape(array(dataDict[aKey]),
                                         (1, len(dataDict[aKey])))
                else:
                    data[aKey] = append(data[aKey],
                                        reshape(array(dataDict[aKey]),
                                                (1, len(dataDict[aKey]))),
                                        axis=0)

        #Process the div files'
        for datfile in glob.glob(directory + "/*.div"):
            fileHandle = open(datfile, 'rb')
            keys, dataDict = csvExtractAllCols(fileHandle)
            stats = union(stats, keys)
            for aKey in keys:
                if not aKey in data:
                    data[aKey] = reshape(array(dataDict[aKey]),
                                         (1, len(dataDict[aKey])))
                else:
                    data[aKey] = append(data[aKey],
                                        reshape(array(dataDict[aKey]),
                                                (1, len(dataDict[aKey]))),
                                        axis=0)

        #Iterate through the stats and calculate mean/standard deviation
        for aKey in stats:
            if aKey in data:
                DATA["mean"][key][aKey] = mean(data[aKey], axis=0)
                DATA["median"][key][aKey] = median(data[aKey], axis=0)
                DATA["std"][key][aKey] = std(data[aKey], axis=0)
                DATA["ste"][key][aKey] = std(data[aKey], axis=0)/ sqrt(len(data[aKey]))
                DATA["min"][key][aKey] = mean(data[aKey], axis=0)-amin(data[aKey], axis=0)
                DATA["max"][key][aKey] = amax(data[aKey], axis=0)-mean(data[aKey], axis=0)

"""The plot panel.
"""
class Plot(wxmpl.PlotPanel):
    """Constructor
    """
    def __init__(self, parent, title, generations, nColours):
        wxmpl.PlotPanel.__init__(self, parent, -1)
        self.title = title
        self.generations = generations
        self.colours = self.setUpColourCycle(nColours)
        self.fig = self.get_figure()
        self.axes = self.fig.gca()

    def setUpColourCycle(self, nColours):
        cmap = cm.get_cmap(name='Set3')
        return [cmap(i) for i in linspace(0.0, 1.0, nColours)]

    """Plots checked data and stats
    """
    def plot(self, checkedDirectories, checkedStats, checkedPlot, checkedErrorBar):
        self.fig.clear()
        self.axes = self.fig.gca()
        self.axes.set_color_cycle(self.colours)

        t = arange(0, self.generations+1, 1)
        for aDir in checkedDirectories:
            for stat in checkedStats:
                if ERRORBAR_TYPES[checkedErrorBar] is None:
                    self.axes.plot(t,
                              DATA[PLOT_TYPES[checkedPlot]][aDir][stat],
                              linewidth=1.0,
                              label=""+aDir+" - "+stat)
                elif ERRORBAR_TYPES[checkedErrorBar] == "minmax":
                    self.axes.errorbar(t,
                                  DATA[PLOT_TYPES[checkedPlot]][aDir][stat],
                                  yerr=[DATA["min"][aDir][stat],DATA["max"][aDir][stat]],
                                  marker='.',
                                  capsize=2,
                                  linestyle='-',
                                  label=""+aDir+" - "+stat)
                else:
                    self.axes.errorbar(t,
                                  DATA[PLOT_TYPES[checkedPlot]][aDir][stat],
                                  yerr=DATA[ERRORBAR_TYPES[checkedErrorBar]][aDir][stat],
                                  marker='.',
                                  capsize=2,
                                  linestyle='-',
                                  label=""+aDir+" - "+stat)

        self.axes.set_xlim((0,self.generations))
        self.axes.set_xlabel('Generation')
        self.axes.set_ylabel('Value')
        self.axes.set_title(self.title)
        self.axes.legend(loc=2,prop={'size':6})

        self.axes.grid(True)
        self.draw()
        self.Layout()

"""The Main Frame.
"""
class MainFrame(wx.Frame):
    """Constructor
    """
    def __init__(self, parent, id, title, plotTitle, generations, directories, **kwds):
        wx.Frame.__init__(self, parent, id, title, **kwds)
        self.title = title
        self.plotTitle = plotTitle
        self.generations = generations
        self.directories = directories
        self.checkedStats = []
        self.checkedDirectories = []
        self.checkedPlotType = PLOT_TYPES.keys()[0]
        self.checkedErrorBar = ERRORBAR_TYPES.keys()[0]
        self.plots = {}

        self.initUI()
        self.Maximize(True)

    """Create the UI.
    """
    def initUI(self):
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.plotVBox = wx.BoxSizer(wx.VERTICAL)

        self.dirBox = wx.CheckListBox(parent=self,
                                      choices=sorted(self.directories.keys()),
                                      size=(200, -1))
        self.dirBox.SetLabel("Setups to Plot")
        self.dirBox.Bind(wx.EVT_CHECKLISTBOX, self.onDirBoxEvent)

        self.statsBox = wx.CheckListBox(parent=self,
                                        choices=[], size=(200, -1))
        self.statsBox.SetLabel("Statistics to Plot")
        self.statsBox.Bind(wx.EVT_CHECKLISTBOX, self.onStatsBoxEvent)

        self.plotBox = wx.RadioBox(parent=self, label="Plot Type",
                                       majorDimension = 1,
                                       choices = PLOT_TYPES.keys(),
                                       size=(200, -1))
        self.plotBox.Bind(wx.EVT_RADIOBOX, self.onPlotBoxEvent)

        self.errorBarBox = wx.RadioBox(parent=self, label="Error Bars",
                                       majorDimension = 1,
                                       choices = ERRORBAR_TYPES.keys(),
                                       size=(200, -1))
        self.errorBarBox.Bind(wx.EVT_RADIOBOX, self.onErrorBarBoxEvent)

        vbox.Add(self.dirBox, 2, wx.EXPAND|wx.ALL, 5)
        vbox.Add(self.statsBox, 2, wx.EXPAND|wx.ALL, 5)
        vbox.Add(self.plotBox, 1, wx.EXPAND|wx.ALL, 5)
        vbox.Add(self.errorBarBox, 1, wx.EXPAND|wx.ALL, 5)

        self.hbox.Add(vbox, 0, wx.EXPAND|wx.ALL, 5)
        self.hbox.Add(self.plotVBox, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.hbox)
        self.Fit()
        wx.EVT_WINDOW_DESTROY(self, self.OnWindowDestroy)

    def generatePlots(self):
        for stat in self.statsBox.GetItems():
            if not stat in self.plots:
                self.plots[stat] = Plot(self, stat, self.generations, len(self.directories))
                self.plotVBox.Add(self.plots[stat], 1, wx.EXPAND|wx.ALL, 5)

    def drawPlots(self):
        update = False
        for stat in self.plots.keys():
            if stat in self.checkedStats:
                if not self.plots[stat].IsShown():
                    self.plots[stat].Show()
                    update = True
                self.plots[stat].plot(self.checkedDirectories, [stat],
                                      self.checkedPlotType, self.checkedErrorBar)
            else:
                self.plots[stat].Hide()
        if update:
            self.Fit()

    """Triggered on window close event
    """
    def OnWindowDestroy(self, evt):
        wx.GetApp().ExitMainLoop()

    """Triggered when a statistic check box is toggled.
    Reads all selected check boxes and re-plots.
    """
    def onStatsBoxEvent(self, event):
        self.checkedStats = self.statsBox.GetCheckedStrings()
        self.drawPlots()

    """Triggered when a directory check box is toggled.
    Reads all selected check boxes, reads data in for selected boxes
    if needed, re-plots.
    """
    def onDirBoxEvent(self, event):
        global stats

        self.checkedDirectories = self.dirBox.GetCheckedStrings()
        for aDir in self.checkedDirectories:
            readDatDirectory(aDir, self.directories[aDir]);

        stats = filter(lambda stat: not stat in self.statsBox.GetItems(), stats)
        self.statsBox.InsertItems(stats, 0)

        self.generatePlots()
        self.drawPlots()

    """Triggered when selecting an error bar type
    """
    def onPlotBoxEvent(self, event):
        self.checkedPlotType = self.plotBox.GetStringSelection()
        self.drawPlots()

    """Triggered when selecting an error bar type
    """
    def onErrorBarBoxEvent(self, event):
        self.checkedErrorBar = self.errorBarBox.GetStringSelection()
        self.drawPlots()

    """Emulates all directories being selected causing all the data to be
    read at once.

    This is to be used for optimising the reading in of data.
    """
    def test(self):
        global stats

        self.checkedDirectories = self.dirBox.GetItems()
        for aDir in self.checkedDirectories:
            readDatDirectory(aDir, self.directories[aDir]);

        stats = filter(lambda stat: not stat in self.statsBox.GetItems(), stats)
        self.statsBox.InsertItems(stats, 0)

        self.plot.plot(self.checkedDirectories, self.checkedStats)
        exit(0)

"""Returns a dictionary of shortnames to directories.

Splits each file name by '_' and generates a frequency table of
words. If a word occurs more often than len(directories) they
are not included in the final shortname.
"""
def findShortNames(directories):
    dirs = OrderedDict()
    phenoms = defaultdict(int)

    for dir in directories:
        for phenom in re.split("W+|_", dir.split("/")[-2]):
            phenoms[phenom] = phenoms[phenom]+1

    for dir in directories:
        key = []
        for phenom in re.split("W+|_", dir.split("/")[-2]):
            if phenoms[phenom] < len(directories):
                key.append(phenom)
        dirs['_'.join(key)] =  dir

    return dirs

"""Sort out the command line options.
"""
def parseCommandLineOptions(argv):
    plotTitle = argv[1]
    try:
        generations = int(argv[2])
    except ValueError:
        generations = 100

    return plotTitle, generations, argv[3:]

"""Main.
"""
def main():
    plotTitle, generations, directories = parseCommandLineOptions(argv)
    directories = findShortNames(directories)
    app = wx.PySimpleApp()
    frame = MainFrame(None, -1, "pyplot", plotTitle, generations, directories)
    frame.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
