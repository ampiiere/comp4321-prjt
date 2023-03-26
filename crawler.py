from bs4 import BeautifulSoup
from sqlitedict import SqliteDict
import requests
from nltk.tokenize import WhitespaceTokenizer
import queue
import re
from dateutil import parser
from datetime import datetime
import string
from porter import porter
from urllib.parse import urljoin


ORIGIN_URL = "http://www.cse.ust.hk"
MAX_PAGE = 30

parentID_childID = dict() # {parentID: [childID,c2]}
pageID_url = dict() # {pageID: url}
url_pageID = dict() # {url: pageID}
forwardidx = dict() # {pageID: [(w1,f1), [w1,f2], [w3,f3]], pageID:[]...}
inverseidx = dict() # {word1: [(page1ID, freq1),(page2ID, freq2)]}
wordID_word = dict() # {wordID: word}
word_wordID = dict()
pageID_elem = dict() # {pageID: [title, mod date, size]}

q = queue.Queue()
stop_words = set([line.rstrip('\n') for line in open('./tools/stopwords.txt')])

def index():
    crawl(ORIGIN_URL, q)
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

def preprocess_text(text):
    # tokenize words and obtain their spans
    span_obj = WhitespaceTokenizer().span_tokenize(text)
    spans = [span for span in span_obj]
    tokens = WhitespaceTokenizer().tokenize(text)
    
    # lower case, remove punctuation, remove numerics, remove stopwords
    tokens = [word.lower() for word in tokens]
    tokens = [re.sub(r"[^\s\w\d]", '', c) for c in tokens]
    tokens = [re.sub(r"\b\d+\b", "", c) for c in tokens]
    tokens=['' if c in stop_words else c for c in tokens]
    
    tokens=list(filter(None, tokens))
    tokens=[porter(c) for c in tokens] #TODO PORTER
    
    return tokens


def count_word_freq(tokenlist):
    page_dict = dict()
    for token in tokenlist:
        if page_dict.get(token):
            page_dict[token] += 1
        else:
            page_dict[token] = 1

    return page_dict


def index_words(page_dict, pageID):
    # initialize forwardidx for page
    forwardidx[pageID] = []
    for word,freq in page_dict.items():
        if word not in word_wordID.keys(): # add word to word_wordID and wordID_word if new
            word_id = len(word_wordID)
            word_wordID[word] = word_id
            wordID_word[word_id] = word
        elif word in word_wordID.keys(): # fetch wordiD from word_wordID if not new
            word_id = word_wordID[word]
        
        if word_id not in inverseidx.keys(): # add new word_id entry if new
            inverseidx[word_id] = [(pageID, freq)]
        elif word_id in inverseidx.keys(): # append record to word_id entry if not new
            inverseidx[word_id].append((pageID, freq))
    
        # adding word, frequency tuple page's foward index entry
        forwardidx[pageID].append((word_id,freq))

def indexnq_links(child_links, pageID):
    parentID_childID[pageID] = []
    for child_link in child_links:
        if child_link not in url_pageID.keys(): # if child link is not indexed
            child_id = len(url_pageID)  # create new url ID 
            url_pageID[child_link] = child_id # index new url into url_pageID, pageID_url
            pageID_url[child_id] = child_link
        elif child_link in url_pageID.keys(): # if child link is indexed
            child_id = url_pageID[child_link] # fetch url id from urlpageID
        
        parentID_childID[pageID].append(child_id)
        q.put(child_link) # queue child link

def mod_cleanup(pageID):
    # remove (pageid, freq) from each word in inverseidx
    for word in forwardidx[pageID]:
        word_id = word[0]
        inverseidx[word_id].remove((pageID, word[1]))
       
    # TODO: Redundant since both index_words and index_links initialize empty []?
    forwardidx[pageID].clear() # clear out fowardidx of pageID
    parentID_childID[pageID].clear() # clear out parentID_childID of pageID


def crawl(url,q):   
    # if num of indexed pages > max pages, job done
    print(len(forwardidx))
    if len(forwardidx) >= MAX_PAGE:
        return 
    
    try:
        response = requests.get(url)
    except:
        new_url = q.get()
        crawl(new_url, q)

    print(url)
    headers = response.headers # header file: 
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # find last modified date from header/<head>
    try:
        last_mod = headers['Last-Modified']
    except KeyError:
        try:
            cmnt_mod = soup.head.find(string=re.compile("last update"))
            last_mod = re.split("last update", cmnt_mod)[1].strip()
        except:
            last_mod = headers['Date']
     
    last_mod = parser.parse(last_mod).replace(tzinfo=None) # remove consideration for timezone
    
    # if current page is already indexed, and has not been modified since the indexing; skip and move to next in the queue
    if url in forwardidx.keys():
        index_mod = parser.parse(pageID_elem[url_pageID[url]][1]).replace(tzinfo=None)
        if last_mod <= index_mod:  # if page's last mod is before our index
            try: 
                new_url = q.get()
                crawl(new_url, q)
            except queue.Empty:
                return
        else: 
            mod_cleanup(pageID) # if page is alreday indexed but needs updating, clean up old index
            
    # Assign pageID
    # if url is in url_pageID index, get old page_id, else index new url
    if url in url_pageID.keys():
        pageID = url_pageID[url]
    else:
        pageID = len(url_pageID)
        url_pageID[url] = pageID
        pageID_url[pageID] = url
    
    
    # find page size from headers/length of page text
    try:
        page_size = headers['Content-Length']
    except KeyError:
        page_size = len(soup.text.strip())

    try:
        # Tokenize text
        page_title = soup.find("title").text
        page_text = soup.text
        # page_text = soup.find(id="main-content-region").text
        
        body_tokens = preprocess_text(page_text)
        title_tokens= preprocess_text(page_title)
        page_tokens = body_tokens + title_tokens
        
        # Index words into forward,inverse idx and wordiD_word, word_wordID
        page_dict = count_word_freq(page_tokens)
        index_words(page_dict, pageID)
        
        
        # Index into page_elem
        pageID_elem[pageID] = [page_title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), page_size] 


        # Extract all children links
        child_urls = soup.find_all('a', href=True)
        child_links = []
        
        for link in child_urls:
            child_links.append(urljoin(url, link.get('href')).rstrip('/'))
        
        # Index and queue all children links
        child_links = list(dict.fromkeys(child_links))
        indexnq_links(child_links, pageID)
    except:
        # page might be empty/require sign in, skip
        return
    
    try:
        new_url = q.get()
        crawl(new_url, q)
    except queue.Empty:
        return
    
    
if __name__ == '__main__':
    index()
    
    
    
    
    

    
    
    

    




    
    
    
    
    
    
    
    
    

