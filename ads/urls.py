from django.urls import path
from . import views

urlpatterns = [
    path('<int:ad_id>/view/', views.track_ad_view, name='track_ad_view'),
    path('<int:ad_id>/click/', views.track_ad_click, name='track_ad_click'),
]
