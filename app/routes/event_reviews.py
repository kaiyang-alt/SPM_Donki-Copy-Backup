from flask import Blueprint, jsonify, request

from app.services.event_review_service import (
    ReviewError, get_review, list_review_events, respond_to_review, submit_review,
)

event_reviews_blueprint = Blueprint('event_reviews', __name__, url_prefix='/api/event-reviews')


def _call(operation, *args):
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return jsonify(error='Authentication is required.'), 401
    try:
        return jsonify(operation(token.strip(), *args)), 200
    except ReviewError as exc:
        return jsonify(error=str(exc)), exc.status
    except Exception:
        return jsonify(error='Unable to complete the review operation.'), 502


@event_reviews_blueprint.get('')
def listing():
    return _call(lambda token: {'events': list_review_events(token)})


@event_reviews_blueprint.get('/<event_id>')
def detail(event_id):
    return _call(get_review, event_id)


def _mutate(operation, event_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error='A JSON object is required.'), 400
    return _call(lambda token: {'event': operation(token, event_id, payload)})


@event_reviews_blueprint.post('/<event_id>/decision')
def decision(event_id):
    return _mutate(submit_review, event_id)


@event_reviews_blueprint.post('/<event_id>/response')
def response(event_id):
    return _mutate(respond_to_review, event_id)
