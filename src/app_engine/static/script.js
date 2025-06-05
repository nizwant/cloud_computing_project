const fileInput = document.getElementById('file-input');

if (fileInput) {
  fileInput.addEventListener('change', function () {
    const file = fileInput.files[0];
    if (file) {
      uploadAudioFile(file);
    }
  });
}

function uploadAudioFile(file) {
  const formData = new FormData();
  formData.append('audio_file', file);

  fetch('/identify', {
    method: 'POST',
    body: formData,
  }).then(response => response.json())
    .then(data => {
      console.log('Server response:', data);
      // Handle result here
    }).catch(error => {
      console.error('Error:', error);
    });
}

let mediaRecorder;
let audioChunks = [];

window.startRecording = function (){
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.start();
      document.getElementById('recording-status').style.display = 'block';

      mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        audioChunks = [];
        document.getElementById('recording-status').style.display = 'none';
        uploadAudioFile(audioBlob);
      };

      setTimeout(() => {
        mediaRecorder.stop();
      }, 5000);
    })
    .catch(err => {
      console.error('Microphone error:', err);
      alert('Microphone access is required to record audio.');
    });
}
