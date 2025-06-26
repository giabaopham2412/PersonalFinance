import json
import queue
import re
import threading

import requests
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
from .forms import UserUpdateForm, ProfileUpdateForm
from .models import Profile
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import google.generativeai as genai
import base64
import io
from transformers import pipeline
from google.cloud import speech
import os
from google.oauth2 import service_account

def get_financial_summary_text(user):
    """
    Generate a text summary of the user's financial data for speech synthesis.
    """
    # Lấy năm và tháng hiện tại
    current_year = datetime.now().year
    current_month = datetime.now().month
    month_name = calendar.month_name[current_month]

    # Lấy dữ liệu thu nhập và chi tiêu
    incomes = Income.objects.filter(user=user, date__year=current_year)
    expenses = Expense.objects.filter(user=user, date__year=current_year)

    # Tính tổng thu nhập và chi tiêu
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expense

    # Tính thu nhập và chi tiêu trong tháng hiện tại
    current_month_incomes = incomes.filter(date__month=current_month)
    current_month_expenses = expenses.filter(date__month=current_month)
    current_month_income = current_month_incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    current_month_expense = current_month_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    current_month_balance = current_month_income - current_month_expense

    # Tính thu nhập theo loại
    income_by_category = incomes.values('source').annotate(total=Sum('amount'))
    income_categories_text = ""
    for item in income_by_category:
        source_display = dict(Income.SOURCE_CHOICES).get(item['source'], item['source'])
        income_categories_text += f"{source_display}: {item['total']} đồng. "

    # Tính chi tiêu theo loại
    expense_by_category = expenses.values('category').annotate(total=Sum('amount'))
    expense_categories_text = ""
    for item in expense_by_category:
        category_display = dict(Expense.CATEGORY_CHOICES).get(item['category'], item['category'])
        expense_categories_text += f"{category_display}: {item['total']} đồng. "

    # Tạo lời khuyên
    advice = "Hãy tiết kiệm!" if balance < 0 else "Bạn có thể tiết kiệm thêm!"

    # Tạo văn bản tổng hợp
    summary = f"""
    Báo cáo tài chính của bạn.
    Tổng thu nhập: {total_income} đồng.
    Tổng chi tiêu: {total_expense} đồng.
    Số dư: {balance} đồng.

    Trong tháng {month_name}:
    Thu nhập: {current_month_income} đồng.
    Chi tiêu: {current_month_expense} đồng.
    Số dư tháng này: {current_month_balance} đồng.

    Chi tiết thu nhập theo loại:
    {income_categories_text}

    Chi tiết chi tiêu theo loại:
    {expense_categories_text}

    Lời khuyên: {advice}
    """

    return summary.strip()
# Trang chủ
def home(request):
    return render(request, 'finance/home.html')

# Thêm thu nhập
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

# Thêm chi tiêu
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

# Báo cáo tài chính

@login_required
def financial_report(request):
    # Lấy năm hiện tại
    current_year = datetime.now().year
    current_month = datetime.now().month

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

    # Lấy dữ liệu thu nhập và chi tiêu theo ngày trong tháng hiện tại
    daily_income_data = incomes.filter(date__month=current_month).values('date__day').annotate(total=Sum('amount')).order_by('date__day')
    daily_income_days = [item['date__day'] for item in daily_income_data]
    daily_income_totals = [float(item['total']) for item in daily_income_data]

    daily_expense_data = expenses.filter(date__month=current_month).values('date__day').annotate(total=Sum('amount')).order_by('date__day')
    daily_expense_days = [item['date__day'] for item in daily_expense_data]
    daily_expense_totals = [float(item['total']) for item in daily_expense_data]

    # Tổng thu nhập và chi tiêu
    total_income = sum(income_by_month)
    total_expense = sum(expense_by_month)
    balance = total_income - total_expense
    advice = "Hãy tiết kiệm!" if balance < 0 else "Bạn có thể tiết kiệm thêm!"

    # Tạo văn bản tổng hợp cho text-to-speech
    financial_summary = get_financial_summary_text(request.user)

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
        'daily_income_days': json.dumps(daily_income_days),
        'daily_income_totals': json.dumps(daily_income_totals),
        'daily_expense_days': json.dumps(daily_expense_days),
        'daily_expense_totals': json.dumps(daily_expense_totals),
        'financial_summary': json.dumps(financial_summary),  # Thêm văn bản tổng hợp cho text-to-speech
    }

    return render(request, 'finance/financial_report.html', context)


