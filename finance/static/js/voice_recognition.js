document.addEventListener('DOMContentLoaded', function () {
    const micButton = document.getElementById('mic-button');
    const voiceResult = document.getElementById('voice-result');

    // Add Font Awesome for microphone icon if not already included
    const fa = document.createElement('link');
    fa.rel = 'stylesheet';
    fa.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css';
    document.head.appendChild(fa);

    // Variables for audio recording
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let recognition = null;
    let useServerSpeechToText = true; // Flag to use server-side speech-to-text
    let silenceTimer = null;
    const silenceTimeout = 2000; // 2 seconds of silence before auto-stopping
    let audioContext = null;
    let analyser = null;
    let silenceDetectionStream = null;

    // Check if browser supports MediaRecorder for advanced audio recording
    const hasMediaRecorder = 'MediaRecorder' in window;

    // Fallback: Check if browser supports speech recognition
    const hasSpeechRecognition = 'webkitSpeechRecognition' in window;

    if (!hasMediaRecorder && !hasSpeechRecognition) {
        micButton.disabled = true;
        micButton.title = 'Your browser does not support voice recognition';
        voiceResult.style.display = 'block';
        voiceResult.textContent = 'Your browser does not support voice recognition. Please use Chrome or Edge.';
        return;
    }

    // Initialize speech recognition (fallback method)
    function initRecognition() {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true; // Changed to true to get interim results for silence detection
        // Set language to Vietnamese for better recognition
        recognition.lang = 'vi-VN';

        // Set up silence detection for speech recognition
        let lastResultTimestamp = Date.now();

        // Function to check for silence based on time since last result
        const checkSilence = () => {
            if (!isRecording || !recognition) return;

            const now = Date.now();
            const timeSinceLastResult = now - lastResultTimestamp;

            // If no speech detected for the silence timeout, stop recording
            if (timeSinceLastResult > silenceTimeout) {
                if (isRecording && recognition) {
                    recognition.stop();
                }
                return;
            }

            // Continue checking for silence
            silenceTimer = setTimeout(checkSilence, 500);
        };

        recognition.onstart = function () {
            micButton.classList.add('recording');
            micButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            micButton.title = 'Recording...';
            voiceResult.style.display = 'block';
            voiceResult.textContent = 'Listening... Please speak your command';

            // Start silence detection
            lastResultTimestamp = Date.now();
            silenceTimer = setTimeout(checkSilence, 500);
        };

        recognition.onend = function () {
            // Clear silence timer
            if (silenceTimer) {
                clearTimeout(silenceTimer);
                silenceTimer = null;
            }

            micButton.classList.remove('recording');
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            micButton.title = 'Press the button or "m" key to start/stop recording';
            recognition = null;
            isRecording = false;
        };

        recognition.onerror = function (event) {
            console.error('Recording error:', event.error);
        };

        recognition.onresult = function (event) {
            // Update the timestamp whenever we get a result (including interim)
            lastResultTimestamp = Date.now();

            // Only process final results
            if (event.results[0].isFinal) {
                const transcript = event.results[0][0].transcript;
                voiceResult.textContent = `You said: ${transcript}`;
                processVoiceCommand(transcript);
            }
        };
    }

    // Initialize media recorder for high-quality audio recording
    async function initMediaRecorder() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Set up silence detection
            if (window.AudioContext || window.webkitAudioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioContext.createAnalyser();
                silenceDetectionStream = stream;

                const microphone = audioContext.createMediaStreamSource(stream);
                microphone.connect(analyser);

                analyser.fftSize = 256;
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);

                // Function to detect silence
                const detectSilence = () => {
                    if (!isRecording) return;

                    analyser.getByteFrequencyData(dataArray);

                    // Calculate average volume
                    let sum = 0;
                    for (let i = 0; i < bufferLength; i++) {
                        sum += dataArray[i];
                    }
                    const average = sum / bufferLength;

                    // If volume is below threshold, consider it silence
                    if (average < 10) { // Adjust threshold as needed
                        if (!silenceTimer) {
                            silenceTimer = setTimeout(() => {
                                // Auto-stop recording after silence timeout
                                if (isRecording) {
                                    handleRecordingToggle();
                                }
                            }, silenceTimeout);
                        }
                    } else {
                        // Reset silence timer if sound is detected
                        if (silenceTimer) {
                            clearTimeout(silenceTimer);
                            silenceTimer = null;
                        }
                    }

                    // Continue checking for silence
                    requestAnimationFrame(detectSilence);
                };

                // Start silence detection
                detectSilence();
            }

            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                // Clear any pending silence timer
                if (silenceTimer) {
                    clearTimeout(silenceTimer);
                    silenceTimer = null;
                }

                // Create audio blob from chunks
                const audioBlob = new Blob(audioChunks, { type: 'audio/mp4' });

                // Show processing message
                voiceResult.textContent = 'Processing audio...';

                // Convert to base64 for sending to server
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = async function() {
                    const base64Audio = reader.result;
                    await sendAudioToServer(base64Audio);
                };
            };

            return true;
        } catch (error) {
            console.error('Media recorder initialization error:', error);
            return false;
        }
    }

    // Send audio to server for speech-to-text processing
    async function sendAudioToServer(audioData) {
        try {
            const response = await fetch('/speech_to_text/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ audio: audioData })
            });

            const data = await response.json();

            if (data.success) {
                // Successfully transcribed and processed
                voiceResult.textContent = `You said: ${data.text}`;

                // Handle the response directly since it's already processed by the server
                if (data.action === "navigate") {
                    voiceResult.textContent = `Navigating to: ${data.url}`;
                    setTimeout(() => window.location.href = data.url, 1000);
                } else if (data.action === "read_report") {
                    voiceResult.textContent = "Reading financial report...";

                    // If we're not on the financial report page, navigate to it
                    if (!window.location.pathname.includes('financial_report')) {
                        setTimeout(() => window.location.href = "/financial_report/", 1000);
                    } else {
                        // If we're already on the financial report page, read the text directly
                        readTextWithSpeechSynthesis(data.text);
                    }
                } else if (data.action === "income_added" || data.action === "expense_added" || 
                           data.action === "income_deleted" || data.action === "expense_deleted") {
                    voiceResult.textContent = data.message;
                    // Show success notification
                    showNotification('Thành công', data.message, 'success');
                    // Redirect to the financial report page
                    setTimeout(() => window.location.href = "/financial_report/", 2000);
                } else if (data.action === "error") {
                    voiceResult.textContent = data.message;
                    showNotification('Error', data.message, 'error');
                } else if (data.error) {
                    voiceResult.textContent = `Lỗi: ${data.error}`;
                    showNotification('Lỗi', data.error, 'error');
                } else {
                    voiceResult.textContent += '\nKhông nhận diện được lệnh. Vui lòng thử lại. (Command not recognized. Please try again.)';
                }
            } else if (data.fallback && hasSpeechRecognition) {
                // Server failed but we can fallback to browser speech recognition
                voiceResult.textContent = 'Server speech recognition failed. Falling back to browser...';
                useServerSpeechToText = false;
                handleRecordingToggle();
            } else {
                // Complete failure
                voiceResult.textContent = `Speech recognition error: ${data.error}`;
            }
        } catch (error) {
            console.error('Server communication error:', error);
            voiceResult.textContent = 'Error communicating with the server. Falling back to browser...';

            // Fallback to browser speech recognition if available
            if (hasSpeechRecognition) {
                useServerSpeechToText = false;
                handleRecordingToggle();
            }
        }
    }

    // Handle recording toggle (start/stop)
    async function handleRecordingToggle() {
        if (isRecording) {
            // Stop recording
            if (useServerSpeechToText && mediaRecorder) {
                mediaRecorder.stop();
                voiceResult.textContent = 'Recording stopped. Processing...';
            } else if (recognition) {
                recognition.stop();
                voiceResult.textContent = 'Recording stopped. Processing...';
            }

            // Clean up silence detection
            if (silenceTimer) {
                clearTimeout(silenceTimer);
                silenceTimer = null;
            }

            micButton.classList.remove('recording');
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
            isRecording = false;

        } else {
            // Start recording
            if (useServerSpeechToText && hasMediaRecorder) {
                // Try to use server-side speech recognition first
                const initialized = await initMediaRecorder();

                if (initialized) {
                    micButton.classList.add('recording');
                    micButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
                    micButton.title = 'Recording...';
                    voiceResult.style.display = 'block';
                    voiceResult.textContent = 'Listening... Please speak your command';

                    mediaRecorder.start();
                    isRecording = true;
                } else if (hasSpeechRecognition) {
                    // Fallback to browser speech recognition
                    useServerSpeechToText = false;
                    initRecognition();
                    recognition.start();
                    isRecording = true;
                }
            } else if (hasSpeechRecognition) {
                // Use browser speech recognition
                initRecognition();
                try {
                    recognition.start();
                    isRecording = true;
                } catch (error) {
                    console.error('Start error:', error);
                }
            }
        }
    }

    // Nhấn phím "m" để bật/tắt thu âm
    document.addEventListener('keydown', function (event) {
        if (event.key === 'm' || event.key === 'M') {
            handleRecordingToggle();
        }
    });

    micButton.title = 'Press the button or "m" key to start/stop recording';

    async function processVoiceCommand(command) {
        try {
            voiceResult.textContent = 'Processing command...';
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
                voiceResult.textContent = `Navigating to: ${data.url}`;
                setTimeout(() => window.location.href = data.url, 1000);
            } else if (data.action === "read_report") {
                voiceResult.textContent = "Reading financial report...";

                // If we're not on the financial report page, navigate to it
                if (!window.location.pathname.includes('financial_report')) {
                    setTimeout(() => window.location.href = "/financial_report/", 1000);
                } else {
                    // If we're already on the financial report page, read the text directly
                    readTextWithSpeechSynthesis(data.text);
                }
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
            } else if (data.action === "error") {
                voiceResult.textContent = data.message;
                showNotification('Error', data.message, 'error');
            } else if (data.error) {
                voiceResult.textContent = `Lỗi: ${data.error}`;
                showNotification('Lỗi', data.error, 'error');
            } else {
                voiceResult.textContent += '\nKhông nhận diện được lệnh. Vui lòng thử lại. (Command not recognized. Please try again.)';
            }
        } catch (error) {
            console.error('Voice command error:', error);
            voiceResult.textContent = 'An error occurred while processing the command. Please try again.';
        }
    }

    // Add click event to the mic button
    micButton.addEventListener('click', handleRecordingToggle);

    // Helper function to get CSRF token from cookies
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

    // Function to read text using the browser's speech synthesis API
    function readTextWithSpeechSynthesis(text) {
        // Check if speech synthesis is supported
        if ('speechSynthesis' in window) {
            // Create a new speech synthesis utterance
            const utterance = new SpeechSynthesisUtterance(text);

            // Set language to Vietnamese (if available) or English
            utterance.lang = 'vi-VN';

            // Optional: adjust speech rate and pitch
            utterance.rate = 1.0;  // Normal speed
            utterance.pitch = 1.0; // Normal pitch

            // Speak the text
            window.speechSynthesis.speak(utterance);

            // Show a message that the text is being read
            voiceResult.textContent = 'Reading financial report...';

            // When the speech is done
            utterance.onend = function() {
                voiceResult.textContent = 'Finished reading financial report.';
            };

            // If there's an error
            utterance.onerror = function(event) {
                console.error('Speech synthesis error:', event);
                voiceResult.textContent = 'Error reading financial report.';
            };
        } else {
            // Speech synthesis not supported
            voiceResult.textContent = 'Speech synthesis is not supported in your browser.';
            console.error('Speech synthesis not supported');
        }
    }

    // Function to show notifications
    function showNotification(title, message, type) {
        // Check if we have a notification system
        if (typeof Toastify === 'function') {
            Toastify({
                text: message,
                duration: 3000,
                close: true,
                gravity: "top",
                position: "right",
                backgroundColor: type === 'success' ? "#4CAF50" : "#F44336",
            }).showToast();
        } else {
            // Fallback to alert if Toastify is not available
            alert(`${title}: ${message}`);
        }
    }
});