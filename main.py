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
        # List available ALSA devices
        print("Available ALSA audio devices:")
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Could not list audio devices")
            return
        
        # Get user input for device selection
        card = input("Enter card number (e.g., 1): ")
        device = input("Enter device number (e.g., 0): ")
        
        # Construct device name
        device_name = f"hw:{card},{device}"
        
        print(f"Recording from device: {device_name}")
        print(f"Recording for {duration} seconds...")
        
        # Record using arecord
        cmd = [
            "arecord",
            "-D", device_name,
            "-f", "S16_LE",  # 16-bit little endian
            "-r", "44100",   # Sample rate
            "-c", "1",       # Mono
            "-d", str(duration),  # Duration
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Recording saved to: {output_file}")
        else:
            print(f"Recording failed: {result.stderr}")
            
    except Exception as e:
        print(f"Recording error: {e}")

def record_from_bluetooth_mic_pulseaudio(duration=5, output_file="output.wav"):
    """Alternative method using PulseAudio"""
    try:
        # List PulseAudio sources
        print("Available PulseAudio sources:")
        result = subprocess.run(["pactl", "list", "short", "sources"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                print(f"{i}: {line}")
        else:
            print("Could not list PulseAudio sources")
            return
        
        source_index = int(input("Enter source index: "))
        
        if source_index < 0 or source_index >= len(lines):
            print("Invalid source index!")
            return
        
        source_name = lines[source_index].split()[1]
        print(f"Selected source: {source_name}")
        
        print(f"Recording for {duration} seconds...")
        
        # Record using parecord (PulseAudio)
        cmd = [
            "parecord",
            "--device", source_name,
            "--file-format", "wav",
            "--rate", "44100",
            "--channels", "1",
            output_file
        ]
        
        # Start recording process
        process = subprocess.Popen(cmd)
        
        # Wait for specified duration
        time.sleep(duration)
        
        # Stop recording
        process.terminate()
        process.wait()
        
        print(f"Recording saved to: {output_file}")
        
    except Exception as e:
        print(f"Recording error: {e}")

def enable_bluetooth_handsfree_profile(device_addr):
    """Switch Bluetooth device to handsfree profile to enable microphone"""
    try:
        print("Switching to handsfree profile to enable microphone...")
        
        # Construct card name
        card_name = f"bluez_card.{device_addr.replace(':', '_')}"
        
        # Try the better quality mSBC codec first
        cmd = ["pactl", "set-card-profile", card_name, "headset-head-unit"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Successfully enabled headset-head-unit profile (mSBC codec)")
        else:
            # Fall back to CVSD codec
            print("Trying CVSD codec...")
            cmd = ["pactl", "set-card-profile", card_name, "headset-head-unit-cvsd"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Successfully enabled headset-head-unit-cvsd profile (CVSD codec)")
            else:
                print(f"Failed to set handsfree profile: {result.stderr}")
                return False
        
        # Wait for profile to activate
        time.sleep(3)
        
        # Check if microphone source is now available
        result = subprocess.run(["pactl", "list", "short", "sources"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Available sources after profile switch:")
            print(result.stdout)
            
            # Look for Bluetooth input source (PipeWire uses bluez_input, not bluez_source)
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if ("bluez_source" in line or "bluez_input" in line) and device_addr.replace(':', '_') in line:
                    print(f"✓ Bluetooth microphone source found: {line}")
                    return True
        
        print("No Bluetooth microphone source found after profile switch")
        return False
        
    except Exception as e:
        print(f"Error enabling handsfree profile: {e}")
        return False

if __name__ == "__main__":
    addr = connect_bluetooth_device(BLUETOOTH_NAME)
    if addr:
        # Enable handsfree profile for microphone access
        if enable_bluetooth_handsfree_profile(addr):
            print("Bluetooth microphone is now available!")
            
            # Record from Bluetooth mic using PulseAudio
            print("now recording from bluetooth mic")
            record_from_bluetooth_mic_pulseaudio(duration=5, output_file="bluetooth_mic.wav")
            
            # Play the recorded WAV file back
            print("now playing recorded WAV file to bluetooth speaker")
            play_wav("bluetooth_mic.wav")
        else:
            print("Failed to enable Bluetooth microphone")