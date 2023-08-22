import firebase_admin
from firebase_admin import credentials, db
import yt_dlp
from dotenv import dotenv_values
from flask import Flask, jsonify

config = dotenv_values(".env")
firebase_url = config['FIREBASE_DB']

# Initialize Firebase
cred = credentials.Certificate('access_key.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_url
})

# Reference to the queue in Firebase Realtime Database
ref = db.reference('queue')

def download_and_convert_to_wav(url, output_name):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_name}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_oldest():
    # Get all items in the queue
    queue_data = ref.get()

    if queue_data:
        # Sort the items based on timestamps
        sorted_items = sorted(queue_data.items(), key=lambda x: x[1].get('timestamps'))

        # Download the oldest URL
        key, value = sorted_items[0]
        youtube_url = value.get('youtubeId')
        if youtube_url:
            download_and_convert_to_wav(youtube_url, f"output_{key}")
            # Remove the URL from the queue
            ref.child(key).delete()

app = Flask(__name__)

@app.route('/download_next', methods=['GET'])
def download_next():
    download_oldest()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
