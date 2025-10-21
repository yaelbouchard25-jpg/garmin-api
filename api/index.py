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
            
            # MODE DEBUG - IMPORTANT
            debug_mode = 'debug' in params
            
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
            
            # Fonction pour gérer les erreurs
            def safe_get(method_name, *args):
                try:
                    if hasattr(client, method_name):
                        method = getattr(client, method_name)
                        result = method(*args)
                        if result is None:
                            if 'activities' in method_name or 'goals' in method_name or 'events' in method_name or 'pressure' in method_name:
                                return []
                            else:
                                return {}
                        return result
                    else:
                        if 'activities' in method_name or 'goals' in method_name or 'events' in method_name or 'pressure' in method_name:
                            return []
                        else:
                            return {}
                except Exception:
                    if 'activities' in method_name or 'goals' in method_name or 'events' in method_name or 'pressure' in method_name:
                        return []
                    else:
                        return {}
            
            # Fonction helper
            def get_value(data, key, default=0):
                if data and isinstance(data, dict):
                    return data.get(key, default)
                return default
            
            # Fonction pour convertir secondes en HH:MM
            def seconds_to_hhmm(seconds):
                if not seconds or seconds == 0:
                    return "0h00"
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}h{minutes:02d}"
            
            # Fonction pour extraire valeur imbriquée
            def get_nested(data, *keys, default=0):
                try:
                    result = data
                    for key in keys:
                        if isinstance(result, dict):
                            result = result.get(key, default)
                        else:
                            return default
                    return result if result is not None else default
                except:
                    return default
            
            # ==================== RÉCUPÉRATION DES DONNÉES ====================
            
            stats = safe_get('get_stats', date_str)
            sleep_data = safe_get('get_sleep_data', date_str)
            heart_rates = safe_get('get_heart_rates', date_str)
            activities = safe_get('get_activities_by_date', date_str, date_str)
            stress_data = safe_get('get_stress_data', date_str)
            body_battery = safe_get('get_body_battery', date_str, date_str)
            respiration = safe_get('get_respiration_data', date_str)
            spo2 = safe_get('get_spo2_data', date_str)
            hrv = safe_get('get_hrv_data', date_str)
            training_readiness = safe_get('get_training_readiness', date_str)
            training_status = safe_get('get_training_status', date_str)
            max_metrics = safe_get('get_max_metrics', date_str)
            hydration = safe_get('get_hydration_data', date_str)
            weight = safe_get('get_weigh_ins', date_str)
            body_comp = safe_get('get_body_composition', date_str, date_str)
            blood_pressure = safe_get('get_blood_pressure', date_str, date_str)
            steps_data = safe_get('get_steps_data', date_str)
            
            # ==================== MODE DEBUG ====================
            if debug_mode:
                debug_data = {
                    "date": date_str,
                    "message": "MODE DEBUG ACTIVÉ - Données brutes de Garmin",
                    "raw_data": {
                        "sleep_data": sleep_data,
                        "hrv": hrv,
                        "stats": stats,
                        "training_readiness": training_readiness,
                        "spo2": spo2
                    }
                }
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(debug_data, indent=2, default=str).encode())
                return
            
            # ==================== EXTRACTION DES DONNÉES ====================
            
            # Extraire les données de sommeil
            daily_sleep = {}
            sleep_scores = {}
            sleep_levels = []
            sleep_movement = []
            
            if isinstance(sleep_data, dict):
                daily_sleep = sleep_data.get('dailySleepDTO', {})
                sleep_levels = sleep_data.get('sleepLevels', [])
                sleep_movement = sleep_data.get('sleepMovement', [])
                
                if isinstance(daily_sleep, dict):
                    sleep_scores = daily_sleep.get('sleepScores', {})
            
            # Extraire le sleep score
            sleep_score = (
                get_nested(daily_sleep, 'overallSleepScore', default=0) or
                get_nested(sleep_scores, 'overallScore', default=0) or
                get_nested(sleep_scores, 'totalScore', default=0) or
                get_nested(daily_sleep, 'sleepScore', default=0)
            )
            
            # Scores détaillés
            quality_score = get_nested(sleep_scores, 'qualityValue', 'value', default=0)
            recovery_score = get_nested(sleep_scores, 'recoveryValue', 'value', default=0)
            duration_score = get_nested(sleep_scores, 'durationValue', 'value', default=0)
            
            # Extraire HRV
            hrv_status = None
            hrv_avg = 0
            hrv_last_night = 0
            
            if isinstance(hrv, dict):
                hrv_status = (
                    hrv.get('status') or 
                    hrv.get('hrvStatus') or
                    get_nested(hrv, 'currentSummary', 'status')
                )
                
                hrv_avg = (
                    hrv.get('lastNightAvg') or
                    hrv.get('weeklyAvg') or
                    get_nested(hrv, 'lastNightHRV', 'avg') or
                    0
                )
                
                hrv_last_night = hrv.get('lastNightAvg', 0)
            
            # ==================== CONSTRUCTION DE LA RÉPONSE COMPLÈTE ====================
            
            data = {
                "date": date_str,
                "timestamp": datetime.now().isoformat(),
                
                # STATISTIQUES DE BASE
                "basic_stats": {
                    "steps": get_value(stats, "totalSteps", 0),
                    "distance_km": round(get_value(stats, "totalDistanceMeters", 0) / 1000, 2),
                    "calories_active": get_value(stats, "activeKilocalories", 0),
                    "calories_total": get_value(stats, "totalKilocalories", 0),
                    "calories_bmr": get_value(stats, "bmrKilocalories", 0),
                    "floors_ascended": get_value(stats, "floorsAscended", 0),
                    "floors_descended": get_value(stats, "floorsDescended", 0),
                    "intensity_minutes_moderate": get_value(stats, "moderateIntensityMinutes", 0),
                    "intensity_minutes_vigorous": get_value(stats, "vigorousIntensityMinutes", 0),
                    "intensity_minutes_goal": get_value(stats, "intensityMinutesGoal", 0),
                    "steps_goal": get_value(stats, "dailyStepGoal", 0),
                },
                
                # FRÉQUENCE CARDIAQUE
                "heart_rate": {
                    "avg": get_value(stats, "averageHeartRateInBeatsPerMinute", 0),
                    "resting": get_value(stats, "restingHeartRate", 0),
                    "max": get_value(stats, "maxHeartRate", 0),
                    "min": get_value(stats, "minHeartRate", 0),
                    "hrv_avg": hrv_avg,
                    "hrv_status": hrv_status,
                    "hrv_baseline_low": get_value(hrv, "baselineLowUpper", 0),
                    "hrv_baseline_balanced": get_value(hrv, "baselineBalancedLow", 0),
                    "hrv_last_night": hrv_last_night,
                    "hrv_last_night_5min": get_value(hrv, "lastNight5MinHigh", 0),
                },
                
                # SOMMEIL DÉTAILLÉ - AVEC FORMAT HEURES:MINUTES
                "sleep": {
                    # Durées en format HH:MM
                    "total_time": seconds_to_hhmm(get_value(daily_sleep, "sleepTimeSeconds", 0)),
                    "deep_sleep": seconds_to_hhmm(get_value(daily_sleep, "deepSleepSeconds", 0)),
                    "light_sleep": seconds_to_hhmm(get_value(daily_sleep, "lightSleepSeconds", 0)),
                    "rem_sleep": seconds_to_hhmm(get_value(daily_sleep, "remSleepSeconds", 0)),
                    "awake_time": seconds_to_hhmm(get_value(daily_sleep, "awakeSleepSeconds", 0)),
                    "unmeasurable_time": seconds_to_hhmm(get_value(daily_sleep, "unmeasurableSleepSeconds", 0)),
                    
                    # Durées en heures décimales (pour calculs)
                    "total_hours": round(get_value(daily_sleep, "sleepTimeSeconds", 0) / 3600, 2),
                    "deep_hours": round(get_value(daily_sleep, "deepSleepSeconds", 0) / 3600, 2),
                    "light_hours": round(get_value(daily_sleep, "lightSleepSeconds", 0) / 3600, 2),
                    "rem_hours": round(get_value(daily_sleep, "remSleepSeconds", 0) / 3600, 2),
                    "awake_hours": round(get_value(daily_sleep, "awakeSleepSeconds", 0) / 3600, 2),
                    "unmeasurable_hours": round(get_value(daily_sleep, "unmeasurableSleepSeconds", 0) / 3600, 2),
                    
                    # SLEEP SCORE
                    "sleep_score": sleep_score,
                    "sleep_score_feedback": get_value(daily_sleep, "sleepScoreFeedback", None),
                    "sleep_score_insight": get_value(daily_sleep, "sleepScoreInsight", None),
                    "sleep_score_quality": quality_score,
                    "sleep_score_recovery": recovery_score,
                    "sleep_score_duration": duration_score,
                    
                    # Qualité
                    "sleep_quality": get_value(daily_sleep, "sleepQualityTypeName", None),
                    "awake_count": get_value(daily_sleep, "awakeCount", 0),
                    "avg_sleep_stress": get_value(daily_sleep, "avgSleepStress", 0),
                    
                    # Horaires
                    "sleep_start": get_value(daily_sleep, "sleepStartTimestampLocal", None),
                    "sleep_end": get_value(daily_sleep, "sleepEndTimestampLocal", None),
                    "sleep_window_confirmed": get_value(daily_sleep, "sleepWindowConfirmed", False),
                    
                    # Siestes
                    "nap_time": seconds_to_hhmm(get_value(daily_sleep, "napTimeSeconds", 0)),
                    "nap_time_hours": round(get_value(daily_sleep, "napTimeSeconds", 0) / 3600, 2),
                    
                    # Respiration pendant le sommeil
                    "avg_respiration": get_value(daily_sleep, "avgSleepRespiration", 0),
                    "lowest_respiration": get_value(daily_sleep, "lowestRespiration", 0),
                    "highest_respiration": get_value(daily_sleep, "highestRespiration", 0),
                    
                    # SpO2 pendant le sommeil
                    "avg_spo2_sleep": get_value(daily_sleep, "avgOxygenSaturation", 0),
                    
                    # Niveaux de sommeil
                    "sleep_levels_count": len(sleep_levels) if sleep_levels else 0,
                    "sleep_movements_count": len(sleep_movement) if sleep_movement else 0,
                },
                
                # BODY BATTERY
                "body_battery": {
                    "charged": get_value(stats, "bodyBatteryChargedValue", 0),
                    "drained": get_value(stats, "bodyBatteryDrainedValue", 0),
                    "highest": get_value(stats, "bodyBatteryHighestValue", 0),
                    "lowest": get_value(stats, "bodyBatteryLowestValue", 0),
                    "current": body_battery[-1].get("charged", 0) if isinstance(body_battery, list) and len(body_battery) > 0 else 0,
                },
                
                # STRESS
                "stress": {
                    "avg": get_value(stats, "averageStressLevel", 0),
                    "max": get_value(stats, "maxStressLevel", 0),
                    "rest_time": seconds_to_hhmm(get_value(stress_data, "restStressMinutes", 0) * 60),
                    "activity_time": seconds_to_hhmm(get_value(stress_data, "activityStressMinutes", 0) * 60),
                    "low_time": seconds_to_hhmm(get_value(stress_data, "lowStressMinutes", 0) * 60),
                    "medium_time": seconds_to_hhmm(get_value(stress_data, "mediumStressMinutes", 0) * 60),
                    "high_time": seconds_to_hhmm(get_value(stress_data, "highStressMinutes", 0) * 60),
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
                    "fitness_age": get_value(max_metrics, "fitnessAge", 0),
                    "vo2_max_running": get_value(max_metrics, "vo2MaxRunningValue", 0),
                    "vo2_max_cycling": get_value(max_metrics, "vo2MaxCyclingValue", 0),
                },
                
                # ACTIVITÉS
                "activities": {
                    "count": len(activities) if isinstance(activities, list) else 0,
                    "list": [
                        {
                            "name": act.get("activityName", ""),
                            "type": act.get("activityType", {}).get("typeKey", "") if isinstance(act.get("activityType"), dict) else "",
                            "duration": seconds_to_hhmm(act.get("duration", 0)),
                            "duration_minutes": round(act.get("duration", 0) / 60, 2),
                            "distance_km": round(act.get("distance", 0) / 1000, 2),
                            "calories": act.get("calories", 0),
                            "avg_hr": act.get("averageHR", 0),
                            "max_hr": act.get("maxHR", 0),
                            "avg_speed": round(act.get("averageSpeed", 0) * 3.6, 2),
                            "elevation_gain": act.get("elevationGain", 0),
                            "elevation_loss": act.get("elevationLoss", 0),
                            "avg_cadence": act.get("averageRunningCadenceInStepsPerMinute", 0),
                            "max_cadence": act.get("maxRunningCadenceInStepsPerMinute", 0),
                        }
                        for act in (activities[:20] if isinstance(activities, list) else [])
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
                    "metabolic_age": get_value(body_comp, "metabolicAge", 0),
                    "visceral_fat": get_value(body_comp, "visceralFat", 0),
                },
                
                # HYDRATATION
                "hydration": {
                    "total_ml": get_value(hydration, "valueInML", None),
                    "goal_ml": get_value(hydration, "goalInML", 0),
                    "sweat_loss_ml": get_value(hydration, "sweatLossInML", None),
                },
                
                # TENSION ARTÉRIELLE
                "blood_pressure": {
                    "systolic": (
                        blood_pressure[0].get("systolic", 0) if isinstance(blood_pressure, list) and len(blood_pressure) > 0 
                        else get_value(blood_pressure, "systolic", 0) if isinstance(blood_pressure, dict) 
                        else 0
                    ),
                    "diastolic": (
                        blood_pressure[0].get("diastolic", 0) if isinstance(blood_pressure, list) and len(blood_pressure) > 0 
                        else get_value(blood_pressure, "diastolic", 0) if isinstance(blood_pressure, dict) 
                        else 0
                    ),
                    "pulse": (
                        blood_pressure[0].get("pulse", 0) if isinstance(blood_pressure, list) and len(blood_pressure) > 0 
                        else get_value(blood_pressure, "pulse", 0) if isinstance(blood_pressure, dict) 
                        else 0
                    ),
                },
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
```

