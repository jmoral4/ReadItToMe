import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from pathlib import Path
import pygame
from urllib.parse import urlparse, unquote
import anthropic
import argparse

CLAUDE_KEY = '<CLAUDE KEY>'
API_KEY='<OPENAI KEY>'

# ANSI escape codes for some colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
RESET = "\033[0m"  # Resets the color to default

REMOTE_OLLAMA_HOST = "http://..."
LOCAL_OLLAMA_HOST = "http://localhost:11434"
OLLAMA_HOST = LOCAL_OLLAMA_HOST  #switch this to LOCAL_OLLAMA_HOST if testing locally


def print_colored(text, color):
    print(f"{color}{text}{RESET}")


def estimate_tokens(text):
    return len(text) // 4


def talk_to_ai(prompt, model, color, api_type='openai', temperature=1, max_tokens=720, top_p=1, frequency_penalty=0,
               presence_penalty=0, system_prompt=None):

    """
    Model Options:
    gpt-4-0125-preview     (GPT-4 turbo)
    claude-3-opus-20240229     (pro membership, strongest model)
    claude-3-sonnet-20240229   (powers the free claude, general purpose GPT-4 tier)
    claude-3-haiku-20240307    (small, fast, GPT-3 tier)
    """

    if system_prompt is None and api_type == 'claude':
        system_prompt = "You are a helpful AI assistant named Claude. Provide concise answers to simple questions and thorough responses to complex, open-ended queries."

    if api_type == 'ollama':
        print(f"Using OLLAMA model: {model} for AI")
        base_url = f'{OLLAMA_HOST}/v1/'
        api_key = 'ollama'
        client = OpenAI(base_url=base_url, api_key=api_key)
        response_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
    elif api_type == 'claude':
        print(f"Using Claude model: {model} for AI")
        api_key = CLAUDE_KEY
        client = anthropic.Anthropic(api_key=api_key)
        response_params = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }
    else:  # Default to GPT
        print(f"Using OpenAI model: {model} for AI")
        api_key = API_KEY
        client = OpenAI(api_key=api_key)
        response_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty
        }

    # Create response based on API type
    if api_type in ['ollama', 'openai']:
        response = client.chat.completions.create(**response_params)
        message_content = response.choices[0].message.content
    else:  # Claude
        message = client.messages.create(**response_params)
        message_content = message.content

    # Process and print the response
    print_colored(f"{model}:", color)
    print_colored(message_content, color)

    return message_content


def get_web_page_contents(url):

    try:
        # Define headers with a User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        # Sending a GET request to the URL with headers
        response = requests.get(url, headers=headers)
        # Checking if the request was successful
        response.raise_for_status()

        # Parsing the content of the page with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extracting and returning the text from the parsed HTML
        return soup.get_text(separator=' ', strip=True)
    except requests.RequestException as e:
        return str(e)


def play_mp3(filepath):
    pygame.mixer.init()
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():  # Wait for the music to finish playing
        pygame.time.Clock().tick(10)  # Tick the clock to wait


def clean_and_shorten_text(text, max_length=10):
    # Remove URL specific characters and shorten the text
    clean_text = "".join(x for x in text if x.isalnum())
    if len(clean_text) > max_length:
        return clean_text[:max_length]
    return clean_text


def generate_filename_from_url(url):
    parsed_url = urlparse(url)
    # Extract domain name and path, optionally you can include other parts like 'path'
    domain_name = parsed_url.netloc.split('.')[-2]  # Usually gives the meaningful part of the domain
    path_parts = parsed_url.path.split('/')
    meaningful_parts = [clean_and_shorten_text(part) for part in path_parts if part][:2]  # Take the first 2 meaningful parts of the path
    filename_parts = [clean_and_shorten_text(domain_name)] + meaningful_parts
    filename = "_".join(filename_parts)
    return f"{filename}.mp3"


def word_count(string):
    words = string.split()
    return len(words)


def generate_audio(content):
    client = OpenAI(api_key=API_KEY)
    print("Generating Audio!")
    audio_resp = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=f"{content}"
    )
    audio_resp.stream_to_file(speech_file_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="READIT To ME 1.0")
    parser.add_argument("--url", help="URL of the webpage to summarize", default=None)
    args = parser.parse_args()

    print("READIT To ME 1.0")

    play_mp3('gettingcontent.mp3')
    if args.url:
        page = args.url
    else:
        page = r"https://news.ycombinator.com/item?id=39765718"  #very large discussion used for testing

    contents = get_web_page_contents(page)
    print(f"Word Count from page:{word_count(contents)}")
    print(f"Tokens Estimate:{estimate_tokens(contents)}")

    speech_filename = generate_filename_from_url(page)
    output_dir = Path("path/to/your/output/directory")  # User-defined output directory
    speech_file_path = output_dir / speech_filename
    print("filepath path:", speech_file_path)

    play_mp3('summary.mp3')
    print(f'Summarizing:{page}')
    prompt = f"""Please synthesize and provide a detailed overview of the following webpage contents.               
        Webpage Contents Below:
        {contents}    
    """

    claude_model_name = "claude-3-opus-20240229"    #api_type= 'claude'
    gpt4_model_name = "gpt-4-0125-preview"          #api_type = 'openai'

    #remember to change both the model AND the api_type. In the future this can be a tuple or auto-detected
    resp = talk_to_ai(prompt, claude_model_name, GREEN, 'claude')

    print(f"SUMMARY:{resp}")

    play_mp3('genaudio.mp3')

    generate_audio(resp)
    print("Audio generated! Now Playing.")
    # Path to your MP3 file
    play_mp3(str(speech_file_path))
    print("Done!")







