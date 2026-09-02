from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from n3_casting import assert_cast_gender, choose_voice, voice_gender

S1_MANIFEST = ROOT / "assets" / "audio" / "serie-1" / "quality-n3.json"
S2_MANIFEST = ROOT / "assets" / "audio" / "serie-2" / "quality-n3.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CastingUnitTests(unittest.TestCase):
    def setUp(self):
        self.pool = [
            {"voice": "pt-BR-AntonioNeural", "gender": "M"},
            {"voice": "pt-BR-ThalitaMultilingualNeural", "gender": "F"},
            {"voice": "pt-BR-FranciscaNeural", "gender": "F"},
        ]

    def test_male_role_gets_male_voice(self):
        voice = choose_voice(
            self.pool,
            ["pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
            expected_gender="M",
        )
        self.assertEqual("M", voice_gender(voice))

    def test_female_role_gets_female_voice(self):
        voice = choose_voice(
            self.pool,
            ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"],
            expected_gender="F",
        )
        self.assertEqual("F", voice_gender(voice))

    def test_fail_closed_without_compatible_voice(self):
        female_only = [{"voice": "pt-BR-FranciscaNeural", "gender": "F"}]
        with self.assertRaises(RuntimeError):
            choose_voice(female_only, ["pt-BR-FranciscaNeural"], expected_gender="M")

    def test_cross_gender_is_rejected(self):
        with self.assertRaises(RuntimeError):
            assert_cast_gender(
                {"TENTANTE_M": "pt-BR-FranciscaNeural"},
                {"TENTANTE_M": "M"},
                context="teste",
            )


class ManifestRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s1 = load(S1_MANIFEST)
        cls.s2 = load(S2_MANIFEST)

    def test_all_series1_explicit_genders_match_cast(self):
        for ep in self.s1["episodes"]:
            cast = ep.get("speaker_cast", {})
            expected = ep.get("speaker_gender", {})
            assert_cast_gender(cast, expected, context=f"A1-{ep['episode']:03d}")

    def test_all_series2_explicit_genders_match_cast(self):
        expected = self.s2.get("role_gender", {})
        for ep in self.s2["episodes"]:
            cast = ep.get("role_cast", {})
            assert_cast_gender(cast, expected, context=f"A2-{ep['episode']:03d}")

    def test_critical_male_dialogues_have_distinct_perceptual_identities(self):
        by_episode = {ep["episode"]: ep for ep in self.s1["episodes"]}
        for number in (8, 13, 15):
            ep = by_episode[number]
            identities = ep.get("voice_identity", {})
            male_speakers = [
                speaker
                for speaker, gender in ep.get("speaker_gender", {}).items()
                if gender == "M"
            ]
            self.assertGreaterEqual(len(male_speakers), 2, f"A1-{number:03d}: diálogo masculino incompleto")
            values = [identities[speaker] for speaker in male_speakers]
            self.assertEqual(
                len(values),
                len(set(values)),
                f"A1-{number:03d}: personagens masculinos sem identidade perceptual distinta",
            )

    def test_every_required_multivoice_episode_has_multiple_identities(self):
        for ep in self.s1["episodes"]:
            if ep.get("multivoice_required"):
                identities = set(ep.get("voice_identity", {}).values())
                self.assertGreaterEqual(len(identities), 2, f"A1-{ep['episode']:03d}")
        for ep in self.s2["episodes"]:
            if ep["episode"] in set(self.s2.get("cinematic_multivoice_episodes", [])):
                identities = set(ep.get("voice_identity", {}).values())
                self.assertGreaterEqual(len(identities), 2, f"A2-{ep['episode']:03d}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
