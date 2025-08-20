from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('chat/', views.ai_chat, name='ai_chat'),
    path('menu-recommendations/', views.menu_recommendations, name='menu_recommendations'),
    path('reservation-suggestions/', views.reservation_suggestions, name='reservation_suggestions'),
    path('sentiment-analysis/', views.sentiment_analysis, name='sentiment_analysis'),
    path('basic-recommendations/', views.basic_recommendations, name='basic_recommendations'),
]