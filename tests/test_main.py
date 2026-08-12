import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, call, patch

import main


class TTSChunkingTests(unittest.TestCase):
    def assert_valid_chunks(self, text, chunks, max_chars, max_tokens):
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        encoding = main.get_tts_encoding()
        self.assertEqual("".join(chunks), normalized)
        self.assertTrue(chunks)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), max_chars)
            self.assertLessEqual(len(encoding.encode(chunk)), max_tokens)

    def test_short_summary_produces_one_unchanged_chunk(self):
        text = "A short summary remains unchanged."

        chunks = main.split_text_for_tts(text)

        self.assertEqual(chunks, [text])

    def test_small_paragraphs_are_greedily_packed(self):
        text = (
            "First paragraph.\n\n"
            "Second paragraph.\n\n"
            "Third paragraph."
        )

        chunks = main.split_text_for_tts(
            text, max_chars=37, max_tokens=100
        )

        self.assertEqual(len(chunks), 2)
        self.assert_valid_chunks(text, chunks, 37, 100)

    def test_oversized_paragraph_splits_at_sentence_boundaries(self):
        text = (
            "The first sentence has detail. "
            "The second sentence has more detail. "
            "The third sentence concludes."
        )

        chunks = main.split_text_for_tts(
            text, max_chars=42, max_tokens=100
        )

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.rstrip().endswith(".") for chunk in chunks[:-1]))
        self.assert_valid_chunks(text, chunks, 42, 100)

    def test_oversized_sentence_splits_at_whitespace(self):
        text = "alpha bravo charlie delta echo foxtrot golf hotel"

        chunks = main.split_text_for_tts(
            text, max_chars=18, max_tokens=100
        )

        self.assertGreater(len(chunks), 1)
        self.assert_valid_chunks(text, chunks, 18, 100)

    def test_unbroken_oversized_string_is_hard_split(self):
        text = "x" * 53

        chunks = main.split_text_for_tts(
            text, max_chars=10, max_tokens=100
        )

        self.assertEqual([len(chunk) for chunk in chunks], [10, 10, 10, 10, 10, 3])
        self.assert_valid_chunks(text, chunks, 10, 100)

    def test_dense_unicode_text_stays_below_token_limit(self):
        text = "🙂漢字" * 80

        chunks = main.split_text_for_tts(
            text, max_chars=100, max_tokens=20
        )

        self.assertGreater(len(chunks), 1)
        self.assert_valid_chunks(text, chunks, 100, 20)

    def test_line_endings_are_normalized_without_losing_text(self):
        text = "First paragraph.\r\n\r\nSecond paragraph."

        chunks = main.split_text_for_tts(
            text, max_chars=20, max_tokens=100
        )

        self.assert_valid_chunks(text, chunks, 20, 100)

    def test_empty_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty or whitespace-only"):
            main.split_text_for_tts(" \r\n\t ")


