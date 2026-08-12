# Long Summary and Multi-Part Audio Plan

## Goal

Allow the summarization model to produce substantially longer, more complete
summaries without losing audio when the summary exceeds OpenAI's per-request
text-to-speech limits.

The first implementation will keep the full summary and generate numbered audio
files that are played in order. Audio concatenation can be added later without
changing the summary or chunking design.

## Current Behavior and Constraints

- `MAX_RESPONSE_TOKENS` limits summary generation. The active Python
  configuration currently uses 4090 tokens.
- The complete summary is sent to the Speech API in one request.
- OpenAI's Speech endpoint accepts at most 4096 input characters per request.
- `gpt-4o-mini-tts` also documents a 2000-input-token model limit.
- Streaming the response reduces latency and memory use, but does not increase
  either input limit.
- A summary over either limit causes audio generation to fail.

## Proposed Behavior

1. Generate and retain the complete summary.
2. Split the summary into ordered, natural-language chunks below both TTS
   limits.
3. Generate one audio file per chunk.
4. Number multi-part files in playback order.
5. Play every part sequentially unless `--download-only` is set.
6. Continue saving the complete textual summary as one `.txt` file when
   `--save-summaries` is used.

## Configuration

### Summary size

- Increase the documented/default `MAX_RESPONSE_TOKENS` from 2000 to 8192.
- Keep it user-configurable because supported output limits differ among
  OpenAI, Claude, and Ollama models.
- Do not use this setting to protect TTS. TTS chunking must handle any summary
  length independently.
- Update the README to explain that larger values increase summary depth, cost,
  generation time, audio duration, and the number of TTS requests.

### TTS chunk size

Define these separately from summary generation:

- API hard limit: 4096 characters.
- Model hard limit: 2000 input tokens.
- Application targets: 3800 characters and 1800 tokens.

The targets leave room for tokenizer differences and future request changes.
They should be named constants initially rather than user settings, preventing
an invalid configuration from exceeding provider limits.

Use `tiktoken` with the encoding appropriate for `gpt-4o-mini-tts`, falling
back explicitly to `o200k_base` if the model alias is not recognized. Character
and token checks must both pass for every chunk.

## Chunking Algorithm

Create a pure helper such as:

```python
split_text_for_tts(text, max_chars, max_tokens) -> list[str]
```

It will use the following hierarchy:

1. Normalize line endings while preserving all spoken text.
2. Split on blank lines to identify paragraphs.
3. Greedily pack complete paragraphs into the current chunk while both limits
   remain satisfied.
4. If one paragraph is too large, split it into sentences.
5. Greedily pack complete sentences using the same two limits.
6. If one sentence is too large, split it at whitespace.
7. Hard-split only an individual token or unbroken string that cannot otherwise
   fit.

Sentence detection should use a small, dependency-free regular expression that
splits after terminal punctuation. Perfect linguistic sentence recognition is
not required because the operation only chooses audio boundaries; it must not
delete, duplicate, reorder, or rewrite text.

Chunk invariants:

- Every non-empty chunk is within both application targets.
- Chunks retain source order.
- Joining chunks with normalized whitespace reproduces the complete normalized
  summary.
- Empty or whitespace-only input is rejected with a clear error.

## Output Naming

Preserve current naming for a one-part result:

```text
article.mp3
```

For multiple parts, use zero-padded suffixes:

```text
article_001.mp3
article_002.mp3
article_003.mp3
```

Rules:

- Derive all part names from the existing generated or fixed filename.
- Use at least three digits so filesystem sorting matches playback order.
- Determine padding from the total part count if more than 999 parts are ever
  generated.
- Write each request to a temporary part file and rename it only after that
  request succeeds, preventing corrupt files from appearing complete.
- Return the ordered list of completed paths from audio generation rather than
  reconstructing names during playback.

## Audio Generation Flow

Keep the existing single-request `generate_audio` function responsible for one
valid TTS chunk. Add an orchestrator such as:

