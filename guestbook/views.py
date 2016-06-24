'''
Created on Mar 5, 2015

@author: sijo
'''
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template

from google.appengine.api import users, urlfetch

from guestbook.models import Greeting, guestbook_key, DEFAULT_GUESTBOOK_NAME

import urllib, json, urllib2

from datetime import datetime

import xml.dom.minidom

import collections

def main_page(request):
    guestbook_name = request.GET.get('guestbook_name', DEFAULT_GUESTBOOK_NAME)
    # Ancestor Queries, as shown here, are strongly consistent with the High
    # Replication Datastore. Queries that span entity groups are eventually
    # consistent. If we omitted the ancestor from this query there would be
    # a slight chance that Greeting that had just been written would not
    # show up in a query.
    greetings_query = Greeting.query(ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
    greetings = greetings_query.fetch(10)

    if users.get_current_user():
        url = users.create_logout_url(request.get_full_path())
        url_linktext = 'Logout'
    else:
        url = users.create_login_url(request.get_full_path())
        url_linktext = 'Login'

    template_values = {
        'greetings': greetings,
        'guestbook_name': guestbook_name,
        'url': url,
        'url_linktext': url_linktext,
    }
    return direct_to_template(request, 'guestbook/main_page.html', template_values)

def sign_post(request):
    if request.method == 'POST':
        guestbook_name = request.POST.get('guestbook_name')
        greeting = Greeting(parent=guestbook_key(guestbook_name))
    
        if users.get_current_user():
            greeting.author = users.get_current_user()
    
        greeting.content = request.POST.get('content')
        greeting.put()
        return HttpResponseRedirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))
    return HttpResponseRedirect('/')

def get_add_status(match_url):
    url = "http://mapps.cricbuzz.com/cbzandroid/3.0/match/%scommentary.json" % match_url
    data = json.loads(urllib.urlopen(url).read())
    return data.get('header').get('status')

def get_json(request):
    urlfetch.set_default_fetch_deadline(60)
    url = "http://mapps.cricbuzz.com/cbzandroid/2.0/currentmatches.json"
    json_input = '[{"matchIndex" : 0}]'
    response = urllib.urlopen(url);
    data = json.loads(response.read())
    rep = [('<i>', ''), ('</i>', '')]
#     print len(data)
    removed = []
    
    # finding index of matches which are not of WC
    for index, ele in enumerate(data):
        if ele.get("srs") in ["NatWest t20 Blast 2016","County Championship Division One 2016","County Championship Division Two 2016","County Championship Division One 2015", "County Championship Division Two 2015",'Royal London One-Day Cup 2015']:
            removed.append(ele)
    
#     removing non WC items
    for items in removed:
