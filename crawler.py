from bs4 import BeautifulSoup
from sqlitedict import SqliteDict
import requests
from nltk.tokenize import WhitespaceTokenizer
import queue
from collections import deque
import re
import os
from dateutil import parser
from datetime import datetime
from tools.porter import porter
from tools.ngrams import ngrams_proccess
from urllib.parse import urljoin
import urllib3

ORIGIN_URL = "https://www.cse.ust.hk/~kwtleung/COMP4321/testpage.htm" # change origin site here
MAX_PAGE = 300 # change max page here

# files doesn't exist
q = queue.Queue()
stop_words = set([line.rstrip('\n') for line in open('./tools/stopwords.txt')])

indexed_before = 0
if not os.path.isfile("./db/indexdb.sqlite"):
    # if db doesn't exist,create new dictionaries. 
    db=SqliteDict("./db/indexdb.sqlite")
    parentID_childID = dict() # {parentID: [childID,c2]}
    childID_parentID = dict() # {childID: [parentID,p2]}
    pageID_url = dict() # {pageID: url}
    url_pageID = dict() # {url: pageID}
    forwardidx = dict() # {pageID: [(w1,f1), [w1,f2], [w3,f3]], pageID:[]...}
    inverseidx = dict() # {word1: [(page1ID, freq1, tfidf),(page2ID, freq2, tfidf)]}
    wordID_word = dict() # {wordID: word}
    word_wordID = dict() 
    pageID_elem = dict() # {pageID: [title , mod date,index date, size]}

    title_titleID = dict() # {titleword: titlewordID}
    titleID_title = dict() # {titlewordID: titleword}
    inversetitleidx = dict() # {word1: [(page1ID, freq1,tfidf),(page2ID, freq2, tfidf)]}
    forwardtitleidx = dict() # {pageID: [(w1,f1), [w1,f2], [w3,f3]], pageID:[]...}
else: 
    # db exists, read from db
    indexed_before = True
    try:
        # catch error if db exists, but doesnt have certian index
        db=SqliteDict("./db/indexdb.sqlite")
        parentID_childID=db['parentID_childID']
        pageID_url=db['pageID_url']
        url_pageID=db['url_pageID']
        forwardidx=db['forwardidx']
        inverseidx=db['inverseidx']
        wordID_word=db['wordID_word']
        word_wordID=db['word_wordID']
        pageID_elem=db['pageID_elem']
        title_titleID=db['title_titleID'] 
        titleID_title=db['titleID_title'] 
        inversetitleidx=db['inversetitleidx'] 
        forwardtitleidx=db['forwardtitleidx']
        childID_parentID=db['childID_parentID']
    except:
        print(f"[LOG] DB wasn't indexed correctly, creating new db!")
        db=SqliteDict("./db/indexdb.sqlite")
        parentID_childID = dict() 
        childID_parentID = dict() 
        pageID_url = dict() 
        url_pageID = dict() 
        forwardidx = dict() 
        inverseidx = dict() 
        wordID_word = dict() 
        word_wordID = dict() 
        pageID_elem = dict() 

        title_titleID = dict() 
        titleID_title = dict() 
        inversetitleidx = dict()
        forwardtitleidx = dict()

def index():
    depth = MAX_PAGE
    print(f"\n[START] Begin crawling, Origin url: {ORIGIN_URL}")
    crawl(ORIGIN_URL, q, indexed_before, depth)
    print("[END] End crawl, saving to database...")
    
    db['parentID_childID']=parentID_childID
    db['pageID_url']= pageID_url
    db['url_pageID'] = url_pageID
    db['forwardidx'] = forwardidx
    db['inverseidx'] = inverseidx
    db['wordID_word'] = wordID_word
    db['word_wordID'] = word_wordID
    db['pageID_elem'] = pageID_elem
    db['title_titleID']= title_titleID 
    db['titleID_title']= titleID_title 
    db['inversetitleidx']= inversetitleidx 
    db['forwardtitleidx'] = forwardtitleidx 
    db['childID_parentID'] = childID_parentID
    db.commit()
    db.close()
    print("[END] Finished Saving.")
    print("[END] Next, calculate term weights by `python tfidf.py`\n")
    
