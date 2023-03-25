from sqlitedict import SqliteDict

db=SqliteDict("./db/indexdb.sqlite")
parentID_childID= db['parentID_childID']
pageID_url = db['pageID_url']
url_pageID = db['url_pageID']
forwardidx = db['forwardidx']
inverseidx = db['inverseidx']
wordID_word = db['wordID_word']
word_wordID = db['word_wordID']
pageID_elem= db['pageID_elem']

# title
# url
# mod date, size
# keyword,freq x10
# child links x10
with open('spider_result.txt', 'w') as f:
    for page_id,words in forwardidx.items():
        elems = pageID_elem[page_id] # title, mod date, size
        url = pageID_url[page_id] # url
        keywords = forwardidx[page_id][:10] # first 10 keywords
        child_ids = parentID_childID[page_id][:10] # first 10 children link id
        child_links = [pageID_url[c_id] for c_id in child_ids] # get links of child
        
        f.write(elems[0]+"\n")
        f.write(url+"\n")
        f.write(f"{elems[1]}, {elems[2]}\n")
        
        # write keyword line
        for tup in keywords:
            f.write(f"{wordID_word[tup[0]]} {tup[1]}; ")
        f.write("\n")
        
        # write child links
        for link in child_links:
            f.write(link)
            f.write("\n")
        
        # add seperation line
        f.write("-"*80+"\n")
            
            
