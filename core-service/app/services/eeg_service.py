import json
import os
import random
import numpy as np
import tempfile
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.eeg_record import EEGRecord
from app.models.eeg_aggregates import DailyEEGRecord, MonthlyEEGRecord, YearlyEEGRecord
from app.schemas.eeg import EEGRecordIn
from datetime import datetime, timedelta, date
from typing import List



class EEGService:
    def __init__(self, db: Session):
        self.db = db

    
    def get_aggregated_data(self, user_id: int, range: str):
        now = datetime.now()
        
        if range == "weekly":
            return self._get_weekly_data(user_id, now)
        elif range == "monthly":
            return self._get_monthly_data(user_id, now)
        elif range == "yearly":
            return self._get_yearly_data(user_id, now)
        elif range == "hourly":
            return self._get_hourly_data(user_id, now)
        elif range == "daily":
            return self._get_daily_data(user_id, now)
        elif range == "quarterly":
            return self._get_quarterly_data(user_id, now)
        
        # Return proper empty structure instead of empty array
        return {
            "labels": [],
            "datasets": [
                {
                    "data": [],
                    "color": "#4287f5",
                    "strokeWidth": 2,
                    "label": "Focus"
                },
                {
                    "data": [],
                    "color": "#FFA500",
                    "strokeWidth": 2,
                    "label": "Stress"
                }
            ],
            "legend": ["Focus", "Stress"]
        }
    
    def _get_weekly_data(self, user_id: int, now: datetime):
        """Returns data in the format expected by frontend for weekly view"""
        # Get start of current week (Monday)
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        
        # Query data from daily_eeg_records table instead of eeg_records
        query = (
            self.db.query(
                extract('dow', DailyEEGRecord.date).label('day_of_week'),
                DailyEEGRecord.focus.label('focus_avg'),
                DailyEEGRecord.stress.label('stress_avg'),
                DailyEEGRecord.wellness.label('wellness_avg')
            )
            .filter(
                DailyEEGRecord.user_id == user_id,
                DailyEEGRecord.date >= start.date(),
                DailyEEGRecord.date < end.date()
            )
            .all()
        )
        
        # Create a dictionary for easy lookup
        data_dict = {int(row.day_of_week): (row.focus_avg or 0, row.stress_avg or 0, row.wellness_avg or 0) for row in query}
        
        # Days mapping: 0=Sunday, 1=Monday, ..., 6=Saturday
        # Frontend expects: Mon, Tue, Wed, Thu, Fri, Sat, Sun
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_mapping = [1, 2, 3, 4, 5, 6, 0]  # Map to PostgreSQL day_of_week values
        
        focus_data = []
        stress_data = []
        wellness_data = []
        
        for day_num in day_mapping:
            if day_num in data_dict:
                focus_val, stress_val, wellness_val = data_dict[day_num]
                focus_data.append(round(focus_val, 1))
                stress_data.append(round(stress_val, 1))
                wellness_data.append(round(wellness_val, 1))
            else:
                # No data for this day, use default values
                focus_data.append(0.0)
                stress_data.append(0.0)
                wellness_data.append(0.0)
        
        return {
            "labels": day_labels,
            "datasets": [
                {
                    "data": focus_data,
                    "color": "#4287f5",
                    "strokeWidth": 2,
                    "label": "Focus"
                },
                {
                    "data": stress_data,
                    "color": "#FFA500",
                    "strokeWidth": 2,
                    "label": "Stress"
                },
                {
                    "data": wellness_data,
                    "color": "#4CAF50",
                    "strokeWidth": 2,
                    "label": "Wellness"
                }
            ],
            "legend": ["Focus", "Stress", "Wellness"],
            "total_samples": len(query)
        }
    
    def _get_monthly_data(self, user_id: int, now: datetime):
        """Returns data in the format expected by frontend for monthly view"""
        # Get current month and year
        current_year = now.year
        current_month = now.month
        
        # For current month, we might need to combine monthly data with current partial data
        # But let's try to use monthly aggregated data if available, otherwise fall back to daily
        
        # Query monthly aggregated data for the current year
        monthly_record = (
            self.db.query(MonthlyEEGRecord)
            .filter(
                MonthlyEEGRecord.user_id == user_id,
                MonthlyEEGRecord.year == current_year,
                MonthlyEEGRecord.month == current_month
            )
            .first()
        )
        
        # If we have monthly data, use it for better performance
        if monthly_record:
            # For simplicity, distribute monthly averages across weeks
            focus_avg = monthly_record.focus
            stress_avg = monthly_record.stress
            wellness_avg = monthly_record.wellness
            
            # Create data for 4 weeks with the monthly averages
            week_labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
            focus_data = [focus_avg] * 4
            stress_data = [stress_avg] * 4
            wellness_data = [wellness_avg] * 4
        else:
            # Fallback to daily data if monthly aggregation not available
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                next_month = start.replace(year=start.year + 1, month=1)
            else:
                next_month = start.replace(month=start.month + 1)
            
            # Query data from daily_eeg_records grouped by week of month
            query = (
                self.db.query(
                    func.floor((extract('day', DailyEEGRecord.date) - 1) / 7).label('week_num'),
                    func.avg(DailyEEGRecord.focus).label('focus_avg'),
                    func.avg(DailyEEGRecord.stress).label('stress_avg'),
                    func.avg(DailyEEGRecord.wellness).label('wellness_avg')
                )
                .filter(
                    DailyEEGRecord.user_id == user_id,
                    DailyEEGRecord.date >= start.date(),
                    DailyEEGRecord.date < next_month.date()
                )
                .group_by('week_num')
                .order_by('week_num')
                .all()
            )
            
            # Create data for 4 weeks
            week_labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
            focus_data = [0.0] * 4
            stress_data = [0.0] * 4
            wellness_data = [0.0] * 4
            
            for row in query:
                week_idx = int(row.week_num)
                if 0 <= week_idx < 4:
                    focus_data[week_idx] = round(row.focus_avg or 0, 1)
                    stress_data[week_idx] = round(row.stress_avg or 0, 1)
                    wellness_data[week_idx] = round(row.wellness_avg or 0, 1)
        
        return {
            "labels": week_labels,
            "datasets": [
                {
                    "data": focus_data,
                    "color": "#4287f5",
                    "strokeWidth": 2,
                    "label": "Focus"
                },
                {
                    "data": stress_data,
                    "color": "#FFA500",
                    "strokeWidth": 2,
                    "label": "Stress"
                },
                {
                    "data": wellness_data,
                    "color": "#4CAF50",
                    "strokeWidth": 2,
                    "label": "Wellness"
                }
            ],
            "legend": ["Focus", "Stress", "Wellness"]
        }
    
    def _get_yearly_data(self, user_id: int, now: datetime):
        """Returns data in the format expected by frontend for yearly view"""
        # Get start of current year
        current_year = now.year
        
        # Check if we have yearly aggregated data for previous year
        yearly_record = (
            self.db.query(YearlyEEGRecord)
            .filter(
                YearlyEEGRecord.user_id == user_id,
                YearlyEEGRecord.year == current_year
            )
            .first()
        )
        
        # If we have yearly data and it's not the current year, use it
        if yearly_record and current_year < datetime.utcnow().year:
            # Use yearly aggregated data - distribute across months
            focus_avg = yearly_record.focus
            stress_avg = yearly_record.stress
            wellness_avg = yearly_record.wellness
            
            month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            focus_data = [focus_avg] * 12
            stress_data = [stress_avg] * 12
            wellness_data = [wellness_avg] * 12
        else:
            # Use monthly aggregated data for better performance than raw EEG records
            query = (
                self.db.query(
                    MonthlyEEGRecord.month.label('month'),
                    MonthlyEEGRecord.focus.label('focus_avg'),
                    MonthlyEEGRecord.stress.label('stress_avg'),
                    MonthlyEEGRecord.wellness.label('wellness_avg')
                )
                .filter(
                    MonthlyEEGRecord.user_id == user_id,
                    MonthlyEEGRecord.year == current_year
                )
                .order_by('month')
                .all()
            )
            
            # Create data for all 12 months
            month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            focus_data = [0.0] * 12
            stress_data = [0.0] * 12
            wellness_data = [0.0] * 12
            
            for row in query:
                month_idx = int(row.month) - 1  # Convert 1-12 to 0-11
                if 0 <= month_idx < 12:
                    focus_data[month_idx] = round(row.focus_avg or 0, 1)
                    stress_data[month_idx] = round(row.stress_avg or 0, 1)
                    wellness_data[month_idx] = round(row.wellness_avg or 0, 1)
        
        return {
            "labels": month_labels,
            "datasets": [
                {
                    "data": focus_data,
                    "color": "#4287f5",
                    "strokeWidth": 2,
                    "label": "Focus"
                },
                {
                    "data": stress_data,
                    "color": "#FFA500",
                    "strokeWidth": 2,
                    "label": "Stress"
                },
                {
                    "data": wellness_data,
                    "color": "#4CAF50",
                    "strokeWidth": 2,
                    "label": "Wellness"
                }
            ],
            "legend": ["Focus", "Stress", "Wellness"]
        }
    
    def _get_hourly_data(self, user_id: int, now: datetime):
        """Returns hourly data for today (current day)"""
        # Get start and end of today
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = start_of_today + timedelta(days=1)
        
        # Query data grouped by hour for today only
        query = (
            self.db.query(
                func.date_trunc('hour', EEGRecord.timestamp).label('hour'),
                func.avg(EEGRecord.focus_label).label('focus_avg'),
                func.avg(EEGRecord.stress_label).label('stress_avg'),
                func.avg(EEGRecord.wellness_label).label('wellness_avg')
            )
            .filter(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= start_of_today,
                EEGRecord.timestamp < end_of_today
            )
            .group_by('hour')
            .order_by('hour')
        )
        
        # Create a dictionary for easy lookup
        results = query.all()
        data_dict = {
            row.hour.replace(minute=0, second=0, microsecond=0): {
                'focus': row.focus_avg,
                'stress': row.stress_avg,
                'wellness': row.wellness_avg
            }
            for row in results
        }
        
        # Generate 24 hourly slots for today
        labels = []
        focus_data = []
        stress_data = []
        wellness_data = []
        
        for i in range(24):
            hour_time = start_of_today + timedelta(hours=i)
            label = hour_time.strftime("%H:%M")
            
            # Get data or use defaults if missing
            data_point = data_dict.get(hour_time, {})
            focus = data_point.get('focus', 0.0)
            stress = data_point.get('stress', 0.0)
            wellness = data_point.get('wellness', 0.0)
            
            labels.append(label)
            focus_data.append(round(focus, 1))
            stress_data.append(round(stress, 1))
            wellness_data.append(round(wellness, 1))
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "data": focus_data,
                    "color": "#4287f5",
                    "strokeWidth": 2,
                    "label": "Focus"
                },
                {
                    "data": stress_data,
                    "color": "#FFA500",
                    "strokeWidth": 2,
                    "label": "Stress"
                },
                {
                    "data": wellness_data,
                    "color": "#4CAF50",
                    "strokeWidth": 2,
                    "label": "Wellness"
                }
            ],
            "legend": ["Focus", "Stress", "Wellness"]
        }
    
    def _get_daily_data(self, user_id: int, now: datetime):
        """Returns hourly data for today (current day)"""
        # Get start and end of today
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = start_of_today + timedelta(days=1)
        
        # Query data grouped by hour for today only
        query = (
            self.db.query(
                func.date_trunc('hour', EEGRecord.timestamp).label('hour'),
                func.avg(EEGRecord.focus_label).label('focus_avg'),
                func.avg(EEGRecord.stress_label).label('stress_avg'),
                func.avg(EEGRecord.wellness_label).label('wellness_avg')
            )
            .filter(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= start_of_today,
                EEGRecord.timestamp < end_of_today
            )
            .group_by('hour')
            .order_by('hour')
        )
        
        # Create a dictionary for easy lookup
        results = query.all()
        data_dict = {
            row.hour.replace(minute=0, second=0, microsecond=0): {
                'focus': row.focus_avg,
                'stress': row.stress_avg,
                'wellness': row.wellness_avg
            }
            for row in results
        }
        
        # Generate 24 hourly slots for today
        labels = []
        focus_data = []
        stress_data = []
        wellness_data = []
        
        for i in range(24):
            hour_time = start_of_today + timedelta(hours=i)
            
            # Format label as "HH:00"
            labels.append(f"{hour_time.hour:02d}:00")
            
            # Get data or use defaults if missing
            data_point = data_dict.get(hour_time, {})
            focus = data_point.get('focus', 0.0)
            stress = data_point.get('stress', 0.0)
            wellness = data_point.get('wellness', 0.0)
            
            focus_data.append(round(focus, 1))
            stress_data.append(round(stress, 1))
            wellness_data.append(round(wellness, 1))
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "data": focus_data,
                    "color": "#4287f5",
                    "strokeWidth": 2,
                    "label": "Focus"
                },
                {
                    "data": stress_data,
                    "color": "#FFA500",
                    "strokeWidth": 2,
                    "label": "Stress"
                },
                {
                    "data": wellness_data,
                    "color": "#4CAF50",
                    "strokeWidth": 2,
                    "label": "Wellness"
                }
            ],
            "legend": ["Focus", "Stress", "Wellness"]
        }
    
    def _get_quarterly_data(self, user_id: int, now: datetime):
        """Returns quarterly data (last 3 months)"""
        start = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=90))
        
        query = (
            self.db.query(
                extract('year', EEGRecord.timestamp).label('year'),
                extract('month', EEGRecord.timestamp).label('month'),
                func.avg(EEGRecord.focus_label).label('focus_label'),
                func.avg(EEGRecord.stress_label).label('stress_label'),
                func.avg(EEGRecord.wellness_label).label('wellness_label')
            )
            .filter(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= start,
                EEGRecord.timestamp <= now
            )
            .group_by('year', 'month')
            .order_by('year', 'month')
        )
        
        result = [
            {
                "year": int(row.year),
                "month": int(row.month),
                "focus_label": row.focus_label,
                "stress_label": row.stress_label,
                "wellness_label": row.wellness_label
            }
            for row in query.all()
        ]
        return result
    
    def get_best_focus_time(self, user_id: int):
        # Use daily aggregated data to determine best focus patterns
        # Get data from last 30 days for better insights
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Query historical daily data
        daily_records = (
            self.db.query(DailyEEGRecord)
            .filter(
                DailyEEGRecord.user_id == user_id,
                DailyEEGRecord.date >= thirty_days_ago.date()
            )
            .all()
        )
        
        if not daily_records:
            return {"best_time_range": None, "avg_focus": None}
        
        # Calculate average focus from daily records
        avg_focus = sum(record.focus for record in daily_records) / len(daily_records)
        
        # For detailed hourly analysis, we still need to use raw EEG records
        # but only for recent data or when daily aggregates aren't sufficient
        query = (
            self.db.query(
                extract('hour', EEGRecord.timestamp).label('hour'),
                func.avg(EEGRecord.focus_label).label('avg_focus')
            )
            .filter(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= thirty_days_ago
            )
            .group_by('hour')
            .order_by('hour')
        )
        
        results = query.all()
        if not results:
            return {"best_time_range": None, "avg_focus": None}
        
        # Find hours with above-average focus
        overall_avg = sum(row.avg_focus for row in results) / len(results)
        good_hours = [
            {"hour": int(row.hour), "focus": row.avg_focus}
            for row in results 
            if row.avg_focus > overall_avg
        ]
        
        if not good_hours:
            return {"best_time_range": None, "avg_focus": None}
        
        # Find consecutive hour ranges
        ranges = []
        i = 0
        while i < len(good_hours):
            start_hour = good_hours[i]["hour"]
            end_hour = start_hour
            range_focus_sum = good_hours[i]["focus"]
            count = 1
            
            # Find consecutive hours
            while (i + 1 < len(good_hours) and 
                   good_hours[i + 1]["hour"] == good_hours[i]["hour"] + 1):
                i += 1
                end_hour = good_hours[i]["hour"]
                range_focus_sum += good_hours[i]["focus"]
                count += 1
            
            ranges.append({
                "start": start_hour,
                "end": end_hour,
                "avg_focus": range_focus_sum / count,
                "duration": count
            })
            i += 1
        
        # Select the best range (highest average focus, with duration as tiebreaker)
        best_range = max(ranges, key=lambda x: (x["avg_focus"], x["duration"]))
        
        # Format the time range
        start_str = datetime.strptime(str(best_range["start"]), "%H").strftime("%I:%M %p")
        end_str = datetime.strptime(str(best_range["end"] + 1), "%H").strftime("%I:%M %p")
        
        return {
            "best_time_range": f"{start_str} to {end_str}",
            "avg_focus": round(best_range["avg_focus"], 2),
          
        }
    
    def suggest_music(self, user_id: int):
        # Load music URLs from JSON file (load once per call; for production, cache this)
        json_path = os.path.join(os.path.dirname(__file__), "../resources/music_urls.json")
        with open(json_path, "r") as f:
            music_urls = json.load(f)
        
        record = (
            self.db.query(EEGRecord)
            .filter(EEGRecord.user_id == user_id)
            .order_by(EEGRecord.timestamp.desc())
            .first()
        )
        
        if not record:
            return {"suggestion": "No EEG data available.", "music_url": None}
        
        # Decide category based on EEG labels (focus: 0.0-3.0, stress: 0.0-3.0, wellness: 0-100)
        if record.stress_label > 2.0:
            category = "relaxing"
            suggestion = "Relaxing music"
        elif record.focus_label > 2.0:
            category = "concentration"
            suggestion = "Concentration music"
        elif record.wellness_label < 40.0:
            category = "uplifting"
            suggestion = "Uplifting music"
        else:
            category = "ambient"
            suggestion = "Ambient music"
        
        url_list = music_urls.get(category, [])
        music_url = random.choice(url_list) if url_list else None
        
        return {
            "suggestion": suggestion,
            "music_url": music_url,
            "focus_label": record.focus_label,
            "stress_label": record.stress_label,
            "wellness_label": record.wellness_label,
            "timestamp": record.timestamp
        }
    
    def get_current_goals(self, user_id: int):
        now = datetime.utcnow()
        today = now.date()
        
        # For current goals, we need live data from today to show real-time progress
        # Check if we have today's data in daily_eeg_records (after day completion)
        daily_record = (
            self.db.query(DailyEEGRecord)
            .filter(
                DailyEEGRecord.user_id == user_id,
                DailyEEGRecord.date == today
            )
            .first()
        )
        
        if daily_record:
            # Use aggregated daily data if available
            avg_focus = daily_record.focus
            avg_wellness = daily_record.wellness
            avg_stress = daily_record.stress
            low_stress_sessions = 1 if avg_stress < 1.0 else 0
        else:
            # Use live EEG records for current day to show real-time progress
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            records = (
                self.db.query(EEGRecord)
                .filter(
                    EEGRecord.user_id == user_id,
                    EEGRecord.timestamp >= start_of_day,
                    EEGRecord.timestamp <= now
                )
                .all()
            )
            
            if records:
                avg_focus = sum(r.focus_label for r in records if r.focus_label) / len([r for r in records if r.focus_label])
                avg_wellness = sum(r.wellness_label for r in records if r.wellness_label) / len([r for r in records if r.wellness_label])
                low_stress_sessions = sum(1 for r in records if r.stress_label and r.stress_label < 1.0)
            else:
                avg_focus = avg_wellness = 0
                low_stress_sessions = 0
        
        meditation_minutes = min(int(avg_wellness), 20) # Example: wellness as meditation progress
        focus_minutes = min(int(avg_focus * 30), 90) # Example: focus as session progress
        
        return [
            {
                "name": "Daily Meditation",
                "current": meditation_minutes,
                "target": 20,
                "unit": "mins"
            },
            {
                "name": "Focus Session",
                "current": focus_minutes,
                "target": 90,
                "unit": "mins"
            },
            {
                "name": "Stress Management",
                "current": low_stress_sessions,
                "target": 3,
                "unit": "exercise"
            }
        ]
    
    def get_recommendations(self, user_id: int):
        """Generate personalized recommendations based on today's EEG data"""
        from datetime import datetime, timedelta
        from app.schemas.recommendation import Recommendation
        
        # Get current time and start of today
        now = datetime.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = start_of_today + timedelta(days=1)
        
        # Query today's records
        records = (
            self.db.query(EEGRecord)
            .filter(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= start_of_today,
                EEGRecord.timestamp < end_of_today
            )
            .all()
        )
        
        print(f"DEBUG: Found {len(records)} records for user {user_id} today")
        print(f"DEBUG: Date range: {start_of_today} to {end_of_today}")
        
        recommendations = []
        
        if not records:
            recommendations.append(Recommendation(
                label="No Data",
                description="No EEG data available for today. Please record some sessions to get personalized recommendations."
            ))
            return recommendations
        
        # Calculate averages from your data
        avg_focus = sum(r.focus_label for r in records) / len(records)
        avg_stress = sum(r.stress_label for r in records) / len(records) 
        avg_wellness = sum(r.wellness_label for r in records) / len(records)
        
        print(f"DEBUG: Averages - Focus: {avg_focus:.2f}, Stress: {avg_stress:.2f}, Wellness: {avg_wellness:.2f}")
        
        # Based on your sample data (Focus=3, Stress=2.54, Wellness=100), you should get:
        
        # 1. High stress recommendation (stress > 2.0)
        if avg_stress > 2.0:
            recommendations.append(Recommendation(
                label="Caffeine Optimization",
                description="High stress detected. Avoid caffeine and try a breathing exercise to relax."
            ))
        
        # 2. Elevated stress recommendation (stress > 1.5) 
        if avg_stress > 1.5:
            recommendations.append(Recommendation(
                label="Breathing Exercise",
                description="Your stress levels are elevated. Take a 5-minute breathing break to help reduce stress."
            ))
        
        # 3. Focus is good (3.0), so no low focus recommendation
        if avg_focus < 1.5:
            recommendations.append(Recommendation(
                label="Morning Focus Boost",
                description="Your average focus is low this morning. Try a short walk or a cup of green tea to boost your alertness."
            ))
        
        # 4. Late night check (if after 10 PM and high focus)
        if now.hour > 22 and avg_focus > 2.0:
            recommendations.append(Recommendation(
                label="Late Night Gaming Alert", 
                description="Your focus is peaking late at night. Consider winding down to ensure a restful sleep."
            ))
        
        # 5. Always add focus peak time
        if records:
            # Find the hour with highest average focus
            hourly_focus = {}
            for record in records:
                hour = record.timestamp.hour
                if hour not in hourly_focus:
                    hourly_focus[hour] = []
                hourly_focus[hour].append(record.focus_label)
            
            # Calculate average focus per hour
            hourly_averages = {
                hour: sum(values) / len(values) 
                for hour, values in hourly_focus.items()
            }
            
            peak_hour = max(hourly_averages.keys(), key=lambda x: hourly_averages[x])
            
            recommendations.append(Recommendation(
                label="Focus Peak Time",
                description=f"Your focus peak time today is around {peak_hour:02d}:00. Schedule important tasks during this period."
            ))
        
        return recommendations
    
    def process_and_label_records(self, records, user_id):
        results = []
        for record in records:
            # Replace these with your actual ML model predictions
            focus = random.uniform(0, 3)
            stress = random.uniform(0, 3)
            wellness = random.uniform(0, 100)
            
            # Save to DB
            eeg = EEGRecord(
                user_id=user_id,
                timestamp=record.timestamp,
                focus_label=focus,
                stress_label=stress,
                wellness_label=wellness,
                created_by=user_id,
                updated_by=user_id
            )
            self.db.add(eeg)
            
            results.append({
                "timestamp": record.timestamp,
                "focus": focus,
                "stress": stress,
                "wellness": wellness
            })
        
        self.db.commit()
        return results
    
    def get_time_of_day_aggregate(self, user_id: int):
        """Aggregate today's EEG data by time-of-day buckets (morning, midday, afternoon, evening, night)."""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Define time-of-day buckets
        buckets = [
            ("Night", 0, 4),      # 00:00 - 04:59
            ("Morning", 5, 9),    # 05:00 - 09:59
            ("Midday", 10, 13),   # 10:00 - 13:59
            ("Afternoon", 14, 17),# 14:00 - 17:59
            ("Evening", 18, 21),  # 18:00 - 21:59
            ("Night", 22, 23),    # 22:00 - 23:59 (append to Night)
        ]
        # Query all today's records
        records = (
            self.db.query(EEGRecord)
            .filter(
                EEGRecord.user_id == user_id,
                EEGRecord.timestamp >= start_of_day,
                EEGRecord.timestamp < end_of_day
            )
            .all()
        )
        # Prepare bucketed data
        bucket_map = {
            "Night": [],
            "Morning": [],
            "Midday": [],
            "Afternoon": [],
            "Evening": []
        }
        for r in records:
            hour = r.timestamp.hour
            if 0 <= hour <= 4 or 22 <= hour <= 23:
                bucket_map["Night"].append(r)
            elif 5 <= hour <= 9:
                bucket_map["Morning"].append(r)
            elif 10 <= hour <= 13:
                bucket_map["Midday"].append(r)
            elif 14 <= hour <= 17:
                bucket_map["Afternoon"].append(r)
            elif 18 <= hour <= 21:
                bucket_map["Evening"].append(r)
        # Calculate averages
        result = []
        for bucket in ["Morning", "Midday", "Afternoon", "Evening", "Night"]:
            recs = bucket_map[bucket]
            if recs:
                focus_avg = round(sum(r.focus_label for r in recs) / len(recs), 2)
                stress_avg = round(sum(r.stress_label for r in recs) / len(recs), 2)
            else:
                focus_avg = 0.0
                stress_avg = 0.0
            result.append({
                "time_of_day": bucket,
                "focus": focus_avg,
                "stress": stress_avg
            })
        return result