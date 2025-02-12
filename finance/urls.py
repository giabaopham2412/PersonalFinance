from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('add_income/', views.add_income, name='add_income'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('financial_report/', views.financial_report, name='financial_report'),
    #path('forecast_finance/', views.forecast_finance, name='forecast_finance'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('delete_income/<int:income_id>/', views.delete_income, name='delete_income'),
    path('delete_expense/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('login/', views.user_login, name='login'), 
]