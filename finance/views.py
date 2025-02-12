import json
from sklearn.linear_model import LinearRegression
from django.shortcuts import get_object_or_404, render, redirect
import numpy as np
from .forms import IncomeForm, ExpenseForm
from .models import Income, Expense
from django.contrib.auth.decorators import login_required
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from io import BytesIO
import base64
from .forms import UserRegistrationForm
from django.contrib import messages
from django.utils.timezone import now
from django.db.models import Sum
import calendar
from datetime import datetime
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
# Create your views here.
def home(request):
    return render(request, 'finance/home.html')
@login_required
def add_income(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            return redirect('financial_report')  # Chuyển hướng đến trang báo cáo tài chính
    else:
        form = IncomeForm(initial={'date': now().date()})  # Tự động điền ngày hiện tại
    return render(request, 'finance/add_income.html', {'form': form})
@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            return redirect('financial_report')  # Sau khi lưu, chuyển hướng đến trang báo cáo tài chính
    else:
        form = ExpenseForm()
    return render(request, 'finance/add_expense.html', {'form': form})
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Sau khi đăng nhập thành công, chuyển hướng về trang home
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect('login')
        else:
            print(form.errors)
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def financial_report(request):
    # Lấy năm hiện tại
    current_year = datetime.now().year

    # Lấy dữ liệu thu nhập theo tháng và nhóm theo loại thu nhập (source)
    incomes = Income.objects.filter(user=request.user, date__year=current_year)
    income_data = incomes.values('source', 'date__month').annotate(total=Sum('amount')).order_by('date__month')

    income_categories = [item['source'] for item in income_data]
    income_totals = [float(item['total']) for item in income_data]  # Chuyển Decimal thành float
    income_by_month = [sum([float(item['total']) for item in income_data if item['date__month'] == month]) for month in range(1, 13)]

    # Lấy dữ liệu chi tiêu theo tháng và nhóm theo danh mục (category)
    expenses = Expense.objects.filter(user=request.user, date__year=current_year)
    expense_data = expenses.values('category', 'date__month').annotate(total=Sum('amount')).order_by('date__month')

    expense_categories = [item['category'] for item in expense_data]
    expense_totals = [float(item['total']) for item in expense_data]  # Chuyển Decimal thành float
    expense_by_month = [sum([float(item['total']) for item in expense_data if item['date__month'] == month]) for month in range(1, 13)]

    # Tính tổng thu nhập và chi tiêu theo từng loại (cho biểu đồ tròn)
    total_income_by_category = incomes.values('source').annotate(total=Sum('amount'))
    total_expense_by_category = expenses.values('category').annotate(total=Sum('amount'))

    income_category_names = [item['source'] for item in total_income_by_category]
    income_category_totals = [float(item['total']) for item in total_income_by_category]

    expense_category_names = [item['category'] for item in total_expense_by_category]
    expense_category_totals = [float(item['total']) for item in total_expense_by_category]

    # Tổng thu nhập và chi tiêu
    total_income = sum(income_by_month)
    total_expense = sum(expense_by_month)
    balance = total_income - total_expense
    advice = "Hãy tiết kiệm!" if balance < 0 else "Bạn có thể tiết kiệm thêm!"

    # Truyền dữ liệu vào template
    context = {
        'months': json.dumps([calendar.month_name[m] for m in range(1, 13)]),  # Tên tháng (January, February, ...)
        'income_values': json.dumps(income_by_month),
        'expense_values': json.dumps(expense_by_month),
        'income_categories': json.dumps(income_category_names),
        'income_totals': json.dumps(income_category_totals),
        'expense_categories': json.dumps(expense_category_names),
        'expense_totals': json.dumps(expense_category_totals),
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'advice': advice,
        'incomes': incomes,  # Truyền dữ liệu thu nhập vào template
        'expenses': expenses,  # Truyền dữ liệu chi tiêu vào template
    }
    return render(request, 'finance/financial_report.html', context)
@login_required
def delete_income(request, income_id):
    income = get_object_or_404(Income, pk=income_id)
    income.delete()
    return redirect('financial_report')  

# Xóa chi tiêu
@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    expense.delete()
    return redirect('financial_report')