# ReadItToMe
Why use ReadItToMe rather than a screen reader? I built this tool for two major use cases.

1. Reading research papers and large web content in a smart way (don't read ads, don't read menus, etc etc).
2. Reading large forums and summarizing the findings, consensus, insights, etc.

In these cases, it blows a standard screenreader out of the water. 

Next step, a Chromium based plugin.

## Features
* Support for OpenAI models  (GPT-3/GPT-4)
* Support for Anthropic models (Claude-2/3)
* Support for Ollama Models (Mistral, Llama2, etc)

## Optional CLI usage
Specify Url
> python main.py --url "https://example.com/page"

Specify a filename (to reuse the same file. By default one file per webpage is generated)
> python main.py --fixed-filename "summary.mp3"

Flags
* --silent  (Don't vocalize the actions being performed)
* --download-only  (Only download the audio files, don't play them back (useful for bulk creating a playlist))

## Setup
* Copy or Rename config.example.json to config.json
* Add your keys for an ai models. OpenAI key is _required_ for OpenAi's natural text to speech which is the main feature of this app. (may support other platforms in the future)
* Add your output directory - this is where audio files generated for playback will be stored
* Add your selected model and model type (openai, claude, ollama)

## Practical Notes
* In general, requires models with 16k+ context sizes in order to be useful (GPT-3.5-turbo, GPT-4-Turbo, Claude-2, Claude-3)
* Not all Ollama models support large context sizes.
* In practice Mistral was passable but most small/medium models did poorly or require tweaking. YMMV!
* Claude-3 and GPT-4 did exceptionally well due to the large context sizes (turbo and recollect quality)
