import PyPDF2
import os   
import subprocess
import networkx as nx
import json
from bs4 import BeautifulSoup
import requests
from optparse import OptionParser

from bwlists import *


parser = OptionParser()
parser.add_option("-i", "--input", dest="inputfolder",
                  help="Input folder", metavar="FILE")
parser.add_option("-o", "--output", dest="outputfile",
                  help="Output file", default="out.graphml", metavar="FILE")
parser.add_option("-q", "--quiet",
                  action="store_true", dest="verbose", default=False,
                  help="don't print status messages to stdout")
parser.add_option("-c", "--citations",
                  action="store_false", dest="usecitations", default=True,
                  help="don't use citations")
parser.add_option("-x", "--no-ixt",
                  action="store_false", dest="useixt", default=True,
                  help="use IXTheo")

(options, args) = parser.parse_args()


inputfolder = options.inputfolder 


## ===========
## Define Functions


def getixkeywords(q):
    keywords= []
    try:
        payload = {'lookfor': q, 'type': 'AllFields', 'limit':20}
        page_text = requests.get('https://ixtheo.de/Search/Results', params=payload)
        #print (" --> "+page_text.text)
        soup = BeautifulSoup(page_text.text)
        url = ''
        for a in soup.find_all('a', href=True):
            #print ("Found the URL:", a['href'])
            if a['href'].strip().startswith ('/Record'):
                url = a['href']
                break
        #print (url)
        if url != '':
            url = 'https://ixtheo.de'+url
            #print (url)
            page2 = requests.get(url)
            soup2 = BeautifulSoup(page2.text)
            trs = soup2.find_all('tr')
            for a in soup2.find_all('a', href=True):
                if a['href'].strip().endswith ('type=Subject'):
                    keywords.append(a.text)
    except Exception as e:
        if not options.verbose:
            print( "Exception in IXTheo:" +str(e))
    return keywords

def getCitationIdentifier(citation):
    cauthor = ""
    #print ("=== DEBUG ===")
    #print (str(citation) + "---> "+ str(citation['title']))
    al = ''
    if 'author' in citation:
        for a in citation['author']:
            if cauthor == "":
                if 'given' in a and 'family' in a:
                    cauthor = a['given']+ " "+a['family']
                    al = al + a['given']+ " "+a['family']
            else:
                if 'given' in a and 'family' in a:
                    cauthor = cauthor+", "+a['given']+ " "+a['family']
                    al = al + a['given']+ " "+a['family']
    node_dict = {}
    if 'date' in citation:
        node_dict['PublicationYear'] = citation['date'][0]
    else:
        node_dict['PublicationYear'] = ''
    if 'title' in citation:
        node_dict['Name'] = node_dict['PublicationYear']+":"+cauthor.replace(" ","_")+":"+citation['title'][0][:10]
    elif 'container-title' in citation:
        node_dict['Name'] = node_dict['PublicationYear']+":"+cauthor.replace(" ","_")+":"+citation['container-title'][0][:10]
    else:
        node_dict['Name'] = node_dict['PublicationYear']+":"+cauthor.replace(" ","_")+":"
    return node_dict['Name']


## ===========
## Starting

G=nx.Graph(selfloops=False)
# Journals
authorlist = []
journallist = []
keywordslist = []
keywords = {}
journals = [ f.path for f in os.scandir(inputfolder) if f.is_dir() ]
error = 0
total = 0
citationslist = {}
#
# 1. Durchlauf: Knoten erstellen

