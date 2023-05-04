from sqlitedict import SqliteDict
import math
from nltk.tokenize import WhitespaceTokenizer
from tools.ngrams import ngrams_proccess
import re
from tools.porter import porter


stop_words = set([line.rstrip('\n') for line in open('./tools/stopwords.txt')])
db=SqliteDict("./db/indexdb.sqlite")

forwardidx = db['forwardidx'] # {pageID: [(w1,f1), [w1,f2], [w3,f3]], pageID:[]...}
inverseidx = db['inverseidx'] # {word1: [[doc1, freq], [doc2, freq2]]}
inversetitleidx = db['inversetitleidx'] 
forwardtitleidx = db['forwardtitleidx'] 
wordID_word = db["wordID_word"]
word_wordID = db["word_wordID"]
title_titleID = db["title_titleID"] # {titleword: titlewordID}
titleID_title = db["titleID_title"] # {titlewordID: titleword}
bodynorm = db['bodynorm'] # {pageid: norm}
titlenorm = db['titlenorm']

def query_tfidf(tokens):
    # give tokens, output {w1: [freq, tfidf1], w2: [freq, idf2]}
    query_idx = {}
    for word in tokens: # transform word into wordID?
        if word not in query_idx.keys():
            query_idx[word] = [1]
        else:
            query_idx[word][0] = query_idx[word][0]+1
    
    # {w1:[freq1]]}
    tfmax = 0 # tfmax in query
    for w, f in query_idx.items(): # f is the list containing the frequency
        if  f[0] > tfmax:
            tfmax = f[0]
    
    num_docs = len(forwardidx)
    for word, freq in query_idx.items(): # for everyword
        tfnorm = freq[0]/tfmax
        
        if word in word_wordID:
            wordID = word_wordID[word]
            df = len(inverseidx[wordID])
        else: # if word is not indexed
            df = 0
            
        tfidf = (0.5+0.5*tfnorm)*math.log(1+num_docs/df)
        query_idx[word].append(tfidf)
    
    return query_idx # {w1: [freq, tfidf]}
                    
def preprocess_text(text):
    """preprocessing text in page into word tokens 

    Args:
        text (str): text in page

    Returns:
        List[str]: List of word tokens
    """
    #TODO Phrase search for only words with "" !!!!!!!! Don't have to bigram the singular words. 
    tokens = WhitespaceTokenizer().tokenize(text)  # tokenize words 
    
    tokens = [word.lower() for word in tokens] # lower case
    tokens = [re.sub(r"[^\s\w\d]", '', c) for c in tokens] # remove punctuation
    tokens = [i for i in tokens if i] # remove empty strings

    tokens=[porter(c) for c in tokens] # porter    

    # get bi and tri grams
    bigram_tokens, trigram_tokens = ngrams_proccess(tokens)
    uni_tokens=['' if c in stop_words else c for c in tokens] # remove stop words from unigram
    uni_tokens=list(filter(None, uni_tokens)) # remove duplicates
    
    bigram_tokens = list(filter(None, bigram_tokens))
    trigram_tokens = list(filter(None, trigram_tokens))
    
    final_tokens = uni_tokens+bigram_tokens+trigram_tokens
    return final_tokens

def cosine_body_score(query_index, wordls, docid):
    # query_index: {word:[freq, tfidf], word:[freq, tfidf]}
    # wordls:  [[w1, tfidf], [w2, tfidf]]
    body_norm = bodynorm[docid]
    dot_prod = 0
    query_norm = 0
    
    for qword, weight in query_index.items(): 
        try: # if query word doesn't exist in doc's mathcing words, then skip query word.
            qword_id = word_wordID[qword]
        except:
            continue
        
        # find query word in doc's list of matching words, if can't find, +0 for that word
        for word in wordls:
            if word[0] == qword_id: # term weight * query weight
                dot_prod += word[1]*weight[1] 

        query_norm += weight[0]**2

    query_norm = math.sqrt(query_norm)
    cosine_score = dot_prod/(body_norm*query_norm)
    return cosine_score
            
    
