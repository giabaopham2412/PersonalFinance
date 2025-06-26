document.addEventListener('DOMContentLoaded', function() {
    // Get data from the page - safely parse JSON with error handling
    function safeJSONParse(elementId) {
        try {
            const value = document.getElementById(elementId).value;
            return JSON.parse(value);
        } catch (error) {
            console.error(`Error parsing JSON from ${elementId}:`, error);
            console.log('Value that failed to parse:', document.getElementById(elementId).value);
            // Return a safe default value based on the expected data type
            return elementId.includes('months') ? [] : [0];
        }
    }

    const months = safeJSONParse('months-data');
    const incomeValues = safeJSONParse('income-values-data');
    const expenseValues = safeJSONParse('expense-values-data');
    const predictedIncome = safeJSONParse('predicted-income-data');
    const predictedExpense = safeJSONParse('predicted-expense-data');

    // Draw actual chart (income and expense)
    const actualCtx = document.getElementById('actualChart').getContext('2d');
    const actualChart = new Chart(actualCtx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Thu Nhập Thực Tế',
                    data: incomeValues,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                },
                {
                    label: 'Chi Tiêu Thực Tế',
                    data: expenseValues,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    enabled: true,
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Tháng',
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: 'Số Tiền (VND)',
                    },
                    beginAtZero: true,
                },
            },
        },
    });

    // Draw forecast chart (actual and predicted income/expense)
    const forecastCtx = document.getElementById('forecastChart').getContext('2d');
    const forecastChart = new Chart(forecastCtx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Thu Nhập Thực Tế',
                    data: incomeValues,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                },
                {
                    label: 'Chi Tiêu Thực Tế',
                    data: expenseValues,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                },
                {
                    label: 'Dự Báo Thu Nhập (AI)',
                    data: predictedIncome,
                    borderColor: 'rgba(0, 255, 0, 1)',
                    backgroundColor: 'rgba(0, 255, 0, 0.2)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                },
                {
                    label: 'Dự Báo Chi Tiêu (AI)',
                    data: predictedExpense,
                    borderColor: 'rgba(255, 165, 0, 1)',
                    backgroundColor: 'rgba(255, 165, 0, 0.2)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    enabled: true,
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Tháng',
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: 'Số Tiền (VND)',
                    },
                    beginAtZero: true,
                },
            },
        },
    });
});