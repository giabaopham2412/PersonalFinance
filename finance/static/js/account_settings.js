document.addEventListener('DOMContentLoaded', function() {
    // Get the form element
    const form = document.getElementById('account-settings-form');
    
    // Add event listener to the update button
    const updateButton = document.getElementById('update-button');
    if (updateButton) {
        updateButton.addEventListener('click', handleSubmit);
    }
    
    /**
     * Handle form submission via AJAX
     * @param {Event} event - The form submission event
     */
    function handleSubmit(event) {
        event.preventDefault();
        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update profile picture in the page
                document.getElementById('profile-picture').src = data.image_url;
                
                // Update profile picture in the navbar if it exists
                const navbarProfilePicture = document.getElementById('navbar-profile-picture');
                if (navbarProfilePicture) {
                    navbarProfilePicture.src = data.image_url;
                }
                
                // Show success message
                const messagesContainer = document.getElementById('messages');
                if (messagesContainer) {
                    messagesContainer.innerHTML = '<div class="alert alert-success" role="alert">' + data.message + '</div>';
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Show error message
            const messagesContainer = document.getElementById('messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = '<div class="alert alert-danger" role="alert">An error occurred. Please try again.</div>';
            }
        });
    }
});