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
Metrics endpoint for Prometheus scraping and metrics API.

This blueprint exposes metrics endpoints for:
- Prometheus-compatible metrics scraping (/metrics)
- Simple JSON metrics API (/metrics/json)
- Health check (/metrics/health)
"""

import json
import logging
from flask import Response, Blueprint

from common.metrics import Metrics, PROMETHEUS_AVAILABLE

# Register blueprint with Flask app
manager = Blueprint('metrics', __name__)


@manager.route('/prometheus', methods=['GET'])
def prometheus_metrics():
    """
    Expose metrics for Prometheus scraping.

    Returns:
        Response: Prometheus-formatted metrics
    """
    try:
        metrics = Metrics.get_instance()
        return Response(
            metrics.generate_prometheus_metrics(),
            mimetype=metrics.get_content_type()
        )
    except Exception as e:
        logging.exception(f"Error generating Prometheus metrics: {e}")
        return Response(
            f"# Error generating metrics: {str(e)}\n",
            mimetype="text/plain",
            status=500
        )


@manager.route('/json', methods=['GET'])
def json_metrics():
    """
    Expose metrics in JSON format for debugging and simple integrations.

    Returns:
        Response: JSON-formatted metrics
    """
    try:
        metrics = Metrics.get_instance()
        simple_metrics = metrics.get_simple_metrics()

        # Convert to JSON-serializable format
        result = {}
        for key, values in simple_metrics.items():
            if values:
                # Get latest value and some statistics
                latest = values[-1]
                all_values = [v['value'] for v in values]
                result[key] = {
                    'latest': latest['value'],
                    'timestamp': latest['timestamp'],
                    'count': len(values),
                    'min': min(all_values),
                    'max': max(all_values),
                    'avg': sum(all_values) / len(all_values)
                }

        return Response(
            json.dumps(result, indent=2),
            mimetype='application/json'
        )
    except Exception as e:
        logging.exception(f"Error generating JSON metrics: {e}")
        return Response(
            json.dumps({'error': str(e)}),
            mimetype='application/json',
            status=500
        )


@manager.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint.

    Returns:
        Response: Health status
    """
    return Response(
        json.dumps({
            'status': 'healthy',
            'prometheus_available': PROMETHEUS_AVAILABLE
        }),
        mimetype='application/json'
    )


@manager.route('/clear', methods=['POST'])
def clear_metrics():
    """
    Clear simple (in-memory) metrics.

    Note: This does not clear Prometheus metrics as they are cumulative.

    Returns:
        Response: Success status
    """
    try:
        metrics = Metrics.get_instance()
        metrics.clear_simple_metrics()
        return Response(
            json.dumps({'status': 'cleared'}),
            mimetype='application/json'
        )
    except Exception as e:
        logging.exception(f"Error clearing metrics: {e}")
        return Response(
            json.dumps({'error': str(e)}),
            mimetype='application/json',
            status=500
        )
