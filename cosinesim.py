from sqlitedict import SqliteDict
import math
from nltk.tokenize import WhitespaceTokenizer
from tools.ngrams import ngrams_proccess
import re
from tools.porter import porter
from operator import itemgetter


stop_words = set([line.rstrip('\n') for line in open('./tools/stopwords.txt')])
db=SqliteDict("./db/indexdb.sqlite")

forwardidx = db['forwardidx'] # {pageID: [(w1,f1, tfidf), [w1,f2, tfidf], [w3,f3]], pageID:[]...}
inverseidx = db['inverseidx'] # {word1: [[doc1, freq, tfidf], [doc2, freq2, tfidf]]}
inversetitleidx = db['inversetitleidx'] 
forwardtitleidx = db['forwardtitleidx'] 
wordID_word = db["wordID_word"]
word_wordID = db["word_wordID"]
title_titleID = db["title_titleID"] # {titleword: titlewordID}
titleID_title = db["titleID_title"] # {titlewordID: titleword}
bodynorm = db['bodynorm'] # {pageid: norm}
titlenorm = db['titlenorm']
pageID_elem = db['pageID_elem'] # {pageID: [title , mod date,index date, size]}
pageID_url = db['pageID_url']
parentID_childID = db['parentID_childID']
childID_parentID=db['childID_parentID']



def query_tfidf(tokens):
    """calculates the tfidf of the query

    Args:
        tokens (List(str)): A list of strings containing the tokens of the query

    Returns:
        Dict: dictionary containing the frequency and tfidf of query, in this format {w1: [freq, tfidf]}
    """
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
        log_df = 0
        
        if word in word_wordID:
            wordID = word_wordID[word]
            df = len(inverseidx[wordID])
            log_df = math.log(1+(num_docs/df))
        else: # if word is not indexed
            log_df = 0
            
        tfidf = (0.5+0.5*tfnorm)*log_df
        query_idx[word].append(tfidf)
    
    return query_idx # {w1: [freq, tfidf]}

def tokenize_clean(text):
    """cleans and tokenizes the query string

    Args:
        text (str): String of query

    Returns:
        List(str): list of tokens cleaned 
    """
    tokens = WhitespaceTokenizer().tokenize(text)  # tokenize words 
    tokens = [word.lower() for word in tokens] # lower case
    tokens = [re.sub(r"[^\s\w\d]", '', c) for c in tokens] # remove punctuation
    tokens = [i for i in tokens if i] # remove empty strings
    tokens=[porter(c) for c in tokens] 
    return tokens
 
def preprocess_text(text):
    """main function for preproccessing the query text

    Args:
        text (str): the query string

    Returns:
        List(str): List of unigram bigram and trigram tokens. 
    """
    phrases = re.findall("'(.*?)'", text) # ['Foo Bar', 'Another Value']
    non_phrase = re.sub("'(.*?)'", '', text) # 'string without the phrases'

    # get non_phrase unigrams
    non_phrase_tokens = tokenize_clean(non_phrase)
    non_phrase_tokens=['' if c in stop_words else c for c in non_phrase_tokens] # remove stop words for unigram only
    non_phrase_tokens = [i for i in non_phrase_tokens if i]
    
    # get bi and tri grams for phrases
    phrase_tokens = []
    for phrase in phrases: # phrase = []
        p_tokens = tokenize_clean(phrase) # unigram for phrase
        bi_phrase_tokens, tri_phrase_tokens = ngrams_proccess(p_tokens) # get bi-trigrams
        uni_phrase_tokens = ['' if c in stop_words else c for c in p_tokens] # remove stopwords from unigram
        uni_phrase_tokens = [i for i in uni_phrase_tokens if i]
        phrase_tokens = phrase_tokens + uni_phrase_tokens + bi_phrase_tokens + tri_phrase_tokens
    
    return non_phrase_tokens+phrase_tokens


def cosine_score_body(query_index, page_words, pageid, query_norm):
    """calculates the cosine similarity body score between one page and query

    Args:
        query_index (Dict): dict of words in query with frequency and tfidf score{word:[freq, tfidf], word:[freq, tfidf]}
        page_words (List(str)): list of wordsID, freq, tfidf of the page [[w1,freq,tfidf], [w1,freq,tfidf]]
        pageid (int): ID of page
        query_norm (int): normalization value of query 

    Returns:
        int: content/body cosine similarity score of page to query
    """
    try:
        body_norm = bodynorm[pageid] # doc's norm
    except: # if page has no body, score is 0
        return 0
    
    dot_product = 0
    
    for word, weight in query_index.items():
        if word in word_wordID: 
            queryword_id = word_wordID[word]
            queryword_weight = weight[1]
            for pair in page_words:# [w1,freq,tfidf]
                if pair[0] == queryword_id: # find matching word in page's words
                    word_product = pair[2]*queryword_weight # dot product of word
                    dot_product+=word_product

        else: # skip word if word isn't even indexed
            continue
    try:
        page_score = dot_product/(body_norm*query_norm)
        # if pageid == 5 or pageid == 6:
            # print(f"{body_norm, dot_product, page_score}")
    except ZeroDivisionError:
        page_score = 0
    return page_score


