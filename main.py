import os
import time
import subprocess
import pygame

BLUETOOTH_NAME = "HBTS001"

def connect_bluetooth_device(device_name):
    print("Starting Bluetooth controller...")
    # Make sure bluetoothctl is properly initialized
    subprocess.run(["sudo", "systemctl", "start", "bluetooth"], check=False)
    time.sleep(2)
    
    # Power on the Bluetooth adapter
    print("Powering on Bluetooth...")
    result = subprocess.run(["bluetoothctl", "power", "on"], capture_output=True, text=True)
    print(f"Power on result: {result.stdout.strip()}")
    
    # Make discoverable
    subprocess.run(["bluetoothctl", "discoverable", "on"], capture_output=True, text=True)
    
    # Start scanning
    print("Starting Bluetooth scan...")
    subprocess.run(["bluetoothctl", "scan", "on"], capture_output=True, text=True)
    print("Scanning for 10 seconds...")
    time.sleep(10)  # Increased scan time
    subprocess.run(["bluetoothctl", "scan", "off"], capture_output=True, text=True)
    
    # Get devices
    print("Getting device list...")
    result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running bluetoothctl: {result.stderr}")
        return None
    
    lines = result.stdout.strip().splitlines()
    print(f"Found {len(lines)} Bluetooth devices:")
    
    if not lines:
        print("No devices found. Make sure your device is in pairing mode.")
        return None
    
    for line in lines:
        print(f"  {line}")
    
    # Find target device
    device_addr = None
    for line in lines:
        if device_name in line:
            parts = line.split()
            if len(parts) >= 2:
                device_addr = parts[1]
            break
    
    if not device_addr:
        print(f"Device '{device_name}' not found in the list above.")
        return None
    
    print(f"Found device {device_name} with address: {device_addr}")
    
    # Pair and connect
    print("Pairing...")
    pair_result = subprocess.run(["bluetoothctl", "pair", device_addr], capture_output=True, text=True)
    print(f"Pair result: {pair_result.stdout.strip()}")
    
    print("Connecting...")
    connect_result = subprocess.run(["bluetoothctl", "connect", device_addr], capture_output=True, text=True)
    print(f"Connect result: {connect_result.stdout.strip()}")
    
    print(f"Attempted connection to {device_name} ({device_addr})")
    return device_addr

def play_mp3(mp3_path):
    pygame.mixer.init()
    pygame.mixer.music.load(mp3_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(1)

def record_from_bluetooth_mic(duration=5, output_file="output.wav"):
    import pyaudio
    import wave
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    p = pyaudio.PyAudio()
    # List devices and select the Bluetooth mic index
    print("Available audio devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"{i}: {info['name']}")
    device_index = int(input("Enter the device index for HAMMER mic: "))
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, input_device_index=device_index, frames_per_buffer=CHUNK)
    print("Recording...")
    frames = []
    for _ in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("Done recording.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(output_file, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

if __name__ == "__main__":
    addr = connect_bluetooth_device(BLUETOOTH_NAME)
    if addr:
        # Example: Play an MP3 file to the Bluetooth speaker
        print("now playing mp3 to bluetooth speaker")
        play_mp3("test.mp3")
        # Example: Record from Bluetooth mic
        print("now recording from bluetooth mic")
        record_from_bluetooth_mic(duration=5, output_file="bluetooth_mic.wav")