#         print "deleted"
        data.remove(items)
    
    ongoing, result, upcoming =[],[],[]      
    for index, ele in enumerate(data):
        
        ele['matchurl'] = ele.get('datapath')
        
        if ele.get('header').get('type') == "TEST":
            ele['header']['status'] = get_add_status(ele.get('datapath'))
            
                   
        if ele.get('miniscore', None) is not None:
            batteamscore = ele.get('miniscore').get('batteamscore') + " (" + ele.get('miniscore').get('overs') + ")"
            bowlteamscore = ele.get('miniscore').get('bowlteamscore') + " (" + ele.get('miniscore').get('bowlteamovers') + ")"
            
            if "(0)" in bowlteamscore:
                bowlteamscore = "Yet to bat"
            
            if ele.get('miniscore').get('oversleft') == "0":
                ele['miniscore']['oversleft'] = 0
            
            ele['miniscore']['prevOvers'] = ele.get('miniscore').get('prevOvers').replace("|", "/")
            
            if ele.get('team1').get('id') == ele.get('miniscore').get('batteamid'):
                batteamname = ele.get('team1').get('sName')
                bowlteamname = ele.get('team2').get('sName')
            else:
                batteamname = ele.get('team2').get('sName')
                bowlteamname = ele.get('team1').get('sName')
            
            ele['bowlingTeamName'] = bowlteamname
            ele['battingTeamName'] = batteamname
            
       
            
            ele['displayBowlingTeamScore'] = bowlteamscore
            ele['displayBattingTeamScore'] = batteamscore
            
        if ele.get('header').get('mchState') in ['complete']:
            if ele.get('miniscore', None) is not None:
                del ele['miniscore']        
         
        if ele.get('header').get('mchState') in ['preview', 'nextlive']:
            ele['header']['status'] += " at " + datetime.strptime(ele['header']['stTme'], '%H:%M').strftime('%I:%M%p') + " in " + ele['header']['vcity'] + ", " + ele['header']['vcountry']
            ele['datapath'] = ''
            starttime=datetime.strptime(ele['header']['startdt']+" "+ele['header']['stTmeGMT'],'%b %d %Y %H:%M')
            if starttime>datetime.now():
                countdown = starttime-datetime.now()
                hours, remainder = divmod(countdown.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                ele['countdown'] = "Starts in "+str(hours).zfill(2)+":"+str(minutes).zfill(2)+":"+str(seconds).zfill(2)
            upcoming.append(ele)
            
        ele['srs'] = ele['srs'].replace("Indian Premier League 2015", "IPL8")
        
        if ele.get('header').get('mchState') not in ['complete', 'preview', 'nextlive','abandon']:
            if ele.get('header').get('mchState') in ['inprogress']:
                ele['srs'] = 'LIVE: {!s}'.format(ele['srs'])
            ongoing.append(ele)
        
        if ele.get('header').get('mchState') in ['complete','abandon']:
            ele['srs'] = '{!s}'.format(ele['srs'])
            result.append(ele)    
                    
#     print "home page"
    template_values = {
        'ongoing': ongoing,
        'upcoming':upcoming,
        'result':result,
        'guestbook_name': DEFAULT_GUESTBOOK_NAME,
        'url': '',
        'url_linktext': '',
    }
    return direct_to_template(request, 'guestbook/main_page.html', template_values)

def get_highlights_from_json(request):
    datapath = request.GET.get('url')
    data = json.loads(urllib.urlopen("http://mapps.cricbuzz.com/cbzandroid/3.0/match/" + datapath + "highlights.json").read())
    
#     print data
    com = []
    com_dict = {}
    innings = []
    highlights = {'highlight':[]}
    ings = data.get("highlights")
    rep = ['<i>', '</i>''<b>', '</b>']
    for ing in reversed(ings):
#         print ing
        for wkt in ing.get("Wickets"):
            com_dict[float(wkt.get("ballno"))] = ["OUT", wkt.get("ballno"), wkt.get("commtxt")]
                  
        for wkt in ing.get("Fours"):
            com_dict[float(wkt.get("ballno"))] = ["FOUR", wkt.get("ballno"), wkt.get("commtxt")]
                  
        for wkt in ing.get("Sixes"):
            com_dict[float(wkt.get("ballno"))] = ["SIX", wkt.get("ballno"), wkt.get("commtxt")]
                  
        for wkt in ing.get("Others"):
            com_dict[float(wkt.get("ballno"))] = ["OTHER", wkt.get("ballno"), wkt.get("commtxt")]
              
        ord_com_dict = collections.OrderedDict(sorted(com_dict.items(), reverse=True))
        com.append(ord_com_dict)
        com_dict = {}
    ing_count = len(com) 
    for ing in com:
        highlight = {}
        
        for k, v in ing.iteritems():
            if 'dropped' in ing[k][2] and ing[k][0] not in ['OUT', 'FOUR', 'SIX']:
                highlight['type'] = "DROPPED"
            else:
                highlight['type'] = ing[k][0]
            highlight['ovs'] = ing[k][1]
            highlight['text'] = str(ing[k][2]).replace("<b>", "").replace("</b>", "")
            
            highlights['highlight'].append(highlight)
            
            highlight = {}
        highlights['team'] = "INNINGS: " + str(ing_count)
        ing_count -= 1    
        innings.append(highlights)
        
        highlights = {'highlight':[]}
    pars = {'innings':innings, }
#     print "highlights"
    return direct_to_template(request, 'guestbook/highlights.html', pars)  
            

#     print com

def get_highlights(request):
    get_highlights_from_json(request)
    datapath = request.GET.get('url')
    dom = xml.dom.minidom.parseString(urllib.urlopen("http://synd.cricbuzz.com/dinamalar/data/" + datapath + "highlights.xml").read())
    data = dom.getElementsByTagName("innings")
    
    num_ings = len(data)
    innings = []
    
    highlights = {'highlight':[]}
    
    for i in xrange(num_ings - 1, -1, -1):
        entries = data[i].getElementsByTagName("line");
        highlight = {}
        for entry in reversed(entries):
#             if entry.getAttribute("type") not in "FOUR":
            highlight['type'] = entry.getAttribute("type")  
            highlight['text'] = entry.childNodes[0].data
            highlights['highlight'].append(highlight)
            highlight = {}
        highlights['team'] = data[i].getElementsByTagName("battingteam")[0].childNodes[0].data.upper() + " (" + data[i].getElementsByTagName("description")[0].childNodes[0].data + ")" 
        innings.append(highlights)
        
        highlights = {'highlight':[]}
    pars = {'innings':innings, }
    return direct_to_template(request, 'guestbook/highlights.html', pars)

def get_details(request):
    datapath = request.GET.get('url')
    dom = xml.dom.minidom.parseString(urllib.urlopen("http://synd.cricbuzz.com/dinamalar/data/" + datapath + "scores.xml").read())
    data = dom.getElementsByTagName("innings")
    batteam,bowlteam='',''
    num_ings = len(data)
    innings = []
    stats = {'batsmen':[], 'bowlers':[], 'fow':[]}
    for i in xrange(num_ings - 1, -1, -1):
        batsmen = data[i].getElementsByTagName("batteam")[0].getElementsByTagName("player");
        bowlers = data[i].getElementsByTagName("bowlteam")[0].getElementsByTagName("player");
        wickets = data[i].getElementsByTagName("fallofwickets")[0].getElementsByTagName("wicket");
        
        batsman = {};bowler = {};wicket = {};teams={data[i].getElementsByTagName("batteam")[0].getAttribute("name"):[],data[i].getElementsByTagName("bowlteam")[0].getAttribute("name"):[]}
        
        for _ in batsmen:
            if num_ings==len(data):
                batteam=data[i].getElementsByTagName("batteam")[0].getAttribute("name")
                batsmanname = _.getElementsByTagName("name")[0].childNodes[0].data
                if _.getElementsByTagName("captain")[0].childNodes[0].data == "yes":
                    batsmanname+="(c)"
                if _.getElementsByTagName("keeper")[0].childNodes[0].data == "yes":
                    batsmanname+="(wk)"
                teams[data[i].getElementsByTagName("batteam")[0].getAttribute("name")].append(batsmanname) 
            if _.getElementsByTagName("status")[0].childNodes[0].data not in " dnb ":
                batsman['name'] = _.getElementsByTagName("batsman-name")[0].childNodes[0].data
                batsman['runs'] = _.getElementsByTagName("runs")[0].childNodes[0].data
                batsman['balls'] = _.getElementsByTagName("balls")[0].childNodes[0].data
                if int(_.getElementsByTagName("fours")[0].childNodes[0].data) != 0:
                    batsman["fours"] = "4s-" + _.getElementsByTagName("fours")[0].childNodes[0].data
                if int(_.getElementsByTagName("sixes")[0].childNodes[0].data) != 0:
                    batsman["sixes"] = "6s-" + _.getElementsByTagName("sixes")[0].childNodes[0].data
                    
                status = _.getElementsByTagName("status")[0].childNodes[0].data
                if status in ["lbw", "bowled", "stumped"]:
                    if status not in ["lbw", "stumped"]:
                        status = ''
                    status += " b " + _.getElementsByTagName("bowler")[0].childNodes[0].data
                    
                elif status in "caught":
                    status = "c " + _.getElementsByTagName("fielder")[0].childNodes[0].data + " b " + _.getElementsByTagName("bowler")[0].childNodes[0].data
                
                elif status in "runout":
                    status = "runout (" + _.getElementsByTagName("fielder")[0].childNodes[0].data + ")"
                
                if "batting" in status:
                    batsman['name'] = "*" + batsman['name']
                batsman["status"] = status
                stats['batsmen'].append(batsman)
                
                batsman = {}
            
        for _ in bowlers:
            if num_ings==len(data):
                bowlteam=data[i].getElementsByTagName("bowlteam")[0].getAttribute("name")
                bowlername = _.getElementsByTagName("name")[0].childNodes[0].data
                if _.getElementsByTagName("captain")[0].childNodes[0].data == "yes":
                    bowlername+="(c)"
                if _.getElementsByTagName("keeper")[0].childNodes[0].data == "yes":
                    bowlername+="(wk)"
                teams[data[i].getElementsByTagName("bowlteam")[0].getAttribute("name")].append(bowlername) 
            if float(_.getElementsByTagName("overs")[0].childNodes[0].data) != 0:     
                bowler['name'] = _.getElementsByTagName("bowler-name")[0].childNodes[0].data
                bowler['overs'] = _.getElementsByTagName("overs")[0].childNodes[0].data
                bowler['maidens'] = _.getElementsByTagName("maidens")[0].childNodes[0].data
                bowler['runs'] = _.getElementsByTagName("runsoff")[0].childNodes[0].data
                bowler['wickets'] = _.getElementsByTagName("wickets")[0].childNodes[0].data
                if int(_.getElementsByTagName("noballs")[0].childNodes[0].data) != 0:
                    bowler["noballs"] = "nb-" + _.getElementsByTagName("noballs")[0].childNodes[0].data
                if int(_.getElementsByTagName("wides")[0].childNodes[0].data) != 0:
                    bowler["wides"] = "wd-" + _.getElementsByTagName("wides")[0].childNodes[0].data
                stats['bowlers'].append(bowler)
                bowler = {}
                
        for _ in wickets: 
#             if float(_.getElementsByTagName("overs")[0].childNodes[0].data)!=0:     
            wicket['name'] = _.getElementsByTagName("batsman-name")[0].childNodes[0].data
            wicket['overs'] = _.getElementsByTagName("overs")[0].childNodes[0].data
            wicket['runs'] = _.getElementsByTagName("runs")[0].childNodes[0].data
            wicket['num'] = _.getElementsByTagName("nbr")[0].childNodes[0].data
            stats['fow'].append(wicket)
            wicket = {}
            
        stats['runs'] = data[i].getElementsByTagName("totalruns")[0].childNodes[0].data
        stats['wickets'] = data[i].getElementsByTagName("totalwickets")[0].childNodes[0].data
        stats['overs'] = data[i].getElementsByTagName("totalovers")[0].childNodes[0].data
        stats['batteam'] = data[i].getElementsByTagName("batteam")[0].getAttribute("name").upper()
        stats['bowlteam'] = data[i].getElementsByTagName("bowlteam")[0].getAttribute("name")
        
        innings.append(stats)
        stats = {'batsmen':[], 'bowlers':[], 'fow':[]}
    
    pars = {'innings':innings,'teams':teams,'batteam':batteam,'bowlteam':bowlteam }
#     print "details"
    return direct_to_template(request, 'guestbook/detail.html', pars)
