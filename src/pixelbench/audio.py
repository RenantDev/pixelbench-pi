"""Ambient soundtrack, synthesised in numpy - no audio files shipped.

The track is a 32 s seamless loop: a four-chord pad, a bass, sparse bells on a
pentatonic scale, and surf noise that breathes in time with the water on screen.

Read `docs/audio-synthesis.md` before changing anything here. The short version:
an earlier version distorted on monitor speakers and it was NOT clipping - it
was 13.4% of the energy sitting below 20 Hz, inaudible infrasound that drives
the cone to the end of its travel and smears everything above it. Measure the
sub-20 Hz content before concluding that a problem is about volume.
"""

import sys

import numpy as np
import pygame

RATE = 44100          # Hz
LOOP_SECONDS = 32.0   # one turn (four 8 s chords)
HIGHPASS_HZ = 50.0    # below this is infrasound: it only makes the speaker
                      # work for nothing and muddies what sits above it
TARGET_RMS = 0.11     # background-track level (~-19 dBFS)
CEILING = 0.72        # peak ceiling after the limiter

# Progression in A minor: Am9 - Fmaj7 - Cmaj7 - G6/9. MIDI numbers.
PROGRESSION = [
    (45, (57, 60, 64, 71)),   # Am9
    (41, (53, 57, 60, 64)),   # Fmaj7
    (48, (60, 64, 67, 71)),   # Cmaj7
    (43, (55, 59, 62, 64)),   # G6/9
]
# A minor pentatonic for the bells.
BELLS = (69, 72, 74, 76, 79, 81, 84)


def _hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def _whole_cycles(f, dur):
    """Snap a frequency so a whole number of cycles fits the loop.

    This is what makes the loop join without a click: every sine starts and
    ends on exactly the same phase.
    """
    return max(1.0, round(f * dur)) / dur


def _sine(f, t, dur, harm=1, phase=0.0):
    """float32 sine with whole cycles and its own starting phase.

    The phase is randomised per partial on purpose: with every sine starting at
    zero they add up coherently and build tall peaks (a large crest factor)
    without gaining any perceived loudness. A constant phase does not change
    the period, so the loop still joins seamlessly.
    """
    return np.sin(np.float32(2 * np.pi * _whole_cycles(f * harm, dur)) * t
                  + np.float32(phase))


def _chord_window(t, center, width, dur):
    """Circular Hann window: chords cross-fade with no step in level."""
    d = np.abs((t - center + dur / 2) % dur - dur / 2) / width
    return np.where(d < 1.0, 0.5 * (1.0 + np.cos(np.pi * d)), 0.0)


def _highpass(x, cutoff, rate):
    """Cut the infrasound with a soft ramp. Done by FFT: does not break the loop."""
    n = len(x)
    spec = np.fft.rfft(x, axis=0)
    fr = np.fft.rfftfreq(n, 1.0 / rate)
    g = np.clip((fr - cutoff / 3.0) / (cutoff - cutoff / 3.0), 0.0, 1.0)
    g = 0.5 - 0.5 * np.cos(np.pi * g)          # half-cosine, no step
    spec *= g[:, None] if x.ndim == 2 else g
    return np.fft.irfft(spec, n, axis=0).astype(np.float32)


def _limiter(x, ceiling=CEILING, knee=0.55):
    """Safety net: compress only what crosses the knee, leave the rest untouched."""
    a = np.abs(x)
    excess = np.clip((a - knee) / (ceiling - knee), 0.0, None)
    target = knee + (ceiling - knee) * np.tanh(excess)
    return np.where(a <= knee, x, x * target / np.maximum(a, 1e-9)).astype(np.float32)


