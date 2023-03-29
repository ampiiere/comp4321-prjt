from bs4 import BeautifulSoup
from sqlitedict import SqliteDict
import requests
from nltk.tokenize import WhitespaceTokenizer
import queue
import re
import os
from dateutil import parser
from datetime import datetime
from tools.porter import porter
from urllib.parse import urljoin
import urllib3

ORIGIN_URL = "http://www.cse.ust.hk/" # change origin site here
MAX_PAGE = 30 # change max page here

parentID_childID = dict() # {parentID: [childID,c2]}
pageID_url = dict() # {pageID: url}
url_pageID = dict() # {url: pageID}
forwardidx = dict() # {pageID: [(w1,f1), [w1,f2], [w3,f3]], pageID:[]...}
inverseidx = dict() # {word1: [(page1ID, freq1),(page2ID, freq2)]}
wordID_word = dict() # {wordID: word}
word_wordID = dict() 
pageID_elem = dict() # {pageID: [title, mod date,index date, size]}

q = queue.Queue()
stop_words = set([line.rstrip('\n') for line in open('./tools/stopwords.txt')])

def index():
    """calls main function, and saves filled dicts() into sqlite database"""
    
    print(f"\n[START] Begin crawling, Origin url: {ORIGIN_URL}")
    crawl(ORIGIN_URL, q)
    print("[END] End crawl, saving to database...")

    if os.path.isfile("./db/indexdb.sqlite"):
        os.remove("./db/indexdb.sqlite")
    db=SqliteDict("./db/indexdb.sqlite")
    db['parentID_childID']=parentID_childID
    db['pageID_url']= pageID_url
    db['url_pageID'] = url_pageID
    db['forwardidx'] = forwardidx
    db['inverseidx'] = inverseidx
    db['wordID_word'] = wordID_word
    db['word_wordID'] = word_wordID
    db['pageID_elem'] = pageID_elem
    db.commit()
    db.close()
    print("[END] Finished Saving.\n")

def preprocess_text(text):
    """preprocessing text in page into word tokens 

    Args:
        text (str): text in page

    Returns:
        List[str]: List of word tokens
    """
    tokens = WhitespaceTokenizer().tokenize(text)  # tokenize words 
    
    # span_obj = WhitespaceTokenizer().span_tokenize(text)
    # spans = [span for span in span_obj]
    
    tokens = [word.lower() for word in tokens] # lower case
    tokens = [re.sub(r"[^\s\w\d]", '', c) for c in tokens] # remove punctuation
    # tokens = [re.sub(r"\b\d+\b", "", c) for c in tokens]
    tokens=['' if c in stop_words else c for c in tokens] # remove stop words
    
    tokens=list(filter(None, tokens)) # remove duplicates
    tokens=[porter(c) for c in tokens] #TODO PORTER
    
    return tokens


def count_word_freq(tokenlist):
    """Count word frequencies

    Args:
        tokenlist (List[str]): List of word tokens in page

    Returns:
        dict(): dictionary with (word, word frequency) key value paris
    """
    page_dict = dict()
    for token in tokenlist:
        if page_dict.get(token):
            page_dict[token] += 1
        else:
            page_dict[token] = 1

    return page_dict


def index_words(page_dict, pageID):
    """indexing words in page into word_wordID,wordID_word, inverseidx, forwardidx

    Args:
        page_dict (dict): dict containing (word, word frequency) key value pairs
        pageID (int_): PageID of page
    """
    forwardidx[pageID] = []
    for word,freq in page_dict.items():
        if word not in word_wordID.keys(): # add word to word_wordID, wordID_word if new
            word_id = len(word_wordID)
            word_wordID[word] = word_id
            wordID_word[word_id] = word
        elif word in word_wordID.keys(): # fetch wordiD from word_wordID if not new
            word_id = word_wordID[word]
        
        if word_id not in inverseidx.keys(): # add new wordid to inverseidx if new
            inverseidx[word_id] = [(pageID, freq)]
        elif word_id in inverseidx.keys(): # append record to wordid entry if not new
            inverseidx[word_id].append((pageID, freq))
    
        forwardidx[pageID].append((word_id,freq)) # adding (word, frequency) to page's foward index entry

