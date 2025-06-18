from django.urls import path
from .views import (
    register_view, login_view, logout_view, dashboard_view, home_view, webcam_view, chat_view,
    get_chats, create_chat, delete_chat, get_messages, send_message
)

urlpatterns = [
    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('chat/', chat_view, name='chat'),
    path('webcam/', webcam_view, name='webcam'),
    
    # API endpoints
    path('api/chats/', get_chats, name='get_chats'),
    path('api/chats/create/', create_chat, name='create_chat'),
    path('api/chats/<int:chat_id>/delete/', delete_chat, name='delete_chat'),
    path('api/chats/<int:chat_id>/messages/', get_messages, name='get_messages'),
    path('api/chats/<int:chat_id>/send/', send_message, name='send_message'),
]