@login_required
def forecast_finance(request):
    # Lấy năm hiện tại
    current_year = datetime.now().year

    # Tổng hợp thu nhập theo tháng
    income_by_month = (
        Income.objects.filter(user=request.user, date__year=current_year)
        .values_list('date__month')
        .annotate(total=Sum('amount'))
        .order_by('date__month')
    )
    income_data = {month: float(total) for month, total in income_by_month}

    # Tổng hợp chi tiêu theo tháng
    expense_by_month = (
        Expense.objects.filter(user=request.user, date__year=current_year)
        .values_list('date__month')
        .annotate(total=Sum('amount'))
        .order_by('date__month')
    )
    expense_data = {month: float(total) for month, total in expense_by_month}

    # Tạo dữ liệu cho biểu đồ
    months = list(range(1, 13))  
    income_values = [income_data.get(month, 0) for month in months]
    expense_values = [expense_data.get(month, 0) for month in months]

    # Dự báo thu nhập và chi tiêu sử dụng hồi quy tuyến tính (AI)
    df = pd.DataFrame({
        'month': months,
        'income': income_values,
        'expense': expense_values
    })

    # Sử dụng LinearRegression để dự đoán
    X = df[['month']]  
    y_income = df['income']
    y_expense = df['expense']

    # Tạo mô hình hồi quy tuyến tính cho thu nhập và chi tiêu
    model_income = LinearRegression()
    model_expense = LinearRegression()

    # Huấn luyện mô hình
    model_income.fit(X, y_income)
    model_expense.fit(X, y_expense)

    # Dự đoán thu nhập và chi tiêu trong năm tiếp theo (Tháng 1 đến tháng 12)
    future_months = np.array(range(1, 13)).reshape(-1, 1)  
    predicted_income = model_income.predict(future_months)
    predicted_expense = model_expense.predict(future_months)

    # Dự báo và lời khuyên
    total_income = sum(income_values)
    total_expense = sum(expense_values)
    balance = total_income - total_expense
    advice = "Hãy tiết kiệm!" if balance < 0 else "Bạn có thể tiết kiệm thêm!"

    # Dự đoán xu hướng
    future_balance = sum(predicted_income) - sum(predicted_expense)
    if future_balance < 0:
        future_advice = "Dự báo tài chính cho thấy bạn cần phải điều chỉnh chi tiêu để tránh thâm hụt!"
    else:
        future_advice = "Dự báo tài chính cho thấy bạn có thể tiết kiệm thêm, tuy nhiên, cần theo dõi chi tiêu chặt chẽ."

    # Kết luận dựa trên dự báo
    if future_balance < 0:
        conclusion = "Cần điều chỉnh chi tiêu và tập trung vào tiết kiệm để tránh tình trạng thâm hụt trong năm tới."
    else:
        conclusion = "Tình hình tài chính ổn định, nhưng vẫn nên tiếp tục theo dõi và điều chỉnh để tối đa hóa tiết kiệm."

    # Truyền dữ liệu vào template
    context = {
        'months': json.dumps([calendar.month_abbr[m] for m in months]),  # Tên tháng (Jan, Feb, ...)
        'income_values': json.dumps(income_values),
        'expense_values': json.dumps(expense_values),
        'predicted_income': json.dumps(predicted_income.tolist()),
        'predicted_expense': json.dumps(predicted_expense.tolist()),
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'advice': advice,
        'future_advice': future_advice,
        'conclusion': conclusion,  # Truyền câu kết luận vào context
    }

    return render(request, 'finance/forecast_finance.html', context)


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Tài khoản {username} đã được tạo thành công! Bạn có thể đăng nhập.')
            return redirect('login')  
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


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


@login_required
def account_settings(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your account has been updated!')

            if request.is_ajax():
                return JsonResponse({
                    'success': True,
                    'message': 'Your account has been updated!',
                    'image_url': profile.image.url
                })
            return redirect('account_settings')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'finance/account_settings.html', context)

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import random

def generate_simple_response(user_input, financial_data, profile):
    """
    Generate a simple response when the AI model fails.
    This is a fallback mechanism to ensure the chat always works.
    """
    # Convert user input to lowercase for easier matching
    user_input_lower = user_input.lower()

    # Get financial data
    total_income = financial_data.get('total_income', 'không có thông tin')
    total_expense = financial_data.get('total_expense', 'không có thông tin')
    balance = financial_data.get('balance', 'không có thông tin')

    # Define some common responses
    greetings = ["Xin chào", "Chào bạn", "Rất vui được gặp bạn"]

    # Check for common questions and provide appropriate responses
    if any(word in user_input_lower for word in ["xin chào", "chào", "hello", "hi"]):
        response = f"{random.choice(greetings)}! Tôi là trợ lý tài chính của bạn. Tôi có thể giúp gì cho bạn?"

    elif any(word in user_input_lower for word in ["thu nhập", "kiếm được", "lương"]):
        response = f"Tổng thu nhập của bạn là {total_income}. Bạn có thể xem chi tiết trong báo cáo tài chính."

    elif any(word in user_input_lower for word in ["chi tiêu", "chi phí", "tốn"]):
        response = f"Tổng chi tiêu của bạn là {total_expense}. Bạn có thể xem chi tiết trong báo cáo tài chính."

    elif any(word in user_input_lower for word in ["số dư", "còn lại", "balance"]):
        response = f"Số dư tài khoản của bạn là {balance}."

    elif any(word in user_input_lower for word in ["tiết kiệm", "save", "saving"]):
        if isinstance(balance, (int, float)) and balance > 0:
            response = "Bạn đang có số dư dương, đây là dấu hiệu tốt. Hãy tiếp tục tiết kiệm!"
        else:
            response = "Để tiết kiệm hiệu quả, bạn nên giảm các khoản chi tiêu không cần thiết và lập kế hoạch tài chính hàng tháng."

    elif any(word in user_input_lower for word in ["đầu tư", "invest", "investment"]):
        response = "Đầu tư là cách tốt để tăng trưởng tài sản. Bạn nên tìm hiểu về các loại hình đầu tư phù hợp với mục tiêu tài chính của mình."

    elif any(word in user_input_lower for word in ["mục tiêu", "kế hoạch", "goal", "plan"]):
        response = "Lập kế hoạch tài chính rõ ràng sẽ giúp bạn đạt được mục tiêu. Hãy xác định mục tiêu ngắn hạn và dài hạn, sau đó phân bổ ngân sách phù hợp."

    else:
        # Default response if no specific pattern is matched
        responses = [
            "Tôi không thể trả lời câu hỏi đó chi tiết. Hãy thử hỏi về thu nhập, chi tiêu hoặc số dư của bạn.",
            "Xin lỗi, tôi không hiểu câu hỏi. Bạn có thể hỏi về tình hình tài chính của mình không?",
            "Tôi chỉ có thể giúp bạn với các câu hỏi liên quan đến tài chính cá nhân.",
            "Hệ thống AI đang được nâng cấp. Vui lòng hỏi câu đơn giản hơn về tài chính của bạn."
        ]
        response = random.choice(responses)

    return JsonResponse({"response": response})