def cosine_score_title(query_index, page_words, pageid, query_norm):
    """calculates the cosine similarity title score between one page and query

    Args:
        query_index (Dict): dict of words in query with frequency and tfidf score{word:[freq, tfidf], word:[freq, tfidf]}
        page_words (List(str)): list of wordsID, freq, tfidf of the page [[w1,freq,tfidf], [w1,freq,tfidf]]
        pageid (int): ID of page
        query_norm (int): normalization value of query 

    Returns:
        int: title cosine similarity score of page to query
    """
    try:
        title_norm = titlenorm[pageid] # doc's norm
    except: # page has no title, title score is 0
        return 0
    
    dot_product = 0
    for word, weight in query_index.items():
        if word in title_titleID: # if que
            queryword_id = title_titleID[word]
            queryword_weight = weight[1]
            for pair in page_words:# [w1,freq,tfidf]
                if pair[0] == queryword_id: # find matching word in page's words
                    word_product = pair[2]*queryword_weight # dot product of word
                    dot_product+=word_product

        else: # skip word if word isn't even indexed
            continue
    try:
        page_score = dot_product/(title_norm*query_norm)
    except ZeroDivisionError:
        page_score = 0
    return page_score


def cosinesim_main(query):
    """main cosine similarity function that calculates cosine similarity between all docs and query

    Args:
        query (str): String of query

    Returns:
        List(): List of docs, their cosine sim scores, and rank. [[docid, score, rank], [docid, score, rank]]
    """
    doc_score_title = {} # {docID: titlescore}
    doc_score_body = {} # {docID: bodyscore}
    doc_score_final = {} # {docID: score}
    # final: [[docid, score], [docid, score], [docid, score]]
    
    query_token = preprocess_text(query)
    query_index = query_tfidf(query_token) # {word:[freq, tfidf], word:[freq, tfidf]}
    query_norm = 0
    for key, value in query_index.items():
        query_norm+=value[1]**2
    query_norm = math.sqrt(query_norm)

    #body scores
    for pageid, page_words in forwardidx.items():
        doc_score_body[pageid] = cosine_score_body(query_index, page_words, pageid, query_norm)
            
    # title scores
    for pageid, page_words in forwardtitleidx.items():
        doc_score_title[pageid] = cosine_score_title(query_index, page_words, pageid, query_norm)

    
    # calculate final score
    for pageid, wordls in forwardidx.items():
        body_score = doc_score_body[pageid]
        if pageid not in doc_score_title:
            title_score = 0
        else:
            title_score = doc_score_title[pageid]
        final_score = (body_score+title_score*3)/4
        doc_score_final[pageid] = final_score
    
    for pageid, wordls in forwardtitleidx.items():
        if pageid not in doc_score_final:
            body_score = 0
            title_score = doc_score_title[pageid]
            final_score = (body_score+title_score*3)/4
            doc_score_final[pageid] = final_score

    rank_list = sorted(doc_score_final.items(), key=lambda x:x[1], reverse=True)[:50] # [('key', 'score')]
    return rank_list # [[docid, score, rank], [docid, score, rank], [docid, score, rank]]

    
def fetch_info(rank_list):
    """Given the scores of docs to query and their pageID, we fetch the information of the page and send back to the webserver. 

    Args:
        rank_list (List()): List of page's pageID with their score and rank. 

    Returns:
        List(): not dict! as list of ranked pages in descending order with their information needed to display on the webpage. 
    """
# [[docid, score, rank], [docid, score, rank], [docid, score, rank]] to

    rank_dict = []
    for page in rank_list:
        doc_id = page[0]
        score = page[1]
        page_title = pageID_elem[doc_id][0]
        last_mod = pageID_elem[doc_id][1]
        size = pageID_elem[doc_id][3]
        page_url = pageID_url[doc_id]
        words = sorted(forwardidx[doc_id], key=itemgetter(1), reverse=True)[:5] # sort by descending frequencies, and get first 5
        final_words = '; '.join([f"{wordID_word[w[0]]} {w[1]}" for w in words])
        try:
            child_links = [pageID_url[id] for id in parentID_childID[doc_id]][:10]
        except:
            child_links = []
        try:
            parent_links = [pageID_url[id] for id in childID_parentID[doc_id]][:10]
        except:
            parent_links = []
        
        rank_dict.append([score, page_title, page_url, last_mod, size, final_words, child_links, parent_links])
    return rank_dict

if __name__ == '__main__':
    save = cosinesim_main("Movies for kids")
    fetched = fetch_info(save)
    print(fetched[0])

    