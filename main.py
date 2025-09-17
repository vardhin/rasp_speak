import os
import time
import subprocess
import pygame
import sys
from contextlib import redirect_stderr
from io import StringIO

BLUETOOTH_NAME = "HBTS001"

def connect_bluetooth_device(device_name):
    print("Starting Bluetooth controller...")
    # Make sure bluetoothctl is properly initialized
    subprocess.run(["sudo", "systemctl", "start", "bluetooth"], check=False)
    time.sleep(1)
    
    # Power on the Bluetooth adapter
    print("Powering on Bluetooth...")
    result = subprocess.run(["bluetoothctl", "power", "on"], capture_output=True, text=True)
    print(f"Power on result: {result.stdout.strip()}")
    
    # Check if device is already known
    print("Checking for known devices...")
    result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
    device_addr = None
    
    if result.returncode == 0:
        lines = result.stdout.strip().splitlines()
        for line in lines:
            if device_name in line:
                parts = line.split()
                if len(parts) >= 2:
                    device_addr = parts[1]
                    print(f"Found known device {device_name} with address: {device_addr}")
                break
    
    # If device not known, scan for it
    if not device_addr:
        print("Device not known, starting scan...")
        # Start scanning in background
        scan_process = subprocess.Popen(["bluetoothctl", "scan", "on"], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
        
        # Check for devices every 2 seconds for up to 20 seconds
        max_attempts = 10
        for attempt in range(max_attempts):
            print(f"Scan attempt {attempt + 1}/{max_attempts}...")
            time.sleep(2)
            
            result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                for line in lines:
                    if device_name in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            device_addr = parts[1]
                            print(f"Found device {device_name} with address: {device_addr}")
                            break
                
                if device_addr:
                    break
        
        # Stop scanning
        subprocess.run(["bluetoothctl", "scan", "off"], capture_output=True, text=True)
        scan_process.terminate()
    
    if not device_addr:
        print(f"Device '{device_name}' not found after scanning.")
        # List all found devices for debugging
        result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            print(f"Available devices ({len(lines)}):")
            for line in lines:
                print(f"  {line}")
        return None
    
    print(f"Attempting to connect to {device_name} ({device_addr})")
    
    # Try to connect (might already be paired)
    print("Attempting connection...")
    connect_result = subprocess.run(["bluetoothctl", "connect", device_addr], 
                                  capture_output=True, text=True, timeout=10)
    
    # If connection fails, try pairing first
    if "Failed" in connect_result.stdout or connect_result.returncode != 0:
        print("Connection failed, trying to pair first...")
        pair_result = subprocess.run(["bluetoothctl", "pair", device_addr], 
                                   capture_output=True, text=True, timeout=15)
        print(f"Pair result: {pair_result.stdout.strip()}")
        
        if pair_result.returncode == 0 or "already paired" in pair_result.stdout.lower():
            print("Trying to connect again...")
            connect_result = subprocess.run(["bluetoothctl", "connect", device_addr], 
                                          capture_output=True, text=True, timeout=10)
    
    print(f"Final connect result: {connect_result.stdout.strip()}")
    
    # Verify connection
    time.sleep(2)
    info_result = subprocess.run(["bluetoothctl", "info", device_addr], 
                               capture_output=True, text=True)
    if "Connected: yes" in info_result.stdout:
        print(f"Successfully connected to {device_name}")
        return device_addr
    else:
        print(f"Connection verification failed for {device_name}")
        return None

def play_mp3(mp3_path):
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(mp3_path)
        
        # Suppress stderr during playback to hide libmpg123 warnings
        with redirect_stderr(StringIO()):
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(1)
        
        print("Audio playback completed successfully")
    except pygame.error as e:
        print(f"Pygame audio error (ignoring): {e}")
    except Exception as e:
        print(f"Audio playback error (ignoring): {e}")

def record_from_bluetooth_mic(duration=5, output_file="output.wav"):
    import pyaudio
    import wave
    
    try:
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        p = pyaudio.PyAudio()
        
        # List devices and select the Bluetooth mic index
        print("Available audio devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(f"{i}: {info['name']} - {info['maxInputChannels']} input channels")
        
        device_index = int(input("Enter the device index for HAMMER mic: "))
        
        # Validate device index
        if device_index < 0 or device_index >= p.get_device_count():
            print("Invalid device index!")
            p.terminate()
            return
        
        device_info = p.get_device_info_by_index(device_index)
        print(f"Selected device: {device_info['name']}")
        print(f"Max input channels: {device_info['maxInputChannels']}")
        print(f"Default sample rate: {device_info['defaultSampleRate']}")
        
        stream = p.open(format=FORMAT, 
                       channels=CHANNELS, 
                       rate=RATE, 
                       input=True, 
                       input_device_index=device_index, 
                       frames_per_buffer=CHUNK)
        
        print(f"Recording for {duration} seconds...")
        frames = []
        
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
            # Show progress
            if i % (RATE // CHUNK) == 0:  # Every second
                print(f"Recording... {i // (RATE // CHUNK) + 1}s")
        
        print("Done recording.")
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save to WAV file
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"Recording saved to: {output_file}")
        
    except Exception as e:
        print(f"Recording error: {e}")
        if 'p' in locals():
            p.terminate()

if __name__ == "__main__":
    addr = connect_bluetooth_device(BLUETOOTH_NAME)
    if addr:
        # Example: Play an MP3 file to the Bluetooth speaker
        print("now playing mp3 to bluetooth speaker")
        play_mp3("test.mp3")
        # Example: Record from Bluetooth mic
        print("now recording from bluetooth mic")
        record_from_bluetooth_mic(duration=5, output_file="bluetooth_mic.wav")