def indexnq_links(child_links, pageID):
    """index links in parentID_childID, url_pageID, pageID_url; then queue child links

    Args:
        child_links (List): list contianing urls of child links
        pageID (int): pageID of parent page
    """
    parentID_childID[pageID] = []
    for child_link in child_links:
        if child_link not in url_pageID.keys(): # add url to url_pageID, pageID_url if not new
            child_id = len(url_pageID)  
            url_pageID[child_link] = child_id 
            pageID_url[child_id] = child_link
        elif child_link in url_pageID.keys(): # fetch urlid if not new
            child_id = url_pageID[child_link] 
        
        parentID_childID[pageID].append(child_id)  # add childurl id to parentID_childID 
        q.put(child_link) # queue child link

def mod_cleanup(pageID):
    """index clean up if page has been modified

    Args:
        pageID (int): pageID of page needed to clean up
    """
    for word in forwardidx[pageID]: # remove (pageid, freq) from each word of page in inverseidx
        word_id = word[0]
        inverseidx[word_id].remove((pageID, word[1]))
       
    forwardidx[pageID].clear() 
    parentID_childID[pageID].clear()
    pageID_elem[pageID].clear()


def crawl(url,q):
    """Main function

    Args:
        url (str): link of page currently proccessing
        q (queue obj): queue storing queued links

    Raises:
        Exception: if page is pdf, skip page.
        Exception: if request has trouble proccessing page, skip page
        Exception: if page is too large, skip page. 

    """
    # if num of indexed pages > max pages, job done
    if len(forwardidx) >= MAX_PAGE:
        return 
    try:
        if ".pdf" in url:
            raise Exception(f"[ERROR] {url}: Page is pdf, skipping. ")
        try:
            response = requests.get(url)
        except (requests.exceptions.SSLError, urllib3.exceptions.SSLError):
            raise Exception(f"[ERROR] {url}: Error loading webpage, skipping. ")
        print(f"[LOG] {len(forwardidx)+1}: {url}")
        
        headers = response.headers # header file
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if len(soup.text) > 500000:
            raise Exception(f"[ERROR] {url}: Page too large, skipping.")
        
        # find last modified date from header, or from "last update" comment present in some HKUST CSE site's htmls
        try: 
            last_mod = headers['Last-Modified']
        except KeyError:
            try:
                cmnt_mod = soup.head.find(string=re.compile("last update"))
                last_mod = re.split("last update", cmnt_mod)[1].strip()
            except:
                last_mod = headers['Date']
        
        last_mod = parser.parse(last_mod).replace(tzinfo=None) # remove consideration for timezone, convert to datetime obj
        
        # Assign pageID, then check if page has been indexed before
        if url in url_pageID.keys():
            pageID = url_pageID[url]
            if pageID in forwardidx.keys():
                index_mod = parser.parse(pageID_elem[url_pageID[url]][2]).replace(tzinfo=None) # get our last index date
                if last_mod <= index_mod: # mod date is before index date, skip page
                    try: 
                        new_url = q.get()
                        crawl(new_url, q)
                    except queue.Empty:
                        return
                else: 
                    mod_cleanup(pageID) # if page is alreday indexed but needs updating, clean up old index
        else:
            pageID = len(url_pageID)
            url_pageID[url] = pageID
            pageID_url[pageID] = url
        
        # find page size from headers/length of page text
        try:
            page_size = headers['Content-Length']
        except KeyError:
            page_size = len(soup.text)

        # Tokenize text
        page_title = soup.find("title").text
        page_text = soup.text
        
        body_tokens = preprocess_text(page_text)
        title_tokens= preprocess_text(page_title)
        page_tokens = body_tokens + title_tokens 
        
        # Index words into forward,inverse idx and wordiD_word, word_wordID
        page_dict = count_word_freq(page_tokens)
        index_words(page_dict, pageID)
        
        # Index page into page_elem: title, mod date, index date, size
        pageID_elem[pageID] = [page_title, last_mod.strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), page_size] 

        # Extract all children links
        child_urls = soup.find_all('a', href=True)
        child_links = []
        
        for link in child_urls:
            child_links.append(urljoin(url, link.get('href')).rstrip('/'))
        
        # Index and queue all children links 
        child_links = list(dict.fromkeys(child_links)) # remove duplicates
        indexnq_links(child_links, pageID)
    
    except Exception as e:
        print(e)
        try:
            new_url = q.get()
            crawl(new_url, q)
            return
        except queue.Empty:
            return 
    
    # fetch new url from queue, and start new recursion loop with new url
    try:
        new_url = q.get()
        crawl(new_url, q)
        return
    except queue.Empty:
        return
    
    
if __name__ == '__main__':
    index()
    
    
    
    
    

    
    
    

    




    
    
    
    
    
    
    
    
    

