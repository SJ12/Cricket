'''
Created on Mar 5, 2015

@author: sijo
'''
from django.conf.urls.defaults import *
from guestbook.views import sign_post, get_details, get_json,main_page,get_highlights,get_highlights_from_json

urlpatterns = patterns('',
    (r'^sign/$', sign_post),
    (r'^json/$', get_json),
    (r'^details/$', get_details),
    (r'^highlights/$', get_highlights_from_json),
    (r'^$', main_page),
)