def _colored_noise(n, exponent, rng):
    """Noise with a 1/f^exponent spectrum, built by FFT (loops perfectly)."""
    spec = rng.normal(size=n // 2 + 1) + 1j * rng.normal(size=n // 2 + 1)
    f = np.arange(len(spec))
    f[0] = 1
    spec *= f ** (-exponent)
    # Zero everything below the cutoff before it even becomes a signal.
    hz = f * (RATE / n)
    spec *= np.clip((hz - HIGHPASS_HZ / 3.0) /
                    (HIGHPASS_HZ - HIGHPASS_HZ / 3.0), 0.0, 1.0)
    spec[0] = 0
    x = np.fft.irfft(spec, n)
    return x / (np.abs(x).max() + 1e-9)


def make_music(dur=LOOP_SECONDS, rate=RATE, seed=7):
    """Looping ambient track: pad, bass, bells and surf.

    Returns int16 (n, 2), ready for pygame.sndarray.make_sound().
    """
    rng = np.random.default_rng(seed)
    n = int(dur * rate)
    t = np.arange(n, dtype=np.float32) / rate
    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)

    step = dur / len(PROGRESSION)
    for k, (bass, chord) in enumerate(PROGRESSION):
        env = _chord_window(t, k * step + step / 2, step, dur).astype(np.float32)

        # Bass: fundamental plus a weak octave.
        fb = _hz(bass)
        ph = rng.uniform(0, 2 * np.pi, 2)
        voice = (_sine(fb, t, dur, phase=ph[0]) +
                 np.float32(0.25) * _sine(fb, t, dur, 2, phase=ph[1]))
        left += np.float32(0.20) * env * voice
        right += np.float32(0.20) * env * voice

        # Pad: each note with 3 harmonics and a slight detune between channels
        # (which gives stereo width without sounding out of tune).
        for i, note in enumerate(chord):
            f = _hz(note)
            amp = 0.34 / (i + 1.6)
            for channel, detune in ((left, 0.9985), (right, 1.0015)):
                fa = f * detune
                ph = rng.uniform(0, 2 * np.pi, 3)
                wave = (_sine(fa, t, dur, phase=ph[0]) +
                        np.float32(0.30) * _sine(fa, t, dur, 2, phase=ph[1]) +
                        np.float32(0.12) * _sine(fa, t, dur, 3, phase=ph[2]))
                channel += np.float32(amp) * env * wave

    # Bells: one note every ~1.7 s with a long decay. The tail of any note that
    # runs past the end of the loop is folded back into the start, so the turn
    # never chops a note in half.
    interval = 1.7
    decay = 2.2
    tail = int(decay * 4 * rate)
    buf_l = np.zeros(n + tail, dtype=np.float32)
    buf_r = np.zeros(n + tail, dtype=np.float32)
    for i in range(int(dur / interval)):
        start = int((i * interval + rng.uniform(-0.12, 0.12)) * rate)
        start = max(0, min(n - 1, start))
        f = _hz(int(rng.choice(BELLS)))
        note_dur = min(decay * 3.0, (n + tail - start) / rate)
        ts = np.arange(int(note_dur * rate), dtype=np.float32) / rate
        env = np.exp(-ts / decay) * (1.0 - np.exp(-ts / 0.012))
        voice = (np.sin(2 * np.pi * f * ts) +
                 0.40 * np.sin(2 * np.pi * f * 2 * ts) +
                 0.12 * np.sin(2 * np.pi * f * 3.01 * ts)) * env
        pan = rng.uniform(0.25, 0.75)
        end = start + len(voice)
        buf_l[start:end] += 0.22 * (1.0 - pan) * 2 * voice
        buf_r[start:end] += 0.22 * pan * 2 * voice
    buf_l[:tail] += buf_l[n:n + tail]
    buf_r[:tail] += buf_r[n:n + tail]
    left += buf_l[:n]
    right += buf_r[:n]

    # Surf: low noise with a slow swell, matching the water in the scene.
    for channel, phase in ((left, 0.0), (right, np.pi / 3)):
        swell = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t / dur + phase))
        channel += 0.14 * _colored_noise(n, 1.0, rng).astype(np.float32) * swell

    stereo = np.stack([left, right], axis=1)
    stereo = _highpass(stereo, HIGHPASS_HZ, rate)
    # Level by RMS (not by peak): a background track with plenty of headroom.
    stereo *= np.float32(TARGET_RMS / (np.sqrt((stereo ** 2).mean()) + 1e-9))
    stereo = _limiter(stereo)
    return (stereo * 32767).astype(np.int16)


class Music:
    """Plays the track on a loop in an SDL thread, outside the render loop."""

    def __init__(self, volume):
        self.sound = None
        self.error = None
        try:
            pygame.mixer.init(RATE, -16, 2, 2048)
            print("synthesising the ambient track...", file=sys.stderr, flush=True)
            arr = make_music()
            self.sound = pygame.sndarray.make_sound(np.ascontiguousarray(arr))
            self.sound.set_volume(volume)
        except Exception as e:                      # no sound card, etc.
            self.error = str(e)

    @property
    def active(self):
        return self.sound is not None

    def play(self):
        if self.sound is not None:
            self.sound.play(loops=-1, fade_ms=3000)

    def stop(self, fade_ms=1200):
        if self.sound is not None:
            self.sound.fadeout(fade_ms)
            pygame.time.wait(fade_ms)
