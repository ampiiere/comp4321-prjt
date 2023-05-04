from django.shortcuts import render
from django.http import HttpResponse
# stores views for page, serves http requests

# view 1
def index(request):
    # returns html code
    return HttpResponse("<h1>Hello, world. You're at the polls index.<h1>")