```python
generate_audio_parts(summary, base_path, voice, model) -> list[Path]
```

The orchestrator will:

1. Chunk the complete summary.
2. Calculate all output paths.
3. Generate parts sequentially.
4. Print progress such as `Generating audio part 2 of 5`.
5. Return paths in playback order after all parts succeed.

Sequential generation is preferred initially because it simplifies ordering,
avoids rate-limit bursts, and makes failures easier to identify. Parallel
generation can be considered later if performance becomes a problem.

If a request fails:

- Report the failed part number and preserve already completed part files.
- Do not print the overall audio-success message.
- Do not play a knowingly incomplete set.
- Propagate the failure using the application's existing error behavior.

Resuming from existing completed parts can be added later, but filenames and
atomic writes should be designed so that feature does not require a format
change.

## Playback Flow

Update URL processing to use the ordered paths returned by
`generate_audio_parts`.

- When playback is enabled, call `play_mp3` once for each path in order.
- Keep the existing spinner active across the entire sequence, not once per
  part.
- When `--download-only` is set, generate every file but play none.
- `--silent` should retain its current meaning and not alter final-audio
  playback behavior.

## Saved Summaries

`--save-summaries` should continue producing one complete text file based on the
unsuffixed base audio path:

```text
article.txt
```

Do not create one text file per audio part. The numbered audio is an API
transport detail; the summary remains one logical document.

## Documentation Updates

Update:

- `config.example.json` with the larger example summary limit.
- `README.md` with the distinction between summary output limits and TTS input
  limits.
- CLI examples to show the resulting numbered files for long summaries.
- The outdated `main.py` comment that attributes the audio limit to Whisper.

Document that the number of audio files depends on the generated text rather
than `MAX_RESPONSE_TOKENS` directly.

## Test Plan

Add focused tests for:

### Chunking

- A short summary produces one unchanged chunk.
- Several small paragraphs are packed without exceeding either target.
- An oversized paragraph is divided at sentence boundaries.
- An oversized sentence is divided at whitespace.
- An unbroken oversized string is safely hard-split.
- Unicode and dense-token text remains below the token target.
- No content is lost, duplicated, or reordered.
- Empty input raises a clear error.

### Generation and filenames

- One chunk retains the existing filename.
- Multiple chunks produce `_001`, `_002`, and subsequent paths in order.
- Every chunk is sent with the configured model and voice.
- A failed part does not cause later parts to run or report overall success.
- Temporary files are not treated as completed output.

### Playback

- Generated parts are played in numeric order.
- `--download-only` skips all playback.
- Playback does not begin if generation fails partway through.
- The complete summary is saved once when requested.

## Implementation Sequence

1. Add tokenizer support and the pure text-chunking helper.
2. Add chunking unit tests, including full-text reconstruction assertions.
3. Add numbered-path and multi-part generation orchestration.
4. Update URL processing and sequential playback.
5. Add generation and playback tests.
6. Increase the example summary limit and update documentation.
7. Run targeted tests, then exercise a summary larger than 4096 characters
   against the real API and confirm every part plays in order.
8. Port the same behavior to `ReadItToMeDotNet` after the Python path is
   accepted, preserving matching naming and playback semantics.

## Acceptance Criteria

- Summary generation is not shortened to satisfy TTS.
- An 8192-token-cap summary can be converted without a request exceeding either
  TTS input limit.
- All summary text appears exactly once across the ordered TTS requests.
- Long outputs create correctly ordered, numbered MP3 files.
- Playback processes all parts sequentially when enabled.
- Download-only mode creates all parts without playback.
- Existing one-part output naming and behavior remain compatible.
- Failures identify the affected part and never report or play an incomplete
  result as successful.

## Deferred Work

- Concatenating parts into one final audio file.
- Parallel TTS generation.
- Automatic resumption of interrupted multi-part jobs.
- A playlist or manifest file describing the generated parts.
- Deleting numbered source parts after a future concatenation succeeds.
