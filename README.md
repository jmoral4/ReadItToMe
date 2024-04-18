# ReadItToMe
Why use ReadItToMe rather than a screen reader? I built this tool for two major use cases.

1. Reading research papers and large web content in a smart way (don't read ads, don't read menus, etc etc).
2. Reading large forums and summarizing the findings, consensus, insights, etc.

In these cases, it blows a standard screenreader out of the water.

## Features
* Support for OpenAI models  (GPT-3/GPT-4)
* Support for Anthropic models (Claude-2/3)
* Support for Ollama Models (Mistral, Llama2, etc)

## Optional CLI usage
Specify Url
> py main.py --url "https://example.com/page"

Specify a filename (to reuse the same file. By default one file per webpage is generated)
> py main.py --fixed-filename "summary.mp3"

Specify a 'playlist' or file with multiple urls, one per line, to process. Can be combined with --silent and --download-only to setup a playlist for later listening. 
> py main.py --playlist \your\directory\playlist.txt

Save the AI generated summaries for later viewing
> py main.py --save-summaries \output\dir

Flags
* --silent  (Don't vocalize the actions being performed)
* --download-only  (Only download the audio files, don't play them back (useful for bulk creating a playlist))

## Setup
* Copy or Rename config.example.json to config.json
* Add your keys for models. OpenAI key is _required_ for OpenAi's natural text to speech which is the main feature of this app. (may support other platforms in the future)
* Add your output directory - this is where audio files generated for playback will be stored
* Add your selected model and model type for text summarization (openai, claude, ollama)

## Technical Decisions
Disclaimer: I'm not a daily Python coder but ironically the core implementation is in Python via experimentation and backported to C# via Claude 3.0 and hand fixup.
* Opted to use Pygame for audio playback in Python as it provided the most seamless user experience (other approaches required convoluted FFMPEG setup on Windows)
* Opted for OpenAI's voice - I personally enjoy the natural way they sound including vocal mannerisms. 

## Practical Notes
* **MAX_RESPONSE_TOKENS** has a very strong effect on how thorough or concise the summary is. At 720, you'll get a reasonable and detailed overview if the story is brief. I personally use 3072 since I use it for large stories or HackerNews threads. Expand this if you prefer a deeper dive - to the limits of your model. Of course, this has a direct effect on cost-per-query.
* In general, requires models with 16k+ context sizes in order to be useful (GPT-3.5-turbo, GPT-4-Turbo, Claude-2, Claude-3)
* Not all Ollama models support large context sizes.
* In practice Mistral was passable but most small/medium models (7B or less) did poorly or required tweaking to deliver useful summaries. YMMV!
* Claude-3 and GPT-4 did exceptionally well due to the large context sizes and recollect quality

## Roadmap
* Chromium and FF based plugins (investigating)
* Support for Mistral Pro (subscription based)
* Support for multiple audio generation models