from dotenv import load_dotenv
load_dotenv('.env')
load_dotenv('.env.local')
# Load environment variables

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"

def generate_simple_response(user_input, financial_data, profile):
    return JsonResponse({
        "response": "Xin lỗi, tôi chưa thể xử lý câu hỏi của bạn ngay bây giờ. Bạn có thể hỏi lại sau nhé!"
    })


def get_financial_context_for_chatbot(user, financial_data=None, year=None):
    from datetime import datetime
    from django.db.models import Sum
    import calendar

    current_year = datetime.now().year
    target_year = year if year else current_year
    previous_year = target_year - 1

    all_incomes = Income.objects.filter(user=user, date__year=target_year)
    all_expenses = Expense.objects.filter(user=user, date__year=target_year)
    prev_incomes = Income.objects.filter(user=user, date__year=previous_year)
    prev_expenses = Expense.objects.filter(user=user, date__year=previous_year)

    # Tổng kết năm hiện tại
    total_income = all_incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = all_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    total_balance = total_income - total_expense

    # Năm trước
    prev_income = prev_incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    prev_expense = prev_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    prev_balance = prev_income - prev_expense

    def percent_change(curr, prev):
        if prev == 0:
            return "N/A"
        delta = curr - prev
        percent = round((delta / prev) * 100)
        return f"{delta} đồng ({percent}%)"

    # Tổng hợp theo nguồn
    income_by_source = all_incomes.values('source').annotate(total=Sum('amount'))
    income_category_rows = [
        f"- {dict(Income.SOURCE_CHOICES).get(i['source'], i['source'])}: {i['total']} đồng"
        for i in income_by_source
    ] or ["- Không có dữ liệu"]

    # Tổng hợp theo danh mục chi tiêu
    expense_by_category = all_expenses.values('category').annotate(total=Sum('amount'))
    expense_category_rows = [
        f"- {dict(Expense.CATEGORY_CHOICES).get(e['category'], e['category'])}: {e['total']} đồng"
        for e in expense_by_category
    ] or ["- Không có dữ liệu"]

    # Tổng hợp theo tháng
    monthly_blocks = []
    for month in range(1, 13):
        m_incomes = all_incomes.filter(date__month=month)
        m_expenses = all_expenses.filter(date__month=month)
        income_total = m_incomes.aggregate(Sum('amount'))['amount__sum'] or 0
        expense_total = m_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        balance_total = income_total - expense_total

        if income_total == 0 and expense_total == 0:
            continue

        income_details = m_incomes.values('source').annotate(total=Sum('amount'))
        expense_details = m_expenses.values('category').annotate(total=Sum('amount'))

        income_lines = "\n    ".join([
            f"- {dict(Income.SOURCE_CHOICES).get(i['source'], i['source'])}: {i['total']} đồng"
            for i in income_details
        ]) or "- Không có"

        expense_lines = "\n    ".join([
            f"- {dict(Expense.CATEGORY_CHOICES).get(e['category'], e['category'])}: {e['total']} đồng"
            for e in expense_details
        ]) or "- Không có"

        month_block = f"""
=== THÁNG: {calendar.month_name[month].upper()} ===
Tổng thu nhập: {income_total} đồng
Chi tiết thu nhập:
    {income_lines}

Tổng chi tiêu: {expense_total} đồng
Chi tiết chi tiêu:
    {expense_lines}

Cân đối: {balance_total} đồng
"""
        monthly_blocks.append(month_block.strip())

    # Ghép toàn bộ ngữ cảnh
    context = f"""
================ TỔNG QUAN TÀI CHÍNH NĂM {target_year} ================
Tổng thu nhập cả năm: {total_income} đồng
Tổng chi tiêu cả năm: {total_expense} đồng
Cân đối cả năm: {total_balance} đồng

========= So sánh với năm {previous_year} =========
Chênh lệch thu nhập: {percent_change(total_income, prev_income)}
Chênh lệch chi tiêu: {percent_change(total_expense, prev_expense)}

========= Thu nhập theo nguồn =========
{chr(10).join(income_category_rows)}

========= Chi tiêu theo danh mục =========
{chr(10).join(expense_category_rows)}

========= Chi tiết từng tháng =========
{chr(10*2).join(monthly_blocks) if monthly_blocks else 'Không có dữ liệu theo tháng.'}
""".strip()

    return context


