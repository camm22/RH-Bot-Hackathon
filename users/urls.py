from django.urls import path
from .views import register_view, login_view, logout_view, dashboard_view, home_view, webcam_view, chat_view

urlpatterns = [
    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('chat/', chat_view, name='chat'),
    path('webcam/', webcam_view, name='webcam'),
]
