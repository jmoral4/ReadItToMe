# ReadItToMe
Why use ReadItToMe rather than a screen reader? I built this tool for two major use cases.

1. Reading research papers and large web content in a smart way (don't read ads, don't read menus, etc etc).
2. Reading large forums and summarizing the findings, consensus, insights, etc.

In these cases, it blows a standard screenreader out of the water.

## Features
* Support for current OpenAI models through the Responses API
* Support for Anthropic Claude models
* Support for Ollama models through its Responses-compatible API

## Optional CLI usage
Specify Url
> py main.py --url "https://example.com/page"

Specify a filename (to reuse the same file. By default one file per webpage is generated)
> py main.py --fixed-filename "summary.mp3"

Summaries that exceed the text-to-speech limits are saved as ordered parts such as
`summary_001.mp3`, `summary_002.mp3`, and `summary_003.mp3`. Short summaries keep
the original `summary.mp3` filename.

Specify a 'playlist' or file with multiple urls, one per line, to process. Can be combined with --silent and --download-only to setup a playlist for later listening. 
> py main.py --playlist \your\directory\playlist.txt

Save the AI generated summaries for later viewing
> py main.py --save-summaries \output\dir

Flags
* --silent  (Don't vocalize the actions being performed)
* --download-only  (Only download the audio files, don't play them back (useful for bulk creating a playlist))
* --long  (Favor comprehensive, detailed coverage instead of the concise default. Depending on the source and token limit, this can produce 20+ minutes of audio and increase summarization and text-to-speech API costs.)

During generated-summary playback on Windows, press Space to pause or resume
from the current position, or Ctrl+C to stop the app. This control is not started
in download-only mode.

### Example (Download a playlist for use in a media player)
py main.py --playlist C:\git\HNplaylist.txt --download-only --silent

## Setup
* Requires Python 3.10 or newer.
* Install the Python dependencies with `py -m pip install -r requirements.txt`.
* Copy or Rename config.example.json to config.json
* Add your keys for models. An OpenAI key is _required_ for OpenAI text to speech, which is the main feature of this app.
* Add your output directory - this is where audio files generated for playback will be stored
* Add your selected model and model type for text summarization (openai, claude, ollama)
* Ollama is optional. To use it for summarization, install Ollama 0.13.3 or newer. `OLLAMA_HOST` is also optional and defaults to `http://localhost:11434`; the app uses its `/v1/responses` endpoint.
* `gpt-5.6-sol` is the recommended OpenAI summarization model. Use `gpt-5.6-terra` for a balance of intelligence and cost, or `gpt-5.6-luna` for cost-sensitive workloads.
* `gpt-4o-mini-tts` is OpenAI's current speech model. `marin` and `cedar` are the recommended voices.

## Technical Decisions
Disclaimer: I'm not a daily Python coder but ironically the core implementation is in Python via experimentation and backported to C# via Claude 3.0 and hand fixup.
* Opted to use Pygame for audio playback in Python as it provided the most seamless user experience (other approaches required convoluted FFMPEG setup on Windows)
* Opted for OpenAI's voice - I personally enjoy the natural way they sound including vocal mannerisms. 

## Practical Notes
* **MAX_RESPONSE_TOKENS** controls the summarization model's output limit and defaults to 8096 in the example configuration. Larger values can increase summary depth, model cost, generation time, audio duration, and the number of text-to-speech requests. Keep the value within the selected OpenAI, Claude, or Ollama model's supported output limit.
* Audio generation is chunked independently of **MAX_RESPONSE_TOKENS**. The app targets 3800 characters and 1800 tokens per request, safely below the speech API's 4096-character limit and the `gpt-4o-mini-tts` 2000-token limit. The number of resulting MP3 files depends on the generated text, not directly on the configured summary token limit.
* `--download-only` generates every numbered part without playing any of them. When playback is enabled, each completed part is queued and played in numeric order while later parts are still generating.
* `--save-summaries` always writes one complete, unsuffixed `.txt` summary even when the audio uses multiple numbered files.
* In general, models with large context windows produce the most useful summaries.
* Not all Ollama models support large context sizes.
* In practice Mistral was passable but most small/medium models (7B or less) did poorly or required tweaking to deliver useful summaries. YMMV!
* Current Claude and GPT models work especially well because of their large context windows and recall quality.

## Roadmap
* Chromium and FF based plugins (investigating)
* Better tested support for specific local models (ollama, oobabooga, or anything that supports the OpenAI api)
* Support for multiple audio generation models
