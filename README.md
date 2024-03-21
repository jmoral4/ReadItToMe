# ReadItToMe
Python app to generate detailed summaries of web pages and then generate ai voice tracks that can read them back to you.

## Features
* Support for OpenAI models  (GPT-3/GPT-4)
* Support for Anthropic models (Claude-2/3)
* Support for Ollama Models (Mistral, Llama2, etc)

## Optional CLI usage
Specify Url
> python main.py --url "https://example.com/page"

Specify a filename (to reuse the same file, otherwise, one file per webpage is generated)
> python main.py --fixed-filename "summary.mp3" 

## Config
* Update the output_dir to your desired path
* Add your own OpenAI/anthropic key or use Ollama for free!

## Practical Notes
* Not all Ollama models support large context sizes.
* In practice Mistral was passable but most small/medium models did poorly or require tweaking. YMMV!
* Claude-3 and GPT-4 did exceptionally well due to the large context sizes (turbo and recollect quality)