def preprocess_text(text):
    """preprocessing text in page into word tokens 

    Args:
        text (str): text in page

    Returns:
        List[str]: List of word tokens
    """
    tokens = WhitespaceTokenizer().tokenize(text)  # tokenize words 
    tokens = [word.lower() for word in tokens] # lower case
    tokens = [re.sub(r"[^\s\w\d]", '', c) for c in tokens] # remove punctuation
    tokens = [i for i in tokens if i] # remove empty strings
    tokens=[porter(c) for c in tokens] # porter    

    bigram_tokens, trigram_tokens = ngrams_proccess(tokens) # get bi-trigrams
    uni_tokens=['' if c in stop_words else c for c in tokens] # remove stop words from unigram
    uni_tokens = [i for i in uni_tokens if i] # remove empty strings
    
    return uni_tokens+bigram_tokens+trigram_tokens


def count_word_freq(tokenlist):
    """Count word frequencies

    Args:
        tokenlist (List[str]): List of word tokens in page

    Returns:
        dict(): dictionary with (word, word frequency) key value paris
    """
    wordfreq_dict = dict()
    for token in tokenlist:
        if wordfreq_dict.get(token):
            wordfreq_dict[token] += 1
        else:
            wordfreq_dict[token] = 1
    return wordfreq_dict # {w1: 4, w2:5 }


def index_title_words(title_dict, pageID):
    """takes title dict and indexes words in title into title_titleID,titleID_title, inversetitleidx, forwardtitleidx

    Args:
        title_dict (dict): word frequency dict containing word: frequency pairs of title from current page {word1: freq1, }
        titleID (int): TitleID, (hopefully) same as PageID
    """
    forwardtitleidx[pageID] = []
    for word,freq in title_dict.items():
        if word not in title_titleID.keys():
            word_id = len(title_titleID)
            title_titleID[word] = word_id
            titleID_title[word_id] = word
        elif word in title_titleID.keys():
            word_id = title_titleID[word]
        
        if word_id not in inversetitleidx.keys(): # if wordid is not in inverse, add new
            inversetitleidx[word_id] = [[pageID, freq]] 
        elif word_id in inversetitleidx.keys(): # if wordid is in inverse, append the doc to the word row
            inversetitleidx[word_id].append([pageID, freq])
            
        forwardtitleidx[pageID].append([word_id, freq]) # add [w1, f1] to the doc row

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
            inverseidx[word_id] = [[pageID, freq]]
        elif word_id in inverseidx.keys(): # append record to wordid entry if not new
            inverseidx[word_id].append([pageID, freq])
    
        forwardidx[pageID].append([word_id,freq]) # adding (word, frequency) to page's foward index entry

def indexnq_links(child_links, pageID):
    """index links in parentID_childID, url_pageID, pageID_url; then queue child links

    Args:
        child_links (List): list contianing urls of child links
        pageID (int): pageID of parent page
    """
    # child_links = list(set(child_links)) # remove duplicates
    for child_link in child_links:
        if child_link not in url_pageID.keys(): # haven't seen child link before
            child_id = len(url_pageID)
            url_pageID[child_link] = child_id 
            pageID_url[child_id] = child_link
            childID_parentID[child_id] = [pageID] 
        elif child_link in url_pageID.keys(): # have seen child link before
            child_id = url_pageID[child_link]
            if child_id not in childID_parentID:
                childID_parentID[child_id] = [pageID]
            else:
                childID_parentID[child_id].append(pageID) 
                
        if pageID not in parentID_childID: #
            parentID_childID[pageID] = [child_id]
        else:
            parentID_childID[pageID].append(child_id) 

        if child_id not in forwardidx:
            q.put(child_link) # queue child link

    

    
def mod_cleanup(pageID):
    """index clean up if page has been modified

    Args:
        pageID (int): pageID of page needed to clean up
    """
    # clean up inverse idx
    for word in forwardidx[pageID]: # remove (pageid, freq) from each word of page in inverseidx
        word_id = word[0]
        inverseidx[word_id].remove([pageID, word[1]])
    
    for word in forwardtitleidx[pageID]: # using forwardtitle[w1, f1] idx to remove all words from page's title from inversetitleidx
        word_id = word[0] # get word ID
        inversetitleidx[word_id].remove([pageID, word[1]]) # remove [pageID, wordID]
    
    forwardidx[pageID].clear() 
    forwardtitleidx[pageID].clear()
    pageID_elem[pageID].clear()
    for childid in parentID_childID[pageID]: # remove child to parent links
        try:
            childID_parentID[childid].remove(pageID)
        except:
            pass
    parentID_childID[pageID].clear() 
    

