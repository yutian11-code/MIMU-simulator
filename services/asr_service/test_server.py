import base64
import unittest

from services.asr_service.server import parse_audio_data_url


class ParseAudioDataUrlTest(unittest.TestCase):
    def test_parses_wav_data_url(self):
        payload = base64.b64encode(b"RIFF....WAVEfmt ").decode("ascii")

        parsed = parse_audio_data_url(f"data:audio/wav;base64,{payload}")

        self.assertEqual(parsed.mime_type, "audio/wav")
        self.assertEqual(parsed.suffix, ".wav")
        self.assertEqual(parsed.content, b"RIFF....WAVEfmt ")

    def test_rejects_non_data_url(self):
        with self.assertRaises(ValueError):
            parse_audio_data_url("not-base64")


if __name__ == "__main__":
    unittest.main()
