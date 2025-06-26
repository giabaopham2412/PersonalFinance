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
            return elementId.includes('categories') || elementId.includes('months') ? [] : [0];
        }
    }

    const months = safeJSONParse('months-data');
    const incomeValues = safeJSONParse('income-values-data');
    const expenseValues = safeJSONParse('expense-values-data');
    const incomeCategories = safeJSONParse('income-categories-data');
    const incomeTotals = safeJSONParse('income-totals-data');
    const expenseCategories = safeJSONParse('expense-categories-data');
    const expenseTotals = safeJSONParse('expense-totals-data');
    const dailyIncomeDays = safeJSONParse('daily-income-days-data');
    const dailyIncomeTotals = safeJSONParse('daily-income-totals-data');
    const dailyExpenseDays = safeJSONParse('daily-expense-days-data');
    const dailyExpenseTotals = safeJSONParse('daily-expense-totals-data');
    const financialSummary = safeJSONParse('financial-summary-data');

    // Function to generate random colors for charts
    function generateRandomColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const r = Math.floor(Math.random() * 255);
            const g = Math.floor(Math.random() * 255);
            const b = Math.floor(Math.random() * 255);
            colors.push(`rgba(${r}, ${g}, ${b}, 0.6)`); 
        }
        return colors;
    }

    // Draw Daily Income Chart
    const dailyIncomeCtx = document.getElementById('dailyIncomeChart').getContext('2d');
    new Chart(dailyIncomeCtx, {
        type: 'bar',
        data: {
            labels: dailyIncomeDays,
            datasets: [{
                label: 'Thu Nhập Theo Ngày',
                data: dailyIncomeTotals,
                backgroundColor: generateRandomColors(dailyIncomeTotals.length),
                borderColor: generateRandomColors(dailyIncomeTotals.length),
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Số Tiền (VND)',
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày',
                    }
                }
            }
        }
    });

    // Draw Daily Expense Chart
    const dailyExpenseCtx = document.getElementById('dailyExpenseChart').getContext('2d');
    new Chart(dailyExpenseCtx, {
        type: 'bar',
        data: {
            labels: dailyExpenseDays,
            datasets: [{
                label: 'Chi Tiêu Theo Ngày',
                data: dailyExpenseTotals,
                backgroundColor: generateRandomColors(dailyExpenseTotals.length),
                borderColor: generateRandomColors(dailyExpenseTotals.length),
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Số Tiền (VND)',
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày',
                    }
                }
            }
        }
    });

    // Draw Income Bar Chart
    const incomeBarCtx = document.getElementById('incomeBarChart').getContext('2d');
    new Chart(incomeBarCtx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [{
                label: 'Thu Nhập Theo Tháng',
                data: incomeValues,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Số Tiền (VND)',
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Tháng',
                    }
                }
            }
        }
    });

    // Draw Expense Bar Chart
    const expenseBarCtx = document.getElementById('expenseBarChart').getContext('2d');
    new Chart(expenseBarCtx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [{
                label: 'Chi Tiêu Theo Tháng',
                data: expenseValues,
                backgroundColor: 'rgba(255, 99, 132, 0.6)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Số Tiền (VND)',
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Tháng',
                    }
                }
            }
        }
    });

    // Draw Income Pie Chart
    const incomePieCtx = document.getElementById('incomePieChart').getContext('2d');
    new Chart(incomePieCtx, {
        type: 'pie',
        data: {
            labels: incomeCategories,
            datasets: [{
                data: incomeTotals,
                backgroundColor: generateRandomColors(incomeCategories.length),
                borderWidth: 1
            }]
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
        }
    });

    // Draw Expense Pie Chart
    const expensePieCtx = document.getElementById('expensePieChart').getContext('2d');
    new Chart(expensePieCtx, {
        type: 'pie',
        data: {
            labels: expenseCategories,
            datasets: [{
                data: expenseTotals,
                backgroundColor: generateRandomColors(expenseCategories.length),
                borderWidth: 1
            }]
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
        }
    });

    // Text-to-Speech functionality
    const readReportBtn = document.getElementById('read-report-btn');

    // Check if the browser supports speech synthesis
    if ('speechSynthesis' in window) {
        // Add click event listener to the button
        readReportBtn.addEventListener('click', function() {
            readFinancialReport(financialSummary);
        });
    } else {
        // If speech synthesis is not supported, disable the button
        readReportBtn.disabled = true;
        readReportBtn.innerHTML = 'Trình duyệt không hỗ trợ đọc báo cáo';
    }

    // Function to read the financial report
    function readFinancialReport(text) {
        // Create a new SpeechSynthesisUtterance object
        const speech = new SpeechSynthesisUtterance();

        // Set the text and language
        speech.text = text;
        speech.lang = 'vi-VN';
        speech.rate = 1.0;
        speech.pitch = 1.0;
        speech.volume = 1.0;

        // Get available voices
        const voices = window.speechSynthesis.getVoices();

        // Try to find a Vietnamese voice
        let vietnameseVoice = voices.find(voice => voice.lang.includes('vi'));

        // If no Vietnamese voice is found, use the default voice
        if (vietnameseVoice) {
            speech.voice = vietnameseVoice;
        }

        // Update the button to show that it's speaking
        readReportBtn.innerHTML = '<i class="fas fa-volume-up"></i> Đang đọc...';
        readReportBtn.disabled = true;

        // When the speech ends, reset the button
        speech.onend = function() {
            readReportBtn.innerHTML = '<i class="fas fa-volume-up"></i> Đọc Báo Cáo';
            readReportBtn.disabled = false;
        };

        // Speak the text
        window.speechSynthesis.speak(speech);
    }

    // Handle voice commands for reading the report
    document.addEventListener('voiceCommand', function(event) {
        const command = event.detail.command.toLowerCase();

        if (command.includes('đọc báo cáo') || command.includes('đọc kết quả') || command.includes('đọc chi tiêu')) {
            readFinancialReport(financialSummary);
        }
    });
});