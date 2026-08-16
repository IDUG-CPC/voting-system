from django.urls import path, re_path
from django.views.generic.base import RedirectView

from ..views import views, views_modal, views_debug


urlpatterns = [
    path('', views.moderator, name='moderator_root'),
    path('signup', views.moderator, name='moderator'),

    # ajax methods

    path('moderator_login', views.moderator_login, name='moderator_login'),
    path('moderator_logout', views.moderator_logout, name='moderator_logout'),
    path('resend_verification', views.resend_verification, name='resend_verification'),
    path('verify-email/<str:token>/', views.verify_moderator_email, name='verify_moderator_email'),
    path('refresh_moderators', views.refresh_moderators, name='refresh_moderators'),

    path('get_modal_edit_value', views_modal.get_modal_edit_value, name='get_modal_edit_value'),
    path('update_modal_edit_value', views_modal.update_modal_edit_value, name='update_modal_edit_value'),

]
