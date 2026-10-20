from flask import Blueprint, jsonify, request

from app.services.venue_search_service import VenueSearchError, search_venues


venue_search_blueprint = Blueprint('venue_search', __name__, url_prefix='/api/venues')


def _token():
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    return token.strip() if scheme.lower() == 'bearer' else ''


@venue_search_blueprint.post('/search')
def search():
    token = _token()
    if not token:
        return jsonify(error='Authentication is required.'), 401
    criteria = request.get_json(silent=True)
    if not isinstance(criteria, dict):
        return jsonify(error='A JSON object is required.'), 400
    try:
        venues = search_venues(token, criteria)
    except VenueSearchError as exc:
        return jsonify(error=str(exc)), exc.status
    limitations = getattr(venues, 'assessment_limitations', [])
    return jsonify(venues=venues, assessment_limitations=limitations, assessment_complete=not limitations), 200
