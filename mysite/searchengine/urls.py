# paths to diff views 
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name = "index"), # in app searchengine, home path directs to views.index page
]