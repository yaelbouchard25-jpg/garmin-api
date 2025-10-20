from garminconnect import Garmin
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import json
import traceback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            email = os.environ.get('GARMIN_EMAIL')
            password = os.environ.get('GARMIN_PASSWORD')
            
            if not email or not password:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": "Identifiants non configurés"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Récupérer la date
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            if 'date' in params and params['date'][0]:
                date_str = params['date'][0]
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"error": "Format invalide. Utilisez YYYY-MM-DD"}
                    self.wfile.write(json.dumps(response).encode())
                    return
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
            
            # Connexion Garmin
            client = Garmin(email, password)
            client.login()
            
            # Fonction CORRIGÉE pour gérer les erreurs ET les méthodes manquantes
            def safe_get(method_name, *args):
                try:
                    # Vérifier si la méthode existe
                    if hasattr(client, method_name):
                        method = getattr(client, method_name)
                        result = method(*args)
                        # Si le résultat est None, retourner un dict ou list vide selon le contexte
                        if result is None:
                            # Deviner le type de retour basé sur le nom de la méthode
                            if 'activities' in method_name or 'goals' in method_name or 'events' in method_name:
                                return []
                            else:
                                return {}
                        return result
                    else:
                        # Méthode n'existe pas, retourner dict ou list vide
                        if 'activities' in method_name or 'goals' in method_name or 'events' in method_name:
                            return []
                        else:
                            return {}
                except Exception:
                    # En cas d'erreur, retourner dict ou list vide
                    if 'activities' in method_name or 'goals' in method_name or 'events' in method_name:
                        return []
                    else:
                        return {}
            
            # ==================== RÉCUPÉRATION DE TOUTES LES DONNÉES ====================
            
            # 1. Statistiques de base (toujours disponibles)
            stats = safe_get('get_stats', date_str)
            
            # 2. Sommeil
            sleep_data = safe_get('get_sleep_data', date_str)
            
            # 3. Fréquence cardiaque détaillée
            heart_rates = safe_get('get_heart_rates', date_str)
            
            # 4. Activités du jour
            activities = safe_get('get_activities_by_date', date_str, date_str)
            
            # 5. Stress détaillé
            stress_data = safe_get('get_stress_data', date_str)
            
            # 6. Body Battery
            body_battery = safe_get('get_body_battery', date_str, date_str)
            
            # 7. Respiration
            respiration = safe_get('get_respiration_data', date_str)
            
            # 8. SpO2
            spo2 = safe_get('get_spo2_data', date_str)
            
            # 9. HRV (Variabilité fréquence cardiaque)
            hrv = safe_get('get_hrv_data', date_str)
            
            # 10. Training Readiness
            training_readiness = safe_get('get_training_readiness', date_str)
            
            # 11. Training Status
            training_status = safe_get('get_training_status', date_str)
            
            # 12. Max Metrics (VO2 Max, etc.)
            max_metrics = safe_get('get_max_metrics', date_str)
            
            # 13. Hydratation
            hydration = safe_get('get_hydration_data', date_str)
            
            # 14. Poids
            weight = safe_get('get_weigh_ins', date_str)
            
            # 15. Composition corporelle
            body_comp = safe_get('get_body_composition', date_str, date_str)
            
            # 16. Tension artérielle
            blood_pressure = safe_get('get_blood_pressure', date_str, date_str)
            
            # 17. Hill Score
            hill_score = safe_get('get_hill_score', date_str, date_str)
            
            # 18. Endurance Score
            endurance_score = safe_get('get_endurance_score', date_str, date_str)
            
            # 19. Race Predictions
            race_predictions = safe_get('get_race_predictions')
            
            # 20. Données solaires
            solar_data = safe_get('get_solar_data')
            
            # 21. Objectifs
            active_goals = safe_get('get_active_goals')
            
            # 22. Wellness Events
            wellness_events = safe_get('get_daily_wellness_events', date_str)
            
            # 23. Fitness Age (nom corrigé)
            fitness_age_data = safe_get('get_fitnessage_data', date_str)
            
            # Fonction helper pour accéder aux données en toute sécurité
            def get_value(data, key, default=0):
                if data and isinstance(data, dict):
                    return data.get(key, default)
                return default
            
            # ==================== CONSTRUCTION DE LA RÉPONSE ====================

            
            data = {
                "date": date_str,
                "timestamp": datetime.now().isoformat(),
                
                # STATISTIQUES DE BASE
                "basic_stats": {
                    "steps": get_value(stats, "totalSteps", 0),
                    "distance_km": round(get_value(stats, "totalDistanceMeters", 0) / 1000, 2),
                    "calories_active": get_value(stats, "activeKilocalories", 0),
                    "calories_total": get_value(stats, "totalKilocalories", 0),
                    "floors_ascended": get_value(stats, "floorsAscended", 0),
                    "floors_descended": get_value(stats, "floorsDescended", 0),
                    "intensity_minutes_moderate": get_value(stats, "moderateIntensityMinutes", 0),
                    "intensity_minutes_vigorous": get_value(stats, "vigorousIntensityMinutes", 0),
                },
                
                # FRÉQUENCE CARDIAQUE
                "heart_rate": {
                    "avg": get_value(stats, "averageHeartRateInBeatsPerMinute", 0),
                    "resting": get_value(stats, "restingHeartRate", 0),
                    "max": get_value(stats, "maxHeartRate", 0),
                    "min": get_value(stats, "minHeartRate", 0),
                    "hrv_avg": get_value(hrv, "lastNightAvg", 0),
                    "hrv_status": get_value(hrv, "status", None),
                },
                
                # SOMMEIL
                "sleep": {
                    "total_hours": round(get_value(stats, "sleepingSeconds", 0) / 3600, 2),
                    "deep_hours": round(get_value(sleep_data, "deepSleepSeconds", 0) / 3600, 2),
                    "light_hours": round(get_value(sleep_data, "lightSleepSeconds", 0) / 3600, 2),
                    "rem_hours": round(get_value(sleep_data, "remSleepSeconds", 0) / 3600, 2),
                    "awake_hours": round(get_value(sleep_data, "awakeSleepSeconds", 0) / 3600, 2),
                    "sleep_score": get_value(sleep_data, "overallSleepScore", 0),
                    "sleep_quality": get_value(sleep_data, "sleepQualityTypeName", None),
                },
                
                # BODY BATTERY
                "body_battery": {
                    "charged": get_value(stats, "bodyBatteryChargedValue", 0),
                    "drained": get_value(stats, "bodyBatteryDrainedValue", 0),
                    "highest": get_value(stats, "bodyBatteryHighestValue", 0),
                    "lowest": get_value(stats, "bodyBatteryLowestValue", 0),
                    "current": body_battery[-1].get("charged", 0) if body_battery and len(body_battery) > 0 else 0,
                },
                
                # STRESS
                "stress": {
                    "avg": get_value(stats, "averageStressLevel", 0),
                    "max": get_value(stats, "maxStressLevel", 0),
                    "rest_time_minutes": get_value(stress_data, "restStressMinutes", 0),
                    "activity_time_minutes": get_value(stress_data, "activityStressMinutes", 0),
                    "low_time_minutes": get_value(stress_data, "lowStressMinutes", 0),
                    "medium_time_minutes": get_value(stress_data, "mediumStressMinutes", 0),
                    "high_time_minutes": get_value(stress_data, "highStressMinutes", 0),
                },
                
                # RESPIRATION
                "respiration": {
                    "avg_waking": get_value(respiration, "avgWakingRespirationValue", 0),
                    "highest": get_value(respiration, "highestRespirationValue", 0),
                    "lowest": get_value(respiration, "lowestRespirationValue", 0),
                },
                
                # SPO2
                "spo2": {
                    "avg": get_value(spo2, "averageSpo2Value", 0),
                    "lowest": get_value(spo2, "lowestSpo2Value", 0),
                },
                
                # ENTRAÎNEMENT
                "training": {
                    "readiness_score": get_value(training_readiness, "score", 0),
                    "readiness_level": get_value(training_readiness, "level", None),
                    "training_status": get_value(training_status, "trainingStatus", None),
                    "vo2_max": get_value(max_metrics, "vo2MaxValue", 0),
                    "fitness_age": get_value(fitness_age_data, "fitnessAge", 0),
                    "hill_score": get_value(hill_score, "hillScore", 0),
                    "endurance_score": get_value(endurance_score, "enduranceScore", 0),
                },
                
                # ACTIVITÉS
                "activities": {
                    "count": len(activities) if activities else 0,
                    "list": [
                        {
                            "name": act.get("activityName", ""),
                            "type": act.get("activityType", {}).get("typeKey", "") if isinstance(act.get("activityType"), dict) else "",
                            "duration_minutes": round(act.get("duration", 0) / 60, 2),
                            "distance_km": round(act.get("distance", 0) / 1000, 2),
                            "calories": act.get("calories", 0),
                            "avg_hr": act.get("averageHR", 0),
                            "max_hr": act.get("maxHR", 0),
                            "avg_speed": round(act.get("averageSpeed", 0) * 3.6, 2),
                            "elevation_gain": act.get("elevationGain", 0),
                        }
                        for act in (activities[:20] if activities else [])
                    ]
                },
                
                # COMPOSITION CORPORELLE
                "body_composition": {
                    "weight_kg": get_value(weight, "weight", 0) / 1000,
                    "bmi": get_value(body_comp, "bmi", 0),
                    "body_fat_percentage": get_value(body_comp, "bodyFat", 0),
                    "body_water_percentage": get_value(body_comp, "bodyWater", 0),
                    "bone_mass_kg": get_value(body_comp, "boneMass", 0),
                    "muscle_mass_kg": get_value(body_comp, "muscleMass", 0),
                },
                
                # HYDRATATION
                "hydration": {
                    "total_ml": get_value(hydration, "valueInML", 0),
                    "goal_ml": get_value(hydration, "goalInML", 0),
                },
                
                # TENSION ARTÉRIELLE
                "blood_pressure": {
                    "systolic": blood_pressure[0].get("systolic", 0) if blood_pressure and len(blood_pressure) > 0 else 0,
                    "diastolic": blood_pressure[0].get("diastolic", 0) if blood_pressure and len(blood_pressure) > 0 else 0,
                    "pulse": blood_pressure[0].get("pulse", 0) if blood_pressure and len(blood_pressure) > 0 else 0,
                },
                
                # PRÉDICTIONS DE COURSE
                "race_predictions": race_predictions if race_predictions else {},
                
                # OBJECTIFS
                "goals": {
                    "active_count": len(active_goals) if active_goals else 0,
                    "list": active_goals if active_goals else []
                },
                
                # DONNÉES SOLAIRES
                "solar": solar_data if solar_data else {},
                
                # WELLNESS EVENTS
                "wellness_events": wellness_events if wellness_events else [],
            }
            
            # Envoyer la réponse
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
            self.wfile.write(json.dumps(error_response).encode())
