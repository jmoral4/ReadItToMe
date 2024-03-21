# ReadItToMe
Why use ReadItToMe rather than a screen reader? I built this tool for two major use cases.

1. Reading research papers and large web content in a smart way (don't read ads, don't read menus, etc etc).
2. Reading large forums and summarizing the findings, consensus, insights, etc.

In these cases, it blows a stock screenreader out of the water. 

Next step, a Chromium based plugin.

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
