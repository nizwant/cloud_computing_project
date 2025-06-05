const fileInput = document.getElementById('file-input');

if (fileInput) {
  fileInput.addEventListener('change', function () {
    const file = fileInput.files[0];
    if (file) {
      uploadAudioFile(file);
    }
  });
}

function uploadAudioFile(audioBlob) {
  const formData = new FormData();
  formData.append('audio_file', audioBlob, 'recording.wav');

  document.getElementById('loading-message').style.display = 'block';

  fetch('/identify', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (response.redirected) {
      window.location.href = response.url;
    } else {
      return response.json();
    }
  })
  .catch(err => {
    console.error('Error identifying song:', err);
    alert('An error occurred while identifying the song.');
  })
  .finally(() => {
    document.getElementById('loading-message').style.display = 'none';
  });
}

let mediaRecorder;
let audioChunks = [];

window.startRecording = function () {
  audioChunks = [];
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      mediaRecorder.start();
      document.getElementById('recording-status').style.display = 'block';

      mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        document.getElementById('recording-status').style.display = 'none';

        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        console.log("Duration approx (sec):", audioBlob.size / 48000 / 2); // crude estimate

        // Trigger a download
        const url = URL.createObjectURL(audioBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'recording.wav';  // You can change the filename here
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        uploadAudioFile(audioBlob);
      };

      // Stop recording after 10 seconds
      setTimeout(() => {
        mediaRecorder.stop();
      }, 10000);
    })
    .catch(err => {
      console.error('Microphone error:', err);
      alert('Microphone access is required to record audio.');
    });
};

document.getElementById('file-input').addEventListener('change', function() {
  if (this.files.length > 0) {
    document.getElementById('loading-message').style.display = 'block';
    document.getElementById('upload-form').submit();
  }
});

