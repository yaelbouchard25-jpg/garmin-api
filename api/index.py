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
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            # MODE DEBUG
            if 'debug' in params:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                email = os.environ.get('GARMIN_EMAIL')
                password = os.environ.get('GARMIN_PASSWORD')
                
                if not email or not password:
                    self.wfile.write(json.dumps({"error": "Credentials missing"}).encode())
                    return
                
                date_str = params['date'][0] if 'date' in params and params['date'][0] else datetime.now().strftime("%Y-%m-%d")
                
                try:
                    client = Garmin(email, password)
                    client.login()
                    
                    # Récupérer toutes les données brutes
                    stats = client.get_stats(date_str)
                    sleep_data = client.get_sleep_data(date_str)
                    hrv = client.get_hrv_data(date_str)
                    spo2 = client.get_spo2_data(date_str)
                    training_readiness = client.get_training_readiness(date_str)
                    max_metrics = client.get_max_metrics(date_str)
                    
                    debug_response = {
                        "DEBUG_MODE": True,
                        "date": date_str,
                        "stats_keys": list(stats.keys()) if isinstance(stats, dict) else None,
                        "stats_sample": {k: stats.get(k) for k in ['averageHeartRateInBeatsPerMinute', 'avgHeartRate', 'averageHR'] if k in stats} if isinstance(stats, dict) else None,
                        "sleep_keys": list(sleep_data.keys()) if isinstance(sleep_data, dict) else None,
                        "daily_sleep_keys": list(sleep_data.get('dailySleepDTO', {}).keys()) if isinstance(sleep_data, dict) else None,
                        "hrv_keys": list(hrv.keys()) if isinstance(hrv, dict) else None,
                        "hrv_full": hrv,
                        "spo2_keys": list(spo2.keys()) if isinstance(spo2, dict) else None,
                        "spo2_full": spo2,
                        "training_readiness_keys": list(training_readiness.keys()) if isinstance(training_readiness, dict) else None,
                        "training_readiness_full": training_readiness,
                        "max_metrics_keys": list(max_metrics.keys()) if isinstance(max_metrics, dict) else None,
                        "max_metrics_full": max_metrics,
                    }
                    
                    self.wfile.write(json.dumps(debug_response, indent=2).encode())
                except Exception as e:
                    error_debug = {
                        "DEBUG_MODE": True,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                    self.wfile.write(json.dumps(error_debug, indent=2).encode())
                return
            
            # MODE NORMAL
            email = os.environ.get('GARMIN_EMAIL')
            password = os.environ.get('GARMIN_PASSWORD')
            
            if not email or not password:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Identifiants non configurés"}).encode())
                return
            
            date_str = params['date'][0] if 'date' in params and params['date'][0] else datetime.now().strftime("%Y-%m-%d")
            
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Format invalide. Utilisez YYYY-MM-DD"}).encode())
                return
            
            # Connexion
            client = Garmin(email, password)
            client.login()
            
            # Fonctions helpers
            def sec_to_time(seconds):
                if not seconds or seconds == 0:
                    return "0h00"
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                return f"{h}h{m:02d}"
            
            def safe_get(method_name, *args):
                try:
                    if hasattr(client, method_name):
                        result = getattr(client, method_name)(*args)
                        return result if result is not None else ({} if 'activit' not in method_name else [])
                    return {} if 'activit' not in method_name else []
                except:
                    return {} if 'activit' not in method_name else []
            
            # Fonction pour chercher dans plusieurs clés possibles
            def get_val_multi(data, keys, default=0):
                """Cherche la valeur dans plusieurs clés possibles"""
                if not data or not isinstance(data, dict):
                    return default
                
                if isinstance(keys, str):
                    keys = [keys]
                
                for key in keys:
                    if key in data and data[key] is not None:
                        value = data[key]
                        # Ne retourner 0 que si c'est vraiment 0, pas None
                        if value != 0 or (value == 0 and default != 0):
                            return value
                
                return default
            
            def get_val(data, key, default=0):
                if data and isinstance(data, dict):
                    val = data.get(key)
                    return val if val is not None else default
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
            daily_sleep = sleep_data.get('dailySleepDTO', {}) if isinstance(sleep_data, dict) else {}
            sleep_levels = sleep_data.get('sleepLevels', []) if isinstance(sleep_data, dict) else []
            sleep_movement = sleep_data.get('sleepMovement', []) if isinstance(sleep_data, dict) else []
            
            # Extraction HRV avec clés multiples
            hrv_status = get_val_multi(hrv, ['status', 'hrvStatus'], None)
            hrv_avg = get_val_multi(hrv, ['lastNightAvg', 'weeklyAvg', 'lastSevenDaysAvg'], 0)
            hrv_last_night = get_val_multi(hrv, ['lastNightAvg', 'value'], 0)
            hrv_baseline_low = get_val_multi(hrv, ['baselineLowUpper', 'baselineLow'], 0)
            hrv_baseline_balanced = get_val_multi(hrv, ['baselineBalancedLow', 'baselineBalanced'], 0)
            hrv_last_night_5min = get_val_multi(hrv, ['lastNight5MinHigh', 'fiveMinuteHigh'], 0)
            
            # Extraction SPO2 avec clés multiples
            spo2_avg = get_val_multi(spo2, ['averageSpo2Value', 'avgSpO2', 'averageSpO2', 'calendarDate'], 0)
            spo2_lowest = get_val_multi(spo2, ['lowestSpo2Value', 'lowestSpO2', 'minSpO2'], 0)
            
            # Extraction training avec clés multiples
            readiness_score = get_val_multi(training_readiness, ['score', 'trainingReadinessScore', 'readiness'], 0)
            readiness_level = get_val_multi(training_readiness, ['level', 'readinessLevel'], None)
            
            # Durées sommeil
            sleep_total_sec = get_val(daily_sleep, "sleepTimeSeconds", 0)
            sleep_deep_sec = get_val(daily_sleep, "deepSleepSeconds", 0)
            sleep_light_sec = get_val(daily_sleep, "lightSleepSeconds", 0)
            sleep_rem_sec = get_val(daily_sleep, "remSleepSeconds", 0)
            sleep_awake_sec = get_val(daily_sleep, "awakeSleepSeconds", 0)
            sleep_unmeas_sec = get_val(daily_sleep, "unmeasurableSleepSeconds", 0)
            sleep_nap_sec = get_val(daily_sleep, "napTimeSeconds", 0)
            
            # FC moyenne : chercher dans les activités si pas dans stats
            avg_hr = get_val_multi(stats, ['averageHeartRateInBeatsPerMinute', 'avgHeartRate', 'averageHR'], 0)
            if avg_hr == 0 and isinstance(activities, list) and len(activities) > 0:
                # Calculer la moyenne des FC des activités
                hr_values = [act.get('averageHR', 0) for act in activities if act.get('averageHR', 0) > 0]
                avg_hr = round(sum(hr_values) / len(hr_values)) if hr_values else 0
            
            # Hydration avec clés multiples
            hydration_total = get_val_multi(hydration, ['valueInML', 'value', 'totalHydration'], None)
            hydration_sweat = get_val_multi(hydration, ['sweatLossInML', 'sweatLoss', 'estimatedSweatLoss'], None)
            
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
                    "avg": avg_hr,
                    "resting": get_val(stats, "restingHeartRate", 0),
                    "max": get_val(stats, "maxHeartRate", 0),
                    "min": get_val(stats, "minHeartRate", 0),
                    "hrv_avg": hrv_avg,
                    "hrv_status": hrv_status,
                    "hrv_baseline_low": hrv_baseline_low,
                    "hrv_baseline_balanced": hrv_baseline_balanced,
                    "hrv_last_night": hrv_last_night,
                    "hrv_last_night_5min": hrv_last_night_5min,
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
                    "sleep_score": get_val_multi(daily_sleep, ['overallSleepScore', 'sleepScore', 'score'], 0),
                    "sleep_score_feedback": get_val(daily_sleep, "sleepScoreFeedback", None),
                    "sleep_score_insight": get_val(daily_sleep, "sleepScoreInsight", None),
                    "sleep_score_quality": get_val_multi(daily_sleep, ['sleepScoreQuality', 'qualityScore'], 0),
                    "sleep_score_recovery": get_val_multi(daily_sleep, ['sleepScoreRecovery', 'recoveryScore'], 0),
                    "sleep_score_duration": get_val_multi(daily_sleep, ['sleepScoreDuration', 'durationScore'], 0),
                    "sleep_quality": get_val(daily_sleep, "sleepQualityTypeName", None),
                    "awake_count": get_val(daily_sleep, "awakeCount", 0),
                    "avg_sleep_stress": get_val(daily_sleep, "avgSleepStress", 0),
                    "sleep_start": get_val(daily_sleep, "sleepStartTimestampLocal", None),
                    "sleep_end": get_val(daily_sleep, "sleepEndTimestampLocal", None),
                    "sleep_window_confirmed": get_val(daily_sleep, "sleepWindowConfirmed", False),
                    "avg_respiration": get_val_multi(daily_sleep, ['avgSleepRespiration', 'avgRespiration', 'averageRespiration'], 0),
                    "lowest_respiration": get_val_multi(daily_sleep, ['lowestRespiration', 'minRespiration'], 0),
                    "highest_respiration": get_val_multi(daily_sleep, ['highestRespiration', 'maxRespiration'], 0),
                    "avg_spo2_sleep": get_val_multi(daily_sleep, ['avgOxygenSaturation', 'avgSpO2', 'averageSpO2'], 0),
                    "sleep_levels_count": len(sleep_levels),
                    "sleep_movements_count": len(sleep_movement),
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
                    "avg_waking": get_val_multi(respiration, ['avgWakingRespirationValue', 'averageWakingRespiration', 'avgRespiration'], 0),
                    "highest": get_val_multi(respiration, ['highestRespirationValue', 'maxRespiration'], 0),
                    "lowest": get_val_multi(respiration, ['lowestRespirationValue', 'minRespiration'], 0),
                },
                "spo2": {
                    "avg": spo2_avg,
                    "lowest": spo2_lowest,
                },
                "training": {
                    "readiness_score": readiness_score,
                    "readiness_level": readiness_level,
                    "training_status": get_val_multi(training_status, ['trainingStatus', 'status'], None),
                    "vo2_max": get_val_multi(max_metrics, ['vo2MaxValue', 'generic', 'vo2Max'], 0),
                    "fitness_age": get_val_multi(max_metrics, ['fitnessAge', 'age'], 0),
                    "vo2_max_running": get_val_multi(max_metrics, ['vo2MaxRunningValue', 'running'], 0),
                    "vo2_max_cycling": get_val_multi(max_metrics, ['vo2MaxCyclingValue', 'cycling'], 0),
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
                    "weight_kg": round(get_val(weight, "weight", 0) / 1000, 2) if get_val(weight, "weight", 0) > 0 else 0,
                    "bmi": get_val(body_comp, "bmi", 0),
                    "body_fat_percentage": get_val(body_comp, "bodyFat", 0),
                    "body_water_percentage": get_val(body_comp, "bodyWater", 0),
                    "bone_mass_kg": get_val(body_comp, "boneMass", 0),
                    "muscle_mass_kg": get_val(body_comp, "muscleMass", 0),
                    "metabolic_age": get_val(body_comp, "metabolicAge", 0),
                    "visceral_fat": get_val(body_comp, "visceralFat", 0),
                },
                "hydration": {
                    "total_ml": hydration_total,
                    "goal_ml": get_val_multi(hydration, ['goalInML', 'goal'], 0),
                    "sweat_loss_ml": hydration_sweat,
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
