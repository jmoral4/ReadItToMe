# Spacebar Playback Controls

## Goal

Allow users to press the spacebar while generated audio is playing to toggle
between paused and playing states.

## Scope

The first implementation will target the Python CLI on Windows, matching the
project's current primary playback environment.

- Space pauses the currently playing generated summary.
- Pressing Space again resumes from the same position.
- The control remains available across every part of a multipart summary.
- The control applies to final summary playback, not short status clips such as
  `gettingcontent.mp3`, `summary.mp3`, or `genaudio.mp3`.
- Download-only mode does not start a keyboard listener.
- Playback behavior is unchanged when no key is pressed.

Cross-platform terminal input and equivalent support in the .NET port are
separate follow-up tasks.

## Proposed Design

Pygame already exposes the required playback operations:

```python
pygame.mixer.music.pause()
pygame.mixer.music.unpause()
```

Add a playback-control object that owns the paused state and synchronizes access
to it. The object should expose a toggle operation so keyboard handling does not
need to manipulate Pygame or shared state directly.

When summary playback starts:

1. Start the existing audio playback thread.
2. Start a daemon keyboard-listener thread using the Windows standard-library
   `msvcrt` module.
3. Poll `msvcrt.kbhit()` and read available keys with `msvcrt.getwch()`.
4. Toggle playback when the returned character is `" "`.
5. Print `Playback paused` or `Playback resumed` after each successful toggle.
6. Signal the listener to stop after the playback queue has finished, then join
   it before returning.

The listener must use a short wait between polls so it does not consume a CPU
core. A `threading.Event` can provide both the stop signal and an interruptible
wait.

## Threading and Lifecycle

Audio generation runs on the main thread while completed audio parts are
consumed by the playback thread. Keyboard input therefore needs its own thread
so pausing remains responsive during generation.

The playback-control state should live for the entire summary rather than for
one MP3 part. This ensures that:

- one listener serves all queued parts;
- thread cleanup happens once per summary;
- state cannot leak into the next URL in playlist mode.

The listener must stop in a `finally` block whether generation succeeds,
playback succeeds, or either operation raises an exception.

If playback finishes while paused, cleanup should still complete without
requiring another key press. Other keys should be consumed and ignored while
the listener is active.

## Terminal Behavior

Print the following hint when interactive summary playback begins:

```text
Press Space to pause or resume playback.
```

`msvcrt.getwch()` reads a key immediately without requiring Enter and without
echoing the space to the terminal. Redirected or unavailable console input
should be detected explicitly; failure to start interactive controls should be
reported without falsely indicating that Space is available.

## Testing

Unit tests should mock keyboard reads and Pygame mixer calls rather than require
an audio device or interactive terminal.

Required cases:

- Space pauses active playback.
- A second Space resumes playback.
- Non-Space keys do not alter playback state.
- The paused state is preserved while the current MP3 remains active.
- The listener starts only for generated-summary playback.
- Download-only mode starts neither playback nor keyboard input.
- The listener stops after all queued parts finish.
- The listener stops when generation or playback fails.
- A new playlist item starts in the playing state.

## Acceptance Criteria

- A single Space press pauses audible summary playback promptly.
- A second Space press resumes from the paused position.
- Enter is not required and the key press is not echoed.
- Multipart and playlist playback retain their existing ordering.
- Playback and input threads terminate cleanly on success and failure.
- Existing non-interactive and download-only behavior remains unchanged.
