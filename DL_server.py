import firebase_admin
from firebase_admin import credentials, db
import yt_dlp
from dotenv import dotenv_values
from flask import Flask, jsonify

config = dotenv_values(".env")
firebase_url = config['FIREBASE_DB']

cred = credentials.Certificate('access_key.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_url
})

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
    filename = None

    if queue_data:
        # Sort the items based on timestamps
        sorted_items = sorted(queue_data.items(), key=lambda x: x[1].get('timestamps'))

        # Download the oldest URL
        key, value = sorted_items[0]
        youtube_url = value.get('youtubeId')
        filename = value.get('timestamps')
        if youtube_url:
            # Put it in a folder called output and call it by number based on the timestamp
            download_and_convert_to_wav(youtube_url, f'output/{filename}')
            # Remove the URL from the queue
            ref.child(key).delete()
        return filename
    else:
        return None

app = Flask(__name__)

@app.route('/download_next', methods=['GET'])
def download_next():
    filename = download_oldest()
    if filename is None:
        # Set status code to 400
        return jsonify({'status': 'error',
                        'message': 'No songs in queue.'}), 400
    return jsonify({'status': 'success',
                    'filename': filename}), 200

if __name__ == '__main__':
    app.run(debug=True)
