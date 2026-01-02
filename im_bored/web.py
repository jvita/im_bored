"""Flask web application for im_bored."""

from pathlib import Path

from flask import Flask


def create_app():
    """Create and configure the Flask application."""
    # Get the project root directory (parent of im_bored package)
    project_root = Path(__file__).parent.parent

    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )

    # Register blueprints
    from im_bored.routes.main import bp as main_bp
    from im_bored.routes.activities import bp as activities_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(activities_bp)

    return app


def run():
    """Run the development server."""
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == "__main__":
    run()
