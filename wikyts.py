#! /usr/bin/python

"""
 Wikyts

 HTML to YTS converter

 Romain Vallet - 2008
 Guillaume Duhamel - 2008-2013
 Theo Berkau 2013
"""

import ConfigParser
import os.path
import sys
import urllib2
import re
import htmlentitydefs
import sys
import mwclient

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
        f.write(msgid.encode('utf-8') + "|" + msgstr.encode('utf-8') + "\n")
        stringIndex += 1
    f.close()

def loadlog():
    strings = []
    prefix = config.get('output', 'prefix')
    directory = config.get('output', 'directory')
    filename = '/'.join((directory, prefix + "log.yts"))

    f = open(filename, 'r')    
    for string in f:        
        string = descape(string.replace('|\n', ''))
        strings.append(string)
    f.close()
    return strings

def commitChangeLang(lang, engList, stringLists):
    str = unicode("{|\n")
    first = True

    if lang == "en":
        for eng in engLists:
            if first == False:
                str += u' |-\n'
            else:
                first = False
            str += u" |<nowiki>" + unicode(eng) + u"</nowiki>\n"
    else:
        for eng in engLists:
            if first == False:
                str += u' |-\n'
            else:
                first = False
            stringExist = eng in stringLists['en']
            if stringExist:
                i = stringLists['en'].index(eng)
                if eng != stringLists[lang][i]:
                    if len(stringLists[lang][i]) != 0:
                        stringTrans = True
                    else:
                        stringTrans = False
                else:
                    stringTrans = False

            if stringExist and stringTrans:
                str += u" |<nowiki>" + unicode(eng) + u"</nowiki>||<nowiki>" + unicode(stringLists[lang][i]) + u"</nowiki>\n"
            else:
                str += u" |<nowiki>" + unicode(eng) + u"</nowiki>||" + u"\n"

    text = str + u" |}\n"

    # Save changes back to page
    print "Patching " + lang + " translation..."
    #print text.encode('utf-8')
    page.save(text, summary = 'Wikyts - Commiting translation changes')

    print "Patching complete"
                
if __name__ == "__main__":
    commitchanges = False
    if len(sys.argv) == 2 and sys.argv[1] == "commit":        
        commitchanges = True

    wikiurl = config.get('urls', 'wiki')
    wikipath = config.get('urls', 'wikipath')
    baseurl = config.get('urls', 'base')
    langsurl = config.get('urls', 'langs')

    # login to wiki
    print "Logging in..."

    un = config.get('login', 'username')
    pw = config.get('login', 'password')

    site = mwclient.Site(wikiurl, path=wikipath)
    site.login(un, pw)

    engLists = []

    # Get log data
    if commitchanges == True:
        # Load log file
        print "Loading log file..."
        logLists = []
        logLists = loadlog()

        langurl = baseurl + 'en'
        html = None
        page = site.Pages[langurl]
        html = page.edit()

        reTd = re.compile('<nowiki.*?>\s*(.*?)\s*</nowiki>', re.DOTALL)
        engLists = reTd.findall(html)
       
        # Remove strings if they're already there
        print "Removing duplicates"
        for string in engLists:
            if string in logLists:
                logLists.remove(string)

        engLists += logLists
        engLists.sort()
        commitChangeLang('en', engLists, None)

    # Get langs page
    print "Retrieving language list..."

    page = site.Pages[langsurl]
    langscontent = page.edit()

    langspattern = re.compile('[|][ ]*([a-zA-Z_]+)[ ]*[||]')
    langresults = langspattern.findall(langscontent)
    langList = []
    for langresult in langresults:
        langurl = baseurl + langresult
        html = None
        page = site.Pages[langurl]
        if page.exists == False:
            continue

        html = page.edit()

        print "Parsing " + langresult + " table..."

        # enumerates the languages
        langs = []
        stringLists = {}
        reLang = re.compile('![ ]*([^ !\n]+)')
        mLangs = reLang.findall(html)
        for mLang in mLangs:
            langs.append(mLang)
            stringLists[mLang] = []

        # enumerates the lines
        nbLines = 0
        reTr = re.compile('[|]-\s*(.*?)\s*\n ', re.DOTALL)
        reTd = re.compile('(?=<|)[^ |\n][^|\n]+')        
        for mTr in reTr.finditer(html):
            tr = mTr.group(1)

            # enumerates the cells
            cellIndex = 0
            mTds = reTd.findall(tr)
            if len(mTds) < len(langs):
                mTds.append(u'');

            for mTd in mTds:
                if mTd.find('<nowiki>') != -1:
                    reTdSub = re.compile('<nowiki.*?>\s*(.*?)\s*</nowiki>', re.DOTALL)
                    str = reTdSub.findall(mTd)
                    str = str[0]
                else:
                    str = mTd

                stringLists[langs[cellIndex]].append(str)
                cellIndex += 1

        if commitchanges != True:
            # creates the .po files
            for lang in langs:
                # skips english as it's the default language
                if lang == "en":
                    continue

                outputYts(lang, stringLists)
        else:
            commitChangeLang(langs[1], engLists, stringLists)
    if commitchanges == True:
        print "All Patching complete"
