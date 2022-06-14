# -*- coding: utf-8 -*-
"""Endpoints for data retrieval of computed RCAs."""
import logging

from flask import Blueprint, jsonify, request

from chaos_genius.core.rca.rca_utils.api_utils import (
    rca_analysis,
    rca_hierarchical_data,
)
from chaos_genius.settings import DEEPDRILLS_ENABLED

blueprint = Blueprint("api_rca", __name__)
logger = logging.getLogger(__name__)


@blueprint.route("/<int:kpi_id>/rca-analysis", methods=["GET"])
def kpi_rca_analysis(kpi_id):
    """API endpoint for RCA analysis data."""
    data = []
    status = "success"
    message = ""

    if not DEEPDRILLS_ENABLED:
        return jsonify({
            "status": "error",
            "message": "DeepDrills is not enabled",
            "data": data
        })

    try:
        timeline = request.args.get("timeline")
        dimension = request.args.get("dimension", None)

        status, message, data = rca_analysis(kpi_id, timeline, dimension)
    except Exception as err:  # noqa: B902
        logger.info(f"Error Found: {err}")
        status = "error"
        message = str(err)
    return jsonify({"status": status, "message": message, "data": data})


@blueprint.route("/<int:kpi_id>/rca-hierarchical-data", methods=["GET"])
def kpi_rca_hierarchical_data(kpi_id):
    """API endpoint for RCA hierarchical data."""
    data = []
    status = "success"
    message = ""

    if not DEEPDRILLS_ENABLED:
        return jsonify({
            "status": "error",
            "message": "DeepDrills is not enabled",
            "data": data
        })

    try:
        timeline = request.args.get("timeline")
        dimension = request.args.get("dimension", None)

        status, message, data = rca_hierarchical_data(
            kpi_id, timeline, dimension
        )
    except Exception as err:  # noqa: B902
        logger.info(f"Error Found: {err}")
        status = "error"
        message = str(err)
    return jsonify({"status": status, "message": message, "data": data})
