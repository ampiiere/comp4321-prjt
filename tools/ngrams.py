import nltk
from nltk.util import ngrams
from nltk.tag import pos_tag
nltk.download('averaged_perceptron_tagger')
from nltk.tokenize import WhitespaceTokenizer

def ngrams_proccess(tokens):
    tokens = [i for i in tokens if i]
    pos_token = [pos[1] for pos in pos_tag(tokens)] # [noun, verb...]
    bi = []
    tri = []
    bigram_tok = list(ngrams(tokens, 2)) # [('The', 'hong'), ('hong', 'kong')]
    trigram_tok = list(ngrams(tokens, 3))
    
    for idx, bigram in enumerate(bigram_tok):
        first_pos = pos_token[idx]
        sec_pos = pos_token[idx+1]
        if first_pos in ["NN","NNS", "NNP", "NNPS", "JJ", "JJR", "JJS"] and sec_pos in ["NN","NNS", "NNP", "NNPS"]:
            bi.append(bigram)

    for idx, trigram in enumerate(trigram_tok):
        first_pos = pos_token[idx]
        sec_pos = pos_token[idx+1]
        thir_pos = pos_token[idx+2]
        if first_pos in ["NN","NNS", "NNP", "NNPS", "JJ", "JJR", "JJS"] and thir_pos in ["NN","NNS", "NNP", "NNPS"]:
            tri.append(trigram)
            
# Stop word filtering?
# for pair in bigram_tok:
#     print(pair[0], pair[1])
#     if ((pair[0] not in stopwords) and (pair[1] not in stopwords)):
#         bi.append(pair)


    return (bi, tri)
    
if __name__== '__main__':
    text = "The hong kong university of science and technology is reknowed for it's infamously high anxiety count. "
    tokens = WhitespaceTokenizer().tokenize(text) # ['ha', 'he']
    ngrams_proccess(tokens)
    
    