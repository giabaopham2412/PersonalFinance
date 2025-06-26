// Base functionality for the entire application

// Toggle chat popup visibility
function toggleChat() {
    const popup = document.getElementById("chat-popup");
    popup.style.display = (popup.style.display === "none" || popup.style.display === "") ? "block" : "none";
}

// Send message to the chat AI
function sendMessage() {
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";

    const chatBody = document.getElementById("chat-body");
    chatBody.innerHTML += `<div><strong>Bạn:</strong> ${message}</div>`;

    // Add a loading message
    const loadingId = 'loading-' + Date.now();
    chatBody.innerHTML += `<div id="${loadingId}"><strong>AI:</strong><br>Đang xử lý...</div>`;
    chatBody.scrollTop = chatBody.scrollHeight;

    // Get the CSRF token from the cookie
    const csrftoken = getCookie('csrftoken');

    fetch("/ask/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken
        },
        body: JSON.stringify({
            message,
            financial_data: {
                total_income: document.getElementById("total-income") ? document.getElementById("total-income").value : "0",
                total_expense: document.getElementById("total-expense") ? document.getElementById("total-expense").value : "0",
                balance: document.getElementById("balance") ? document.getElementById("balance").value : "0"
            }
        })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP error! Status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        // Remove the loading message
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }

        // Check if response exists
        const responseText = data && data.response ? data.response : "Không nhận được phản hồi từ máy chủ. Vui lòng thử lại.";
        chatBody.innerHTML += `<div><strong>AI:</strong><br>${responseText.replace(/\n/g, '<br>')}</div>`;
        chatBody.scrollTop = chatBody.scrollHeight;
    })
    .catch(error => {
        // Remove the loading message
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }

        console.error('Error:', error);
        chatBody.innerHTML += `<div><strong>AI:</strong><br>Đã xảy ra lỗi: ${error.message}. Vui lòng thử lại.</div>`;
        chatBody.scrollTop = chatBody.scrollHeight;
    });
}

// Utility function to get cookie by name (for CSRF token)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Function to show notifications
function showNotification(title, message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <strong>${title}</strong>
        <p>${message}</p>
    `;

    // Add styles
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '15px';
    notification.style.borderRadius = '5px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '300px';

    if (type === 'success') {
        notification.style.backgroundColor = '#4CAF50';
        notification.style.color = 'white';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#f44336';
        notification.style.color = 'white';
    }

    // Add to document
    document.body.appendChild(notification);

    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.5s';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 5000);
}

// Function to read text using speech synthesis
function readTextWithSpeechSynthesis(text) {
    if ('speechSynthesis' in window) {
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

        // Speak the text
        window.speechSynthesis.speak(speech);
    } else {
        console.error('Speech synthesis not supported');
        showNotification('Lỗi', 'Trình duyệt không hỗ trợ đọc báo cáo', 'error');
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listener for Enter key in chat input
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });
    }
});