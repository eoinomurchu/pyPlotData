#!/usr/bin/python

import csv
import difflib
import glob
import itertools
import wx
import wxmpl

from collections import defaultdict
from pylab import array, append, arange, mean, reshape, shape, std
from sys import argv

meanData = defaultdict(dict)
stdData = defaultdict(dict)
stats = []
title = ""

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
    global meanData
    global stdData

    #Don't read data in if it's already read
    if not key in meanData:
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
                meanData[key][aKey] = mean(data[aKey], axis=0)
                stdData[key][aKey] = std(data[aKey], axis=0)

"""The plot panel.
"""
class Plot(wxmpl.PlotPanel):
    """Constructor
    """
    def __init__(self, parent, title, generations):
        wxmpl.PlotPanel.__init__(self, parent, -1)
        self.title = title
        self.generations = generations
        self.fig = self.get_figure()
        self.Show()

    """Plots checked data and stats
    """
    def plot(self, checkedDirectories, checkedStats):
        self.fig.clear()
        axes = self.fig.gca()

        t = arange(0, self.generations+1, 1)
        for aDir in checkedDirectories:
            for stat in checkedStats:
                axes.plot(t, meanData[aDir][stat], linewidth=1.0)
                axes.errorbar(t, meanData[aDir][stat], yerr=stdData[aDir][stat],
                              marker='.',
                              capsize=2,
                              linestyle='-',
                              label=""+aDir+" - "+stat)

        axes.set_xlabel('Generation')
        axes.set_ylabel('Value')
        axes.set_title(self.title)
        axes.legend()

        axes.grid(True)
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
        self.initUI()
        self.Maximize(True)

    """Create the UI.
    """
    def initUI(self):
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.dirBox = wx.CheckListBox(parent=self, name='dirBox',
                                      choices=self.directories.keys(),
                                      size=(200, -1))
        self.dirBox.Bind(wx.EVT_CHECKLISTBOX, self.onDirBoxEvent)

        self.statsBox = wx.CheckListBox(parent=self, name='statsBox',
                                        choices=[], size=(200, -1))
        self.statsBox.Bind(wx.EVT_CHECKLISTBOX, self.onStatsBoxEvent)

        vbox.Add(self.dirBox, 1, wx.EXPAND|wx.ALL, 5)
        vbox.Add(self.statsBox, 1, wx.EXPAND|wx.ALL, 5)
        hbox.Add(vbox, 0, wx.EXPAND|wx.ALL, 5)

        self.plot = Plot(self, self.plotTitle, self.generations)
        hbox.Add(self.plot, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(hbox)
        self.Fit()

        wx.EVT_WINDOW_DESTROY(self, self.OnWindowDestroy)

    """Triggered on window close event
    """
    def OnWindowDestroy(self, evt):
        wx.GetApp().ExitMainLoop()

    """Triggered when a statistic check box is toggled.
    Reads all selected check boxes and re-plots.
    """
    def onStatsBoxEvent(self, event):
        self.checkedStats = self.statsBox.GetCheckedStrings()
        self.plot.plot(self.checkedDirectories, self.checkedStats)

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

        self.plot.plot(self.checkedDirectories, self.checkedStats)

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
Takes all combinations of pairs of directories and extracts non-matching
sub strings. The longest non matching set of sub strings for a particular
directory is used as that directory's short name/key in the directories dict.

TODO Rather, I should split by '_' as ExperimentManager script uses that as
delimiter. For each directory pairing, split them, remove common strings,
and then concatenate with what has been found so far by previous pairings.
"""
def findShortNames(directories):
    dirKeys = {}
    dirPairs = list(itertools.combinations(directories, 2))

    for pair in dirPairs:
        key1, key2 = s1, s2  = pair
        s = difflib.SequenceMatcher(a=s1, b=s2)
        fullIndices = []
        for block in s.get_matching_blocks():
            fullIndices.append(block[0:3])

        while(fullIndices):
            block = fullIndices[-1]
            s1 = removeSubString(s1, block[0], block[2])
            s2 = removeSubString(s2, block[1], block[2])
            fullIndices = fullIndices[:-1]

        if key1 in dirKeys:
            if len(dirKeys[key1]) < len(s1):
                dirKeys[key1] = s1
        else:
            dirKeys[key1] = s1

        if key2 in dirKeys:
            if len(dirKeys[key2]) < len(s2):
                dirKeys[key2] = s2
        else:
            dirKeys[key2] = s2

    return {v:k for k, v in dirKeys.items()}

"""Returns the given string with a sub string removed.
Given a string and a start index and length of a sub string, this
removes the sub string and returns the string. If the sub string is
internal (not at beginning or end) a space is inserted where the sub
string once was.
"""
def removeSubString(s, start, length):
    return s[:start]+("" if length==0 or start==0 else " ")+s[start+length:]

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
