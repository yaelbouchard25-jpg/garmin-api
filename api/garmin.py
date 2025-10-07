from garminconnect import Garmin
from datetime import datetime
import os
import traceback

def handler(request):
    try:
        # Récupérer les identifiants
        email = os.environ.get('GARMIN_EMAIL')
        password = os.environ.get('GARMIN_PASSWORD')
        
        # Vérifier que les identifiants existent
        if not email or not password:
            return {
                'statusCode': 400,
                'body': {
                    "error": "Identifiants Garmin non configurés",
                    "detail": f"Email présent: {bool(email)}, Password présent: {bool(password)}"
                }
            }
        
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
        
        return {
            'statusCode': 200,
            'body': data
        }
        
    except Exception as e:
        # Retourner l'erreur détaillée
        error_detail = traceback.format_exc()
        return {
            'statusCode': 500,
            'body': {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": error_detail
            }
        }
