"""Generate the deterministic wooden block snap bundled with Macroblock."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 44_100
DURATION_SECONDS = 0.22


def _impact(local_time: float, base_frequency: float, amplitude: float) -> float:
    if local_time < 0:
        return 0.0
    body = (
        math.sin(math.tau * base_frequency * local_time)
        + 0.52 * math.sin(math.tau * base_frequency * 1.61 * local_time + 0.4)
        + 0.24 * math.sin(math.tau * base_frequency * 2.37 * local_time + 1.1)
    )
    return amplitude * body * math.exp(-31 * local_time)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = root / "assets" / "sounds" / "block-connect.wav"
    destination.parent.mkdir(parents=True, exist_ok=True)
    random_source = random.Random(0xB10C)
    samples: list[float] = []
    filtered_noise = 0.0
    for index in range(round(SAMPLE_RATE * DURATION_SECONDS)):
        current_time = index / SAMPLE_RATE
        noise = random_source.uniform(-1.0, 1.0)
        filtered_noise = 0.64 * filtered_noise + 0.36 * noise
        first_noise = filtered_noise * math.exp(-85 * current_time)
        second_time = current_time - 0.066
        second_noise = (
            filtered_noise * math.exp(-105 * second_time)
            if second_time >= 0
            else 0.0
        )
        value = (
            _impact(current_time, 385, 0.5)
            + _impact(second_time, 575, 0.42)
            + 0.24 * first_noise
            + 0.17 * second_noise
        )
        samples.append(value)

    peak = max(abs(sample) for sample in samples) or 1.0
    pcm = b"".join(
        struct.pack("<h", round(max(-1.0, min(1.0, sample / peak * 0.78)) * 32767))
        for sample in samples
    )
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)
    print(f"Generated {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
