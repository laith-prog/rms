from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('chat/', views.ai_chat, name='ai_chat'),
    path('menu-recommendations/', views.menu_recommendations, name='menu_recommendations'),
    path('reservation-suggestions/', views.reservation_suggestions, name='reservation_suggestions'),
    path('sentiment-analysis/', views.sentiment_analysis, name='sentiment_analysis'),
    path('basic-recommendations/', views.basic_recommendations, name='basic_recommendations'),

    # New endpoints
    path('menu/search/semantic/', views.semantic_menu_search, name='semantic_menu_search'),
    path('orders/upsell/', views.upsell_recommendations, name='upsell_recommendations'),
    path('reviews/summarize/', views.reviews_summarize, name='reviews_summarize'),
    path('reservations/predict-wait/', views.predict_wait_time, name='predict_wait_time'),
    path('chat/start-session/', views.start_chat_session, name='start_chat_session'),
    path('chat/<uuid:session_id>/messages/', views.chat_session_messages, name='chat_session_messages'),
]