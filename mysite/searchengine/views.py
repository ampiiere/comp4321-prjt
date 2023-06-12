from django.shortcuts import render
from searchengine.scripts import cosinesim
from .forms import QueryForm
# stores views for page, serves http requests


def index(response, pageid):
    return render(response, "searchengine/base.html", {})

def home(response):
    return render(response, "searchengine/home.html", {})

def result(response):
    if response.method == 'GET':
        query = QueryForm(response.GET)
        if query.is_valid():
            query_form = query.cleaned_data['query']
            rank_list = cosinesim.cosinesim_main(query_form) # [[docid, score, rank], [docid, score, rank], [docid, score, rank]]
            query_results = cosinesim.fetch_info(rank_list) #["page1", "page1 score", "page title1",'url1', 'lastmoddate1', 'size', "VEEEERY LONG LIST OF WORDS AND FREQUENCIES", ["c1", "c2"], ["p1", "p2"]]]
            return render(response, "searchengine/result.html", {'query_results': query_results, 'query_before':query_form})
    else:
        return(response, "searchengine/home.html", {})
