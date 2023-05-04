# https://vijinimallawaarachchi.com/2017/05/09/porter-stemming-algorithm/
# Porter's algorithm instructions from the above site
import nltk
from nltk.stem import PorterStemmer

def count_m(word):
    vowel = 'aeiou'
    structure = []
    # [C](VC)m[V]
    for c in word:
        if c in vowel:
            if (len(structure) == 0) or (structure[-1] == "c"):
                structure.append("v")
            # if last is also a vowel, skip char
        else: # not in vowel
            if (len(structure) == 0) or (structure[-1] == "v"):
                structure.append("c")
            # if last is also a c, skip char
    

    if len(structure) % 2 == 0: # if even
        m = len(structure)//2 - 1
    else: # if odd
        m = len(structure)//2
        
    return (structure, m)
            
    
def porter(word):
    if not word.isalpha() or len(word) == 1:
        return word
    
    vowel = 'aeiou'
    # cur_struc, m = count_m(word)
    try:
        # 1a
        if word.endswith('sses'):
            word = word[:-4] + 'ss'
        elif word.endswith('ies'):
            word = word[:-3] + 'i'
        elif word.endswith('ss'):
            word = word
        elif word.endswith('s'):
            word = word[:-1]
            
        # 1b
        temp = word
        if word.endswith('eed'):
            if count_m(word[:-3])[1] > 0:
                word = word[:-3]+'ee'
        elif 'v' in count_m(word)[0][1:-1]: # if v is in any position other than first and last
            if word.endswith('ed'):
                word = word[:-2]
                if word.endswith('at'):
                    word = word[:-2] + 'ate'
                elif word.endswith('bl'):
                    word = word[:-2] + 'ble'
                elif word.endswith('iz'):
                    word = word[:-2] + 'ize'
                elif (word[-1] == word[-2]) and (word[-1] not in 'lsz'):
                    word = word[0] # single letter?
            # if strucutre is larger than 3, and if m=1, and if stem ends with cvc, and the last c is not wxy.
                elif (len(count_m(word)[0])>=3) and (count_m(word)[1]==1) and ((count_m(word)[0][:-3] == ['c','v','c']) and (word[-1] not in 'wxy')): 
                    word = word + 'e'
                    
            elif word.endswith('ing'):
                word = word[:-3]
                if word.endswith('at'):
                    word = word[:-2] + 'ate'
                elif word.endswith('bl'):
                    word = word[:-2] + 'ble'
                elif word.endswith('iz'):
                    word = word[:-2] + 'ize'
                elif (word[-1] == word[-2]) and (word[-1] not in 'lsz'):
                    word = word[0] # single letter?

                elif (len(count_m(word)[0])>=0) and (count_m(word)==1) and ((count_m(word)[0][:-3] == ['c','v','c']) and (word[-1] not in 'wxy')): 
                    word = word + 'e'
        
        # 1c
        # if any vowels in word
        if any(char in vowel for char in word) and word.endswith('y'):
            word = word[:-1]+'i'
            # print(word)

        # 2
        Step2Dict = {'ational': 'ate',
                    'tional': 'tion',
                    'enci': 'ence',
                    'anci': 'ance',
                    'izer': 'ize',
                    'abli': 'able',
                    'alli': 'al',
                    'entli': 'ent',
                    'eli': 'e',
                    'ousli': 'ous',
                    'ization': 'ize',
                    'ation': 'ate',
                    'ator': 'ate',
                    'alism': 'al',
                    'iveness': 'ive',
                    'fulness': 'ful',
                    'ousness': 'ous',
                    'aliti': 'al',
                    'iviti': 'ive',
                    'biliti': 'ble'}

        for key, value in Step2Dict.items():
            if count_m(word)[1]>0 and word.endswith(key):
                word = word[:-len(key)] + value
                # print(word)
                
        # 3
        Step3Dict = {'icate': 'ic',
                    'ative': '',
                    'alize': 'al',
                    'iciti': 'ic',
                    'ical': 'ic',
                    'ful': '',
                    'ness': ''}
        for key, value in Step3Dict.items():
            if count_m(word)[1]>0 and word.endswith(key):
                word = word[:-len(key)] + value
                # print(word)
                
        # 4
        Step4List = ['al', 'ance', 'ence', 'er', 'ic', 'able', 'ible', 'ant', 'ement', 'ment', 'ent',
                    'ion', 'ou', 'ism', 'ate', 'iti', 'ous', 'ive', 'ize']
        for i in Step4List:
            if i == 'ion':
                if count_m(word)[1]>1 and (word[-1] in 'st') and (word.endswith(i)):
                    word = word[:-len(i)]
            if count_m(word)[1]>1 and word.endswith(i):
                # print(count_m(word)[1])
                word = word[:-len(i)]

                
        #5 a
        if count_m(word)[1] >1 and word[-1] == 'e':
            word = word[:-1]
        # if struc >3, m ==1
        elif (count_m(word)[1]==1):
            if (len(count_m(word)[0])>=3):
                if not ((count_m(word)[0][:-3] == ['c','v','c']) and (word[-1] not in 'wxy')):
                    if word[-1] == 'e':
                        word = word[:-1]
            else:
                # if not 3 or longer, then already not cvc
                if word[-1] == 'e':
                    word = word[:-1]
        
        # 5b
        if (count_m(word)[1]>1) and (word[-1] == word[-2]) and word.endswith('l'):
            word = word[0]
    except Exception as e:
        return word
          
    return word


if __name__ == '__main__':
    word = 'unanimous'
    print(porter(word))
    ps = PorterStemmer()
    print(ps.stem(word))

            

