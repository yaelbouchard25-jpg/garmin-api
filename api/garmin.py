from flask import Flask, jsonify, request
from garminconnect import Garmin
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/api/garmin', methods=['GET'])
def get_garmin_data():
    try:
        # Récupérer les identifiants depuis les variables d'environnement
        email = os.environ.get('GARMIN_EMAIL')
        password = os.environ.get('GARMIN_PASSWORD')
        
        if not email or not password:
            return jsonify({"error": "Identifiants Garmin non configurés"}), 400
        
        # Connexion à Garmin
        client = Garmin(email, password)
        client.login()
        
        # Date du jour
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Récupérer les statistiques
        stats = client.get_stats(today)
        
        # Préparer les données
        data = {
            "date": today,
            "steps": stats.get("totalSteps", 0),
            "distance": round(stats.get("totalDistanceMeters", 0) / 1000, 2),
            "calories": stats.get("activeKilocalories", 0),
            "heart_rate": stats.get("averageHeartRateInBeatsPerMinute", 0),
            "sleep_hours": round(stats.get("sleepingSeconds", 0) / 3600, 2) if stats.get("sleepingSeconds") else 0
        }
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Pour Vercel
def handler(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()