def crawl(url,q, indexed_before, depth):
    """Main function

    Args:
        url (str): link of page currently proccessing
        q (queue obj): queue storing queued links

    Raises:
        Exception: if page is pdf, skip page.
        Exception: if request has trouble proccessing page, skip page
        Exception: if page is too large, skip page. 

    """
    
    if not indexed_before: # stop when forwardidx reaches max length
        if len(forwardidx) >= MAX_PAGE:
            return
    elif indexed_before:    # stop when reached max length recursion depth
        if depth < 0:
            return
        
    try:
        if ".pdf" in url:
            raise Exception(f"[ERROR] {url}: Page is pdf, skipping. ")
        try:
            response = requests.get(url)
        except (requests.exceptions.SSLError, urllib3.exceptions.SSLError):
            raise Exception(f"[ERROR] {url}: Error loading webpage, skipping. ")
        headers = response.headers # header file
        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except:
            raise Exception(f"[ERROR] {url}: Page doesn't have text, skipping.")
        
        if len(soup.text) > 500000:
            raise Exception(f"[ERROR] {url}: Page too large, skipping.")

        # find last modified date from header,
        try: 
            last_mod = headers['Last-Modified']
        except KeyError:
            # try:
            #     cmnt_mod = soup.head.find(string=re.compile("last update"))
            #     last_mod = re.split("last update", cmnt_mod)[1].strip()
            # except:
                last_mod = headers['Date']
        
        last_mod = parser.parse(last_mod).replace(tzinfo=None) # remove consideration for timezone, convert to datetime obj
        
        # Assign pageID, then check if page has been indexed before (cuz url could be child link -> not indexed)
        if url in url_pageID.keys():
            pageID = url_pageID[url]
            if pageID in forwardidx.keys(): # if indexed before
                index_mod = parser.parse(pageID_elem[url_pageID[url]][2]).replace(tzinfo=None) # get our last index date
                print(f"[LOG] {pageID} {url}: Indexed before, last index date {index_mod}, last mod date {last_mod}")
                
                if (last_mod <= index_mod): # does indexed page need update?
                    # doesn't need update, skip page
                    if indexed_before: # if crawled before, get original child links to populate queue
                        child_ls = [pageID_url[childid] for childid in parentID_childID[pageID]]
                        for child_url in child_ls:
                            q.put(child_url)
                            
                    try: 
                        new_url = q.get()
                        crawl(new_url, q, indexed_before, depth-1)
                        return
                    except queue.Empty:
                        return
                else: # needs update, clean up index, then continue index
                    mod_cleanup(pageID)           
        else: # if page is new, create new page ID and title ID
            pageID = len(url_pageID)
            url_pageID[url] = pageID
            pageID_url[pageID] = url
            
        print(f"[LOG] {pageID}: {url}")
        # find page size from headers/length of page text
        try:
            page_size = headers['Content-Length']
        except KeyError:
            page_size = len(soup.text)

        # Tokenize text and title
        page_title = soup.find("title").text

        page_text = soup.text
        body_tokens = preprocess_text(page_text)
        title_tokens= preprocess_text(page_title)
        
        # Index words from body into forward,inverse idx and wordiD_word, word_wordID
        body_dict = count_word_freq(body_tokens) # {w1: 4, w2:5 }
        index_words(body_dict, pageID)
        
        # Index words from title into forwardtitle,inverse title idx and titleID_title, title_titleID
        title_dict = count_word_freq(title_tokens)  # {w1: 4, w2:5 }
        index_title_words(title_dict, pageID)
        
        
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
        print(f"[ERROR] {pageID} {url}: {e}, skipping page")
        try:
            new_url = q.get()
            crawl(new_url, q, indexed_before, depth) # skipped page not cuz indexed before, page is never indexed, hence depth is same
            return
        except queue.Empty:
            return 
    
    # fetch new url from queue, and start new recursion loop with new url
    try:
        new_url = q.get()
        crawl(new_url, q, indexed_before, depth-1)
        return
    except queue.Empty:
        return
    
if __name__ == '__main__':
    index()
    
    
    
    
    
    

    
    
    

    




    
    
    
    
    
    
    
    
    

