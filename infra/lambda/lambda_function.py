import os
import json
import boto3
import psycopg2
from datetime import datetime, timedelta

# Set up S3 client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    # --- Connect to RDS PostgreSQL (core database) ---
    conn = psycopg2.connect(
        host=os.environ['DB_HOST'],
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        connect_timeout=10
    )
    cur = conn.cursor()

    # ---- Extract EventBridge details ----
    aggregation_type = event.get('aggregation_type')  # 'daily', 'monthly', 'yearly'
   
    now = datetime.utcnow()

    try:
        if aggregation_type == "daily":
            # Process daily aggregation
            target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            process_daily_aggregation(parsed_date, conn)

        elif aggregation_type == "monthly":
            # Compute previous month dynamically
            prev_month = (now.replace(day=1) - timedelta(days=1))
            year = prev_month.year
            month = prev_month.month
            print(f"Running monthly aggregation for {year}-{month:02d}")
            process_monthly_aggregation(year, month, conn)

        elif aggregation_type == "yearly":
            # Compute previous year dynamically
            year = now.year - 1
            print(f"Running yearly aggregation for {year}")
            process_yearly_aggregation(year, conn)


        # After aggregation, upload success status
        s3.put_object(
            Body=json.dumps({"status": "aggregation completed", "type": aggregation_type}),
            Bucket=os.environ.get('S3_DAILY_BUCKET'),  # Use daily bucket for status logs
            Key=f"status/aggregation_success_{aggregation_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        return {"status": "ok", "message": f"{aggregation_type} aggregation completed"}

    except Exception as e:
        # If error occurs, log to S3
        print(f"ERROR: {str(e)}")
        s3.put_object(
            Body=json.dumps({"status": "error", "message": str(e), "type": aggregation_type}),
            Bucket=os.environ.get('S3_DAILY_BUCKET'),
            Key=f"status/aggregation_error_{aggregation_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        raise

    finally:
        cur.close()
        conn.close()

# --- DAILY AGGREGATION ---

def process_daily_aggregation(target_date, conn):
    """Process daily aggregation for a specific date"""
    data_count = query_db(conn, "SELECT count(*) FROM eeg_records WHERE timestamp::date = %s", (target_date,))

    if data_count == 0:
        raise Exception(f"No EEG data found for {target_date}")
    
    users_with_data = query_db(conn, "SELECT DISTINCT user_id FROM eeg_records WHERE timestamp::date = %s", (target_date,))

    for user_tuple in users_with_data:
        user_id = user_tuple[0]
        aggregate_daily_for_user(user_id, target_date, conn)

    # Perform backup and cleanup
    backup_and_clean_eeg_records(target_date, conn)

def aggregate_daily_for_user(user_id, target_date, conn):
    """Aggregate daily data for a specific user"""
    daily_stats = query_db(conn, """
        SELECT AVG(focus_label), AVG(stress_label), AVG(wellness_label)
        FROM eeg_records
        WHERE user_id = %s AND timestamp::date = %s
    """, (user_id, target_date))

    if daily_stats and daily_stats[0]:
        save_daily_aggregate(user_id, target_date, daily_stats, conn)
    else:
        raise Exception(f"No valid data found for user {user_id} on {target_date}")

def save_daily_aggregate(user_id, target_date, daily_stats, conn):
    """Save or update daily aggregation record"""
    focus_val, stress_val, wellness_val = map(lambda x: round(x, 2), daily_stats)
    
    existing_record = query_db(conn, """
        SELECT * FROM daily_eeg_records WHERE user_id = %s AND date = %s
    """, (user_id, target_date))

    if existing_record:
        # Update existing record
        query_db(conn, """
            UPDATE daily_eeg_records
            SET focus = %s, stress = %s, wellness = %s
            WHERE user_id = %s AND date = %s
        """, (focus_val, stress_val, wellness_val, user_id, target_date))
    else:
        # Insert new record
        query_db(conn, """
            INSERT INTO daily_eeg_records (user_id, date, focus, stress, wellness)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, target_date, focus_val, stress_val, wellness_val))

    conn.commit()

# --- BACKUP AND CLEANUP FUNCTION --- 

def backup_and_clean_eeg_records(target_date, conn):
    """Backup EEG records to S3 and delete from the EEGRecord table"""
    try:
        # Fetch all EEG records for the target date
        records_to_backup = query_db(conn, """
            SELECT * FROM eeg_records WHERE timestamp::date = %s
        """, (target_date,))

        if not records_to_backup:
            print(f"No records to backup for {target_date}")
            return

        # Prepare data to upload to S3 (convert records to dictionary format)
        backup_data = []
        for record in records_to_backup:
            backup_data.append({
                "id": record[0],
                "user_id": record[1],
                "timestamp": record[2].isoformat() if record[2] else None,
                "focus_label": record[3],
                "stress_label": record[4],
                "wellness_label": record[5]
            })
        
        # Upload data to S3 DAILY BACKUP BUCKET
        s3.put_object(
            Body=json.dumps(backup_data, default=str),
            Bucket=os.environ['S3_DAILY_BUCKET'],
            Key=f"daily_backups/{target_date}/eeg_records_backup.json"
        )

        # Delete from the main table after successful backup
        query_db(conn, """
            DELETE FROM eeg_records WHERE timestamp::date = %s
        """, (target_date,))
        conn.commit()
        print(f"✅ Backup and cleanup successful for {target_date} - {len(backup_data)} records")

    except Exception as e:
        # Log any error that occurs in backup or cleanup
        print(f"❌ Error in backup and cleanup for {target_date}: {str(e)}")
        conn.rollback()
        raise

# --- MONTHLY AGGREGATION ---

def process_monthly_aggregation(year, month, conn):
    """Process monthly aggregation and cleanup daily records for that month"""
    try:
        # Check if we have daily data for this month
        daily_count = query_db(conn, """
            SELECT count(*) FROM daily_eeg_records WHERE EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s
        """, (year, month))

        if daily_count == 0:
            raise Exception(f"No daily records found for {year}-{month:02d}")
        
        # Get all users who have daily records for the target month
        users_with_data = query_db(conn, """
            SELECT DISTINCT user_id FROM daily_eeg_records WHERE EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s
        """, (year, month))

        for user_tuple in users_with_data:
            user_id = user_tuple[0]
            aggregate_monthly_for_user(user_id, year, month, conn)

        # Clean up daily records for this month after successful aggregation
        cleanup_daily_records_for_month(year, month, conn)

    except Exception as e:
        raise Exception(f"Error in monthly aggregation for {year}-{month:02d}: {str(e)}")
    
    
def cleanup_daily_records_for_month(year, month, conn):
    """Backup daily records to S3 and delete after monthly aggregation"""
    try:
        # Fetch records to be backed up
        records_to_backup = query_db(conn, """
            SELECT * FROM daily_eeg_records WHERE EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s
        """, (year, month))

        if not records_to_backup:
            print(f"No daily records found for {year}-{month:02d}")
            return

        # Prepare data for S3 backup
        backup_data = []
        for record in records_to_backup:
            backup_data.append({
                "id": record[0],
                "user_id": record[1],
                "date": record[2].isoformat() if record[2] else None,
                "focus": record[3],
                "stress": record[4],
                "wellness": record[5]
            })
        
        # Upload to S3 MONTHLY BACKUP BUCKET
        s3.put_object(
            Body=json.dumps(backup_data, default=str),
            Bucket=os.environ['S3_MONTHLY_BUCKET'],
            Key=f"monthly_backups/{year}/{month:02d}/daily_records_backup.json"
        )

        print(f"Deleting {len(records_to_backup)} daily records for {year}-{month:02d}")
        
        # Delete the records for this month from daily_eeg_records table
        query_db(conn, """
            DELETE FROM daily_eeg_records WHERE EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s
        """, (year, month))
        conn.commit()
        print(f"✅ Successfully backed up and deleted {len(records_to_backup)} daily records for {year}-{month:02d}")

    except Exception as e:
        # Log any error that occurs during cleanup
        print(f"❌ Error cleaning up daily records for {year}-{month:02d}: {str(e)}")
        conn.rollback()
        raise
   

def aggregate_monthly_for_user(user_id, year, month, conn):
    """Aggregate monthly data for a specific user"""
    monthly_stats = query_db(conn, """
        SELECT AVG(focus), AVG(stress), AVG(wellness)
        FROM daily_eeg_records
        WHERE user_id = %s AND EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s
    """, (user_id, year, month))

    if monthly_stats and monthly_stats[0]:
        save_monthly_aggregate(user_id, year, month, monthly_stats, conn)

def save_monthly_aggregate(user_id, year, month, monthly_stats, conn):
    """Save or update monthly aggregation record"""
    focus_val, stress_val, wellness_val = map(lambda x: round(x, 2), monthly_stats)

    existing_record = query_db(conn, """
        SELECT * FROM monthly_eeg_records WHERE user_id = %s AND year = %s AND month = %s
    """, (user_id, year, month))

    if existing_record:
        query_db(conn, """
            UPDATE monthly_eeg_records
            SET focus = %s, stress = %s, wellness = %s
            WHERE user_id = %s AND year = %s AND month = %s
        """, (focus_val, stress_val, wellness_val, user_id, year, month))
    else:
        query_db(conn, """
            INSERT INTO monthly_eeg_records (user_id, year, month, focus, stress, wellness)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, year, month, focus_val, stress_val, wellness_val))

    conn.commit()

# --- YEARLY AGGREGATION ---

def process_yearly_aggregation(year, conn):
    """Process yearly aggregation"""
    try:
        users_with_data = query_db(conn, """
            SELECT DISTINCT user_id FROM monthly_eeg_records WHERE year = %s
        """, (year,))

        for user_tuple in users_with_data:
            user_id = user_tuple[0]
            aggregate_yearly_for_user(user_id, year, conn)

    except Exception as e:
        raise Exception(f"Error in yearly aggregation for {year}: {str(e)}")

def aggregate_yearly_for_user(user_id, year, conn):
    """Aggregate yearly data for a specific user"""
    yearly_stats = query_db(conn, """
        SELECT AVG(focus), AVG(stress), AVG(wellness)
        FROM monthly_eeg_records
        WHERE user_id = %s AND year = %s
    """, (user_id, year))

    if yearly_stats and yearly_stats[0]:
        save_yearly_aggregate(user_id, year, yearly_stats, conn)

def save_yearly_aggregate(user_id, year, yearly_stats, conn):
    """Save or update yearly aggregation record"""
    focus_val, stress_val, wellness_val = map(lambda x: round(x, 2), yearly_stats)

    existing_record = query_db(conn, """
        SELECT * FROM yearly_eeg_records WHERE user_id = %s AND year = %s
    """, (user_id, year))

    if existing_record:
        query_db(conn, """
            UPDATE yearly_eeg_records
            SET focus = %s, stress = %s, wellness = %s
            WHERE user_id = %s AND year = %s
        """, (focus_val, stress_val, wellness_val, user_id, year))
    else:
        query_db(conn, """
            INSERT INTO yearly_eeg_records (user_id, year, focus, stress, wellness)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, year, focus_val, stress_val, wellness_val))

    conn.commit()

def query_db(conn, query, params):
    """Helper function for executing SQL queries"""
    cur = conn.cursor()
    cur.execute(query, params)
    return cur.fetchall()