def ask_gemini(request):
    try:
        data = json.loads(request.body)
        user_input = data.get("message", "")
        financial_data = data.get("financial_data", {})

        # Lấy thông tin người dùng
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=request.user)

        # Extract year from user query if present
        year = None
        year_match = re.search(r'\b(20\d{2})\b', user_input)  # Match years like 2021, 2022, etc.
        if year_match:
            year = int(year_match.group(1))

        # Extract month from user query if present
        month = None

        # English month names
        month_names = list(calendar.month_name)[1:]  # Get list of month names (January, February, etc.)
        month_pattern = r'\b(' + '|'.join(month_names) + r')\b'
        month_match = re.search(month_pattern, user_input, re.IGNORECASE)

        # Vietnamese month patterns (Tháng 1, Tháng 2, etc.)
        if not month_match:
            vn_month_pattern = r'\b[Tt]háng\s+(\d{1,2})\b'
            vn_month_match = re.search(vn_month_pattern, user_input)
            if vn_month_match:
                month_num = int(vn_month_match.group(1))
                if 1 <= month_num <= 12:
                    month = month_num
                    month_name = calendar.month_name[month]

        # Process English month names if found
        if month_match:
            month_name = month_match.group(1).title()  # Capitalize first letter
            month = list(calendar.month_name).index(month_name)

        # Update user input with month information if a month was found (either English or Vietnamese)
        if month is not None:
            # Add month information to the user input for better context
            month_name = calendar.month_name[month]
            user_input = f"{user_input} (Specifically asking about {month_name})"

        # Get comprehensive financial context for the specified year or current year
        financial_context = get_financial_context_for_chatbot(request.user, financial_data, year)

        # Chuẩn bị ngữ cảnh cho AI với dữ liệu tài chính đầy đủ
        context = f"""
        ### INSTRUCTIONS:
        You are a financial assistant. Answer ONLY with the number in đồng (e.g., "2234667 đồng"). Do not explain.

        ### DATA:
        {financial_context}

        ### PROFILE:
        - Age: {profile.age or 'unknown'}
        - Occupation: {profile.occupation or 'unknown'}

        ### QUESTION:
        {user_input}
        """
        try:
            # Gọi Hugging Face API thay vì tải model về
            def call_hf():
                try:
                    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
                    payload = {
                        "inputs": context,
                        "parameters": {
                            "max_new_tokens": 100,
                            "temperature": 0.4,
                            "top_k": 50,
                            "top_p": 0.9,
                            "do_sample": True
                        }
                    }
                    response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
                    if response.status_code == 200:
                        result_queue.put(response.json())
                    else:
                        result_queue.put(RuntimeError(f"API error {response.status_code}: {response.text}"))
                except Exception as e:
                    result_queue.put(e)

            result_queue = queue.Queue()
            generation_thread = threading.Thread(target=call_hf)
            generation_thread.daemon = True
            generation_thread.start()

            try:
                output = result_queue.get(timeout=10)
                if isinstance(output, Exception):
                    raise output
            except queue.Empty:
                print("Model generation timed out")
                return generate_simple_response(user_input, financial_data, profile)
            except Exception as timeout_error:
                print(f"Error during model generation: {str(timeout_error)}")
                return generate_simple_response(user_input, financial_data, profile)

            if isinstance(output, list) and "generated_text" in output[0]:
                reply = output[0]["generated_text"].replace(context, "").strip()
                if len(reply.split()) > 100:
                    sentences = reply.split('. ')
                    reply = '. '.join(sentences[:3]) + ('.' if not sentences[2].endswith('.') else '')
                return JsonResponse({"response": reply})
            else:
                return generate_simple_response(user_input, financial_data, profile)

        except Exception as gen_error:
            print(f"Error generating response: {str(gen_error)}")
            return generate_simple_response(user_input, financial_data, profile)

    except Exception as e:
        print(f"Error in ask_gemini: {str(e)}")
        return JsonResponse({"response": f"Lỗi: {str(e)}"}, status=500)


@csrf_exempt
def chat_health_check(request):
    """
    A simple health check endpoint for the chat functionality.
    This can be used to verify if the chat is working correctly.
    """
    try:
        # Check if we can import the required libraries
        import torch
        from transformers import AutoTokenizer

        # Return a success response
        return JsonResponse({
            "status": "ok",
            "message": "Chat service is operational",
            "torch_version": torch.__version__,
            "transformers_available": True
        })
    except Exception as e:
        # Return an error response
        return JsonResponse({
            "status": "error",
            "message": f"Chat service is experiencing issues: {str(e)}",
            "error": str(e)
        }, status=500)
def generate_simple_response(user_input, financial_data, profile):
    return JsonResponse({
        "response": f"Xin lỗi, tôi chưa thể xử lý câu hỏi của bạn ngay bây giờ. Bạn có thể hỏi lại sau nhé!"
    })

