#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Unit tests for the metrics collection module.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from common.metrics import (
    Metrics,
    SimpleMetrics,
    TimerContext,
    get_metrics,
    record_duration,
    increment_counter,
    set_gauge,
    measure_time,
    PROMETHEUS_AVAILABLE,
)


class TestSimpleMetrics:
    """Tests for SimpleMetrics class."""

    def test_record_metric(self):
        """Test recording a simple metric."""
        metrics = SimpleMetrics()
        metrics.record("test_metric", 1.5)

        result = metrics.get_metrics()
        assert "test_metric" in result
        assert len(result["test_metric"]) == 1
        assert result["test_metric"][0]["value"] == 1.5

    def test_record_metric_with_tags(self):
        """Test recording a metric with tags."""
        metrics = SimpleMetrics()
        metrics.record("test_metric", 2.0, {"env": "test", "region": "us"})

        result = metrics.get_metrics()
        key = "test_metric{env=test,region=us}"
        assert key in result
        assert result[key][0]["value"] == 2.0

    def test_record_multiple_values(self):
        """Test recording multiple values for the same metric."""
        metrics = SimpleMetrics()
        for i in range(5):
            metrics.record("counter", float(i))

        result = metrics.get_metrics()
        assert len(result["counter"]) == 5
        values = [r["value"] for r in result["counter"]]
        assert values == [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        metrics = SimpleMetrics()
        metrics.record("test", 1.0)
        metrics.clear()

        result = metrics.get_metrics()
        assert len(result) == 0

    def test_metric_limit(self):
        """Test that metrics are limited to 1000 entries."""
        metrics = SimpleMetrics()
        for i in range(1100):
            metrics.record("limited", float(i))

        result = metrics.get_metrics()
        assert len(result["limited"]) == 1000
        # Should keep the last 1000 entries
        assert result["limited"][0]["value"] == 100.0


class TestMetrics:
    """Tests for Metrics singleton class."""

    def setup_method(self):
        """Reset singleton before each test."""
        Metrics._instance = None
        Metrics._histograms = {}
        Metrics._counters = {}
        Metrics._gauges = {}

    def test_singleton(self):
        """Test that Metrics is a singleton."""
        m1 = Metrics.get_instance()
        m2 = Metrics.get_instance()
        assert m1 is m2

    def test_get_metrics_function(self):
        """Test the get_metrics convenience function."""
        m1 = get_metrics()
        m2 = Metrics.get_instance()
        assert m1 is m2

    def test_record(self):
        """Test recording a metric value."""
        metrics = Metrics.get_instance()
        metrics.record("test_record", 3.14)

        result = metrics.get_simple_metrics()
        assert "test_record" in result

    def test_histogram(self):
        """Test histogram recording."""
        metrics = Metrics.get_instance()
        metrics.histogram("test_histogram", 0.5, {"label": "test"})

        result = metrics.get_simple_metrics()
        assert "test_histogram" in result

    def test_counter(self):
        """Test counter incrementing."""
        metrics = Metrics.get_instance()
        metrics.counter("test_counter", 1, {"type": "test"})
        metrics.counter("test_counter", 2, {"type": "test"})

        result = metrics.get_simple_metrics()
        key = "test_counter{type=test}"
        assert key in result
        assert len(result[key]) == 2

    def test_gauge(self):
        """Test gauge setting."""
        metrics = Metrics.get_instance()
        metrics.gauge("test_gauge", 42.0, {"name": "test"})

        result = metrics.get_simple_metrics()
        key = "test_gauge{name=test}"
        assert key in result

    def test_clear_simple_metrics(self):
        """Test clearing simple metrics."""
        metrics = Metrics.get_instance()
        metrics.record("to_clear", 1.0)
        metrics.clear_simple_metrics()

        result = metrics.get_simple_metrics()
        assert len(result) == 0


class TestTimerContext:
    """Tests for TimerContext class."""

    def test_timer_context(self):
        """Test timing with context manager."""
        metrics = Metrics.get_instance()
        Metrics._instance = None  # Reset singleton

        metrics = Metrics.get_instance()
        with metrics.timer("test_timer") as timer:
            time.sleep(0.01)  # Sleep 10ms

        assert timer.duration >= 0.01
        assert timer.duration < 0.1  # Should be less than 100ms

        result = metrics.get_simple_metrics()
        assert "test_timer_duration_seconds" in result

    def test_timer_with_tags(self):
        """Test timer with tags."""
        Metrics._instance = None  # Reset singleton
        metrics = Metrics.get_instance()

        with metrics.timer("tagged_timer", {"env": "test"}):
            pass

        result = metrics.get_simple_metrics()
        key = "tagged_timer_duration_seconds{env=test}"
        assert key in result


class TestDecorators:
    """Tests for decorator functions."""

    def setup_method(self):
        """Reset singleton before each test."""
        Metrics._instance = None
        Metrics._histograms = {}
        Metrics._counters = {}
        Metrics._gauges = {}

    def test_timed_decorator(self):
        """Test the timed decorator."""
        @Metrics.timed("decorated_function")
        def sample_function():
            time.sleep(0.01)
            return "result"

        result = sample_function()
        assert result == "result"

        metrics = Metrics.get_instance()
        simple_metrics = metrics.get_simple_metrics()
        assert "decorated_function_duration_seconds" in simple_metrics

    def test_timed_decorator_with_tags(self):
        """Test the timed decorator with tags."""
        @Metrics.timed("tagged_function", tags={"version": "1.0"})
        def sample_function():
            return "tagged"

        sample_function()

        metrics = Metrics.get_instance()
        simple_metrics = metrics.get_simple_metrics()
        key = "tagged_function_duration_seconds{version=1.0}"
        assert key in simple_metrics

    def test_counted_decorator(self):
        """Test the counted decorator."""
        @Metrics.counted("call_counter")
        def counted_function():
            return "counted"

        for _ in range(3):
            counted_function()

        metrics = Metrics.get_instance()
        simple_metrics = metrics.get_simple_metrics()
        assert "call_counter_total" in simple_metrics
        assert len(simple_metrics["call_counter_total"]) == 3


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def setup_method(self):
        """Reset singleton before each test."""
        Metrics._instance = None
        Metrics._histograms = {}
        Metrics._counters = {}
        Metrics._gauges = {}

    def test_record_duration(self):
        """Test record_duration function."""
        record_duration("test_op", 1.5, {"env": "test"})

        metrics = Metrics.get_instance()
        result = metrics.get_simple_metrics()
        key = "test_op_duration_seconds{env=test}"
        assert key in result

    def test_increment_counter(self):
        """Test increment_counter function."""
        increment_counter("api_calls", 1, {"endpoint": "/test"})

        metrics = Metrics.get_instance()
        result = metrics.get_simple_metrics()
        key = "api_calls_total{endpoint=/test}"
        assert key in result

    def test_set_gauge(self):
        """Test set_gauge function."""
        set_gauge("queue_size", 50, {"queue": "main"})

        metrics = Metrics.get_instance()
        result = metrics.get_simple_metrics()
        key = "queue_size{queue=main}"
        assert key in result

    def test_measure_time_context_manager(self):
        """Test measure_time context manager."""
        with measure_time("measured_op", {"type": "test"}) as timer:
            time.sleep(0.01)

        assert timer.duration >= 0.01

        metrics = Metrics.get_instance()
        result = metrics.get_simple_metrics()
        key = "measured_op_duration_seconds{type=test}"
        assert key in result


class TestPrometheusIntegration:
    """Tests for Prometheus integration."""

    def setup_method(self):
        """Reset singleton before each test."""
        Metrics._instance = None
        Metrics._histograms = {}
        Metrics._counters = {}
        Metrics._gauges = {}

    def test_generate_prometheus_metrics(self):
        """Test generating Prometheus-compatible metrics."""
        metrics = Metrics.get_instance()
        metrics.record("test", 1.0)

        output = metrics.generate_prometheus_metrics()
        assert isinstance(output, bytes)

    def test_get_content_type(self):
        """Test getting content type for Prometheus."""
        metrics = Metrics.get_instance()
        content_type = metrics.get_content_type()

        if PROMETHEUS_AVAILABLE:
            assert "text/plain" in content_type or "openmetrics" in content_type
        else:
            assert content_type == "text/plain"


class TestThreadSafety:
    """Tests for thread safety."""

    def setup_method(self):
        """Reset singleton before each test."""
        Metrics._instance = None
        Metrics._histograms = {}
        Metrics._counters = {}
        Metrics._gauges = {}

    def test_concurrent_recording(self):
        """Test concurrent metric recording."""
        import threading

        metrics = Metrics.get_instance()

        def record_metrics(thread_id):
            for i in range(100):
                metrics.record(f"thread_{thread_id}", float(i))

        threads = [threading.Thread(target=record_metrics, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        result = metrics.get_simple_metrics()
        for i in range(5):
            assert f"thread_{i}" in result
            assert len(result[f"thread_{i}"]) == 100


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
class TestPrometheusMetrics:
    """Tests that require prometheus_client."""

    def setup_method(self):
        """Reset singleton before each test."""
        Metrics._instance = None
        Metrics._histograms = {}
        Metrics._counters = {}
        Metrics._gauges = {}

    def test_histogram_with_buckets(self):
        """Test histogram with custom buckets."""
        metrics = Metrics.get_instance()
        metrics.histogram(
            "custom_histogram",
            0.5,
            labels={"test": "true"},
            buckets=(0.1, 0.5, 1.0, float("inf"))
        )

        output = metrics.generate_prometheus_metrics()
        assert b"custom_histogram" in output

    def test_counter_increment(self):
        """Test Prometheus counter increment."""
        metrics = Metrics.get_instance()
        metrics.counter("prom_counter", 5, {"env": "test"})

        output = metrics.generate_prometheus_metrics()
        assert b"prom_counter" in output

    def test_gauge_set(self):
        """Test Prometheus gauge set."""
        metrics = Metrics.get_instance()
        metrics.gauge("prom_gauge", 42.0, {"type": "test"})

        output = metrics.generate_prometheus_metrics()
        assert b"prom_gauge" in output
