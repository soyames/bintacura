from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'communication'

router = DefaultRouter()
router.register(r'posts', views.CommunityPostViewSet, basename='post')
router.register(r'comments', views.CommentViewSet, basename='comment')
router.register(r'groups', views.CommunityGroupViewSet, basename='group')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('online-users/', views.online_users, name='online-users'),
    path('update-activity/', views.update_activity, name='update-activity'),
    path('go-offline/', views.go_offline, name='go-offline'),
    path('ai-chat/', views.ai_chat_proxy, name='ai-chat'),
]
