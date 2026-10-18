"""Unit tests for ranking and composite scoring formula."""

from app.ranking import (
    ScoringWeights,
    calculate_score,
    normalize_latency,
    normalize_speed,
    normalize_stability,
)


def test_normalize_latency():
    assert normalize_latency(40.0) == 100.0  # Ultra-low latency
    assert normalize_latency(50.0) == 100.0
    assert normalize_latency(1500.0) == 0.0  # Unusable latency
    assert normalize_latency(1800.0) == 0.0
    assert 0.0 < normalize_latency(200.0) < 100.0
    assert normalize_latency(None) == 0.0


def test_normalize_speed():
    assert normalize_speed(25.0) == 100.0
    assert normalize_speed(50.0) == 100.0  # Capped at 100
    assert normalize_speed(12.5) == 50.0
    assert normalize_speed(0.0) == 0.0
    assert normalize_speed(None) == 0.0


def test_normalize_stability():
    assert normalize_stability(3.0) == 100.0  # Jitter <= 5ms
    assert normalize_stability(200.0) == 0.0  # Jitter >= 200ms
    assert 0.0 < normalize_stability(50.0) < 100.0


def test_calculate_score_failed_candidate():
    score = calculate_score(
        status="failed",
        latency_ms=100.0,
        latency_variance=5.0,
        download_speed_mbps=20.0,
        success_rate=0.0,
    )
    assert score == 0.0


def test_calculate_score_working_full_metrics():
    # Ideal candidate
    score_best = calculate_score(
        status="working",
        latency_ms=60.0,
        latency_variance=3.0,
        download_speed_mbps=25.0,
        success_rate=100.0,
    )
    assert score_best >= 95.0

    # Slower candidate
    score_slow = calculate_score(
        status="working",
        latency_ms=450.0,
        latency_variance=40.0,
        download_speed_mbps=5.0,
        success_rate=100.0,
    )
    assert score_best > score_slow


def test_calculate_score_latency_only_scan():
    # Speed not tested (None)
    score = calculate_score(
        status="working",
        latency_ms=120.0,
        latency_variance=10.0,
        download_speed_mbps=None,
        success_rate=100.0,
    )
    assert 0.0 < score <= 100.0
    # Make sure it doesn't default to 0 or crash
    assert score > 50.0
