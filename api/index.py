from garminconnect import Garmin
from datetime import datetime
from http.server import BaseHTTPRequestHandler
import os
import json
import traceback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Récupérer les identifiants
            email = os.environ.get('GARMIN_EMAIL')
            password = os.environ.get('GARMIN_PASSWORD')
            
            # Vérifier que les identifiants existent
            if not email or not password:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "error": "Identifiants Garmin non configurés",
                    "detail": f"Email présent: {bool(email)}, Password présent: {bool(password)}"
                }
                self.wfile.write(json.dumps(response).encode())
                return
            
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
            
            # Envoyer la réponse
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        except Exception as e:
            # Retourner l'erreur détaillée
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
            self.wfile.write(json.dumps(error_response).encode())
