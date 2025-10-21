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
            
            # Récupérer la date et les paramètres
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            # Vérifier mode debug
            debug_mode = False
            if 'debug' in params:
                debug_mode = True
            
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
            
            # Fonction pour convertir secondes en format HH:MM
            def seconds_to_time(seconds):
                if not seconds or seconds == 0:
                    return "0h00"
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}h{minutes:02d}"
            
            # Fonction de sécurité
            def safe_get(method_name, *args):
                try:
                    if hasattr(client, method_name):
                        method = getattr(client, method_name)
                        result = method(*args)
                        if result is None:
                            return [] if 'activities' in method_name or 'pressure' in method_name else {}
                        return result
                    return [] if 'activities' in method_name or 'pressure' in method_name else {}
                except:
                    return [] if 'activities' in method_name or 'pressure' in method_name else {}
            
            def get_val(data, key, default=0):
                if data and isinstance(data, dict):
                    return data.get(key, default)
                return default
            
            # Récupération des données
            stats = safe_get('get_stats', date_str)
            sleep_data = safe_get('get_sleep_data', date_str)
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
            
            # MODE DEBUG
            if debug_mode:
                try:
                    debug_data = {
                        "date": date_str,
                        "debug_mode": True,
                        "sleep_data_keys": list(sleep_data.keys()) if isinstance(sleep_data, dict) else "not_dict",
                        "hrv_keys": list(hrv.keys()) if isinstance(hrv, dict) else "not_dict",
                        "sleep_data": str(sleep_data)[:5000],
                        "hrv": str(hrv)[:5000]
                    }
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(debug_data, indent=2).encode())
                    return
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Debug error: {str(e)}"}).encode())
                    return
            
            # Extraction données sommeil
            daily_sleep = {}
            if isinstance(sleep_data, dict):
                daily_sleep = sleep_data.get('dailySleepDTO', {})
            
            # Extraction HRV
            hrv_status = None
            hrv_avg = 0
            if isinstance(hrv, dict):
                hrv_status = hrv.get('status') or hrv.get('hrvStatus')
                hrv_avg = hrv.get('lastNightAvg', 0) or hrv.get('weeklyAvg', 0)
            
            # Durées de sommeil
            sleep_total = get_val(daily_sleep, "sleepTimeSeconds", 0)
            sleep_deep = get_val(daily_sleep, "deepSleepSeconds", 0)
            sleep_light = get_val(daily_sleep, "lightSleepSeconds", 0)
            sleep_rem = get_val(daily_sleep, "remSleepSeconds", 0)
            sleep_awake = get_val(daily_sleep, "awakeSleepSeconds", 0)
            
            # Construction réponse
            data = {
                "date": date_str,
                "timestamp": datetime.now().isoformat(),
                
                "basic_stats": {
                    "steps": get_val(stats, "totalSteps", 0),
                    "distance_km": round(get_val(stats, "totalDistanceMeters", 0) / 1000, 2),
                    "calories_active": get_val(stats, "activeKilocalories", 0),
                    "calories_total": get_val(stats, "totalKilocalories", 0),
                    "calories_bmr": get_val(stats, "bmrKilocalories", 0),
                    "floors_ascended": get_val(stats, "floorsAscended", 0),
                    "floors_descended": get_val(stats, "floorsDescended", 0),
                    "intensity_minutes_moderate": get_val(stats, "moderateIntensityMinutes", 0),
                    "intensity_minutes_vigorous": get_val(stats, "vigorousIntensityMinutes", 0),
                    "intensity_minutes_goal": get_val(stats, "intensityMinutesGoal", 0),
                    "steps_goal": get_val(stats, "dailyStepGoal", 0),
                },
                
                "heart_rate": {
                    "avg": get_val(stats, "averageHeartRateInBeatsPerMinute", 0),
                    "resting": get_val(stats, "restingHeartRate", 0),
                    "max": get_val(stats, "maxHeartRate", 0),
                    "min": get_val(stats, "minHeartRate", 0),
                    "hrv_avg": hrv_avg,
                    "hrv_status": hrv_status,
                },
                
                "sleep": {
                    "total_hours": round(sleep_total / 3600, 2),
                    "total_formatted": seconds_to_time(sleep_total),
                    "deep_hours": round(sleep_deep / 3600, 2),
                    "deep_formatted": seconds_to_time(sleep_deep),
                    "light_hours": round(sleep_light / 3600, 2),
                    "light_formatted": seconds_to_time(sleep_light),
                    "rem_hours": round(sleep_rem / 3600, 2),
                    "rem_formatted": seconds_to_time(sleep_rem),
                    "awake_hours": round(sleep_awake / 3600, 2),
                    "awake_formatted": seconds_to_time(sleep_awake),
                    "sleep_score": get_val(daily_sleep, "overallSleepScore", 0),
                    "sleep_score_feedback": get_val(daily_sleep, "sleepScoreFeedback", None),
                    "awake_count": get_val(daily_sleep, "awakeCount", 0),
                    "avg_sleep_stress": get_val(daily_sleep, "avgSleepStress", 0),
                },
                
                "body_battery": {
                    "charged": get_val(stats, "bodyBatteryChargedValue", 0),
                    "drained": get_val(stats, "bodyBatteryDrainedValue", 0),
                    "highest": get_val(stats, "bodyBatteryHighestValue", 0),
                    "lowest": get_val(stats, "bodyBatteryLowestValue", 0),
                },
                
                "stress": {
                    "avg": get_val(stats, "averageStressLevel", 0),
                    "max": get_val(stats, "maxStressLevel", 0),
                },
                
                "respiration": {
                    "avg_waking": get_val(respiration, "avgWakingRespirationValue", 0),
                    "highest": get_val(respiration, "highestRespirationValue", 0),
                    "lowest": get_val(respiration, "lowestRespirationValue", 0),
                },
                
                "spo2": {
                    "avg": get_val(spo2, "averageSpo2Value", 0),
                    "lowest": get_val(spo2, "lowestSpo2Value", 0),
                },
                
                "training": {
                    "readiness_score": get_val(training_readiness, "score", 0),
                    "vo2_max": get_val(max_metrics, "vo2MaxValue", 0),
                    "fitness_age": get_val(max_metrics, "fitnessAge", 0),
                },
                
                "activities": {
                    "count": len(activities) if isinstance(activities, list) else 0,
                    "list": [
                        {
                            "name": act.get("activityName", ""),
                            "type": act.get("activityType", {}).get("typeKey", ""),
                            "duration_formatted": seconds_to_time(act.get("duration", 0)),
                            "distance_km": round(act.get("distance", 0) / 1000, 2),
                            "calories": act.get("calories", 0),
                        }
                        for act in (activities[:10] if isinstance(activities, list) else [])
                    ]
                },
                
                "body_composition": {
                    "weight_kg": get_val(weight, "weight", 0) / 1000 if get_val(weight, "weight", 0) > 0 else 0,
                    "bmi": get_val(body_comp, "bmi", 0),
                },
                
                "hydration": {
                    "total_ml": get_val(hydration, "valueInML", None),
                    "goal_ml": get_val(hydration, "goalInML", 0),
                },
            }
            
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
