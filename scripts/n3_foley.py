from __future__ import annotations

import math
import random
from typing import Iterable

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise

SR = 44100


def _quiet(seg: AudioSegment, db: float) -> AudioSegment:
    if seg.dBFS == float('-inf'):
        return seg
    return seg.apply_gain(db - seg.dBFS)


def room_tone(duration_ms: int) -> AudioSegment:
    base = WhiteNoise().to_audio_segment(duration=duration_ms).low_pass_filter(900).high_pass_filter(80)
    return _quiet(base, -42).set_channels(2)


def wind(duration_ms: int) -> AudioSegment:
    base = WhiteNoise().to_audio_segment(duration=duration_ms).low_pass_filter(1200).high_pass_filter(110)
    base = _quiet(base, -38).set_channels(2)
    # Lenta modulação de presença sem efeito musical.
    chunks = []
    step = 800
    for i in range(0, duration_ms, step):
        c = base[i:i+step]
        gain = -3.0 + 2.5 * math.sin(i / 3000.0)
        chunks.append(c.apply_gain(gain))
    return sum(chunks, AudioSegment.empty())[:duration_ms]


def traffic_bed(duration_ms: int) -> AudioSegment:
    low = WhiteNoise().to_audio_segment(duration=duration_ms).low_pass_filter(650).high_pass_filter(55)
    low = _quiet(low, -41).set_channels(2)
    return low


def traffic_pass(duration_ms: int = 4200) -> AudioSegment:
    base = WhiteNoise().to_audio_segment(duration=duration_ms).low_pass_filter(950).high_pass_filter(70)
    base = _quiet(base, -31)
    out = AudioSegment.silent(duration=0).set_channels(2)
    steps = 14
    chunk = max(80, duration_ms // steps)
    for i in range(steps):
        part = base[i*chunk:(i+1)*chunk]
        if not len(part):
            continue
        pos = -0.9 + 1.8 * (i / max(1, steps - 1))
        envelope = -8 + 8 * math.sin(math.pi * i / max(1, steps - 1))
        out += part.pan(pos).apply_gain(envelope)
    return out[:duration_ms]


def footsteps(count: int = 6, interval_ms: int = 560) -> AudioSegment:
    total = max(900, (count - 1) * interval_ms + 700)
    out = AudioSegment.silent(duration=total).set_channels(2)
    rng = random.Random(31082026 + count)
    for i in range(count):
        thump = Sine(rng.randint(70, 105)).to_audio_segment(duration=rng.randint(75, 120)).fade_out(90)
        texture = WhiteNoise().to_audio_segment(duration=90).low_pass_filter(1800).apply_gain(-18).fade_out(80)
        hit = (thump.apply_gain(-10).overlay(texture)).set_channels(2).pan(-0.25 if i % 2 == 0 else 0.25)
        out = out.overlay(hit, position=i * interval_ms)
    return _quiet(out, -29)


def cup_tap() -> AudioSegment:
    click = Sine(1850).to_audio_segment(duration=55).fade_out(50).apply_gain(-10)
    body = Sine(620).to_audio_segment(duration=170).fade_out(160).apply_gain(-17)
    noise = WhiteNoise().to_audio_segment(duration=45).high_pass_filter(1800).apply_gain(-25)
    return click.overlay(body).overlay(noise).set_channels(2)


def lighter() -> AudioSegment:
    click = WhiteNoise().to_audio_segment(duration=35).high_pass_filter(2800).apply_gain(-13)
    spark = WhiteNoise().to_audio_segment(duration=180).high_pass_filter(1600).fade_out(160).apply_gain(-24)
    return click.overlay(spark, position=28).set_channels(2)


def cigarette_crackle(duration_ms: int = 2200) -> AudioSegment:
    out = AudioSegment.silent(duration=duration_ms).set_channels(2)
    rng = random.Random(20260831)
    for _ in range(max(3, duration_ms // 420)):
        pos = rng.randint(0, max(0, duration_ms - 30))
        c = WhiteNoise().to_audio_segment(duration=rng.randint(8, 25)).high_pass_filter(3000).apply_gain(-32)
        out = out.overlay(c.set_channels(2).pan(rng.uniform(-0.25, 0.25)), position=pos)
    return out


def club_ambience(duration_ms: int) -> AudioSegment:
    crowd = WhiteNoise().to_audio_segment(duration=duration_ms).low_pass_filter(1800).high_pass_filter(180)
    crowd = _quiet(crowd, -39).set_channels(2)
    # Pulso grave sintético sem melodia e sem material musical protegido.
    pulse = AudioSegment.silent(duration=duration_ms).set_channels(2)
    for pos in range(0, duration_ms, 620):
        hit = Sine(58).to_audio_segment(duration=150).fade_out(130).apply_gain(-27).set_channels(2)
        pulse = pulse.overlay(hit, position=pos)
    return crowd.overlay(pulse)


def studio_tone(duration_ms: int) -> AudioSegment:
    return _quiet(WhiteNoise().to_audio_segment(duration=duration_ms).low_pass_filter(700).high_pass_filter(120), -46).set_channels(2)


def build_bed(scene: str, duration_ms: int) -> AudioSegment:
    if scene == 'nightclub':
        return club_ambience(duration_ms)
    if scene == 'bridge':
        return room_tone(duration_ms).overlay(wind(duration_ms)).overlay(traffic_bed(duration_ms))
    if scene == 'living_room':
        return room_tone(duration_ms)
    if scene == 'studio':
        return studio_tone(duration_ms)
    if scene == 'home_table':
        return room_tone(duration_ms)
    return AudioSegment.silent(duration=duration_ms).set_channels(2)


def event(name: str) -> AudioSegment:
    if name == 'traffic_pass':
        return traffic_pass()
    if name == 'footsteps':
        return footsteps()
    if name == 'cup_tap':
        return cup_tap()
    if name == 'lighter':
        return lighter()
    if name == 'cigarette_crackle':
        return cigarette_crackle()
    raise KeyError(f'Efeito N3 desconhecido: {name}')


def apply_sound_design(voice: AudioSegment, scene: str, events: Iterable[dict] = ()) -> AudioSegment:
    voice = voice.set_channels(2)
    bed = build_bed(scene, len(voice))
    mixed = voice.overlay(bed)
    for item in events:
        fx = event(str(item['name']))
        at = item.get('at', 0)
        if isinstance(at, float) and 0 <= at <= 1:
            position = int(len(voice) * at)
        else:
            position = int(at)
        gain = float(item.get('gain_db', 0))
        pan = item.get('pan')
        if pan is not None:
            fx = fx.pan(float(pan))
        mixed = mixed.overlay(fx.apply_gain(gain), position=max(0, position))
    return mixed
