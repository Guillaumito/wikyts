#! /usr/bin/python

"""
 Wikyts

 HTML to YTS converter

 Romain Vallet - 2008
 Guillaume Duhamel - 2008-2013
"""

import ConfigParser
import os.path
import sys
import urllib2
import re
import htmlentitydefs

conffile = 'wikyts.ini'
if not os.path.exists(conffile):
    print "ini file not found"
    sys.exit()

config = ConfigParser.SafeConfigParser()
config.readfp(open(conffile))

reEntities = re.compile("&(#?\w+?);")

def descapeEntity(m, defs=htmlentitydefs.entitydefs):
    # callback: translate one entity to its UTF-8 value
    try:
        string = m.group(1)
        if string[0] == '#':
            string = chr(int(string[1:]))
        else:
            string = defs[string]
        return unicode( string , 'latin1' ).encode('utf-8')
    except KeyError:
        return m.group(0) # use as is

# replaces characters entities by their values
def descape(string):
    return reEntities.sub(descapeEntity, string)

def outputYts(lang, stringLists):
    prefix = config.get('output', 'prefix')
    directory = config.get('output', 'directory')
    filename = '/'.join((directory, prefix + lang + ".yts"))
    print "Creating " + filename
    f = open(filename, 'w')
    stringIndex = 0
    for string in stringLists['en']:
        msgid = descape(string.replace('|', '\\|').replace('\\', '\\\\'))
        msgstr = descape(stringLists[lang][stringIndex])
        if msgstr == "":
            msgstr = msgid
        f.write(msgid + "|" + msgstr + "\n")
        stringIndex += 1
    f.close()

langsurl = config.get('urls', 'langs')
baseurl = config.get('urls', 'base')

langsfile = urllib2.urlopen(langsurl)
langscontent = langsfile.read()
langsfile.close()

langspattern = re.compile('<td>[ ]*([a-zA-Z_]+)[ ]*</td>')
langresults = langspattern.findall(langscontent)
for langresult in langresults:
    langurl = baseurl + langresult
    html = None
    try:
        f = urllib2.urlopen(langurl)
        html = f.read()
        f.close()
    except:
        pass

    if not html: continue

    # finds the table that contains the data
    reTable = re.compile('<table.*?<(th|strong|b)>\s*en\s*</(th|strong|b)>.*?</table>', re.DOTALL)
    mTable = reTable.search(html)
    if mTable == None:
        print "Data table not found"
        sys.exit()
    table = mTable.group()

    # enumerates the languages
    langs = []
    stringLists = {}
    reLang = re.compile('<th.*?>\s*(.*?)\s*</th>', re.DOTALL)
    for mLang in reLang.finditer(table):
        langs.append(mLang.group(1))
        stringLists[mLang.group(1)] = []

    # enumerates the lines
    nbLines = 0
    reTr = re.compile('<tr.*?>\s*(.*?)\s*</tr>', re.DOTALL)
    reTd = re.compile('<td.*?>\s*(.*?)\s*</td>', re.DOTALL)
    for mTr in reTr.finditer(table):
        tr = mTr.group(1)

        # enumerates the cells
        cellIndex = 0
        for mTd in reTd.finditer(tr):
            stringLists[langs[cellIndex]].append(mTd.group(1))
            cellIndex += 1

    # creates the .po files
    for lang in langs:

        # skips english as it's the default language
        if lang == "en":
            continue

        outputYts(lang, stringLists)
