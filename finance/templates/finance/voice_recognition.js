document.addEventListener('DOMContentLoaded', function () {
    const micButton = document.getElementById('mic-button');
    const voiceResult = document.getElementById('voice-result');

    const fa = document.createElement('link');
    fa.rel = 'stylesheet';
    fa.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css';
    document.head.appendChild(fa);

    if (!('webkitSpeechRecognition' in window)) {
        micButton.disabled = true;
        micButton.title = 'Trình duyệt không hỗ trợ nhận dạng giọng nói';
        voiceResult.style.display = 'block';
        voiceResult.textContent = 'Trình duyệt của bạn không hỗ trợ nhận dạng giọng nói. Vui lòng sử dụng Chrome hoặc Edge.';
        return;
    }

    let recognition = null;
    let isRecording = false;

    function initRecognition() {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'vi-VN';

        recognition.onstart = function () {
            micButton.classList.add('recording');
            micButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            micButton.title = 'Đang ghi âm...';
            voiceResult.style.display = 'block';
            voiceResult.textContent = 'Đang nghe... Hãy nói lệnh của bạn';
        };

        recognition.onend = function () {
            micButton.classList.remove('recording');
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            micButton.title = 'Nhấn vào nút hoặc phím "m" để bắt đầu/dừng ghi âm';
            recognition = null;
            isRecording = false;
        };

        recognition.onerror = function (event) {
            console.error('Recording error:', event.error);
        };

        recognition.onresult = function (event) {
            const transcript = event.results[0][0].transcript;
            voiceResult.textContent = `Bạn nói: ${transcript}`;
            processVoiceCommand(transcript);
        };
    }

    function handleRecordingToggle() {
        if (isRecording) {
            if (recognition) {
                recognition.stop();
                voiceResult.textContent = 'Đã dừng ghi âm. Đang xử lý...';
            }
        } else {
            initRecognition();
            try {
                recognition.start();
                isRecording = true;
            } catch (error) {
                console.error('Start error:', error);
            }
        }
    }

    // Nhấn phím "m" để bật/tắt thu âm
    document.addEventListener('keydown', function (event) {
        if (event.key === 'm' || event.key === 'M') {
            handleRecordingToggle();
        }
    });

    micButton.title = 'Nhấn vào nút hoặc phím "m" để bắt đầu/dừng ghi âm';

    async function processVoiceCommand(command) {
        try {
            voiceResult.textContent = 'Đang xử lý lệnh...';
            const response = await fetch("/process_voice_command/", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ command })
            });

            const data = await response.json();

            if (data.action === "navigate") {
                voiceResult.textContent = `Đang chuyển đến: ${data.url}`;
                setTimeout(() => window.location.href = data.url, 1000);
            } else if (data.action === "income_added") {
                voiceResult.textContent = data.message;
                // Show success notification
                showNotification('Thành công', data.message, 'success');
                // Refresh the page after 2 seconds to show the new data
                setTimeout(() => window.location.href = "/financial_report/", 2000);
            } else if (data.action === "expense_added") {
                voiceResult.textContent = data.message;
                // Show success notification
                showNotification('Thành công', data.message, 'success');
                // Refresh the page after 2 seconds to show the new data
                setTimeout(() => window.location.href = "/financial_report/", 2000);
            } else if (data.action === "income_deleted") {
                voiceResult.textContent = data.message;
                // Show success notification
                showNotification('Thành công', data.message, 'success');
                // Refresh the page after 2 seconds to show the new data
                setTimeout(() => window.location.href = "/financial_report/", 2000);
            } else if (data.action === "expense_deleted") {
                voiceResult.textContent = data.message;
                // Show success notification
                showNotification('Thành công', data.message, 'success');
                // Refresh the page after 2 seconds to show the new data
                setTimeout(() => window.location.href = "/financial_report/", 2000);
            } else if (data.action === "read_report") {
                voiceResult.textContent = "Đang đọc báo cáo tài chính...";

                // If we're not on the financial report page, navigate to it
                if (!window.location.pathname.includes('financial_report')) {
                    setTimeout(() => window.location.href = "/financial_report/", 1000);
                } else {
                    // If we're already on the financial report page, read the text directly
                    readTextWithSpeechSynthesis(data.text);
                }
            } else if (data.response) {
                voiceResult.textContent = `AI: ${data.response}`;
            } else if (data.error) {
                voiceResult.textContent = `Lỗi: ${data.error}`;
                showNotification('Lỗi', data.error, 'error');
            } else {
                voiceResult.textContent += '\nKhông nhận diện được lệnh. Vui lòng thử lại.';
            }
        } catch (error) {
            console.error('Voice command error:', error);
            voiceResult.textContent = 'Có lỗi xảy ra khi xử lý lệnh. Vui lòng thử lại.';
        }
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

    // Add click event to the mic button
    micButton.addEventListener('click', handleRecordingToggle);

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
});