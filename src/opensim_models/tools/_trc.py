"""TRC file reading and writing utilities for OpenSim marker tracking."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


def write_trc_file(
    path: Path,
    times: Sequence[float],
    markers: Mapping[str, Sequence[Sequence[float]]],
    units: str = "m",
) -> Path:
    """Write marker trajectories to a standard OpenSim .trc file."""
    n_frames = len(times)
    n_markers = len(markers)
    data_rate = (
        float((n_frames - 1) / (times[-1] - times[0]))
        if n_frames > 1 and times[-1] > times[0]
        else 100.0
    )

    marker_names = list(markers.keys())
    lines = [
        f"PathFileType\t4\t(X/Y/Z)\t{path.name}",
        (
            "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\t"
            "OrigDataRate\tOrigDataStartFrame\tOrigNumFrames"
        ),
        (
            f"{data_rate:.2f}\t{data_rate:.2f}\t{n_frames}\t"
            f"{n_markers}\t{units}\t{data_rate:.2f}\t1\t{n_frames}"
        ),
    ]

    line4_parts = ["Frame#", "Time"]
    for name in marker_names:
        line4_parts.extend([name, "", ""])
    lines.append("\t".join(line4_parts))

    line5_parts = ["", ""]
    for i in range(1, n_markers + 1):
        line5_parts.extend([f"X{i}", f"Y{i}", f"Z{i}"])
    lines.append("\t".join(line5_parts))

    for idx, t in enumerate(times):
        row = [str(idx + 1), f"{float(t):.6f}"]
        for name in marker_names:
            pt = markers[name][idx]
            row.extend(
                [
                    f"{float(pt[0]):.6f}",
                    f"{float(pt[1]):.6f}",
                    f"{float(pt[2]):.6f}",
                ]
            )
        lines.append("\t".join(row))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
