from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('new_game/', views.new_game, name='new_game'),
    path('new_game/<str:difficulty>/', views.new_game, name='new_game_difficulty'),
    path('new_game/<int:rows>/<int:cols>/<int:mines>/', views.new_game, name='new_game_custom'),
    path('click/<int:row>/<int:col>/', views.click, name='click'),
    path('flag/<int:row>/<int:col>/', views.flag, name='flag'),
    path('reset/', views.reset, name='reset'),
]