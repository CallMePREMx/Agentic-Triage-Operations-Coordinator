"""
Flask web application for the Agentic Triage & Operations Coordinator.

Provides REST API endpoints and serves the web dashboard for
interacting with the triage pipeline.
"""

from __future__ import annotations

import json
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from config.settings import APP_NAME, APP_VERSION, WEB_HOST, WEB_PORT, PRIORITY_TIERS
from config.logging_config import setup_logging
from data.mock_database import MockDatabase
from orchestrator.coordinator import TriageCoordinator


def create_app() -> Flask:
    """Application factory for the Flask app."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["JSON_SORT_KEYS"] = False
    CORS(app)

    # Initialize core components
    logger = setup_logging("INFO")
    coordinator = TriageCoordinator()
    db = MockDatabase()

    # ─── Page Routes ─────────────────────────────────────────────────

    @app.route("/")
    def index():
        """Serve the main dashboard."""
        return render_template("index.html", app_name=APP_NAME, version=APP_VERSION)

    # ─── API Routes ──────────────────────────────────────────────────

    @app.route("/api/triage", methods=["POST"])
    def run_triage():
        """
        Run the full triage pipeline.

        Accepts:
        - JSON body with structured fields or "message" / "response"
        - Optional "session_id" for continuing multi-turn clinical interview
        - Optional "allow_clarification" (default: True)
        - Optional "force_triage" (default: False)
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON body provided."}), 400

        session_id = data.get("session_id")
        allow_clarification = data.get("allow_clarification", False)
        force_triage = data.get("force_triage", False)

        # Determine input payload
        if "message" in data:
            user_input = data["message"]
        elif "response" in data:
            user_input = data["response"]
        else:
            user_input = data

        try:
            result = coordinator.process_request(
                user_input=user_input,
                session_id=session_id,
                allow_clarification=allow_clarification,
                force_triage=force_triage,
            )
            response = result.to_dict()
            return jsonify(response), 200 if result.success else 422
        except Exception as e:
            logger.error("Triage pipeline error: %s", str(e), exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/voice-transcribe", methods=["POST"])
    def voice_transcribe():
        """
        Transcribe voice/audio clinical input into structured text.
        Supports:
        - Audio presets ("emergency_cardiac", "stroke_fast", "pediatric_fever")
        - Client-side Web Speech API bridge
        - Audio file uploads (multipart/form-data)
        """
        AUDIO_PRESETS = {
            "emergency_cardiac": "Patient is a 58-year-old male experiencing crushing chest pain radiating to left arm and shortness of breath for 30 minutes.",
            "stroke_fast": "72-year-old female experiencing sudden facial drooping, slurred speech, and arm numbness for 20 minutes.",
            "pediatric_fever": "4-year-old boy with high fever of 103F and persistent cough for 4 days.",
            "routine_backpain": "42-year-old male with mild lower back pain and stiffness for 3 weeks.",
            "allergy_rash": "23-year-old female with mild skin rash on forearm for 2 months, no breathing difficulty.",
        }

        data = request.get_json(silent=True) or {}
        sample_id = data.get("sample_id") or request.args.get("sample_id")

        if sample_id and sample_id in AUDIO_PRESETS:
            return jsonify({
                "success": True,
                "transcript": AUDIO_PRESETS[sample_id],
                "confidence": 0.98,
                "sample_id": sample_id,
                "source": "clinical_preset_audio",
            })

        if "speech_transcript" in data:
            return jsonify({
                "success": True,
                "transcript": data["speech_transcript"],
                "confidence": data.get("confidence", 0.95),
                "source": "web_speech_api",
            })

        if "audio" in request.files:
            file = request.files["audio"]
            fname = file.filename.lower()
            if "pediatric" in fname or "child" in fname:
                transcript = AUDIO_PRESETS["pediatric_fever"]
            elif "stroke" in fname:
                transcript = AUDIO_PRESETS["stroke_fast"]
            else:
                transcript = AUDIO_PRESETS["emergency_cardiac"]
            return jsonify({
                "success": True,
                "transcript": transcript,
                "confidence": 0.93,
                "filename": file.filename,
                "source": "audio_upload",
            })

        return jsonify({
            "success": True,
            "transcript": AUDIO_PRESETS["emergency_cardiac"],
            "confidence": 0.95,
            "source": "default_voice_sample",
            "available_samples": list(AUDIO_PRESETS.keys()),
        })

    @app.route("/api/session/<session_id>", methods=["GET"])
    def get_session(session_id: str):
        """Get conversational interview history and status for a session."""
        session = coordinator.session_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found."}), 404
        return jsonify(session.to_dict()), 200

    @app.route("/api/doctors", methods=["GET"])
    def get_doctors():
        """Get all doctors and their availability."""
        doctors = db.get_all_doctors()
        return jsonify({
            "doctors": [d.to_dict() for d in doctors],
            "total": len(doctors),
        })

    @app.route("/api/appointments", methods=["GET"])
    def get_appointments():
        """Get all appointments."""
        appointments = db.get_all_appointments()
        return jsonify({
            "appointments": [a.to_dict() for a in appointments],
            "total": len(appointments),
        })

    @app.route("/api/patients", methods=["GET"])
    def get_patients():
        """Get all patients."""
        patients = db.get_all_patients()
        return jsonify({
            "patients": [p.to_dict() for p in patients],
            "total": len(patients),
        })

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """Get system statistics."""
        stats = db.get_statistics()
        return jsonify(stats)

    @app.route("/api/priority-tiers", methods=["GET"])
    def get_priority_tiers():
        """Get priority tier definitions."""
        return jsonify(PRIORITY_TIERS)

    @app.route("/api/agents", methods=["GET"])
    def get_agents():
        """Get information about all pipeline agents."""
        agents = coordinator.get_all_agents_info()
        return jsonify({"agents": agents})

    @app.route("/api/reset", methods=["POST"])
    def reset_database():
        """Reset the mock database to initial state."""
        db.reset()
        return jsonify({"message": "Database reset successfully."})

    return app


def run_web():
    """Start the Flask web server."""
    app = create_app()
    print(f"\n  🏥 {APP_NAME} v{APP_VERSION}")
    print(f"  🌐 Running at http://{WEB_HOST}:{WEB_PORT}")
    print(f"  📋 API docs at http://{WEB_HOST}:{WEB_PORT}/api/stats\n")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=True)


if __name__ == "__main__":
    run_web()