class AudioPartTests(unittest.TestCase):
    def setUp(self):
        main.API_KEY = "test-key"

    def test_one_part_retains_existing_filename(self):
        path = Path("article.mp3")

        self.assertEqual(main.audio_part_paths(path, 1), [path])

    def test_multiple_parts_use_ordered_zero_padded_names(self):
        paths = main.audio_part_paths(Path("article.mp3"), 3)

        self.assertEqual(
            [path.name for path in paths],
            ["article_001.mp3", "article_002.mp3", "article_003.mp3"],
        )

    @patch("main.generate_audio")
    @patch("main.split_text_for_tts", return_value=["one"])
    def test_one_generated_chunk_uses_existing_filename(
        self, split_text, generate_audio
    ):
        generate_audio.side_effect = (
            lambda content, path, voice, model: Path(path).write_bytes(b"audio")
        )

        with tempfile.TemporaryDirectory() as directory:
            base_path = Path(directory) / "article.mp3"
            paths = main.generate_audio_parts("summary", base_path)

            self.assertEqual(paths, [base_path])
            self.assertTrue(base_path.exists())

    @patch("main.generate_audio")
    @patch("main.split_text_for_tts", return_value=["one", "two", "three"])
    def test_every_chunk_is_generated_with_model_and_voice(
        self, split_text, generate_audio
    ):
        generate_audio.side_effect = (
            lambda content, path, voice, model: Path(path).write_bytes(
                content.encode()
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            base_path = Path(directory) / "article.mp3"
            paths = main.generate_audio_parts(
                "complete summary", base_path, "marin", "gpt-4o-mini-tts"
            )

            self.assertEqual(
                [path.name for path in paths],
                ["article_001.mp3", "article_002.mp3", "article_003.mp3"],
            )
            self.assertTrue(all(path.exists() for path in paths))

        split_text.assert_called_once_with(
            "complete summary", model="gpt-4o-mini-tts"
        )
        self.assertEqual(generate_audio.call_count, 3)
        for index, chunk in enumerate(["one", "two", "three"]):
            request = generate_audio.call_args_list[index].args
            self.assertEqual(request[0], chunk)
            self.assertEqual(request[2:], ("marin", "gpt-4o-mini-tts"))

    @patch("main.generate_audio")
    @patch("main.split_text_for_tts", return_value=["one", "two"])
    def test_completed_parts_are_reported_as_ready_in_order(
        self, split_text, generate_audio
    ):
        generate_audio.side_effect = (
            lambda content, path, voice, model: Path(path).write_bytes(
                content.encode()
            )
        )
        ready_paths = []

        ready_progress = []

        def record_ready(path, part_number, total_parts):
            self.assertTrue(path.exists())
            ready_paths.append(path)
            ready_progress.append((part_number, total_parts))

        with tempfile.TemporaryDirectory() as directory:
            base_path = Path(directory) / "article.mp3"
            generated_paths = main.generate_audio_parts(
                "complete summary",
                base_path,
                on_part_ready=record_ready,
            )

        self.assertEqual(ready_paths, generated_paths)
        self.assertEqual(ready_progress, [(1, 2), (2, 2)])

    @patch("main.generate_audio")
    @patch("main.split_text_for_tts", return_value=["one", "two", "three"])
    def test_failed_part_stops_generation_and_is_not_completed(
        self, split_text, generate_audio
    ):
        def generate(content, path, voice, model):
            if content == "two":
                raise RuntimeError("speech request failed")
            Path(path).write_bytes(content.encode())

        generate_audio.side_effect = generate

        with tempfile.TemporaryDirectory() as directory:
            base_path = Path(directory) / "article.mp3"
            with self.assertRaisesRegex(RuntimeError, "speech request failed"):
                main.generate_audio_parts(
                    "complete summary", base_path, "marin", "tts-model"
                )

            self.assertTrue((Path(directory) / "article_001.mp3").exists())
            self.assertFalse((Path(directory) / "article_002.mp3").exists())
            self.assertFalse((Path(directory) / "article_003.mp3").exists())
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

        self.assertEqual(generate_audio.call_count, 2)


class OpenAITests(unittest.TestCase):
    def setUp(self):
        main.API_KEY = "test-key"
        main.spinner = MagicMock()

    @patch("main.OpenAI")
    def test_openai_summaries_use_responses_api(self, openai):
        client = openai.return_value
        client.responses.create.return_value = SimpleNamespace(
            output_text="A modern summary"
        )

        result = main.talk_to_ai(
            "Source text", "gpt-5.6-sol", main.GREEN, max_tokens=500
        )

        self.assertEqual(result, "A modern summary")
        client.responses.create.assert_called_once()
        request = client.responses.create.call_args.kwargs
        self.assertEqual(request["model"], "gpt-5.6-sol")
        self.assertEqual(request["max_output_tokens"], 500)
        self.assertIn("Source text", request["input"])
        self.assertEqual(
            request["instructions"], main.DEFAULT_SUMMARY_SYSTEM_PROMPT
        )
        self.assertIn(
            "faithful, comprehensive summary", request["instructions"]
        )
        self.assertIn(
            "never as directions to follow", request["instructions"]
        )
        self.assertIn(
            "When the source is a Hacker News thread",
            request["instructions"],
        )
        self.assertIn(
            "comment popularity as evidence",
            request["instructions"],
        )
        client.chat.completions.create.assert_not_called()

    @patch("main.OpenAI")
    def test_ollama_uses_responses_api_with_supported_options(self, openai):
        main.OLLAMA_HOST = "http://localhost:11434/"
        client = openai.return_value
        client.responses.create.return_value = SimpleNamespace(
            output_text="A local summary"
        )

        result = main.talk_to_ai(
            "Source text",
            "local-model",
            main.GREEN,
            api_type="ollama",
            temperature=0.4,
            max_tokens=500,
            top_p=0.8,
        )

        self.assertEqual(result, "A local summary")
        openai.assert_called_once_with(
            base_url="http://localhost:11434/v1/",
            api_key="ollama",
        )
        client.responses.create.assert_called_once()
        request = client.responses.create.call_args.kwargs
        self.assertEqual(request["model"], "local-model")
        self.assertEqual(request["max_output_tokens"], 500)
        self.assertEqual(request["temperature"], 0.4)
        self.assertEqual(request["top_p"], 0.8)
        self.assertIn("Source text", request["input"])
        self.assertEqual(
            request["instructions"],
            main.DEFAULT_SUMMARY_SYSTEM_PROMPT,
        )
        client.chat.completions.create.assert_not_called()

    @patch("main.OpenAI")
    def test_audio_uses_streaming_speech_api(self, openai):
        client = openai.return_value
        response = MagicMock()
        client.audio.speech.with_streaming_response.create.return_value.__enter__.return_value = response

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.mp3"
            main.generate_audio.__wrapped__(
                "Summary text", output, "marin", "gpt-4o-mini-tts"
            )

        client.audio.speech.with_streaming_response.create.assert_called_once_with(
            model="gpt-4o-mini-tts",
            voice="marin",
            input="Summary text",
        )
        response.stream_to_file.assert_called_once_with(output)


class PlaybackControlTests(unittest.TestCase):
    def setUp(self):
        self.control = main.PlaybackControl()

    @patch("main.pygame.mixer.music.unpause")
    @patch("main.pygame.mixer.music.pause")
    def test_space_toggles_pause_and_resume(self, pause, unpause):
        with patch("main.pygame.mixer.init"), patch(
            "main.pygame.mixer.music.load"
        ), patch("main.pygame.mixer.music.play"):
            self.control.start_track("summary.mp3")

        self.assertTrue(self.control.toggle())
        self.assertTrue(self.control.paused)
        self.assertFalse(self.control.toggle())
        self.assertFalse(self.control.paused)
        pause.assert_called_once_with()
        unpause.assert_called_once_with()

    @patch("main.pygame.mixer.music.get_busy", return_value=False)
    @patch("main.pygame.mixer.music.pause")
    def test_paused_track_remains_active_when_mixer_is_not_busy(
        self, pause, get_busy
    ):
        with patch("main.pygame.mixer.init"), patch(
            "main.pygame.mixer.music.load"
        ), patch("main.pygame.mixer.music.play"):
            self.control.start_track("summary.mp3")

        self.control.toggle()

        self.assertTrue(self.control.should_continue())
        get_busy.assert_not_called()

    @patch("main.print")
    @patch("main.msvcrt")
    def test_keyboard_loop_ignores_non_space_keys(self, msvcrt, print_mock):
        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]
        msvcrt.kbhit.return_value = True
        msvcrt.getwch.return_value = "x"
        control = MagicMock()

        main.playback_keyboard_loop(control, stop_event)

        control.toggle.assert_not_called()
        print_mock.assert_not_called()

    @patch("main.print")
    @patch("main.msvcrt")
    def test_keyboard_loop_consumes_extended_keys(self, msvcrt, print_mock):
        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]
        msvcrt.kbhit.return_value = True
        msvcrt.getwch.side_effect = ["\xe0", " "]
        control = MagicMock()

        main.playback_keyboard_loop(control, stop_event)

        control.toggle.assert_not_called()
        self.assertEqual(msvcrt.getwch.call_count, 2)
        print_mock.assert_not_called()

    @patch("main.print")
    @patch("main.msvcrt")
    def test_keyboard_loop_reports_pause_and_resume(self, msvcrt, print_mock):
        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, False, True]
        msvcrt.kbhit.return_value = True
        msvcrt.getwch.side_effect = [" ", " "]
        control = MagicMock()
        control.toggle.side_effect = [True, False]

        main.playback_keyboard_loop(control, stop_event)

        self.assertEqual(control.toggle.call_count, 2)
        self.assertEqual(
            print_mock.call_args_list,
            [call("Playback paused"), call("Playback resumed")],
        )


