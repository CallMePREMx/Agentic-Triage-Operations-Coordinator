"""
Tests for the Flask Web Application & REST API.

Validates:
- Dashboard HTML rendering
- /api/triage endpoint with structured and free-text inputs
- /api/triage error handling
- /api/doctors, /api/appointments, /api/patients, /api/stats endpoints
- /api/priority-tiers and /api/agents endpoints
- /api/reset endpoint
"""

import json
import pytest
from web.app import create_app


@pytest.fixture
def app():
    """Create Flask application fixture configured for testing."""
    application = create_app()
    application.config.update({
        "TESTING": True,
    })
    yield application


@pytest.fixture
def client(app):
    """Create Flask test client fixture."""
    return app.test_client()


class TestWebDashboard:
    """Tests for the web dashboard HTML interface."""

    def test_index_page(self, client):
        """Root URL should serve the HTML dashboard."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Agentic Triage" in response.data or b"Dashboard" in response.data or b"html" in response.data.lower()


class TestTriageApi:
    """Tests for the /api/triage endpoint."""

    def test_triage_structured_input(self, client):
        """Submit structured patient data via JSON."""
        payload = {
            "name": "Jane Doe",
            "age": 35,
            "symptoms": ["chest pain", "shortness of breath"],
            "duration": "20 minutes",
        }
        response = client.post(
            "/api/triage",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["patient"]["name"] == "Jane Doe"
        assert data["patient"]["priority_tier"] == "RED"
        assert data["appointment"] is not None
        assert "confirmation_summary" in data

    def test_triage_free_text_message(self, client):
        """Submit natural language message via JSON."""
        payload = {
            "message": "65-year-old male with severe chest pain for 45 minutes",
        }
        response = client.post(
            "/api/triage",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["patient"]["priority_tier"] == "RED"

    def test_triage_missing_symptoms(self, client):
        """Input without symptoms should return unprocessable entity (422)."""
        payload = {
            "name": "No Symptoms Patient",
            "age": 40,
            "symptoms": [],
        }
        response = client.post(
            "/api/triage",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_triage_empty_body(self, client):
        """POST without JSON body should return 400 Bad Request."""
        response = client.post("/api/triage", data="", content_type="application/json")
        assert response.status_code == 400


class TestClinicApiEndpoints:
    """Tests for read-only and administrative clinic API endpoints."""

    def test_get_doctors(self, client):
        """GET /api/doctors returns doctor directory."""
        response = client.get("/api/doctors")
        assert response.status_code == 200
        data = response.get_json()
        assert "doctors" in data
        assert data["total"] > 0
        assert any(d["name"] == "Priya Sharma" for d in data["doctors"])

    def test_get_appointments(self, client):
        """GET /api/appointments returns booked appointments list."""
        response = client.get("/api/appointments")
        assert response.status_code == 200
        data = response.get_json()
        assert "appointments" in data
        assert "total" in data

    def test_get_patients(self, client):
        """GET /api/patients returns registered patients list."""
        response = client.get("/api/patients")
        assert response.status_code == 200
        data = response.get_json()
        assert "patients" in data

    def test_get_stats(self, client):
        """GET /api/stats returns clinic statistics."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_doctors" in data
        assert "total_appointments" in data
        assert "utilization_rate" in data

    def test_get_priority_tiers(self, client):
        """GET /api/priority-tiers returns clinical tier definitions."""
        response = client.get("/api/priority-tiers")
        assert response.status_code == 200
        data = response.get_json()
        assert "RED" in data
        assert "GREEN" in data
        assert data["RED"]["max_wait_minutes"] == 0

    def test_get_agents(self, client):
        """GET /api/agents returns pipeline agent metadata."""
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.get_json()
        assert "agents" in data
        names = [a["name"] for a in data["agents"]]
        assert "IntakeAgent" in names
        assert "TriageAgent" in names
        assert "OperationsAgent" in names
        assert "CriticAgent" in names

    def test_reset_database(self, client):
        """POST /api/reset resets the mock database."""
        response = client.post("/api/reset")
        assert response.status_code == 200
        data = response.get_json()
        assert "reset" in data["message"].lower()

    def test_voice_transcribe_preset(self, client):
        """POST /api/voice-transcribe with preset sample returns clinical transcript."""
        response = client.post(
            "/api/voice-transcribe",
            data=json.dumps({"sample_id": "emergency_cardiac"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "chest pain" in data["transcript"]
        assert data["confidence"] > 0.9

    def test_voice_transcribe_web_speech(self, client):
        """POST /api/voice-transcribe with client speech transcript returns formatted result."""
        response = client.post(
            "/api/voice-transcribe",
            data=json.dumps({"speech_transcript": "Patient feels dizzy for 2 hours", "confidence": 0.92}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["transcript"] == "Patient feels dizzy for 2 hours"

    def test_multi_turn_triage_api(self, client):
        """POST /api/triage supports clarification turns and session retrieval."""
        # Turn 1: ambiguous symptom
        res1 = client.post(
            "/api/triage",
            data=json.dumps({"message": "I have chest pain", "allow_clarification": True}),
            content_type="application/json",
        )
        assert res1.status_code == 200
        data1 = res1.get_json()
        assert data1["needs_clarification"] is True
        session_id = data1["session_id"]
        assert session_id != ""

        # Check session retrieval
        res_session = client.get(f"/api/session/{session_id}")
        assert res_session.status_code == 200
        s_data = res_session.get_json()
        assert s_data["session_id"] == session_id

        # Turn 2: answer clarification
        res2 = client.post(
            "/api/triage",
            data=json.dumps({
                "session_id": session_id,
                "message": "Pain radiates to left arm for 30 minutes, 60yo male",
                "allow_clarification": True,
            }),
            content_type="application/json",
        )
        assert res2.status_code == 200
        data2 = res2.get_json()
        assert data2["needs_clarification"] is False
        assert data2["patient"]["priority_tier"] == "RED"
        assert data2["appointment"] is not None