for journal in journals:
    journalname = journal.split("/")[-1]
    if not options.verbose:
        print ("In Journal "+journalname)
    journallist.append (journalname)
    years = [ f.path for f in os.scandir(journal) if f.is_dir() ]
    for yearf in years:
        year = yearf.split("/")[-1]
        #print ("===============")
        #print ("In Year "+year)
        issues = [ f.path for f in os.scandir(yearf) if f.is_dir() ]
        for issuef in issues:
            issue = issuef.split("/")[-1]
            #print ("In issue "+issue)
            files = []
            for dirpath, dirnames, filenames in os.walk(issuef):
                for filename in [f for f in filenames if f.endswith(".pdf")]:
                    files.append(os.path.join(dirpath, filename))
            #if not options.verbose:
            #    print (issuef + ":" +str(files))
            total = total + len(files)
            for file in files:
                try:
                    # Lese das PDF
                    print (file)
                    node_dict = {}
                    node_dict['PublicationYear'] = year
                    node_dict['Issue'] = issue
                    node_dict['Type'] = "document"
                    node_dict['Provenance'] = file
                    #print ("File: "+file)
                    read_pdf = PyPDF2.PdfFileReader(file)
                    page = read_pdf.getPage(0)
                    page_content = page.extractText().replace ("\n-\n", "-").replace("  ", "\n ").replace("\n\n", "\n \n").replace("—", "\n ").replace("  ","\n ").replace("Einsichten in den Psalter","\n Einsichten in den Psalter").replace("Beat Weber", "Beat Weber\n ").replace("1 Darstellung", "\n").split("\n \n \n \n")[0]
                    if page_content.count ("\n") < 4:
                        page_content = page_content + page.extractText().replace ("\n-\n", "-").replace("\n\n", "\n \n").split("\n \n \n \n")[1]
                    if "\n1" in page_content:
                        page_content = page_content.split("\n1")[0]
                    if page_content.count ("\n") < 3:
                        page_content = page_content + page.extractText().split("\n1")[1]
                    if "ﬁ" in page_content:
                        page_content = page_content.split("ﬁ")[0]
                    counter = 0
                    title =""
                    author = ""
                    counter = 0
                    for line in page_content.split("\n"):
                        if line.strip() != "":
                            if counter == 0:
                                author = line.strip()
                                if len(author.split(" "))>1:
                                    counter = 2
                                else: 
                                    counter = 1
                                if author.endswith (","):
                                    counter = 6
                            elif counter == 6:
                                author = author + " "+ line.strip()
                                if len(author.split(" "))>=1:
                                    counter = 2
                                else: 
                                    counter = 1
                                if author.endswith (","):
                                    counter = 6
                            elif counter == 1:
                                author = author + " "+line.strip()
                                counter = 2
                            elif  list(filter(line.strip().startswith, pref_list)) != []:
                                counter = 3
                            elif counter == 2:
                                title = title +" "+ line.strip()
                    title = title.strip()
                    author = author.strip()
                    if (not "!" in author) and (not "ˇ" in author) and (not "ˆ" in author) and (not ":" in author) and (not '"' in author):
                        #print (" --> "+author+": "+title+" ")
                        # Knoten für Dokument erzeugen
                        node_dict['Name'] = year+":"+author.replace(" ","_")+":"+title[:10]
                        node_dict['Title'] = title
                        G.add_node(node_dict['Name'])
                        G.nodes[node_dict['Name']].update(node_dict)  
                        authorlist.append (author)
                        
                        # Für die Liste 
                        if options.usecitations:
                            try:
                                out = subprocess.Popen(['anystyle', 'find', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                stdout,stderr = out.communicate()
                                d = json.loads(stdout)
                            except:
                                continue
                        else:
                            d = []
                        print (author + " -- "+title)
                        if options.useixt:
                            kw = getixkeywords(author + " "+title)
                            keywordslist = keywordslist+ kw
                            keywords[year+":"+author.replace(" ","_")+":"+title[:10]] = kw
                        else: 
                            kw = []    
                        for citation in d:
                         
                            #print ("===========")
                            #print (citation)
                            cauthor = ""
                            al = ''
                            
                            #if 'author' in citation:
                            #    for a in citation['author']:
                            #        #print (a['given'])
                            #        if 'given' in a and 'family' in a:
                            #            authorlist.append (a['given']+ " "+a['family'])
                            #            al = al + a['given']+ " "+a['family']
                            if 'author' in citation:
                                for a in citation['author']:
                                    if cauthor == "":
                                        if 'given' in a and 'family' in a:
                                            cauthor = a['given']+ " "+a['family']
                                            al = al + a['given']+ " "+a['family']
                                    else:
                                        if 'given' in a and 'family' in a:
                                            cauthor = cauthor+", "+a['given']+ " "+a['family']
                                            al = al + a['given']+ " "+a['family']
                            if citation['type'] == 'article-journal':
                                for jn in citation['container-title']:
                                    journallist.append (jn)
                            tl = ''
                            if 'title' in citation:
                                tl = citation['title'][0] #" ".join(citation['title'])
                            if any(title_blacklist in tl for title_blacklist in title_blacklist): 
                                continue
                            if 'container-title' in citation:
                                tl = tl+ " " + " ".join(citation['container-title'])
                            if not 'title' in citation and not 'author' in citation:
                                continue
                            if len (tl) < 10 or len(tl) > 150:
                                continue
                            if citation['type'] == "None" or citation['type'] == "none" or citation['type']==None:
                                continue
                            # Jetzt den listen hinzufügen
                            if not year+":"+author.replace(" ","_")+":"+title[:10] in citationslist:
                                citationslist[year+":"+author.replace(" ","_")+":"+title[:10]] = [citation]
                            else:
                                citationslist[year+":"+author.replace(" ","_")+":"+title[:10]].append (citation)
                            if options.useixt:
                                kwl = getixkeywords(al + " "+tl)
                                #if len(kwl) > 0:
                                #    if not options.verbose:
                                #        print (" FOund > 0 by "+getCitationIdentifier(citation))
                                keywords[getCitationIdentifier(citation)] = kwl
                                keywordslist = keywordslist+ keywords[getCitationIdentifier(citation)]
                        #out = subprocess.Popen(['anystyle', 'find', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        #stdout,stderr = out.communicate()
                        #print (stdout)
                    else:
                        error = error +1
                except Exception as e:
                    if not options.verbose:
                        print( "Exception:" +str(e))
if not options.verbose:
    print ("=========")
    print ("Errors: "+str(error) + "/"+str(total))
authorlist = list(set(authorlist))
journallist = list(set(journallist))
keywordslist = list(set(keywordslist))
for author in authorlist:
    nodedict={}
    nodedict['Name'] = author.replace(" ","_")
    nodedict['Type'] = "author"
    nodedict['Lastname'] = author.rsplit(' ', 1)[1]
    nodedict['Firstname'] =  author.rsplit(' ', 1)[0]
    G.add_node(nodedict['Name'])
    G.nodes[nodedict['Name']].update(nodedict) 
for journal in journallist:
    nodedict={}
    nodedict['Name'] = journal
    nodedict['Type'] = "journal"
    G.add_node(nodedict['Name'])
    G.nodes[nodedict['Name']].update(nodedict) 
for keyword in keywordslist:
    nodedict={}
    nodedict['Name'] = keyword.replace(" ","_")
    nodedict['Content'] = keyword
    nodedict['Type'] = "Keyword"
    G.add_node(nodedict['Name'])
    G.nodes[nodedict['Name']].update(nodedict) 
# EDGES
# =======

if not options.verbose:
    print ("2. Durchlauf: EDGES")
error = 0
total = 0
for journal in journals:
    journalname = journal.split("/")[-1]
    #print ("In Journal "+journalname)
    journallist.append (journal)
    years = [ f.path for f in os.scandir(journal) if f.is_dir() ]
    for yearf in years:
        year = yearf.split("/")[-1]
        #print ("===============")
        #print ("In Year "+year)
        issues = [ f.path for f in os.scandir(yearf) if f.is_dir() ]
        for issuef in issues:
            issue = issuef.split("/")[-1]
            #print ("In issue "+issue)
            files = []
            for dirpath, dirnames, filenames in os.walk(issuef):
                for filename in [f for f in filenames if f.endswith(".pdf")]:
                    files.append(os.path.join(dirpath, filename))
            #print (issuef + ":" +str(files))
            total = total + len(files)
            for file in files:
                try:
                    node_dict = {}
                    node_dict['PublicationYear'] = year
                    node_dict['Issue'] = issue
                    node_dict['Type'] = "document"
                    node_dict['Provenance'] = file
                    #print ("File: "+file)
                    read_pdf = PyPDF2.PdfFileReader(file)
                    page = read_pdf.getPage(0)
                    page_content = page.extractText().replace ("\n-\n", "-").replace("  ", "\n ").replace("\n\n", "\n \n").replace("—", "\n ").replace("  ","\n ").replace("Einsichten in den Psalter","\n Einsichten in den Psalter").replace("Beat Weber", "Beat Weber\n ").replace("1 Darstellung", "\n").split("\n \n \n \n")[0]
                    if page_content.count ("\n") < 4:
                        page_content = page_content + page.extractText().replace ("\n-\n", "-").replace("\n\n", "\n \n").split("\n \n \n \n")[1]
                    if "\n1" in page_content:
                        page_content = page_content.split("\n1")[0]
                    if page_content.count ("\n") < 3:
                        page_content = page_content + page.extractText().split("\n1")[1]
                    if "ﬁ" in page_content:
                        page_content = page_content.split("ﬁ")[0]
                    counter = 0
                    title =""
                    author = ""
                    counter = 0
                    for line in page_content.split("\n"):
                        if line.strip() != "":
                            if counter == 0:
                                author = line.strip()
                                if len(author.split(" "))>1:
                                    counter = 2
                                else: 
                                    counter = 1
                                if author.endswith (","):
                                    counter = 6
                            elif counter == 6:
                                author = author + " "+ line.strip()
                                if len(author.split(" "))>=1:
                                    counter = 2
                                else: 
                                    counter = 1
                                if author.endswith (","):
                                    counter = 6
                            elif counter == 1:
                                author = author + " "+line.strip()
                                counter = 2
                            elif  list(filter(line.strip().startswith, pref_list)) != []:
                                counter = 3
                            elif counter == 2:
                                title = title +" "+ line.strip()
                    title = title.strip()
                    author = author.strip()
                    #print (" --> "+author+": "+title+" ")
                    if (not "!" in author) and (not "ˇ" in author) and (not "ˆ" in author) and (not ":" in author) and (not '"' in author):
                        #print (" --> "+author+": "+title+" ")
                        #edge_dict['Name'] = title
                        G.add_edge (author.replace(" ","_"),year+":"+author.replace(" ","_")+":"+title[:10])
                        G[author.replace(" ","_")][year+":"+author.replace(" ","_")+":"+title[:10]]['Type'] = 'isAuthor'
                        G.add_edge (journalname,year+":"+author.replace(" ","_")+":"+title[:10])
                        #for key, value in edge_dict.items():
                        G[journalname][year+":"+author.replace(" ","_")+":"+title[:10]]['Type'] = 'isSource'

                        #out = subprocess.Popen(['anystyle', 'find', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        #stdout,stderr = out.communicate()
                        #print (stdout)
                        # Keywords
                        kw = keywords[year+":"+author.replace(" ","_")+":"+title[:10]]
                        for k in kw:
                            G.add_edge (year+":"+author.replace(" ","_")+":"+title[:10], k.replace(" ","_"))
                            G[year+":"+author.replace(" ","_")+":"+title[:10]][k.replace(" ","_")]['Type'] = 'hasKeyword'

                    else:
                        error = error +1
                except Exception as e:
                    if not options.verbose:
                        print("Exception: "+str(e))
if not options.verbose:
    print ("=========")
    print ("Errors: "+str(error) + "/"+str(total))


# Zitate
error = 0
total = 0
journals = [ f.path for f in os.scandir(inputfolder) if f.is_dir() ]
for journal in journals:
    journalname = journal.split("/")[-1]
    #print ("In Journal "+journalname)
    journallist.append (journalname)
    years = [ f.path for f in os.scandir(journal) if f.is_dir() ]
    for yearf in years:
        year = yearf.split("/")[-1]
        #print ("===============")
        #print ("In Year "+year)
        issues = [ f.path for f in os.scandir(yearf) if f.is_dir() ]
        for issuef in issues:
            issue = issuef.split("/")[-1]
            #print ("In issue "+issue)
            files = []
            for dirpath, dirnames, filenames in os.walk(issuef):
                for filename in [f for f in filenames if f.endswith(".pdf")]:
                    files.append(os.path.join(dirpath, filename))
            #print (issuef + ":" +str(files))
            total = total + len(files)
            for file in files:
                try:
                    node_dict = {}
                    node_dict['PublicationYear'] = year
                    node_dict['Issue'] = issue
                    node_dict['Type'] = "document"
                    node_dict['Provenance'] = file
                    #print ("File: "+file)
                    read_pdf = PyPDF2.PdfFileReader(file)
                    page = read_pdf.getPage(0)
                    page_content = page.extractText().replace ("\n-\n", "-").replace("  ", "\n ").replace("\n\n", "\n \n").replace("—", "\n ").replace("  ","\n ").replace("Einsichten in den Psalter","\n Einsichten in den Psalter").replace("Beat Weber", "Beat Weber\n ").replace("1 Darstellung", "\n").split("\n \n \n \n")[0]
                    if page_content.count ("\n") < 4:
                        page_content = page_content + page.extractText().replace ("\n-\n", "-").replace("\n\n", "\n \n").split("\n \n \n \n")[1]
                    if "\n1" in page_content:
                        page_content = page_content.split("\n1")[0]
                    if page_content.count ("\n") < 3:
                        page_content = page_content + page.extractText().split("\n1")[1]
                    if "ﬁ" in page_content:
                        page_content = page_content.split("ﬁ")[0]
                    counter = 0
                    title =""
                    author = ""
                    counter = 0
                    for line in page_content.split("\n"):
                        if line.strip() != "":
                            if counter == 0:
                                author = line.strip()
                                if len(author.split(" "))>1:
                                    counter = 2
                                else: 
                                    counter = 1
                                if author.endswith (","):
                                    counter = 6
                            elif counter == 6:
                                author = author + " "+ line.strip()
                                if len(author.split(" "))>=1:
                                    counter = 2
                                else: 
                                    counter = 1
                                if author.endswith (","):
                                    counter = 6
                            elif counter == 1:
                                author = author + " "+line.strip()
                                counter = 2
                            elif  list(filter(line.strip().startswith, pref_list)) != []:
                                counter = 3
                            elif counter == 2:
                                title = title +" "+ line.strip()
                    title = title.strip()
                    author = author.strip()
                    if (not "!" in author) and (not "ˇ" in author) and (not "ˆ" in author) and (not ":" in author) and (not '"' in author):
                        #print (" --> "+author+": "+title+" -> "+author.replace(" ","_"),year+":"+author.replace(" ","_")+":"+title[:10])
                        #print (":"+str(citationslist[author.replace(" ","_"),year+":"+author.replace(" ","_")+":"+title[:10]]))
                        #out = subprocess.Popen(['anystyle', 'find', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        #stdout,stderr = out.communicate()
                        #d = json.loads(stdout)
                        if not year+":"+author.replace(" ","_")+":"+title[:10] in citationslist:
                            #print (" No Citations for "+year+":"+author.replace(" ","_")+":"+title[:10])
                            continue
                        for citation in citationslist[year+":"+author.replace(" ","_")+":"+title[:10]]:
                            #print ("===========")
                            #print (" Found "+str(citation['title']))
                            if not 'type' in citation:
                                continue
                            if citation['type'] == "None":
                                continue
                            cauthor = ""
                            al = ''
                            if 'author' in citation:
                                for a in citation['author']:
                                    if cauthor == "":
                                        if 'given' in a and 'family' in a:
                                            cauthor = a['given']+ " "+a['family']
                                            al = al + a['given']+ " "+a['family']
                                    else:
                                        if 'given' in a and 'family' in a:
                                            cauthor = cauthor+", "+a['given']+ " "+a['family']
                                            al = al + a['given']+ " "+a['family']
                            node_dict = {}
                            if 'date' in citation:
                                node_dict['PublicationYear'] = citation['date'][0]
                            else:
                                continue
                            #if 'title' in citation:
                            #    node_dict['Name'] = node_dict['PublicationYear']+":"+cauthor.replace(" ","_")+":"+citation['title'][0][:10]
                            #elif 'container-title' in citation:
                            #    node_dict['Name'] = node_dict['PublicationYear']+":"+cauthor.replace(" ","_")+":"+citation['container-title'][0][:10]
                            #else:
                            #    node_dict['Name'] = node_dict['PublicationYear']+":"+cauthor.replace(" ","_")+":"
                            node_dict['Name'] = getCitationIdentifier(citation)
                            #print ("===============> "+node_dict['Name'])
                            if 'title' in citation:
                                node_dict['Title'] = citation['title'][0]
                            elif 'container-title' in citation:
                                node_dict['Title'] = citation['container-title'][0]
                            else:
                                node_dict['Title'] = "-"
                            node_dict['Type'] = "document"
                            node_dict['Provenance'] = "anystyle"    
                            
                            
                            #node_dict['Issue'] = issue
                            if citation['type'] == 'article-journal':
                                for jn in citation['container-title']:
                                    journallist.append (jn)
                            #print (d['author']['given']+" "+d['author']['familiy'])
                            G.add_node(node_dict['Name'])
                            G.nodes[node_dict['Name']].update(node_dict)
                            # Autoren
                            if 'author' in citation:
                                for a in citation['author']:
                                    if 'given' in a and 'family' in a:
                                        authorname = (a['given']+ " "+a['family'])
                                        authorname.replace(" ","_")
                                        G.add_edge (authorname.replace(" ","_"),node_dict['Name'])
                                        G[authorname.replace(" ","_")][node_dict['Name']]['Type'] = 'isAuthor'
                            # Journal
                            if citation['type'] == 'article-journal':
                                for jn in citation['container-title']:
                                    G.add_edge (jn,node_dict['Name'])
                                    G[jn][node_dict['Name']]['Type'] = 'isSource'
                            # Zitation
                            #if year+":"+author.replace(" ","_")+":"+title[:10] not in G:
                            #        print (" MISSING NODE "+year+":"+author.replace(" ","_")+":"+title[:10])
                            #print ("Adding citation: "+year+":"+author.replace(" ","_")+":"+title[:10] +" -- "+node_dict['Name'])
                            G.add_edge (year+":"+author.replace(" ","_")+":"+title[:10],node_dict['Name'] )
                            G[year+":"+author.replace(" ","_")+":"+title[:10]][node_dict['Name']]['Type'] = 'cites'
                            # Keywords
                            tl = ''
                            if 'title' in citation:
                                tl = " ".join(citation['title'])
                            if 'container-title' in citation:
                                tl = tl+ " " + " ".join(citation['container-title'])
                            kw = keywords[node_dict['Name']]
                            #print (" Searching KW for "+node_dict['Name']+" and found "+str(kw))
                            for k in kw:
                                #print (k+ "-->"+node_dict['Name'])
                                #if node_dict['Name'] not in G:
                                #    print (" MISSING NODE "+node_dict['Name'])
                                #if k.replace(" ","_") not in G:
                                #    print (" MISSING NODE "+k.replace(" ","_"))
                                G.add_edge (node_dict['Name'], k.replace(" ","_"))
                                G[node_dict['Name']][k.replace(" ","_")]['Type'] = 'hasKeyword'
                    else:
                        error = error +1
                except Exception as e:
                    if not options.verbose:
                        print("Exception: "+str(e))

G.remove_nodes_from(list(nx.isolates(G)))
nx.write_graphml(G,options.outputfile)






