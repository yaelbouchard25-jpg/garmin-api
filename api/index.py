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
            
            # Fonction améliorée pour gérer les erreurs ET les méthodes manquantes
            def safe_get(method_name, *args, default=None):
                try:
                    # Vérifier si la méthode existe
                    if hasattr(client, method_name):
                        method = getattr(client, method_name)
                        return method(*args)
                    else:
                        return default
                except Exception:
                    return default
            
            # ==================== RÉCUPÉRATION DE TOUTES LES DONNÉES ====================
            
            # 1. Statistiques de base (toujours disponibles)
            stats = safe_get('get_stats', date_str, {})
            
            # 2. Sommeil
            sleep_data = safe_get('get_sleep_data', date_str, {})
            
            # 3. Fréquence cardiaque détaillée
            heart_rates = safe_get('get_heart_rates', date_str, {})
            
            # 4. Activités du jour
            activities = safe_get('get_activities_by_date', date_str, date_str, [])
            
            # 5. Stress détaillé
            stress_data = safe_get('get_stress_data', date_str, {})
            
            # 6. Body Battery
            body_battery = safe_get('get_body_battery', date_str, date_str, [])
            
            # 7. Respiration
            respiration = safe_get('get_respiration_data', date_str, {})
            
            # 8. SpO2
            spo2 = safe_get('get_spo2_data', date_str, {})
            
            # 9. HRV (Variabilité fréquence cardiaque)
            hrv = safe_get('get_hrv_data', date_str, {})
            
            # 10. Training Readiness
            training_readiness = safe_get('get_training_readiness', date_str, {})
            
            # 11. Training Status
            training_status = safe_get('get_training_status', date_str, {})
            
            # 12. Max Metrics (VO2 Max, etc.)
            max_metrics = safe_get('get_max_metrics', date_str, {})
            
            # 13. Hydratation
            hydration = safe_get('get_hydration_data', date_str, {})
            
            # 14. Poids
            weight = safe_get('get_weigh_ins', date_str, {})
            
            # 15. Composition corporelle
            body_comp = safe_get('get_body_composition', date_str, date_str, {})
            
            # 16. Tension artérielle
            blood_pressure = safe_get('get_blood_pressure', date_str, date_str, [])
            
            # 17. Hill Score
            hill_score = safe_get('get_hill_score', date_str, date_str, {})
            
            # 18. Endurance Score
            endurance_score = safe_get('get_endurance_score', date_str, date_str, {})
            
            # 19. Race Predictions
            race_predictions = safe_get('get_race_predictions', {})
            
            # 20. Données solaires
            solar_data = safe_get('get_solar_data', {})
            
            # 21. Objectifs
            active_goals = safe_get('get_active_goals', [])
            
            # 22. Wellness Events
            wellness_events = safe_get('get_daily_wellness_events', date_str, [])
            
            # 23. Fitness Age (nom corrigé)
            fitness_age_data = safe_get('get_fitnessage_data', date_str, {})
            
            # ==================== CONSTRUCTION DE LA RÉPONSE ====================
            
            data = {
                "date": date_str,
                "timestamp": datetime.now().isoformat(),
                
                # STATISTIQUES DE BASE
                "basic_stats": {
                    "steps": stats.get("totalSteps", 0),
                    "distance_km": round(stats.get("totalDistanceMeters", 0) / 1000, 2),
                    "calories_active": stats.get("activeKilocalories", 0),
                    "calories_total": stats.get("totalKilocalories", 0),
                    "floors_ascended": stats.get("floorsAscended", 0),
                    "floors_descended": stats.get("floorsDescended", 0),
                    "intensity_minutes_moderate": stats.get("moderateIntensityMinutes", 0),
                    "intensity_minutes_vigorous": stats.get("vigorousIntensityMinutes", 0),
                },
                
                # FRÉQUENCE CARDIAQUE
                "heart_rate": {
                    "avg": stats.get("averageHeartRateInBeatsPerMinute", 0),
                    "resting": stats.get("restingHeartRate", 0),
                    "max": stats.get("maxHeartRate", 0),
                    "min": stats.get("minHeartRate", 0),
                    "hrv_avg": hrv.get("lastNightAvg") if hrv else 0,
                    "hrv_status": hrv.get("status") if hrv else None,
                },
                
                # SOMMEIL
                "sleep": {
                    "total_hours": round(stats.get("sleepingSeconds", 0) / 3600, 2),
                    "deep_hours": round(sleep_data.get("deepSleepSeconds", 0) / 3600, 2) if sleep_data else 0,
                    "light_hours": round(sleep_data.get("lightSleepSeconds", 0) / 3600, 2) if sleep_data else 0,
                    "rem_hours": round(sleep_data.get("remSleepSeconds", 0) / 3600, 2) if sleep_data else 0,
                    "awake_hours": round(sleep_data.get("awakeSleepSeconds", 0) / 3600, 2) if sleep_data else 0,
                    "sleep_score": sleep_data.get("overallSleepScore") if sleep_data else 0,
                    "sleep_quality": sleep_data.get("sleepQualityTypeName") if sleep_data else None,
                },
                
                # BODY BATTERY
                "body_battery": {
                    "charged": stats.get("bodyBatteryChargedValue", 0),
                    "drained": stats.get("bodyBatteryDrainedValue", 0),
                    "highest": stats.get("bodyBatteryHighestValue", 0),
                    "lowest": stats.get("bodyBatteryLowestValue", 0),
                    "current": body_battery[-1].get("charged") if body_battery else 0,
                },
                
                # STRESS
                "stress": {
                    "avg": stats.get("averageStressLevel", 0),
                    "max": stats.get("maxStressLevel", 0),
                    "rest_time_minutes": stress_data.get("restStressMinutes", 0) if stress_data else 0,
                    "activity_time_minutes": stress_data.get("activityStressMinutes", 0) if stress_data else 0,
                    "low_time_minutes": stress_data.get("lowStressMinutes", 0) if stress_data else 0,
                    "medium_time_minutes": stress_data.get("mediumStressMinutes", 0) if stress_data else 0,
                    "high_time_minutes": stress_data.get("highStressMinutes", 0) if stress_data else 0,
                },
                
                # RESPIRATION
                "respiration": {
                    "avg_waking": respiration.get("avgWakingRespirationValue") if respiration else 0,
                    "highest": respiration.get("highestRespirationValue") if respiration else 0,
                    "lowest": respiration.get("lowestRespirationValue") if respiration else 0,
                },
                
                # SPO2
                "spo2": {
                    "avg": spo2.get("averageSpo2Value") if spo2 else 0,
                    "lowest": spo2.get("lowestSpo2Value") if spo2 else 0,
                },
                
                # ENTRAÎNEMENT
                "training": {
                    "readiness_score": training_readiness.get("score") if training_readiness else 0,
                    "readiness_level": training_readiness.get("level") if training_readiness else None,
                    "training_status": training_status.get("trainingStatus") if training_status else None,
                    "vo2_max": max_metrics.get("vo2MaxValue") if max_metrics else 0,
                    "fitness_age": fitness_age_data.get("fitnessAge") if fitness_age_data else 0,
                    "hill_score": hill_score.get("hillScore") if hill_score else 0,
                    "endurance_score": endurance_score.get("enduranceScore") if endurance_score else 0,
                },
                
                # ACTIVITÉS
                "activities": {
                    "count": len(activities) if activities else 0,
                    "list": [
                        {
                            "name": act.get("activityName", ""),
                            "type": act.get("activityType", {}).get("typeKey", ""),
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
                    "weight_kg": weight.get("weight", 0) / 1000 if weight else 0,
                    "bmi": body_comp.get("bmi") if body_comp else 0,
                    "body_fat_percentage": body_comp.get("bodyFat") if body_comp else 0,
                    "body_water_percentage": body_comp.get("bodyWater") if body_comp else 0,
                    "bone_mass_kg": body_comp.get("boneMass") if body_comp else 0,
                    "muscle_mass_kg": body_comp.get("muscleMass") if body_comp else 0,
                },
                
                # HYDRATATION
                "hydration": {
                    "total_ml": hydration.get("valueInML", 0) if hydration else 0,
                    "goal_ml": hydration.get("goalInML", 0) if hydration else 0,
                },
                
                # TENSION ARTÉRIELLE
                "blood_pressure": {
                    "systolic": blood_pressure[0].get("systolic", 0) if blood_pressure else 0,
                    "diastolic": blood_pressure[0].get("diastolic", 0) if blood_pressure else 0,
                    "pulse": blood_pressure[0].get("pulse", 0) if blood_pressure else 0,
                } if blood_pressure else {},
                
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
