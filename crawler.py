from bs4 import BeautifulSoup
from sqlitedict import SqliteDict
import requests
from nltk.tokenize import WhitespaceTokenizer
from queue import Queue
import re
from dateutil import parser
import string


ORIGIN_URL = "http://www.cse.ust.hk"
MAX_PAGE = 30

parentID_childID = dict() # {parentID: childID}
pageID_url = dict() # {pageID: url}
url_pageID = dict() # {url: pageID}
forwardidx = dict() # {pageID: [[w1,f1], [w1,f2], [w3,f3]], pageID:[]...}
inverseidx = dict() # {word1: [page1ID, (start, end), freq1]}
wordID_word = dict() # {wordID: word}
pageID_elem = dict() # {pageID: [title, mod date, size]}

q = Queue()
stop_words = set([line.rstrip('\n') for line in open('./tools/stopwords.txt')])

def porter(word):
    return word

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
    
    for idx,span in enumerate(spans):
        if tokens[idx] == '':
            spans[idx] = ''
            
    tokens=list(filter(None, tokens))
    spans=list(filter(None, spans))
    
    tokens=[porter(c) for c in tokens]
    
    print(len(tokens), len(spans))
            

def crawl(url,q):
    # if num of indexed pages > max pages, job done
    if len(pageID_url) > MAX_PAGE:
        return 
    
    response = requests.get(url)
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
    
    # if cur url is in index and is modified before index's last modified date, skip
    if url in url_pageID.keys:
        if last_mod <= pageID_elem[url_pageID[url]][1]:  
            try:
                new_url = q.get()
            except Queue.empty:
                return
            crawl(new_url, q)
   
   # find page size(from header), current page's page ID, page title. 
    try:
        page_size = headers['Content-Length']
    except KeyError:
        page_size = len(soup.text.strip())
        
    cur_pageID = len(url_pageID) 
    page_title = soup.find("title").text
    
    
    # INDEXING
    url_pageID[url] = cur_pageID
    pageID_url[cur_pageID] = url
    
    # Tokenize text
    tokens = preprocess_text(soup.text)
    
    
    try:
        new_url = q.get()
    except Queue.empty:
        return
    crawl(new_url, q)

if __name__ == '__main__':
    response = requests.get('https://hkust.edu.hk/news/internationalization-and-partnership/hkust-and-china-unicom-establish-joint-laboratory-empower')
    soup = BeautifulSoup(response.text, 'html.parser')
    preprocess_text(soup.text)
    
    

    
    
    
    
    # pageID_elem = [title, mod date, size]
    
    




    
    
    
    
    
    
    
    
    

