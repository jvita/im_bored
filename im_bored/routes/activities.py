"""Activities management routes and API endpoints."""

from flask import Blueprint, jsonify, render_template, request

from im_bored import db

bp = Blueprint('activities', __name__)


@bp.route('/activities')
def activities_page():
    """Redirect to main page (single page app now)."""
    from flask import redirect
    return redirect('/')


@bp.route('/api/activities', methods=['GET'])
def get_activities():
    """Get all activities grouped by type (JSON)."""
    grouped_activities = db.get_all_activities()
    return jsonify({
        'success': True,
        'activities': grouped_activities
    })


@bp.route('/api/types', methods=['GET'])
def get_types():
    """Get all activity types (JSON)."""
    types = db.get_all_types()
    return jsonify({
        'success': True,
        'types': types
    })


@bp.route('/api/activities', methods=['POST'])
def create_activity():
    """Create a new activity (JSON)."""
    data = request.get_json()

    if not data or 'type' not in data or 'description' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required fields: type and description'
        }), 400

    activity_type = data['type'].strip()
    description = data['description'].strip()

    if not activity_type or not description:
        return jsonify({
            'success': False,
            'message': 'Type and description cannot be empty'
        }), 400

    activity_id = db.add_activity(activity_type, description)

    return jsonify({
        'success': True,
        'message': 'Activity created successfully',
        'id': activity_id
    }), 201


@bp.route('/api/activities/<int:activity_id>', methods=['PUT'])
def update_activity(activity_id):
    """Update activity completion status (JSON)."""
    data = request.get_json()

    if not data or 'completed' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required field: completed'
        }), 400

    completed = bool(data['completed'])
    success = db.update_activity_completion(activity_id, completed)

    if success:
        return jsonify({
            'success': True,
            'message': 'Activity updated successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Activity not found'
        }), 404


@bp.route('/api/activities/<int:activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    """Delete an activity (JSON)."""
    success = db.delete_activity(activity_id)

    if success:
        return jsonify({
            'success': True,
            'message': 'Activity deleted successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Activity not found'
        }), 404
