from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('add_income/', views.add_income, name='add_income'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('financial_report/', views.financial_report, name='financial_report'),
    path('forecast_finance/', views.forecast_finance, name='forecast_finance'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('delete_income/<int:income_id>/', views.delete_income, name='delete_income'),
    path('delete_expense/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('login/', views.user_login, name='login'), 
    path('account/', views.account_settings, name='account_settings'),
    path('ask/', views.ask_gemini, name='ask_gemini'),
    path('process_voice_command/', views.process_voice_command, name='process_voice_command'),
    path('speech_to_text/', views.speech_to_text, name='speech_to_text'),
    path('chat_health_check/', views.chat_health_check, name='chat_health_check'),
    path('create_guest_account/', views.create_guest_account, name='create_guest_account'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)