from sqlitedict import SqliteDict
import math


db=SqliteDict("./db/indexdb.sqlite")

forwardidx = db['forwardidx'] # {pageID: [(w1,f1, tfidf), [w1,f2], [w3,f3]], pageID:[]...}
inverseidx = db['inverseidx'] # {word1: [[doc1, freq], [doc2, freq2]]}
inversetitleidx = db['inversetitleidx'] 
forwardtitleidx = db['forwardtitleidx']

bodynorm = {}
titlenorm = {}

def doc_body_norm():
    """calculates normalization value(body) in cosinesimialry equation. 
    """
    for page_id,wordls in forwardidx.items():
        # for each page calculate page norm
        page_norm = 0
        for w in wordls:
            page_norm+= w[2]**2
        page_norm = math.sqrt(page_norm)
        bodynorm[page_id] = page_norm
        
            
def doc_title_norm():
    """calculates normalization value(title) in cosinesimialry equation. 
    """
    for page_id,wordls in forwardtitleidx.items():
        # for each page calculate page norm
        page_norm = 0
        for w in wordls:
            page_norm+= w[2]**2
        
        page_norm = math.sqrt(page_norm)
        titlenorm[page_id] = page_norm
        
        

def calc_tfidf():
    """calculates the tfidf score of content words of the documents. 
    """
    total_doc_num = len(forwardidx)
    for pageID, page in forwardidx.items():
        tfmax = 0
        for w in page:
            if w[1]>tfmax:
                tfmax = w[1]
        for word in page: # (w1,f1)
            tf_norm = word[1] / tfmax # word frequency in doc/ highest frequency word
            df = len(inverseidx[word[0]]) # number of docs with this term
            idf = math.log(1+total_doc_num/df)
            
            weight = (0.5+0.5*tf_norm)*idf
            if len(word) == 3: #already calced 
                word[2] = weight
            else:
                word.append(weight)
            
            for page_post in inverseidx[word[0]]:# page_post-> [doc1, freq]
                if page_post[0] == pageID:
                    if len(page_post) == 3:
                        page_post[2] = weight
                    else:
                        page_post.append(weight) # [doc1, freq, tfidf]


def title_tfidf():
    """calculates the tfidf score of title words of the documents
    """
    total_doc_num = len(forwardtitleidx)
    for pageID, page in forwardtitleidx.items():
        tfmax = 0
        for w in page:
            if w[1]>tfmax:
                tfmax = w[1]
        for word in page: # (w1,f1)
            tf_norm = word[1] / tfmax # word frequency in doc/ highest frequency word
            df = len(inversetitleidx[word[0]]) # number of docs with this term
            idf = math.log(1+total_doc_num/df)
            
            weight = (0.5+0.5*tf_norm)*idf
            if len(word) == 3: #already calced 
                word[2] = weight
            else:
                word.append(weight)
            
            for page_post in inversetitleidx[word[0]]:
                if page_post[0] == pageID:
                    if len(page_post) == 3:
                        page_post[2] = weight
                    else:
                        page_post.append(weight) # [doc1, freq, tfidf]

def main_tfidf():
    """main function to calcualte the tfidf score of title and body words """
    print(f"\n[START] Begin calculating Term weights for documents")
    calc_tfidf()
    title_tfidf()
    doc_title_norm()
    doc_body_norm()

    db['forwardidx'] = forwardidx  # {pageID: [(w1,f1), [w1,f2], [w3,f3]], pageID:[]...}
    db['inverseidx'] = inverseidx  # {word1: [[doc1, freq], [doc2, freq2]]}
    db['inversetitleidx']  = inversetitleidx 
    db['forwardtitleidx'] = forwardtitleidx
    db['bodynorm'] = bodynorm
    db['titlenorm'] = titlenorm
    db.commit()
    db.close()
    print(f"[END] Finish calculating Term weights for documents.")
    print(f"[END] cd into the /mysite directory, and activate Django server by `python manage.py runserver`")
    print(f"[END] Then go to http://127.0.0.1:8000/ \n")

if __name__ == "__main__":
    main_tfidf()
