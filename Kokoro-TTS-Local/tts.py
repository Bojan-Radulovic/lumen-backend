import torch
from typing import Optional, Tuple, List, Union
from models import build_model, generate_speech, list_available_voices
from tqdm.auto import tqdm
import soundfile as sf
from pathlib import Path
import numpy as np
import time
import os
import sys
from faststream import FastStream
from faststream.rabbit import RabbitBroker
import io
import base64

broker = RabbitBroker("amqp://guest:guest@localhost:5672/")
app = FastStream(broker)

# Define path type for consistent handling
PathLike = Union[str, Path]

# Constants with validation
def validate_sample_rate(rate: int) -> int:
    """Validate sample rate is within acceptable range"""
    valid_rates = [16000, 22050, 24000, 44100, 48000]
    if rate not in valid_rates:
        print(f"Warning: Unusual sample rate {rate}. Valid rates are {valid_rates}")
        return 24000  # Default to safe value
    return rate

def validate_language(lang: str) -> str:
    """Validate language code"""
    valid_langs = ['a', 'b']  # 'a' for American English, 'b' for British English
    if lang not in valid_langs:
        print(f"Warning: Invalid language code '{lang}'. Using 'a' (American English).")
        return 'a'  # Default to American English
    return lang

# Define and validate constants
SAMPLE_RATE = validate_sample_rate(24000)
DEFAULT_MODEL_PATH = Path('kokoro-v1_0.pth').absolute()
DEFAULT_OUTPUT_FILE = Path('output.wav').absolute()
DEFAULT_LANGUAGE = validate_language('a')  # 'a' for American English, 'b' for British English
DEFAULT_TEXT = "Hello, welcome to this text-to-speech test."

# Ensure output directory exists
DEFAULT_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Configure tqdm for better Windows console support
tqdm.monitor_interval = 0

def print_menu():
    """Print the main menu options."""
    print("\n=== Kokoro TTS Menu ===")
    print("1. List available voices")
    print("2. Generate speech")
    print("3. Exit")
    return input("Select an option (1-3): ").strip()

def select_voice(voices: List[str]) -> str:
    """Interactive voice selection."""
    print("\nAvailable voices:")
    for i, voice in enumerate(voices, 1):
        print(f"{i}. {voice}")
    
    while True:
        try:
            choice = input("\nSelect a voice number (or press Enter for default 'af_bella'): ").strip()
            if not choice:
                return "af_bella"
            choice = int(choice)
            if 1 <= choice <= len(voices):
                return voices[choice - 1]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def get_text_input() -> str:
    """Get text input from user."""
    print("\nEnter the text you want to convert to speech")
    print("(or press Enter for default text)")
    text = input("> ").strip()
    return text if text else DEFAULT_TEXT

def get_speed() -> float:
    """Get speech speed from user."""
    while True:
        try:
            speed = input("\nEnter speech speed (0.5-2.0, default 1.0): ").strip()
            if not speed:
                return 1.0
            speed = float(speed)
            if 0.5 <= speed <= 2.0:
                return speed
            print("Speed must be between 0.5 and 2.0")
        except ValueError:
            print("Please enter a valid number.")

def save_audio_with_retry(audio_data: np.ndarray, sample_rate: int, output_path: PathLike, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """
    Attempt to save audio data to file with retry logic.
    
    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate in Hz
        output_path: Path to save the audio file
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        True if successful, False otherwise
    """
    # Convert and normalize path to Path object
    output_path = Path(output_path).absolute()
    
    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            # Validate audio data before saving
            if audio_data is None or len(audio_data) == 0:
                raise ValueError("Empty audio data")
                
            # Check write permissions for the directory
            if not os.access(str(output_path.parent), os.W_OK):
                raise PermissionError(f"No write permission for directory: {output_path.parent}")
                
            # Save audio file
            sf.write(str(output_path), audio_data, sample_rate)
            return True
            
        except (IOError, PermissionError) as e:
            if attempt < max_retries - 1:
                print(f"\nFailed to save audio (attempt {attempt + 1}/{max_retries}): {e}")
                print("The output file might be in use by another program (e.g., media player).")
                print(f"Please close any programs that might be using '{output_path}'")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"\nError: Could not save audio after {max_retries} attempts: {e}")
                print(f"Please ensure '{output_path}' is not open in any other program and try again.")
                return False
        except Exception as e:
            print(f"\nUnexpected error saving audio: {type(e).__name__}: {e}")
            return False
            
    return False

