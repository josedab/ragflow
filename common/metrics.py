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
Performance monitoring metrics collection module.

This module provides a comprehensive metrics collection system for RAGFlow,
supporting both simple in-memory metrics and Prometheus-compatible metrics export.
"""

import logging
import time
import threading
from functools import wraps
from contextlib import contextmanager
from typing import Optional


# Try to import prometheus_client, fall back to simple metrics if not available
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed. Using simple in-memory metrics.")


class SimpleMetrics:
    """Simple in-memory metrics collection when prometheus_client is not available."""

    def __init__(self):
        self._metrics = {}
        self._lock = threading.Lock()

    def record(self, name: str, value: float, tags: Optional[dict] = None):
        """Record a metric value."""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = []
            self._metrics[key].append({
                'value': value,
                'timestamp': time.time()
            })
            # Keep only last 1000 entries per metric
            if len(self._metrics[key]) > 1000:
                self._metrics[key] = self._metrics[key][-1000:]

    def get_metrics(self) -> dict:
        """Get all recorded metrics."""
        with self._lock:
            return dict(self._metrics)

    def clear(self):
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()

    @staticmethod
    def _make_key(name: str, tags: Optional[dict] = None) -> str:
        """Create a unique key for a metric with tags."""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}{{{tag_str}}}"
        return name


class Metrics:
    """
    Comprehensive metrics collection with Prometheus support.

    This class provides both simple in-memory metrics and Prometheus-compatible
    histogram, counter, and gauge metrics for production monitoring.
    """

    _instance = None
    _lock = threading.Lock()

    # Prometheus metrics (initialized lazily)
    _histograms = {}
    _counters = {}
    _gauges = {}

    # Default histogram buckets for different metric types
    DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf"))
    SIZE_BUCKETS = (100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, float("inf"))

    def __init__(self):
        self._simple_metrics = SimpleMetrics()
        self._registry = REGISTRY if PROMETHEUS_AVAILABLE else None

    @classmethod
    def get_instance(cls) -> 'Metrics':
        """Get the singleton instance of Metrics."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record(self, name: str, value: float, tags: Optional[dict] = None):
        """
        Record a metric value (simple metrics).

        Args:
            name: The metric name
            value: The metric value
            tags: Optional tags/labels for the metric
        """
        self._simple_metrics.record(name, value, tags)

    def histogram(self, name: str, value: float, labels: Optional[dict] = None,
                  description: str = "", buckets: tuple = None):
        """
        Record a histogram observation.

        Args:
            name: The histogram name
            value: The observation value
            labels: Optional labels for the metric
            description: Metric description
            buckets: Custom histogram buckets
        """
        if not PROMETHEUS_AVAILABLE:
            self.record(name, value, labels)
            return

        if buckets is None:
            buckets = self.DURATION_BUCKETS

        # Get or create histogram
        if name not in self._histograms:
            with self._lock:
                if name not in self._histograms:
                    label_names = list(labels.keys()) if labels else []
                    self._histograms[name] = Histogram(
                        name, description or f"Histogram for {name}",
                        label_names, buckets=buckets
                    )

        histogram = self._histograms[name]
        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)

        # Also record to simple metrics for easy access
        self.record(name, value, labels)

    def counter(self, name: str, value: float = 1, labels: Optional[dict] = None,
                description: str = ""):
        """
        Increment a counter.

        Args:
            name: The counter name
            value: The increment value (default 1)
            labels: Optional labels for the metric
            description: Metric description
        """
        if not PROMETHEUS_AVAILABLE:
            self.record(name, value, labels)
            return

        # Get or create counter
        if name not in self._counters:
            with self._lock:
                if name not in self._counters:
                    label_names = list(labels.keys()) if labels else []
                    self._counters[name] = Counter(
                        name, description or f"Counter for {name}",
                        label_names
                    )

        counter = self._counters[name]
        if labels:
            counter.labels(**labels).inc(value)
        else:
            counter.inc(value)

        # Also record to simple metrics
        self.record(name, value, labels)

    def gauge(self, name: str, value: float, labels: Optional[dict] = None,
              description: str = ""):
        """
        Set a gauge value.

        Args:
            name: The gauge name
            value: The gauge value
            labels: Optional labels for the metric
            description: Metric description
        """
        if not PROMETHEUS_AVAILABLE:
            self.record(name, value, labels)
            return

        # Get or create gauge
        if name not in self._gauges:
            with self._lock:
                if name not in self._gauges:
                    label_names = list(labels.keys()) if labels else []
                    self._gauges[name] = Gauge(
                        name, description or f"Gauge for {name}",
                        label_names
                    )

        gauge = self._gauges[name]
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)

        # Also record to simple metrics
        self.record(name, value, labels)

    def timer(self, name: str, tags: Optional[dict] = None):
        """
        Context manager for timing operations.

        Args:
            name: The metric name
            tags: Optional tags/labels for the metric

        Returns:
            TimerContext for use with 'with' statement
        """
        return TimerContext(self, name, tags)

    @staticmethod
    def timed(name: str, tags: Optional[dict] = None, description: str = ""):
        """
        Decorator for timing function execution.

        Args:
            name: The metric name
            tags: Optional tags/labels for the metric
            description: Metric description

        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    metrics = Metrics.get_instance()
                    metrics.histogram(
                        f"{name}_duration_seconds",
                        duration,
                        tags,
                        description or f"Duration of {name} in seconds"
                    )
            return wrapper
        return decorator

    @staticmethod
    def counted(name: str, tags: Optional[dict] = None, description: str = ""):
        """
        Decorator for counting function calls.

        Args:
            name: The metric name
            tags: Optional tags/labels for the metric
            description: Metric description

        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                metrics = Metrics.get_instance()
                metrics.counter(
                    f"{name}_total",
                    1,
                    tags,
                    description or f"Total calls to {name}"
                )
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_simple_metrics(self) -> dict:
        """Get all simple (in-memory) metrics."""
        return self._simple_metrics.get_metrics()

    def generate_prometheus_metrics(self) -> bytes:
        """Generate Prometheus-compatible metrics output."""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(self._registry)
        else:
            # Return empty bytes if Prometheus not available
            return b""

    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics."""
        if PROMETHEUS_AVAILABLE:
            return CONTENT_TYPE_LATEST
        return "text/plain"

    def clear_simple_metrics(self):
        """Clear all simple metrics."""
        self._simple_metrics.clear()


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, metrics: Metrics, name: str, tags: Optional[dict] = None):
        self.metrics = metrics
        self.name = name
        self.tags = tags
        self.start = None
        self.duration = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start
        self.metrics.histogram(
            f"{self.name}_duration_seconds",
            self.duration,
            self.tags,
            f"Duration of {self.name} in seconds"
        )
        return False  # Don't suppress exceptions


# Convenience functions for easy access
def get_metrics() -> Metrics:
    """Get the global Metrics instance."""
    return Metrics.get_instance()


def record_duration(name: str, duration: float, tags: Optional[dict] = None):
    """Record a duration metric."""
    get_metrics().histogram(f"{name}_duration_seconds", duration, tags)


def increment_counter(name: str, value: float = 1, tags: Optional[dict] = None):
    """Increment a counter metric."""
    get_metrics().counter(f"{name}_total", value, tags)


def set_gauge(name: str, value: float, tags: Optional[dict] = None):
    """Set a gauge metric value."""
    get_metrics().gauge(name, value, tags)


@contextmanager
def measure_time(name: str, tags: Optional[dict] = None):
    """Context manager for measuring operation time."""
    with get_metrics().timer(name, tags) as timer:
        yield timer
