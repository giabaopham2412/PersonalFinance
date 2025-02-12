from django import forms
from .models import Income, Expense
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['amount', 'source', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),  # Widget để hiển thị trường ngày dưới dạng lịch
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']