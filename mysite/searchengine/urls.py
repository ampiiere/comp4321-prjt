# paths to diff views 
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), # to home
    path('result', views.result, name='result'), # to display results
    path('<int:page_id>', views.index, name='index'), # to view page remotely?
]

# path('similar', views.similar, name='similar'),