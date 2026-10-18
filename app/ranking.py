"""Configurable composite ranking algorithm and normalization for proxy candidates."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ScoringWeights:
    weight_success: float = 0.35
    weight_latency: float = 0.30
    weight_speed: float = 0.25
    weight_stability: float = 0.10

    def normalized(self) -> "ScoringWeights":
        total = self.weight_success + self.weight_latency + self.weight_speed + self.weight_stability
        if total <= 0:
            return ScoringWeights()
        return ScoringWeights(
            weight_success=self.weight_success / total,
            weight_latency=self.weight_latency / total,
            weight_speed=self.weight_speed / total,
            weight_stability=self.weight_stability / total,
        )


def normalize_latency(latency_ms: Optional[float], min_lat: float = 50.0, max_lat: float = 1500.0) -> float:
    """Normalize latency in ms to 0.0 - 100.0 scale (lower latency is better)."""
    if latency_ms is None or latency_ms <= 0:
        return 0.0
    if latency_ms <= min_lat:
        return 100.0
    if latency_ms >= max_lat:
        return 0.0
    return ((max_lat - latency_ms) / (max_lat - min_lat)) * 100.0


def normalize_speed(speed_mbps: Optional[float], target_speed_mbps: float = 25.0) -> float:
    """Normalize throughput in Mbps to 0.0 - 100.0 scale (higher speed is better)."""
    if speed_mbps is None or speed_mbps <= 0:
        return 0.0
    return min(100.0, (speed_mbps / target_speed_mbps) * 100.0)


def normalize_stability(variance_ms: Optional[float], max_jitter: float = 200.0) -> float:
    """Normalize latency jitter/variance to 0.0 - 100.0 scale (lower jitter is better)."""
    if variance_ms is None:
        return 50.0  # Neutral baseline if single probe
    if variance_ms <= 5.0:
        return 100.0
    if variance_ms >= max_jitter:
        return 0.0
    return max(0.0, ((max_jitter - variance_ms) / (max_jitter - 5.0)) * 100.0)


def calculate_score(
    status: str,
    latency_ms: Optional[float],
    latency_variance: Optional[float],
    download_speed_mbps: Optional[float],
    success_rate: float,
    weights: Optional[ScoringWeights] = None,
) -> float:
    """
    Calculate composite score between 0.0 and 100.0.
    A failed candidate always receives 0.0.
    If speed testing is disabled, weights are redistributed dynamically
    so latency-only scans remain strictly comparable and fair.
    """
    if status.lower() != "working" or success_rate <= 0:
        return 0.0

    w = (weights or ScoringWeights()).normalized()

    score_success = min(100.0, max(0.0, success_rate))
    score_lat = normalize_latency(latency_ms)
    score_stab = normalize_stability(latency_variance)

    if download_speed_mbps is not None and download_speed_mbps > 0:
        score_speed = normalize_speed(download_speed_mbps)
        composite = (
            w.weight_success * score_success
            + w.weight_latency * score_lat
            + w.weight_speed * score_speed
            + w.weight_stability * score_stab
        )
    else:
        # Re-weight among success, latency, and stability
        active_weight = w.weight_success + w.weight_latency + w.weight_stability
        if active_weight > 0:
            scale = 1.0 / active_weight
            composite = (
                (w.weight_success * scale) * score_success
                + (w.weight_latency * scale) * score_lat
                + (w.weight_stability * scale) * score_stab
            )
        else:
            composite = score_lat

    return round(max(0.0, min(100.0, composite)), 1)
