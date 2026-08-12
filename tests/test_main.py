import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import main


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
        self.assertIn("helpful AI assistant", request["instructions"])
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


if __name__ == "__main__":
    unittest.main()
