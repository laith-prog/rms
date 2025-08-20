from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    # Basic AI features
    path("chat/", views.chat, name="chat"),
    path("recommend/", views.recommend, name="recommend"),
    
    # Advanced AI features
    path("menu-recommendations/", views.menu_recommendations, name="menu_recommendations"),
    path("reservation-suggestions/", views.reservation_suggestions, name="reservation_suggestions"),
    path("sentiment-analysis/", views.sentiment_analysis, name="sentiment_analysis"),
]