@csrf_exempt
@require_POST
def process_voice_command(request):
    global speech_to_text_context

    try:
        data = json.loads(request.body)
        command = data.get("command", "").lower()

        # If no command is provided in the request, use the saved context
        if not command and speech_to_text_context:
            command = speech_to_text_context.lower()
            # Clear the context after using it
            speech_to_text_context = ""

        # Check for direct income/expense commands with amount (Vietnamese)
        income_match_vi = re.search(r'thêm thu nhập\s+(.+?)\s+(\d+)', command)
        # Alternative Vietnamese income patterns
        alt_income_match_vi = re.search(r'thêm\s+(\d+)\s+(lương|thu nhập|tiền|kinh doanh|đầu tư)', command)
        # Direct source-amount pattern (e.g., "thêm lương 100000")
        direct_income_match_vi = re.search(r'thêm\s+(lương|thu nhập|tiền|kinh doanh|đầu tư)\s+(\d+)', command)
        # Simple income pattern (e.g., "lương 100000")
        simple_income_vi = re.search(r'^(lương|thu nhập|tiền|kinh doanh|đầu tư)\s+(\d+)$', command)
        # Very simple income pattern (e.g., "lương100", "tiền100")
        very_simple_income_vi = re.search(r'^(lương|thu nhập|tiền|kinh doanh|đầu tư)(\d+)$', command)
        # Income with "là" pattern (e.g., "lương là 100", "thu nhập là 200")
        income_la_vi = re.search(r'(lương|thu nhập|tiền|kinh doanh|đầu tư)\s+là\s+(\d+)', command)
        # Income with "có" pattern (e.g., "tôi có lương 100", "có thu nhập 200")
        income_co_vi = re.search(r'có\s+(lương|thu nhập|tiền|kinh doanh|đầu tư)\s+(\d+)', command)

        expense_match_vi = re.search(r'thêm chi tiêu\s+(.+?)\s+(\d+)', command)
        # Alternative Vietnamese expense patterns
        alt_expense_match_vi = re.search(r'thêm\s+(\d+)\s+(chi tiêu|chi phí|thực phẩm|ăn|giáo dục|học|giải trí|di chuyển|xe)', command)
        # Direct category-amount pattern (e.g., "thêm thực phẩm 100000")
        direct_expense_match_vi = re.search(r'thêm\s+(thực phẩm|ăn|giáo dục|học|giải trí|di chuyển|xe|chi phí)\s+(\d+)', command)
        # Simple expense pattern (e.g., "thực phẩm 100000")
        simple_expense_vi = re.search(r'^(thực phẩm|ăn|giáo dục|học|giải trí|di chuyển|xe|chi phí)\s+(\d+)$', command)
        # Very simple expense pattern (e.g., "thực phẩm100", "giáo dục100")
        very_simple_expense_vi = re.search(r'^(thực phẩm|ăn|giáo dục|học|giải trí|di chuyển|xe|chi phí)(\d+)$', command)
        # Expense with "là" pattern (e.g., "thực phẩm là 100", "giáo dục là 200")
        expense_la_vi = re.search(r'(thực phẩm|ăn|giáo dục|học|giải trí|di chuyển|xe|chi phí)\s+là\s+(\d+)', command)
        # Expense with "chi" pattern (e.g., "chi thực phẩm 100", "chi giáo dục 200")
        expense_chi_vi = re.search(r'chi\s+(thực phẩm|ăn|giáo dục|học|giải trí|di chuyển|xe)\s+(\d+)', command)

        # Check for direct income/expense commands with amount (English)
        income_match_en = re.search(r'add (income|salary|revenue|earnings)\s+(\d+)', command)
        expense_match_en = re.search(r'add (expense|cost|spending|expenditure)\s+(.+?)\s+(\d+)', command)

        # Direct English category-amount pattern (e.g., "add food 100000")
        direct_expense_match_en = re.search(r'add\s+(food|meal|grocery|education|school|course|entertainment|movie|game|transport|travel|car)\s+(\d+)', command)

        # Simplified English income pattern (e.g., "add salary 100000")
        simple_income_match_en = re.search(r'add (income|salary|revenue|earnings)\s+(\d+)', command)

        # Alternative income pattern (e.g., "add 100 salary")
        alt_income_match_en = re.search(r'add\s+(\d+)\s+(income|salary|revenue|earnings)', command)

        # Simple English patterns (e.g., "salary 100")
        simple_income_en = re.search(r'^(salary|income|revenue|earnings)\s+(\d+)$', command)
        simple_expense_en = re.search(r'^(food|meal|grocery|education|school|course|entertainment|movie|game|transport|travel|car)\s+(\d+)$', command)

        # Very simple English patterns without spaces (e.g., "salary100")
        very_simple_income_en = re.search(r'^(salary|income|revenue|earnings)(\d+)$', command)
        very_simple_expense_en = re.search(r'^(food|meal|grocery|education|school|course|entertainment|movie|game|transport|travel|car)(\d+)$', command)

        # English patterns with "is" (e.g., "salary is 100")
        income_is_en = re.search(r'(salary|income|revenue|earnings)\s+is\s+(\d+)', command)
        expense_is_en = re.search(r'(food|meal|grocery|education|school|course|entertainment|movie|game|transport|travel|car)\s+is\s+(\d+)', command)

        # English patterns with "have" or "got" (e.g., "I have salary 100", "got income 200")
        income_have_en = re.search(r'(have|got)\s+(salary|income|revenue|earnings)\s+(\d+)', command)

        # English patterns with "spend" or "pay" (e.g., "spend on food 100", "pay for education 200")
        expense_spend_en = re.search(r'(spend|pay)(\s+on|\s+for)?\s+(food|meal|grocery|education|school|course|entertainment|movie|game|transport|travel|car)\s+(\d+)', command)

        # Check for delete commands (Vietnamese)
        delete_income_match_vi = re.search(r'xóa thu nhập\s+(\d+)', command)
        delete_expense_match_vi = re.search(r'xóa chi tiêu\s+(\d+)', command)
        delete_last_income_match_vi = re.search(r'xóa khoản thu nhập (cuối cùng|gần nhất|mới nhất)', command)
        delete_last_expense_match_vi = re.search(r'xóa khoản chi tiêu (cuối cùng|gần nhất|mới nhất)', command)

        # Check for delete commands (English)
        delete_income_match_en = re.search(r'delete income\s+(\d+)', command)
        delete_expense_match_en = re.search(r'delete expense\s+(\d+)', command)
        delete_last_income_match_en = re.search(r'delete (last|latest|recent) income', command)
        delete_last_expense_match_en = re.search(r'delete (last|latest|recent) expense', command)

        # Process income commands
        income_match = (income_match_vi or alt_income_match_vi or direct_income_match_vi or 
                      income_match_en or simple_income_match_en or alt_income_match_en or 
                      simple_income_vi or simple_income_en or very_simple_income_vi or 
                      very_simple_income_en or income_la_vi or income_co_vi or income_is_en or 
                      income_have_en)

        if income_match:
            # Extract source and amount from the command
            if income_match == income_match_vi:
                # Vietnamese command
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == alt_income_match_vi:
                # Alternative Vietnamese command (amount first, then category)
                amount = int(income_match.group(1))
                source_text = income_match.group(2).strip()
            elif income_match == direct_income_match_vi:
                # Direct Vietnamese command (source first, then amount)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == simple_income_vi:
                # Simple Vietnamese command (just source and amount)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == very_simple_income_vi:
                # Very simple Vietnamese command (no space between source and amount)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == income_la_vi:
                # Vietnamese command with "là" (is)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == income_co_vi:
                # Vietnamese command with "có" (have)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == income_match_en:
                # English command with category
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == simple_income_match_en:
                # Simple English command
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == alt_income_match_en:
                # Alternative English command (amount first, then category)
                amount = int(income_match.group(1))
                source_text = income_match.group(2).strip()
            elif income_match == simple_income_en:
                # Simple English command (just source and amount)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == very_simple_income_en:
                # Very simple English command (no space between source and amount)
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == income_is_en:
                # English command with "is"
                source_text = income_match.group(1).strip()
                amount = int(income_match.group(2))
            elif income_match == income_have_en:
                # English command with "have" or "got"
                source_text = income_match.group(2).strip()
                amount = int(income_match.group(3))

            # Map the source text to one of the predefined sources
            source = 'Other'  # Default

            # Check for Vietnamese terms
            if 'lương' in source_text:
                source = 'Salary'
            elif 'kinh doanh' in source_text:
                source = 'Business'
            elif 'đầu tư' in source_text:
                source = 'Investment'

            # Check for English terms
            elif source_text == 'salary' or source_text == 'income':
                source = 'Salary'
            elif source_text == 'business' or source_text == 'revenue':
                source = 'Business'
            elif source_text == 'investment' or source_text == 'earnings':
                source = 'Investment'

            # Create and save the income
            income = Income(
                user=request.user,
                amount=amount,
                source=source,
                date=now().date()
            )
            income.save()

            return JsonResponse({
                "success": True,
                "message": f"Đã thêm khoản thu nhập {source_text} với số tiền {amount}",
                "action": "income_added",
                "data": {
                    "source": source,
                    "amount": amount,
                    "date": now().date().isoformat()
                }
            })

        # Process expense commands
        expense_match = (expense_match_vi or alt_expense_match_vi or direct_expense_match_vi or 
                       expense_match_en or direct_expense_match_en or simple_expense_vi or 
                       simple_expense_en or very_simple_expense_vi or very_simple_expense_en or 
                       expense_la_vi or expense_chi_vi or expense_is_en or expense_spend_en)

        if expense_match:
            # Initialize variables
            category_text = ""
            amount = 0

            if expense_match == expense_match_vi:
                # Extract category and amount from the command (Vietnamese)
                category_text = expense_match_vi.group(1).strip()
                amount = int(expense_match_vi.group(2))
            elif expense_match == alt_expense_match_vi:
                # Alternative Vietnamese command (amount first, then category)
                amount = int(alt_expense_match_vi.group(1))
                category_text = alt_expense_match_vi.group(2).strip()
            elif expense_match == direct_expense_match_vi:
                # Direct Vietnamese command (category first, then amount)
                category_text = direct_expense_match_vi.group(1).strip()
                amount = int(direct_expense_match_vi.group(2))
            elif expense_match == simple_expense_vi:
                # Simple Vietnamese command (just category and amount)
                category_text = simple_expense_vi.group(1).strip()
                amount = int(simple_expense_vi.group(2))
            elif expense_match == very_simple_expense_vi:
                # Very simple Vietnamese command (no space between category and amount)
                category_text = very_simple_expense_vi.group(1).strip()
                amount = int(very_simple_expense_vi.group(2))
            elif expense_match == expense_la_vi:
                # Vietnamese command with "là" (is)
                category_text = expense_la_vi.group(1).strip()
                amount = int(expense_la_vi.group(2))
            elif expense_match == expense_chi_vi:
                # Vietnamese command with "chi" (spend)
                category_text = expense_chi_vi.group(1).strip()
                amount = int(expense_chi_vi.group(2))
            elif expense_match == expense_match_en:
                # Extract category and amount from the command (English)
                category_type = expense_match_en.group(1).strip()  # expense, cost, etc.
                category_text = expense_match_en.group(2).strip()
                amount = int(expense_match_en.group(3))
            elif expense_match == direct_expense_match_en:
                # Direct English command (category first, then amount)
                category_text = direct_expense_match_en.group(1).strip()
                amount = int(direct_expense_match_en.group(2))
            elif expense_match == simple_expense_en:
                # Simple English command (just category and amount)
                category_text = simple_expense_en.group(1).strip()
                amount = int(simple_expense_en.group(2))
            elif expense_match == very_simple_expense_en:
                # Very simple English command (no space between category and amount)
                category_text = very_simple_expense_en.group(1).strip()
                amount = int(very_simple_expense_en.group(2))
            elif expense_match == expense_is_en:
                # English command with "is"
                category_text = expense_is_en.group(1).strip()
                amount = int(expense_is_en.group(2))
            elif expense_match == expense_spend_en:
                # English command with "spend" or "pay"
                category_text = expense_spend_en.group(3).strip()
                amount = int(expense_spend_en.group(4))

            # Map the category text to one of the predefined categories
            category = 'Other'  # Default

            # Check for Vietnamese terms
            if 'thực phẩm' in category_text or 'ăn' in category_text:
                category = 'Food'
            elif 'giáo dục' in category_text or 'học' in category_text:
                category = 'Education'
            elif 'giải trí' in category_text:
                category = 'Entertainment'
            elif 'di chuyển' in category_text or 'xe' in category_text:
                category = 'Transport'

            # Check for English terms
            elif 'food' in category_text or 'meal' in category_text or 'grocery' in category_text:
                category = 'Food'
            elif 'education' in category_text or 'school' in category_text or 'course' in category_text:
                category = 'Education'
            elif 'entertainment' in category_text or 'movie' in category_text or 'game' in category_text:
                category = 'Entertainment'
            elif 'transport' in category_text or 'travel' in category_text or 'car' in category_text:
                category = 'Transport'

            # Create and save the expense
            expense = Expense(
                user=request.user,
                amount=amount,
                category=category,
                date=now().date()
            )
            expense.save()

            # Prepare response message based on language
            message = ""
            if expense_match == expense_match_vi:
                message = f"Đã thêm khoản chi tiêu {category_text} với số tiền {amount}"
            else:
                message = f"Added {category_text} expense with amount {amount}"

            return JsonResponse({
                "success": True,
                "message": message,
                "action": "expense_added",
                "data": {
                    "category": category,
                    "amount": amount,
                    "date": now().date().isoformat()
                }
            })

        # Handle delete income by ID
        delete_income_match = delete_income_match_vi or delete_income_match_en

        if delete_income_match:
            income_id = int(delete_income_match.group(1))
            try:
                income = get_object_or_404(Income, pk=income_id, user=request.user)
                source = income.source
                amount = income.amount
                income.delete()

                # Prepare response message based on language
                message = ""
                if delete_income_match == delete_income_match_vi:
                    message = f"Đã xóa khoản thu nhập {source} với số tiền {amount}"
                else:
                    message = f"Deleted income {source} with amount {amount}"

                return JsonResponse({
                    "success": True,
                    "message": message,
                    "action": "income_deleted",
                    "data": {
                        "id": income_id
                    }
                })
            except Exception as e:
                # Prepare error message based on language
                error_message = ""
                if delete_income_match == delete_income_match_vi:
                    error_message = f"Không thể xóa khoản thu nhập với ID {income_id}: {str(e)}"
                else:
                    error_message = f"Could not delete income with ID {income_id}: {str(e)}"

                return JsonResponse({
                    "success": False,
                    "message": error_message,
                    "action": "error"
                })

        # Handle delete expense by ID
        delete_expense_match = delete_expense_match_vi or delete_expense_match_en

        if delete_expense_match:
            expense_id = int(delete_expense_match.group(1))
            try:
                expense = get_object_or_404(Expense, pk=expense_id, user=request.user)
                category = expense.category
                amount = expense.amount
                expense.delete()

                # Prepare response message based on language
                message = ""
                if delete_expense_match == delete_expense_match_vi:
                    message = f"Đã xóa khoản chi tiêu {category} với số tiền {amount}"
                else:
                    message = f"Deleted expense {category} with amount {amount}"

                return JsonResponse({
                    "success": True,
                    "message": message,
                    "action": "expense_deleted",
                    "data": {
                        "id": expense_id
                    }
                })
            except Exception as e:
                # Prepare error message based on language
                error_message = ""
                if delete_expense_match == delete_expense_match_vi:
                    error_message = f"Không thể xóa khoản chi tiêu với ID {expense_id}: {str(e)}"
                else:
                    error_message = f"Could not delete expense with ID {expense_id}: {str(e)}"

                return JsonResponse({
                    "success": False,
                    "message": error_message,
                    "action": "error"
                })

        # Handle delete last income
        delete_last_income_match = delete_last_income_match_vi or delete_last_income_match_en

        if delete_last_income_match:
            try:
                # Get the most recent income
                income = Income.objects.filter(user=request.user).order_by('-date', '-id').first()
                if income:
                    source = income.source
                    amount = income.amount
                    income_id = income.id
                    income.delete()

                    # Prepare response message based on language
                    message = ""
                    if delete_last_income_match == delete_last_income_match_vi:
                        message = f"Đã xóa khoản thu nhập gần nhất: {source} với số tiền {amount}"
                    else:
                        message = f"Deleted latest income: {source} with amount {amount}"

                    return JsonResponse({
                        "success": True,
                        "message": message,
                        "action": "income_deleted",
                        "data": {
                            "id": income_id
                        }
                    })
                else:
                    # Prepare error message based on language
                    error_message = ""
                    if delete_last_income_match == delete_last_income_match_vi:
                        error_message = "Không tìm thấy khoản thu nhập nào để xóa"
                    else:
                        error_message = "No income found to delete"

                    return JsonResponse({
                        "success": False,
                        "message": error_message,
                        "action": "error"
                    })
            except Exception as e:
                # Prepare error message based on language
                error_message = ""
                if delete_last_income_match == delete_last_income_match_vi:
                    error_message = f"Không thể xóa khoản thu nhập gần nhất: {str(e)}"
                else:
                    error_message = f"Could not delete latest income: {str(e)}"

                return JsonResponse({
                    "success": False,
                    "message": error_message,
                    "action": "error"
                })

        # Handle delete last expense
        delete_last_expense_match = delete_last_expense_match_vi or delete_last_expense_match_en

        if delete_last_expense_match:
            try:
                # Get the most recent expense
                expense = Expense.objects.filter(user=request.user).order_by('-date', '-id').first()
                if expense:
                    category = expense.category
                    amount = expense.amount
                    expense_id = expense.id
                    expense.delete()

                    # Prepare response message based on language
                    message = ""
                    if delete_last_expense_match == delete_last_expense_match_vi:
                        message = f"Đã xóa khoản chi tiêu gần nhất: {category} với số tiền {amount}"
                    else:
                        message = f"Deleted latest expense: {category} with amount {amount}"

                    return JsonResponse({
                        "success": True,
                        "message": message,
                        "action": "expense_deleted",
                        "data": {
                            "id": expense_id
                        }
                    })
                else:
                    # Prepare error message based on language
                    error_message = ""
                    if delete_last_expense_match == delete_last_expense_match_vi:
                        error_message = "Không tìm thấy khoản chi tiêu nào để xóa"
                    else:
                        error_message = "No expense found to delete"

                    return JsonResponse({
                        "success": False,
                        "message": error_message,
                        "action": "error"
                    })
            except Exception as e:
                # Prepare error message based on language
                error_message = ""
                if delete_last_expense_match == delete_last_expense_match_vi:
                    error_message = f"Không thể xóa khoản chi tiêu gần nhất: {str(e)}"
                else:
                    error_message = f"Could not delete latest expense: {str(e)}"

                return JsonResponse({
                    "success": False,
                    "message": error_message,
                    "action": "error"
                })

        # Check for read financial report command (both Vietnamese and English)
        elif any(phrase in command for phrase in [
            "đọc báo cáo", "đọc kết quả", "đọc chi tiêu", "đọc thu nhập", "đọc tài chính", "đọc tình hình", "đọc tóm tắt",
            "đọc to báo cáo", "đọc cho tôi báo cáo", "đọc thông tin tài chính", "đọc tổng quan", "đọc tổng kết",
            "read report", "read financial report", "read summary", "read finances", "read income", "read expense",
            "read financial summary", "read overview", "read financial status", "read financial situation", "read aloud report"
        ]):
            # Get financial summary
            summary = get_financial_summary_text(request.user)

            # Prepare response message based on language
            message = ""
            if any(term in command for term in ["đọc", "đọc to", "đọc cho"]):
                message = "Đang đọc báo cáo tài chính"
            else:
                message = "Reading financial report"

            return JsonResponse({
                "success": True,
                "message": message,
                "action": "read_report",
                "text": summary
            })

        # Handle navigation commands (both Vietnamese and English)
        # Add Income
        elif any(phrase in command for phrase in [
            "thêm thu nhập", "thêm khoản thu", "đi đến thêm thu nhập", "mở thêm thu nhập", "chuyển đến thêm thu nhập",
            "add income", "new income", "go to add income", "open add income", "navigate to add income"
        ]):
            return JsonResponse({"action": "navigate", "url": "/add_income"})

        # Add Expense
        elif any(phrase in command for phrase in [
            "thêm chi tiêu", "thêm khoản chi", "đi đến thêm chi tiêu", "mở thêm chi tiêu", "chuyển đến thêm chi tiêu",
            "add expense", "new expense", "go to add expense", "open add expense", "navigate to add expense"
        ]):
            return JsonResponse({"action": "navigate", "url": "/add_expense"})

        # Financial Report
        elif any(phrase in command for phrase in [
            "báo cáo", "xem báo cáo", "đi đến báo cáo", "mở báo cáo", "chuyển đến báo cáo", "xem tài chính",
            "financial report", "view report", "show report", "go to report", "open report", "navigate to report", "view finance"
        ]):
            return JsonResponse({"action": "navigate", "url": "/financial_report"})

        # Home
        elif any(phrase in command for phrase in [
            "trang chủ", "về trang chủ", "đi đến trang chủ", "mở trang chủ", "chuyển đến trang chủ", "quay về trang chủ",
            "home", "go home", "main page", "go to home", "open home", "navigate to home", "return home"
        ]):
            return JsonResponse({"action": "navigate", "url": "/"})

        # Forecast
        elif any(phrase in command for phrase in [
            "dự báo", "đi đến dự báo", "mở dự báo", "chuyển đến dự báo", "xem dự báo", "dự đoán",
            "forecast", "prediction", "financial forecast", "go to forecast", "open forecast", "navigate to forecast", "view forecast"
        ]):
            return JsonResponse({"action": "navigate", "url": "/forecast_finance"})

        # Account
        elif any(phrase in command for phrase in [
            "tài khoản", "đi đến tài khoản", "mở tài khoản", "chuyển đến tài khoản", "thông tin cá nhân", "hồ sơ",
            "account", "profile", "my account", "settings", "go to account", "open account", "navigate to account", "user profile"
        ]):
            return JsonResponse({"action": "navigate", "url": "/account"})

        # Return a message that the command was not recognized (in both Vietnamese and English)
        return JsonResponse({
            "success": False,
            "message": "Không nhận diện được lệnh. Vui lòng thử lại với các lệnh như: 'lương 100', 'thực phẩm 200', 'thêm thu nhập', 'thêm chi tiêu', 'báo cáo', 'trang chủ', 'dự báo', 'đọc báo cáo'. (Command not recognized. Please try again with commands like: 'salary 100', 'food 200', 'add income', 'add expense', 'report', 'home', 'forecast', 'read report'.)",
            "action": "error"
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# Global variable to store the transcribed text context
speech_to_text_context = ""

HF_ASR_MODEL = "openai/whisper-large-v3"
def speech_to_text(request):
    """
    Convert base64-encoded audio to text using Hugging Face ASR model.
    """
    global speech_to_text_context

    try:
        data = json.loads(request.body)
        audio_data = data.get("audio")
        if not audio_data:
            return JsonResponse({"error": "No audio data provided"}, status=400)

        # Remove base64 prefix if exists
        if "base64," in audio_data:
            audio_data = audio_data.split("base64,")[1]

        audio_bytes = base64.b64decode(audio_data)

        # Set appropriate content type (assume audio is wav; adjust if needed)
        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "audio/wav"  # hoặc audio/mpeg nếu là mp3
        }

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_ASR_MODEL}",
            headers=headers,
            data=audio_bytes,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "")
            speech_to_text_context = text

            # Gọi xử lý command (nếu có)
            mock_request = request
            mock_request._body = json.dumps({"command": text}).encode("utf-8")
            command_response = process_voice_command(mock_request)
            response_data = json.loads(command_response.content)
            response_data["text"] = text
            response_data["success"] = True
            return JsonResponse(response_data)

        else:
            return JsonResponse({
                "success": False,
                "error": f"Hugging Face API error: {response.status_code} {response.text}"
            }, status=500)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)