def cosine_title_score(query_index, titlels, docid):
    # query_index: {word:[freq, tfidf], word:[freq, tfidf]}
    # wordls:  [[w1, tfidf], [w2, tfidf]]
    title_norm = titlenorm[docid]
    dot_prod = 0
    query_norm = 0
    
    for qword, weight in query_index.items(): 
        try: # if query word doesn't exist in doc's mathcing words, then skip query word.
            qword_id = word_wordID[qword]
        except:
            continue
        
        # find query word in doc's list of matching words, if can't find, +0 for that word
        for word in titlels:
            if word[0] == qword_id: # term weight * query weight
                dot_prod += word[1]*weight[1] 

        query_norm += weight[0]**2

    query_norm = math.sqrt(query_norm)
    cosine_score = dot_prod/(title_norm*query_norm)
    return cosine_score

def cosine_main(query):
    # clean query
    query_token = preprocess_text(query)
    query_index = query_tfidf(query_token) # {word:[freq, tfidf], word:[freq, tfidf]}
    
    sim_doc_body = {} # {docID: [[w1, tfidf], [w2, tfidf]]} only words in query
    sim_doc_title = {} # {docID:[[w1, tfidf], [w2, tfidf]]}
    doc_score_title = {} # {docID: score}
    doc_score_body = {}
    for word,weight in query_index.items():
        if (word not in word_wordID) and (word not in title_titleID): # if query word is not indexed, skip 
            continue
        elif word not in word_wordID: # word not in content, cosine score of body is 0 for all docs
            qwordID_title = title_titleID[word]
            post_title_list = inversetitleidx[qwordID_title] # [[doc1, freq, tfidf], [doc1, freq, tfidf]]
            
        elif word not in title_titleID: # word not in title, cosine score of title is 0 for all docs
            qwordID_body = word_wordID[word]
            post_body_list = inverseidx[qwordID_body] # [[doc1, freq, tfidf], [doc1, freq, tfidf]]

        else:
            qwordID_title = title_titleID[word]
            qwordID_body = word_wordID[word]
            post_title_list = inversetitleidx[qwordID_title]
            post_body_list = inverseidx[qwordID_body]
        
        # storing match words in doc into sim doc
        # post body list: [[doc1, freq, tfidf], [doc1, freq, tfidf]]
        # simdoc -> doc:[[w1, tfidf], [w2, tfidf]]
        for doc in post_body_list: 
            if doc[0] in sim_doc_body: 
                sim_doc_body[doc[0]].append([qwordID_body, doc[2]]) # docID: [[w1, tfidf]]
            else:
                sim_doc_body[doc[0]] = [[qwordID_body, doc[2]]]

        # sotring match words into doc into sim doc title
        for doc in post_title_list: 
            if doc[0] in sim_doc_title: 
                sim_doc_title[doc[0]].append([qwordID_title, doc[2]]) # docID: [[w1, tfidf]]
            else:
                sim_doc_title[doc[0]] = [[qwordID_title, doc[2]]]
                
                
    for docid, wordls in sim_doc_body.items(): # wordls -> [[w1, tfidf], [w2, tfidf]] matched words only
        doc_score_body[docid] = cosine_body_score(query_index, wordls, docid) 
        
    for docid, titlels in sim_doc_title.items():
        doc_score_title[docid] = cosine_title_score(query_index, titlels, docid)

    combine_score = {}
    for docid, score in doc_score_body.items():
        try: # catch error if doc has no title
            comb_doc_score = (doc_score_title[docid]*2+score)/3 #TODO title weighs of 2
            combine_score[docid] = comb_doc_score
        except: 
            comb_doc_score = score/3 # (0*3+body)/3
            combine_score[docid] = comb_doc_score
            
    for docid, score in doc_score_title.items(): # no body, but has titles
        if docid not in combine_score:
            comb_doc_score = score*3/3 # (title*3+0)/3
            combine_score[docid] = comb_doc_score
    
    rank_list = list(combine_score.keys()) # [docid1, docid2]
    rank_list = sorted(rank_list, key=combine_score.get, reverse=True) #Desc order, ranks doc id to score
    
    rank_compile = []
    for idx, pageid in enumerate(rank_list): # [docid, score, rank]
        rank_compile.append([pageid, combine_score[pageid], idx+1])
    
    return rank_compile
    
    

if __name__ == '__main__':
    rank = cosine_main("Hong kong university of science and technology")
    print(rank)

    