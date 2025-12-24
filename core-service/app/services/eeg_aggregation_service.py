from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from datetime import datetime, timedelta, date
from app.models.eeg_record import EEGRecord
from app.models.eeg_aggregates import DailyEEGRecord, MonthlyEEGRecord, YearlyEEGRecord, EEGRecordsBackup
import logging

logger = logging.getLogger(__name__)

class EEGAggregationService:
    def __init__(self, db: Session):
        self.db = db

    async def process_daily_aggregation(self, target_date: date = None, use_fallback: bool = True):
        """Process daily aggregation for a specific date"""
        if target_date is None:
            target_date = (datetime.now() - timedelta(days=1)).date()
        
        logger.info(f"Starting daily aggregation for date: {target_date}")
        
        try:
            # Check if we have data for the target date
            data_count = self.db.query(EEGRecord).filter(
                func.date(EEGRecord.timestamp) == target_date
            ).count()
            
            logger.info(f"Found {data_count} records for {target_date}")
            
            # Only use fallback logic if explicitly enabled AND no specific date was provided
            if data_count == 0 and use_fallback:
                today = datetime.now().date()
                today_count = self.db.query(EEGRecord).filter(
                    func.date(EEGRecord.timestamp) == today
                ).count()
                
                if today_count > 0:
                    logger.info(f"No data found for {target_date}, using today's data ({today}) with {today_count} records")
                    target_date = today
                    data_count = today_count
                else:
                    logger.warning(f"No EEG data found for {target_date} or {today}")
                    return
            elif data_count == 0:
                logger.warning(f"No EEG data found for {target_date}")
                return
            
            # Get all users who have EEG records for the target date
            users_with_data = self.db.query(EEGRecord.user_id).filter(
                func.date(EEGRecord.timestamp) == target_date
            ).distinct().all()

            aggregated_users = 0
            for user_tuple in users_with_data:
                user_id = user_tuple[0]
                await self._aggregate_daily_for_user(user_id, target_date)
                aggregated_users += 1
            
            logger.info(f"Aggregated data for {aggregated_users} users on {target_date}")
            
            # Only backup and clean if we're processing older data (not today)
            if target_date < datetime.now().date():
                await self._backup_and_clean_eeg_records(target_date)
                logger.info(f"Backed up and cleaned data for {target_date}")
            else:
                logger.info(f"Skipping backup/cleanup for current date {target_date}")
            
            logger.info(f"Daily aggregation completed for {target_date}")
            
        except Exception as e:
            logger.error(f"Error in daily aggregation: {str(e)}")
            self.db.rollback()
            raise

    async def _aggregate_daily_for_user(self, user_id: int, target_date: date):
        """Aggregate daily data for a specific user"""
        # Calculate averages for the day
        daily_stats = self.db.query(
            func.avg(EEGRecord.focus_label).label('avg_focus'),
            func.avg(EEGRecord.stress_label).label('avg_stress'),
            func.avg(EEGRecord.wellness_label).label('avg_wellness'),
            func.count(EEGRecord.id).label('record_count')
        ).filter(
            and_(
                EEGRecord.user_id == user_id,
                func.date(EEGRecord.timestamp) == target_date
            )
        ).first()

        if daily_stats and daily_stats.avg_focus is not None:
            # Check if record already exists
            existing_record = self.db.query(DailyEEGRecord).filter(
                and_(
                    DailyEEGRecord.user_id == user_id,
                    DailyEEGRecord.date == target_date
                )
            ).first()

            focus_val = round(daily_stats.avg_focus, 2)
            stress_val = round(daily_stats.avg_stress, 2)
            wellness_val = round(daily_stats.avg_wellness, 2)

            if existing_record:
                # Update existing record
                existing_record.focus = focus_val
                existing_record.stress = stress_val
                existing_record.wellness = wellness_val
                logger.info(f"Updated daily record for user {user_id} on {target_date}: F={focus_val}, S={stress_val}, W={wellness_val} (from {daily_stats.record_count} records)")
            else:
                # Create new record
                daily_record = DailyEEGRecord(
                    user_id=user_id,
                    date=target_date,
                    focus=focus_val,
                    stress=stress_val,
                    wellness=wellness_val
                )
                self.db.add(daily_record)
                logger.info(f"Created daily record for user {user_id} on {target_date}: F={focus_val}, S={stress_val}, W={wellness_val} (from {daily_stats.record_count} records)")

            self.db.commit()
        else:
            logger.warning(f"No valid data found for user {user_id} on {target_date}")

    async def _backup_and_clean_eeg_records(self, target_date: date):
        """Move EEG records to backup table and delete from main table"""
        try:
            # Get records to backup
            records_to_backup = self.db.query(EEGRecord).filter(
                func.date(EEGRecord.timestamp) == target_date
            ).all()
            
            if not records_to_backup:
                logger.info(f"No records to backup for {target_date}")
                return

            logger.info(f"Backing up {len(records_to_backup)} records for {target_date}")

            # Create backup records
            backup_count = 0
            for record in records_to_backup:
                backup_record = EEGRecordsBackup(
                    original_id=record.id,
                    user_id=record.user_id,
                    timestamp=record.timestamp.date(),
                    focus_label=record.focus_label,
                    stress_label=record.stress_label,
                    wellness_label=record.wellness_label,
                    backup_date=datetime.now().date()
                )
                self.db.add(backup_record)
                backup_count += 1

            # Commit backup records first
            self.db.commit()
            logger.info(f"✅ Created {backup_count} backup records")

            # Delete from main table
            deleted_count = self.db.query(EEGRecord).filter(
                func.date(EEGRecord.timestamp) == target_date
            ).delete(synchronize_session=False)

            self.db.commit()
            logger.info(f"🗑️ Deleted {deleted_count} records from main table for {target_date}")
            
        except Exception as e:
            logger.error(f"Error in backup_and_clean for {target_date}: {str(e)}")
            self.db.rollback()
            raise

    async def process_monthly_aggregation(self, year: int = None, month: int = None):
        """Process monthly aggregation and cleanup daily records for that month"""
        if year is None or month is None:
            last_month = datetime.now().replace(day=1) - timedelta(days=1)
            year = last_month.year
            month = last_month.month

        logger.info(f"Starting monthly aggregation for {year}-{month:02d}")

        try:
            # Check if we have daily data for this month
            daily_count = self.db.query(DailyEEGRecord).filter(
                and_(
                    func.extract('year', DailyEEGRecord.date) == year,
                    func.extract('month', DailyEEGRecord.date) == month
                )
            ).count()
            
            logger.info(f"Found {daily_count} daily records for {year}-{month:02d}")
            
            if daily_count == 0:
                logger.warning(f"No daily records found for {year}-{month:02d}")
                return

            # Get all users who have daily records for the target month
            users_with_data = self.db.query(DailyEEGRecord.user_id).filter(
                and_(
                    func.extract('year', DailyEEGRecord.date) == year,
                    func.extract('month', DailyEEGRecord.date) == month
                )
            ).distinct().all()

            logger.info(f"Processing {len(users_with_data)} users for {year}-{month:02d}")

            aggregated_users = 0
            for user_tuple in users_with_data:
                user_id = user_tuple[0]
                await self._aggregate_monthly_for_user(user_id, year, month)
                aggregated_users += 1

            logger.info(f"Aggregated monthly data for {aggregated_users} users")

            # Clean up daily records for this month after successful aggregation
            await self._cleanup_daily_records(year, month)

            logger.info(f"Monthly aggregation completed for {year}-{month:02d}")

        except Exception as e:
            logger.error(f"Error in monthly aggregation for {year}-{month:02d}: {str(e)}")
            self.db.rollback()
            raise

    async def _aggregate_monthly_for_user(self, user_id: int, year: int, month: int):
        """Aggregate monthly data for a specific user"""
        try:
            # Calculate averages for the month
            monthly_stats = self.db.query(
                func.avg(DailyEEGRecord.focus).label('avg_focus'),
                func.avg(DailyEEGRecord.stress).label('avg_stress'),
                func.avg(DailyEEGRecord.wellness).label('avg_wellness'),
                func.count(DailyEEGRecord.id).label('daily_count')
            ).filter(
                and_(
                    DailyEEGRecord.user_id == user_id,
                    func.extract('year', DailyEEGRecord.date) == year,
                    func.extract('month', DailyEEGRecord.date) == month
                )
            ).first()

            if monthly_stats and monthly_stats.avg_focus is not None:
                # Check if record already exists
                existing_record = self.db.query(MonthlyEEGRecord).filter(
                    and_(
                        MonthlyEEGRecord.user_id == user_id,
                        MonthlyEEGRecord.year == year,
                        MonthlyEEGRecord.month == month
                    )
                ).first()

                focus_val = round(monthly_stats.avg_focus, 2)
                stress_val = round(monthly_stats.avg_stress, 2)
                wellness_val = round(monthly_stats.avg_wellness, 2)

                if existing_record:
                    # Update existing record
                    existing_record.focus = focus_val
                    existing_record.stress = stress_val
                    existing_record.wellness = wellness_val
                    logger.info(f"Updated monthly record for user {user_id} for {year}-{month:02d}: F={focus_val}, S={stress_val}, W={wellness_val} (from {monthly_stats.daily_count} daily records)")
                else:
                    # Create new record
                    monthly_record = MonthlyEEGRecord(
                        user_id=user_id,
                        year=year,
                        month=month,
                        focus=focus_val,
                        stress=stress_val,
                        wellness=wellness_val
                    )
                    self.db.add(monthly_record)
                    logger.info(f"Created monthly record for user {user_id} for {year}-{month:02d}: F={focus_val}, S={stress_val}, W={wellness_val} (from {monthly_stats.daily_count} daily records)")

                self.db.commit()
            else:
                logger.warning(f"No valid monthly data found for user {user_id} for {year}-{month:02d}")

        except Exception as e:
            logger.error(f"Error aggregating monthly data for user {user_id} for {year}-{month:02d}: {str(e)}")
            self.db.rollback()
            raise

    async def _cleanup_daily_records(self, year: int, month: int):
        """Delete daily records for the specified month after monthly aggregation"""
        try:
            logger.info(f"Starting cleanup of daily records for {year}-{month:02d}")
            
            # Count records to be deleted
            records_to_delete = self.db.query(DailyEEGRecord).filter(
                and_(
                    func.extract('year', DailyEEGRecord.date) == year,
                    func.extract('month', DailyEEGRecord.date) == month
                )
            ).all()
            
            if not records_to_delete:
                logger.info(f"No daily records found to delete for {year}-{month:02d}")
                return

            logger.info(f"Deleting {len(records_to_delete)} daily records for {year}-{month:02d}")
            
            # Delete daily records for this month
            deleted_count = self.db.query(DailyEEGRecord).filter(
                and_(
                    func.extract('year', DailyEEGRecord.date) == year,
                    func.extract('month', DailyEEGRecord.date) == month
                )
            ).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"🗑️ Successfully deleted {deleted_count} daily records for {year}-{month:02d}")
            
        except Exception as e:
            logger.error(f"Error cleaning up daily records for {year}-{month:02d}: {str(e)}")
            self.db.rollback()
            raise

    async def process_yearly_aggregation(self, year: int = None):
        """Process yearly aggregation (default: last year)"""
        if year is None:
            year = datetime.now().year - 1

        try:
            # Get all users who have monthly records for the target year
            users_with_data = self.db.query(MonthlyEEGRecord.user_id).filter(
                MonthlyEEGRecord.year == year
            ).distinct().all()

            for user_tuple in users_with_data:
                user_id = user_tuple[0]
                await self._aggregate_yearly_for_user(user_id, year)

            logger.info(f"Yearly aggregation completed for {year}")

        except Exception as e:
            logger.error(f"Error in yearly aggregation: {str(e)}")
            self.db.rollback()
            raise

    async def _aggregate_yearly_for_user(self, user_id: int, year: int):
        """Aggregate yearly data for a specific user"""
        # Calculate averages for the year
        yearly_stats = self.db.query(
            func.avg(MonthlyEEGRecord.focus).label('avg_focus'),
            func.avg(MonthlyEEGRecord.stress).label('avg_stress'),
            func.avg(MonthlyEEGRecord.wellness).label('avg_wellness')
        ).filter(
            and_(
                MonthlyEEGRecord.user_id == user_id,
                MonthlyEEGRecord.year == year
            )
        ).first()

        if yearly_stats and yearly_stats.avg_focus is not None:
            # Check if record already exists
            existing_record = self.db.query(YearlyEEGRecord).filter(
                and_(
                    YearlyEEGRecord.user_id == user_id,
                    YearlyEEGRecord.year == year
                )
            ).first()

            if existing_record:
                # Update existing record
                existing_record.focus = round(yearly_stats.avg_focus, 2)
                existing_record.stress = round(yearly_stats.avg_stress, 2)
                existing_record.wellness = round(yearly_stats.avg_wellness, 2)
            else:
                # Create new record
                yearly_record = YearlyEEGRecord(
                    user_id=user_id,
                    year=year,
                    focus=round(yearly_stats.avg_focus, 2),
                    stress=round(yearly_stats.avg_stress, 2),
                    wellness=round(yearly_stats.avg_wellness, 2)
                )
                self.db.add(yearly_record)

            self.db.commit()
