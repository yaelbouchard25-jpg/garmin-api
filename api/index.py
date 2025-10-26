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
            # Récupérer paramètres URL
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            # VÉRIFIER MODE DEBUG EN PREMIER
            if 'debug' in params:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                debug_response = {
                    "DEBUG_MODE": True,
                    "message": "Mode debug activé - récupération des données brutes...",
                    "params_received": str(params)
                }
                self.wfile.write(json.dumps(debug_response, indent=2).encode())
                
                # Maintenant récupérer les vraies données
                email = os.environ.get('GARMIN_EMAIL')
                password = os.environ.get('GARMIN_PASSWORD')
                
                if not email or not password:
                    return
                
                date_str = params['date'][0] if 'date' in params and params['date'][0] else datetime.now().strftime("%Y-%m-%d")
                
                try:
                    client = Garmin(email, password)
                    client.login()
                    
                    sleep_data = client.get_sleep_data(date_str)
                    hrv = client.get_hrv_data(date_str)
                    
                    debug_full = {
                        "DEBUG_MODE": True,
                        "date": date_str,
                        "sleep_data_type": str(type(sleep_data)),
                        "sleep_data_keys": list(sleep_data.keys()) if isinstance(sleep_data, dict) else "not_dict",
                        "sleep_data_sample": str(sleep_data)[:2000],
                        "hrv_type": str(type(hrv)),
                        "hrv_keys": list(hrv.keys()) if isinstance(hrv, dict) else "not_dict",
                        "hrv_sample": str(hrv)[:2000],
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(debug_full, indent=2).encode())
                except Exception as e:
                    error_debug = {
                        "DEBUG_MODE": True,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(error_debug, indent=2).encode())
                return
            
            # MODE NORMAL (sans debug)
            email = os.environ.get('GARMIN_EMAIL')
            password = os.environ.get('GARMIN_PASSWORD')
            
            if not email or not password:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": "Identifiants non configurés"}
                self.wfile.write(json.dumps(response).encode())
                return
            
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
            
            # Fonction conversion temps
            def sec_to_time(seconds):
                if not seconds or seconds == 0:
                    return "0h00"
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                return f"{h}h{m:02d}"
            
            def safe_get(method_name, *args):
                try:
                    if hasattr(client, method_name):
                        method = getattr(client, method_name)
                        result = method(*args)
                        if result is None:
                            return [] if 'activit' in method_name or 'pressure' in method_name else {}
                        return result
                    return [] if 'activit' in method_name or 'pressure' in method_name else {}
                except:
                    return [] if 'activit' in method_name or 'pressure' in method_name else {}
            
            def get_val(data, key, default=0):
                if data and isinstance(data, dict):
                    return data.get(key, default)
                return default
            
            # Récupération données
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
            
            # Extraction sommeil
            daily_sleep = {}
            sleep_levels = []
            sleep_movement = []
            if isinstance(sleep_data, dict):
                daily_sleep = sleep_data.get('dailySleepDTO', {})
                sleep_levels = sleep_data.get('sleepLevels', [])
                sleep_movement = sleep_data.get('sleepMovement', [])
            
            # Extraction HRV
            hrv_status = None
            hrv_avg = 0
            hrv_last_night = 0
            if isinstance(hrv, dict):
                hrv_status = hrv.get('status') or hrv.get('hrvStatus')
                hrv_avg = hrv.get('lastNightAvg', 0) or hrv.get('weeklyAvg', 0)
                hrv_last_night = hrv.get('lastNightAvg', 0)
            
            # Durées sommeil
            sleep_total_sec = get_val(daily_sleep, "sleepTimeSeconds", 0)
            sleep_deep_sec = get_val(daily_sleep, "deepSleepSeconds", 0)
            sleep_light_sec = get_val(daily_sleep, "lightSleepSeconds", 0)
            sleep_rem_sec = get_val(daily_sleep, "remSleepSeconds", 0)
            sleep_awake_sec = get_val(daily_sleep, "awakeSleepSeconds", 0)
            sleep_unmeas_sec = get_val(daily_sleep, "unmeasurableSleepSeconds", 0)
            sleep_nap_sec = get_val(daily_sleep, "napTimeSeconds", 0)
            
            # Réponse complète
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
                    "hrv_baseline_low": get_val(hrv, "baselineLowUpper", 0),
                    "hrv_baseline_balanced": get_val(hrv, "baselineBalancedLow", 0),
                    "hrv_last_night": hrv_last_night,
                    "hrv_last_night_5min": get_val(hrv, "lastNight5MinHigh", 0),
                },
                "sleep": {
                    "total_hours": round(sleep_total_sec / 3600, 2),
                    "total_formatted": sec_to_time(sleep_total_sec),
                    "deep_hours": round(sleep_deep_sec / 3600, 2),
                    "deep_formatted": sec_to_time(sleep_deep_sec),
                    "light_hours": round(sleep_light_sec / 3600, 2),
                    "light_formatted": sec_to_time(sleep_light_sec),
                    "rem_hours": round(sleep_rem_sec / 3600, 2),
                    "rem_formatted": sec_to_time(sleep_rem_sec),
                    "awake_hours": round(sleep_awake_sec / 3600, 2),
                    "awake_formatted": sec_to_time(sleep_awake_sec),
                    "unmeasurable_hours": round(sleep_unmeas_sec / 3600, 2),
                    "unmeasurable_formatted": sec_to_time(sleep_unmeas_sec),
                    "nap_time_hours": round(sleep_nap_sec / 3600, 2),
                    "nap_formatted": sec_to_time(sleep_nap_sec),
                    "sleep_score": get_val(daily_sleep, "overallSleepScore", 0),
                    "sleep_score_feedback": get_val(daily_sleep, "sleepScoreFeedback", None),
                    "sleep_score_insight": get_val(daily_sleep, "sleepScoreInsight", None),
                    "sleep_score_quality": 0,
                    "sleep_score_recovery": 0,
                    "sleep_score_duration": 0,
                    "sleep_quality": get_val(daily_sleep, "sleepQualityTypeName", None),
                    "awake_count": get_val(daily_sleep, "awakeCount", 0),
                    "avg_sleep_stress": get_val(daily_sleep, "avgSleepStress", 0),
                    "sleep_start": get_val(daily_sleep, "sleepStartTimestampLocal", None),
                    "sleep_end": get_val(daily_sleep, "sleepEndTimestampLocal", None),
                    "sleep_window_confirmed": get_val(daily_sleep, "sleepWindowConfirmed", False),
                    "avg_respiration": get_val(daily_sleep, "avgSleepRespiration", 0),
                    "lowest_respiration": get_val(daily_sleep, "lowestRespiration", 0),
                    "highest_respiration": get_val(daily_sleep, "highestRespiration", 0),
                    "avg_spo2_sleep": get_val(daily_sleep, "avgOxygenSaturation", 0),
                    "sleep_levels_count": len(sleep_levels) if sleep_levels else 0,
                    "sleep_movements_count": len(sleep_movement) if sleep_movement else 0,
                },
                "body_battery": {
                    "charged": get_val(stats, "bodyBatteryChargedValue", 0),
                    "drained": get_val(stats, "bodyBatteryDrainedValue", 0),
                    "highest": get_val(stats, "bodyBatteryHighestValue", 0),
                    "lowest": get_val(stats, "bodyBatteryLowestValue", 0),
                    "current": body_battery[-1].get("charged", 0) if isinstance(body_battery, list) and len(body_battery) > 0 else 0,
                },
                "stress": {
                    "avg": get_val(stats, "averageStressLevel", 0),
                    "max": get_val(stats, "maxStressLevel", 0),
                    "rest_time_minutes": get_val(stress_data, "restStressMinutes", 0),
                    "activity_time_minutes": get_val(stress_data, "activityStressMinutes", 0),
                    "low_time_minutes": get_val(stress_data, "lowStressMinutes", 0),
                    "medium_time_minutes": get_val(stress_data, "mediumStressMinutes", 0),
                    "high_time_minutes": get_val(stress_data, "highStressMinutes", 0),
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
                    "readiness_level": get_val(training_readiness, "level", None),
                    "training_status": get_val(training_status, "trainingStatus", None),
                    "vo2_max": get_val(max_metrics, "vo2MaxValue", 0),
                    "fitness_age": get_val(max_metrics, "fitnessAge", 0),
                    "vo2_max_running": get_val(max_metrics, "vo2MaxRunningValue", 0),
                    "vo2_max_cycling": get_val(max_metrics, "vo2MaxCyclingValue", 0),
                },
                "activities": {
                    "count": len(activities) if isinstance(activities, list) else 0,
                    "list": [
                        {
                            "name": act.get("activityName", ""),
                            "type": act.get("activityType", {}).get("typeKey", "") if isinstance(act.get("activityType"), dict) else "",
                            "duration_minutes": round(act.get("duration", 0) / 60, 2),
                            "duration_formatted": sec_to_time(act.get("duration", 0)),
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
                "body_composition": {
                    "weight_kg": get_val(weight, "weight", 0) / 1000 if get_val(weight, "weight", 0) > 0 else 0,
                    "bmi": get_val(body_comp, "bmi", 0),
                    "body_fat_percentage": get_val(body_comp, "bodyFat", 0),
                    "body_water_percentage": get_val(body_comp, "bodyWater", 0),
                    "bone_mass_kg": get_val(body_comp, "boneMass", 0),
                    "muscle_mass_kg": get_val(body_comp, "muscleMass", 0),
                    "metabolic_age": get_val(body_comp, "metabolicAge", 0),
                    "visceral_fat": get_val(body_comp, "visceralFat", 0),
                },
                "hydration": {
                    "total_ml": get_val(hydration, "valueInML", None),
                    "goal_ml": get_val(hydration, "goalInML", 0),
                    "sweat_loss_ml": get_val(hydration, "sweatLossInML", None),
                },
                "blood_pressure": {
                    "systolic": (
                        blood_pressure[0].get("systolic", 0) if isinstance(blood_pressure, list) and len(blood_pressure) > 0 
                        else get_val(blood_pressure, "systolic", 0) if isinstance(blood_pressure, dict) 
                        else 0
                    ),
                    "diastolic": (
                        blood_pressure[0].get("diastolic", 0) if isinstance(blood_pressure, list) and len(blood_pressure) > 0 
                        else get_val(blood_pressure, "diastolic", 0) if isinstance(blood_pressure, dict) 
                        else 0
                    ),
                    "pulse": (
                        blood_pressure[0].get("pulse", 0) if isinstance(blood_pressure, list) and len(blood_pressure) > 0 
                        else get_val(blood_pressure, "pulse", 0) if isinstance(blood_pressure, dict) 
                        else 0
                    ),
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
