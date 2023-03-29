# Database Schema

==See schema_graph.html for graph of schema.==

### parentID_childID
> Relationship: parentID -> childID 
> Format: {parentID: childID,c2}

It is a dictionary containing parentID to childID mapping. It is implemented to store the child link IDs of a parent link ID. 
- in `indexnq_links(child_links,pageID)`, given a parent ID, we would store parent ID and the corresponding child links' IDs as a key value pair, to record their relationship. 


### pageID_url 
> Relationship: pageID -> url
> Format: {pageID: url}

It is a dictionary containing pageID to url mapping. This is implemented so when we want to fetch the url given a pageID, we may reference this index. 
- in `indexnq_links(child_links,pageID)` we store a new pageID to url pair when recording a new child link. 
- in `crawl(url, q)` we generate a new pageID to url key value pair when indexing a new page. 

### url_pageID
> Relatinoship: url -> pageID
> Format: {url: pageID}

It is a dictionary containing url to pageID mapping, it is the inverse of pageID_url. Implemented so when given a url, we can obtain the pageID. 
- in `indexnq_links(child_links)` , it is used to check if child url to child pageID mapping exists, if not, then we generate a new mapping.
- in `crawl(url, q)`, it's used to check if we alrady have url to pageID mapping of the page, and if so, we obtain the pageID of the url; else we generate a new pageID to url key value pair.

### forwardidx
> Relatinoship: pageID -> (word, word frequency)
> Format: {pageID:[(word1, freq1), (word2, freq2)]}

It is a dictionary containing pageID to [word, word frequency] mapping. This is done so we may obtain a list of a page's words and thier frequencies given a pageID. 
- `index_words(page_dict, pageID)`, we append (wordID, word frequency) to pageID entires, to record the word and page relationship. 
- Also used in `crawl(url, q)` to check if we have already indexed the page.

### inverseidx
> Relatinoship: wordID -> (pageID, word frequency on page)
> Format: {wordID: [(pageID1, freq1), (pageID2, freq2)]}

It is a dictaionry containing wordID to (pageID, word frequency) tuple mappping. It is the inverse of forwardidx. This is done so given a wordID, we may get get the pages that contain the word, and their word frequencies. 
- `index_words(page_dict, pageID)`, we append (pageID, word frequency) to wordID entires, to record the word and page relationship.


### wordID_word
> Relatinoship: wordID -> word
> Format: {wordID: word}

It is a dictionary containing wordID to word mapping. Implemented to fetch a word given a wordID. 
- in `index_words(page_dict, pageID)`, we generate a wordID to word mapping so when using inverseidx we may know what word it is(since it uses wordID as it's keys). 

### word_wordID
> Relatinoship: word -> wordID
> Format: {word: wordID}

It is a dictionary containing word to wordID mapping. It is the inverse of wordID_word. Implemented to fetch a wordID given a word. 
- in `index_words(page_dict, pageID)`, we use the index to check if word has already been indexed. 
- Also used to convert words to wordID, then index into inverseidx and forwardidx

### pageID_elem
> Relatinoship: pageID -> (title, modification date, size)
> Format: {pageID: [title, modification date, index date, index date, size]}

It is a dictionary containing pageID to [title, modification date, size, index date] mapping. This is so given a pageID, we may fetch the metadata(title, mod date, size) of a page. 
 - in `crawl(url, q)`, the index is used to check if page has been modified after indexing, access title of page, and size of page. 


### Comments

- The entire database is stored in /db/indexdb.sqlite. May consider implementing hash maps if speed is too slow. 
- Porter method is not properly implmented, currently it is a empty function in porter.py
- Size of page is found either in the header, or by finding the length of soup.text object.

