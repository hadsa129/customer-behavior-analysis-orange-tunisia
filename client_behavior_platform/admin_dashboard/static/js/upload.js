let droppedFiles = false;
let fileName = '';
const dropzone = document.querySelector('.dropzone');
const button = document.querySelector('.upload-btn');
const syncing = document.querySelector('.syncing');
const done = document.querySelector('.done');
const bar = document.querySelector('.bar');
let timeoutID;

['drag', 'dragstart', 'dragend', 'dragover', 'dragenter', 'dragleave', 'drop'].forEach(event => {
    dropzone.addEventListener(event, function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
});

dropzone.addEventListener('dragover', function() {
    dropzone.classList.add('is-dragover');
});

['dragleave', 'dragend', 'drop'].forEach(event => {
    dropzone.addEventListener(event, function() {
        dropzone.classList.remove('is-dragover');
    });
});

dropzone.addEventListener('drop', function(e) {
    droppedFiles = e.dataTransfer.files;
    fileName = droppedFiles[0].name;
    document.querySelector('.filename').innerHTML = fileName;
    document.querySelector('.dropzone .upload').style.display = 'none';
});

button.addEventListener('click', function() {
    startUpload();
});

document.querySelector('input[type="file"]').addEventListener('change', function() {
    fileName = this.files[0].name;
    document.querySelector('.filename').innerHTML = fileName;
    document.querySelector('.dropzone .upload').style.display = 'none';
});

function startUpload() {
    if (!uploading && fileName !== '') {
        uploading = true;
        button.innerHTML = 'Uploading...';
        dropzone.style.display = 'none';
        syncing.classList.add('active');
        done.classList.remove('active'); // Ensure done is hidden during upload
        bar.classList.add('active');

        // Create FormData object and append the file
        const formData = new FormData();
        formData.append('file', droppedFiles[0]);

        // Make AJAX request to upload the file
        fetch('/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken') // Ensure CSRF token is sent with the request
                }
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    showDone();
                } else {
                    // Handle error
                    button.innerHTML = 'Upload Failed';
                    uploading = false;
                    syncing.classList.remove('active');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.innerHTML = 'Upload Failed';
                uploading = false;
                syncing.classList.remove('active');
            });
    }
}

function showDone() {
    button.innerHTML = 'Done';
    syncing.classList.remove('active');
    done.classList.add('active');
    bar.classList.remove('active');
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