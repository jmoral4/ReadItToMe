import requests
from openai import OpenAI
from bs4 import BeautifulSoup
from pathlib import Path
import pygame
from urllib.parse import urlparse, unquote
import anthropic
import argparse
import json
from halo import Halo


# ANSI escape codes for some colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
RESET = "\033[0m"  # Resets the color to default

# used for more tailored spinner sequances
spinner = Halo(spinner='dots')

def print_colored(text, color):
    print(f"{color}{text}{RESET}")


def estimate_tokens(text):
    return len(text) // 4


def talk_to_ai(content, model, color, api_type='openai', temperature=1, max_tokens=2000, top_p=1, frequency_penalty=0,
               presence_penalty=0, system_prompt=None):
    """
    Model Options:
    See OpenAi Models here for latest: https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
    gpt-4-turbo-preview    (GPT-4 turbo used in Pro subscription, most modern model, 128k context 4k response)
    gpt-4                  (GPT-4 8k context)
    gpt-4-32k              (GPT-4-32k context)
    gpt-3.5-turbo          (GPT-3.5 turbo latest model, 16k context)


    See Claude Models here for latest: https://docs.anthropic.com/claude/docs/models-overview
    claude-3-opus-20240229     (pro membership, strongest model)
    claude-3-sonnet-20240229   (powers the free claude, general purpose GPT-4 tier)
    claude-3-haiku-20240307    (small, fast, GPT-3 tier)
    """
    try:
        base_sys_prompt = "You are a helpful AI assistant named ROBOT. Provide concise answers to simple questions and thorough responses to complex, open-ended queries."

        if system_prompt is None and api_type == 'claude':
            system_prompt = base_sys_prompt.replace('ROBOT', 'Claude')
        elif system_prompt is None and api_type == 'openai':
            system_prompt = base_sys_prompt.replace('ROBOT', 'ChatGPT')

        print("Using System Prompt:", system_prompt)
        spinner.text = f"Generating Summary using {api_type} {model}"
        spinner.start()
        if api_type == 'ollama':
            prompt = f"""Please synthesize and provide a detailed overview of the following textual content.               
                Content:
                {content}    
            """
            base_url = f'{OLLAMA_HOST}/v1/'
            api_key = 'ollama'
            client = OpenAI(base_url=base_url, api_key=api_key)
            response_params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
        elif api_type == 'claude':
            prompt = f"""Please synthesize and provide a detailed overview of the following webpage content.               
                   Webpage Content:
                   {content}    
               """
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
            # special prompt for GPT-4 which gets hung up on 'not having internet access to summarize'
            prompt = f"""Please synthesize and provide a detailed overview of the following textual content.               
                   Content:
                   {content}    
               """
            #print_colored(f"DEBUG Query:{prompt}", YELLOW)
            api_key = API_KEY
            client = OpenAI(api_key=api_key)
            response_params = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens
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

        spinner.stop()
        return message_content
    except Exception as e:
        spinner.fail(f"Failed due to {e}")
        raise
    finally:
        if spinner.spinner_id:
            spinner.stop()


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
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():  # Wait for the music to finish playing
            pygame.time.Clock().tick(10)  # Tick the clock to wait
    except pygame.error as e:
        print(f"An error occurred: {e}")


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


@Halo(text='Generating Audio', spinner='dots')
def generate_audio(content, voice="nova"):
    """
    Voice Options: (alloy, echo, fable, onyx, nova, and shimmer)
    https://platform.openai.com/docs/guides/text-to-speech
    """
    if voice is None:
        voice = "nova"

    client = OpenAI(api_key=API_KEY)
    audio_resp = client.audio.speech.create(
        model="tts-1",
        voice= voice,
        input=f"{content}"
    )
    audio_resp.stream_to_file(speech_file_path)


if __name__ == "__main__":

    with open('config.json') as config_file:
        config = json.load(config_file)
        CLAUDE_KEY = config['CLAUDE_KEY']
        API_KEY = config['OPENAI_KEY']
        OUTPUT_DIR = config['OUTPUT_DIR']
        SELECTED_MODEL = config['SELECTED_MODEL']
        SELECTED_MODEL_TYPE = config['SELECTED_MODEL_TYPE']
        OLLAMA_HOST = config['OLLAMA_HOST']
        AUDIO_VOICE = config['AUDIO_VOICE']
        MAX_TOKENS = config['MAX_RESPONSE_TOKENS']

    parser = argparse.ArgumentParser(description="READIT To ME 1.0")
    parser.add_argument("--url", help="URL of the webpage to summarize", default=None)
    parser.add_argument("--download-only", help="Only download the audio files, no playback", default=None)
    parser.add_argument("--silent", help="Don't vocalize actions being performed", default=None)
    parser.add_argument("--fixed-filename", help="Use a fixed filename for the audio output", default=None)

    args = parser.parse_args()

    print("READIT To ME 1.0")

    if not args.silent:
        play_mp3('gettingcontent.mp3')

    if args.url:
        page = args.url
    else:
        page = r"https://news.ycombinator.com/item?id=39766170"  # large discussion used for testing

    contents = get_web_page_contents(page)
    print(f"Word Count from page:{word_count(contents)}")
    print(f"Tokens Estimate:{estimate_tokens(contents)}")

    if args.fixed_filename:
        speech_filename = args.fixed_filename
    else:
        speech_filename = generate_filename_from_url(page)

    output_dir = Path(OUTPUT_DIR)
    speech_file_path = output_dir / speech_filename
    print("filepath path:", speech_file_path)

    if not args.silent:
        play_mp3('summary.mp3')

    print(f'Summarizing:{page}')

    #remember to change both the model AND the api_type. In the future this can be a tuple or auto-detected
    resp = talk_to_ai(contents, SELECTED_MODEL, GREEN, SELECTED_MODEL_TYPE, max_tokens=MAX_TOKENS)

    print(f"SUMMARY:{resp}")

    if not args.silent:
        play_mp3('genaudio.mp3')

    print(f"Generating Audio with {AUDIO_VOICE} Voice")
    generate_audio(resp, AUDIO_VOICE)
    print("Audio generated! Now Playing.")

    # Path to your MP3 file
    if not args.download_only:
        # only show the spinner for the final playbck (the others are less than 2seconds)
        spinner.text = 'Now Playing'
        spinner.start()
        play_mp3(str(speech_file_path))
        spinner.stop()

    print("Done!")







