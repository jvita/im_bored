"""Main routes for homepage and random activity."""

from flask import Blueprint, jsonify, render_template, request

from im_bored import db

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Render the homepage."""
    return render_template('index.html')


@bp.route('/get-random-activity', methods=['POST'])
def get_random_activity():
    """Get a random uncompleted activity (AJAX endpoint)."""
    # Get optional type filter from request body
    activity_types = None
    if request.is_json:
        data = request.get_json()
        activity_types = data.get('types')

    activity = db.get_random_uncompleted_activity(activity_types)

    if activity:
        return jsonify({
            'success': True,
            'activity': {
                'id': activity['id'],
                'type': activity['type'],
                'description': activity['description']
            }
        })
    else:
        if activity_types:
            type_msg = f" of type {', '.join(activity_types)}" if len(activity_types) > 1 else f" of type '{activity_types[0]}'"
        else:
            type_msg = ""
        return jsonify({
            'success': False,
            'message': f'No uncompleted activities found{type_msg}! Add some first.'
        }), 404