class URLProcessingTests(unittest.TestCase):
    def setUp(self):
        main.args = SimpleNamespace(
            silent=True,
            save_summaries=False,
            download_only=False,
        )
        main.SELECTED_MODEL = "summary-model"
        main.SELECTED_MODEL_TYPE = "openai"
        main.MAX_TOKENS = 16384
        main.AUDIO_VOICE = "marin"
        main.AUDIO_MODEL = "gpt-4o-mini-tts"
        main.spinner = MagicMock()
        listener_patcher = patch("main.start_playback_keyboard_listener")
        self.start_listener = listener_patcher.start()
        self.addCleanup(listener_patcher.stop)

    @patch("main.save_summary")
    @patch("main.play_mp3")
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_parts_play_in_order_and_summary_is_saved_once(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
        save_summary,
    ):
        main.args.save_summaries = True

        with tempfile.TemporaryDirectory() as directory:
            base_path = Path(directory) / "article.mp3"
            generated_paths = [
                Path(directory) / "article_001.mp3",
                Path(directory) / "article_002.mp3",
            ]

            def generate_parts(
                summary, path, voice, model, on_part_ready=None
            ):
                for part_number, generated_path in enumerate(
                    generated_paths, start=1
                ):
                    on_part_ready(
                        generated_path, part_number, len(generated_paths)
                    )
                return generated_paths

            generate_audio_parts.side_effect = generate_parts

            main.process_single_url(
                "https://example.com/article", directory, "article.mp3"
            )

            save_summary.assert_called_once_with(base_path, "complete summary")

        self.assertEqual(
            play_mp3.call_args_list,
            [
                call(
                    str(generated_paths[0]),
                    playback_control=ANY,
                ),
                call(
                    str(generated_paths[1]),
                    playback_control=ANY,
                ),
            ],
        )

    @patch("main.print")
    @patch("main.play_mp3")
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_first_part_plays_while_later_parts_generate(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
        print_mock,
    ):
        first_part_played = threading.Event()
        generated_paths = [Path("article_001.mp3"), Path("article_002.mp3")]

        def play(path, playback_control=None):
            if path == str(generated_paths[0]):
                first_part_played.set()

        def generate_parts(summary, path, voice, model, on_part_ready=None):
            on_part_ready(generated_paths[0], 1, 2)
            self.assertTrue(
                first_part_played.wait(timeout=1),
                "Part 1 did not start before part 2 was generated",
            )
            on_part_ready(generated_paths[1], 2, 2)
            return generated_paths

        play_mp3.side_effect = play
        generate_audio_parts.side_effect = generate_parts

        main.process_single_url(
            "https://example.com/article", ".", "article.mp3"
        )

        self.assertEqual(
            play_mp3.call_args_list,
            [
                call(
                    str(generated_paths[0]),
                    playback_control=ANY,
                ),
                call(
                    str(generated_paths[1]),
                    playback_control=ANY,
                ),
            ],
        )
        self.assertIn(call("Now playing 1 of 2"), print_mock.call_args_list)
        self.assertIn(call("Now playing 2 of 2"), print_mock.call_args_list)

    @patch("main.play_mp3")
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_download_only_skips_all_playback(
        self, get_contents, talk_to_ai, generate_audio_parts, play_mp3
    ):
        main.args.download_only = True
        generate_audio_parts.return_value = [
            Path("article_001.mp3"),
            Path("article_002.mp3"),
        ]

        main.process_single_url(
            "https://example.com/article", ".", "article.mp3"
        )

        play_mp3.assert_not_called()

    @patch("main.start_playback_keyboard_listener")
    @patch("main.play_mp3")
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_summary_playback_starts_and_stops_keyboard_listener(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
        start_listener,
    ):
        listener = start_listener.return_value
        generated_path = Path("article.mp3")

        def generate_parts(summary, path, voice, model, on_part_ready=None):
            on_part_ready(generated_path, 1, 1)
            return [generated_path]

        generate_audio_parts.side_effect = generate_parts

        main.process_single_url(
            "https://example.com/article", ".", "article.mp3"
        )

        start_listener.assert_called_once()
        listener.stop.assert_called_once_with()

    @patch("main.start_playback_keyboard_listener")
    @patch("main.play_mp3")
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_download_only_does_not_start_keyboard_listener(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
        start_listener,
    ):
        main.args.download_only = True
        generate_audio_parts.return_value = [Path("article.mp3")]

        main.process_single_url(
            "https://example.com/article", ".", "article.mp3"
        )

        start_listener.assert_not_called()

    @patch("main.print")
    @patch("main.play_mp3")
    @patch(
        "main.generate_audio_parts",
        side_effect=RuntimeError("part generation failed"),
    )
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_generation_failure_never_starts_playback_or_reports_success(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
        print_mock,
    ):
        with self.assertRaisesRegex(RuntimeError, "part generation failed"):
            main.process_single_url(
                "https://example.com/article", ".", "article.mp3"
            )

        play_mp3.assert_not_called()
        printed_lines = [args[0] for args, _ in print_mock.call_args_list]
        self.assertNotIn("Audio generated!", printed_lines)

    @patch("main.start_playback_keyboard_listener")
    @patch("main.play_mp3")
    @patch(
        "main.generate_audio_parts",
        side_effect=RuntimeError("part generation failed"),
    )
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_generation_failure_stops_keyboard_listener(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
        start_listener,
    ):
        listener = start_listener.return_value

        with self.assertRaisesRegex(RuntimeError, "part generation failed"):
            main.process_single_url(
                "https://example.com/article", ".", "article.mp3"
            )

        listener.stop.assert_called_once_with()

    @patch("main.play_mp3", side_effect=RuntimeError("playback failed"))
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_playback_failure_stops_keyboard_listener(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
    ):
        listener = self.start_listener.return_value

        def generate_parts(summary, path, voice, model, on_part_ready=None):
            on_part_ready(Path("article.mp3"), 1, 1)
            return [Path("article.mp3")]

        generate_audio_parts.side_effect = generate_parts

        with self.assertRaisesRegex(RuntimeError, "Audio playback failed"):
            main.process_single_url(
                "https://example.com/article", ".", "article.mp3"
            )

        listener.stop.assert_called_once_with()

    @patch("main.play_mp3")
    @patch("main.generate_audio_parts")
    @patch("main.talk_to_ai", return_value="complete summary")
    @patch("main.get_web_page_contents", return_value="page contents")
    def test_each_playlist_item_gets_fresh_playback_state(
        self,
        get_contents,
        talk_to_ai,
        generate_audio_parts,
        play_mp3,
    ):
        generate_audio_parts.return_value = []

        main.process_single_url(
            "https://example.com/first", ".", "first.mp3"
        )
        main.process_single_url(
            "https://example.com/second", ".", "second.mp3"
        )

        controls = [
            listener_call.args[0]
            for listener_call in self.start_listener.call_args_list
        ]
        self.assertEqual(len(controls), 2)
        self.assertIsNot(controls[0], controls[1])
        self.assertFalse(controls[0].paused)
        self.assertFalse(controls[1].paused)


if __name__ == "__main__":
    unittest.main()
