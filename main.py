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
        # Temporarily redirect stderr to suppress libmpg123 warnings
        original_stderr = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
        
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(1)
        finally:
            # Restore stderr
            os.dup2(original_stderr, 2)
            os.close(devnull)
            os.close(original_stderr)
        
        print("Audio playback completed successfully")
    except pygame.error as e:
        print(f"Pygame audio error (ignoring): {e}")
    except Exception as e:
        print(f"Audio playback error (ignoring): {e}")

def play_wav(wav_path):
    """Play a WAV file to the Bluetooth speaker using pygame"""
    try:
        # Check if file exists
        if not os.path.exists(wav_path):
            print(f"Error: WAV file '{wav_path}' not found!")
            return
        
        # Temporarily redirect stderr to suppress any warnings
        original_stderr = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
        
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(wav_path)
            pygame.mixer.music.play()
            
            print(f"Playing WAV file: {wav_path}")
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        finally:
            # Restore stderr
            os.dup2(original_stderr, 2)
            os.close(devnull)
            os.close(original_stderr)
        
        print("WAV playback completed successfully")
        
    except pygame.error as e:
        print(f"Pygame audio error: {e}")
    except Exception as e:
        print(f"WAV playback error: {e}")

def play_wav_alternative(wav_path):
    """Alternative method using aplay command"""
    try:
        if not os.path.exists(wav_path):
            print(f"Error: WAV file '{wav_path}' not found!")
            return
        
        print(f"Playing WAV file: {wav_path}")
        result = subprocess.run(["aplay", wav_path], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("WAV playback completed successfully")
        else:
            print(f"aplay error: {result.stderr}")
            
    except Exception as e:
        print(f"WAV playback error: {e}")

def record_from_bluetooth_mic(duration=5, output_file="output.wav"):
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
    except ImportError:
        print("sounddevice not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "sounddevice", "soundfile"])
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
    
    try:
        # List devices
        print("Available audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"{i}: {device['name']} - {device['max_input_channels']} input channels")
        
        device_index = int(input("Enter the device index for Bluetooth mic: "))
        
        # Validate device index
        if device_index < 0 or device_index >= len(devices):
            print("Invalid device index!")
            return
        
        device_info = devices[device_index]
        print(f"Selected device: {device_info['name']}")
        print(f"Max input channels: {device_info['max_input_channels']}")
        print(f"Default sample rate: {device_info['default_samplerate']}")
        
        # Recording parameters
        sample_rate = int(device_info['default_samplerate'])
        channels = 1
        
        print(f"Recording for {duration} seconds...")
        
        # Record audio
        recording = sd.rec(int(duration * sample_rate), 
                          samplerate=sample_rate, 
                          channels=channels, 
                          device=device_index,
                          dtype='float32')
        
        # Show progress
        for i in range(duration):
            time.sleep(1)
            print(f"Recording... {i + 1}s")
        
        sd.wait()  # Wait until recording is finished
        print("Done recording.")
        
        # Save to WAV file
        sf.write(output_file, recording, sample_rate)
        print(f"Recording saved to: {output_file}")
        
    except Exception as e:
        print(f"Recording error: {e}")

if __name__ == "__main__":
    addr = connect_bluetooth_device(BLUETOOTH_NAME)
    if addr:
        # Example: Play an MP3 file to the Bluetooth speaker
        #print("now playing mp3 to bluetooth speaker")
        #play_mp3("test.mp3")
        
        # Example: Record from Bluetooth mic
        print("now recording from bluetooth mic")
        record_from_bluetooth_mic(duration=5, output_file="bluetooth_mic.wav")
        
        # Example: Play the recorded WAV file back
        print("now playing recorded WAV file to bluetooth speaker")
        play_wav("bluetooth_mic.wav")
        
        # Alternative method if pygame doesn't work
        # play_wav_alternative("bluetooth_mic.wav")