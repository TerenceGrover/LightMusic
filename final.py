import numpy as np
from scipy.io import wavfile
from scipy import signal
import pygame
import serial
import time
from scipy.signal import butter, filtfilt
import threading
import requests

global filename;
SERIAL_PORT = '/dev/cu.usbmodem1101'
SERIAL_BAUDRATE = 115200
NUM_BINS = 5
FREQUENCY_MIN = 25
FREQUENCY_MAX = 8000
SLEEP_BEFORE_PLAY = 0.12
SLEEP_BETWEEN_SENDS = 0.096
NUM_LEVELS = 13
SERVER_URL = 'http://127.0.0.1:5000/download_next'

def read_and_process_music(music_file):
    # Read the wav file
    sample_rate, data = wavfile.read(music_file)
    # Normalize to mono
    data = data.sum(axis=1) / 2
    # Perform the Fourier transform
    frequencies, times, Zxx = signal.stft(data, fs=sample_rate, nperseg=sample_rate//5, noverlap=sample_rate//10)
    mask = (frequencies > FREQUENCY_MIN) & (frequencies < FREQUENCY_MAX)
    frequencies = frequencies[mask]
    # apply butterworth filter -- Experimental -- Not sure if this is necessary
    b, a = butter(3, 0.05)
    Zxx = filtfilt(b, a, Zxx, axis=0)
    Zxx = Zxx[mask, :]
    # Take absolute value to get magnitude (power)
    Zxx = np.abs(Zxx)
    # Now you can perform your frequency binning on Zxx, just remember it needs to be done for each column (time step)
    bin_edges = np.logspace(np.log10(min(frequencies)+1), np.log10(max(frequencies)), NUM_BINS+1)
    bin_medians = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(NUM_BINS)]
    bin_freqs = np.digitize(frequencies, bins=bin_edges)
    bin_vols_over_time = []
    for t in range(Zxx.shape[1]):
        bin_vols = [np.sum(Zxx[bin_freqs==i, t]) for i in range(1, NUM_BINS+1)]
        bin_vols_over_time.append(bin_vols)
    bin_vols_over_time = np.array(bin_vols_over_time)
    # Normalize each frequency band separately
    for i in range(NUM_BINS):
        bin_vols_over_time[:, i] = bin_vols_over_time[:, i] / np.max(bin_vols_over_time[:, i])
    # Scale to integer values for visualization
    bin_vols_over_time = np.round(bin_vols_over_time * (NUM_LEVELS - 1)).astype(int)
    return bin_vols_over_time

def download_and_update_song():
    global filename
    response = requests.get(SERVER_URL)
    if response.status_code == 200:
        json_data = response.json()
        if json_data.get('status') == 'success':
            print("Successfully downloaded next song.")
            # Update your MUSIC_FILE variable with the new filename.
            filename = f'./output/{json_data.get("filename")}.wav'
            # Assuming you know the pattern of the filename or it can be parsed from the response
            return True  # return True if successful
    print("Failed to download next song.")
    # Add a 3s delay before trying again
    time.sleep(3)
    return False  # return False if unsuccessful

# Create a serial object
ser = serial.Serial(SERIAL_PORT, 115200)

# Start threads to launch the music slightly after the serial connection is established
def play_music():
    time.sleep(SLEEP_BEFORE_PLAY)
    pygame.mixer.music.play()

while True:  # Loop to keep playing songs indefinitely
    # Try to download the next song and update MUSIC_FILE if successful
    if download_and_update_song():
        # Initialize the mixer module
        pygame.mixer.init()
        # Load the music file
        pygame.mixer.music.load(filename)
        # Wait for connection to establish
        time.sleep(1)

        # Start threads to launch the music slightly after the serial connection is established
        print("Starting music")
        threading.Thread(target=play_music).start()
        print("Music started")

        bin_vols_over_time = read_and_process_music(filename)

        for t in range(bin_vols_over_time.shape[0]):
            data = bin_vols_over_time[t]
            data_string = ",".join(map(str, data)) + "\n"
            ser.write(data_string.encode())
            time.sleep(SLEEP_BETWEEN_SENDS)

        # Close the serial connection
        ser.close()