@broker.subscriber("to_tts")
async def callback(msg):
    global model, voices_cache
    try:
        print("I recived: ", msg)
        text = str(msg['text'])
        
        choice = "2" # TODO Make pretty
        
        if choice == "1":
            # List voices
            voices_cache = list_available_voices()
            print("\nAvailable voices:")
            for voice in voices_cache:
                print(f"- {voice}")
                
        elif choice == "2":
            # Generate speech
            # Use cached voices if available
            if voices_cache is None:
                voices_cache = list_available_voices()
            
            if not voices_cache:
                print("No voices found! Please check the voices directory.")
                return {"error": "No voices found! Please check the voices directory."}
            
            # Get user inputs
            voice = "bf_isabella" # TODO Make pretty
            
            # Validate text (don't allow extremely long inputs)
            if len(text) > 10000:  # Reasonable limit for text length
                print("Text is too long. Please enter a shorter text.")
                return {"error": "Text is too long. Please enter a shorter text."}
                
            speed = 1 # TODO Make pretty
            
            print(f"\nGenerating speech for: '{text}'")
            print(f"Using voice: {voice}")
            print(f"Speed: {speed}x")
            
            # Generate speech
            all_audio = []
            # Use Path object for consistent path handling
            voice_path = Path("voices").absolute() / f"{voice}.pt"
            
            # Verify voice file exists
            if not voice_path.exists():
                print(f"Error: Voice file not found: {voice_path}")
                return {"error": f"Error: Voice file not found: {voice_path}"}
            
            # Set a timeout for generation with per-segment timeout
            max_gen_time = 300  # 5 minutes max total
            max_segment_time = 60  # 60 seconds max per segment
            start_time = time.time()
            segment_start_time = start_time
            
            try:
                # Setup watchdog timer for overall process
                import threading
                generation_complete = False
                
                def watchdog_timer():
                    if not generation_complete:
                        print("\nWatchdog: Generation taking too long, process will be cancelled")
                        # Can't directly interrupt generator, but this will inform user
                
                # Start watchdog timer
                watchdog = threading.Timer(max_gen_time, watchdog_timer)
                watchdog.daemon = True  # Don't prevent program exit
                watchdog.start()
                
                # Initialize generator
                try:
                    generator = model(text, voice=voice_path, speed=speed, split_pattern=r'\n+')
                except (ValueError, TypeError, RuntimeError) as e:
                    print(f"Error initializing speech generator: {e}")
                    watchdog.cancel()
                    return {"error": f"Error initializing speech generator: {e}"}
                except Exception as e:
                    print(f"Unexpected error initializing generator: {type(e).__name__}: {e}")
                    watchdog.cancel()
                    return {"error": f"Unexpected error initializing generator: {type(e).__name__}: {e}"}
                
                # Process segments
                with tqdm(desc="Generating speech") as pbar:
                    for gs, ps, audio in generator:
                        # Check overall timeout
                        current_time = time.time()
                        if current_time - start_time > max_gen_time:
                            print("\nWarning: Total generation time exceeded limit, stopping")
                            break
                        
                        # Check per-segment timeout
                        segment_elapsed = current_time - segment_start_time
                        if segment_elapsed > max_segment_time:
                            print(f"\nWarning: Segment took too long ({segment_elapsed:.1f}s), stopping")
                            break
                        
                        # Reset segment timer
                        segment_start_time = current_time
                        
                        # Process audio if available
                        if audio is not None:
                            # Only convert if it's a numpy array, not if already tensor
                            audio_tensor = audio if isinstance(audio, torch.Tensor) else torch.from_numpy(audio).float()
                            
                            all_audio.append(audio_tensor)
                            print(f"\nGenerated segment: {gs}")
                            if ps:  # Only print phonemes if available
                                print(f"Phonemes: {ps}")
                            pbar.update(1)
                
                # Mark generation as complete (for watchdog)
                generation_complete = True
                watchdog.cancel()
                
            except ValueError as e:
                print(f"Value error during speech generation: {e}")
            except RuntimeError as e:
                print(f"Runtime error during speech generation: {e}")
                # If CUDA out of memory, provide more helpful message
                if "CUDA out of memory" in str(e):
                    print("CUDA out of memory error - try using a shorter text or switching to CPU")
            except KeyError as e:
                print(f"Key error during speech generation: {e}")
                print("This might be caused by a missing voice configuration")
            except FileNotFoundError as e:
                print(f"File not found: {e}")
            except Exception as e:
                print(f"Unexpected error during speech generation: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
            
            # Save audio
            if all_audio:
                try:
                    # Handle single segment case without concatenation
                    if len(all_audio) == 1:
                        final_audio = all_audio[0]
                    else:
                        try:
                            final_audio = torch.cat(all_audio, dim=0)
                        except RuntimeError as e:
                            print(f"Error concatenating audio segments: {e}")
                            return {"error": f"Error concatenating audio segments: {e}"}
                    
                    # Use consistent Path object
                    with io.BytesIO() as wav_buffer:
                        sf.write(wav_buffer, final_audio.numpy(), SAMPLE_RATE, format='WAV')
                        wav_bytes = wav_buffer.getvalue()
                        wav_b64 = base64.b64encode(wav_bytes).decode('utf-8')
                        print("Sending encoded audio bytes")
                        return {"audio_bytes": wav_b64}
                    
                except Exception as e:
                    print(f"Error processing audio: {type(e).__name__}: {e}")
                    return {"error": f"Error processing audio: {type(e).__name__}: {e}"}
            else:
                print("Error: Failed to generate audio")
                return {"error": "Error: Failed to generate audio"}
        else:
            print("\nInvalid choice. Please try again.")
            return {"error": "\nInvalid choice. Please try again."}
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    
    torch.cuda.empty_cache()

model = None
voices_cache = None

@app.after_startup
async def start():
    global model, voices_cache  # Declare them as global so modifications persist outside the function

    # Set up device safely
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    except (RuntimeError, AttributeError, ImportError) as e:
        print(f"CUDA initialization error: {e}. Using CPU instead.")
        device = 'cpu'  # Fallback if CUDA check fails
    print(f"Using device: {device}")
    
    # Build model
    print("\nInitializing model...")
    with tqdm(total=1, desc="Building model") as pbar:
        model = build_model(DEFAULT_MODEL_PATH, device)  # Assign to global model
        pbar.update(1)
    
    # Cache for voices to avoid redundant calls
    voices_cache = None
    print("Waiting...")
