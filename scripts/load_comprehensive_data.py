#!/usr/bin/env python3
"""Load comprehensive trainee wellness data from CSV into the system."""

import csv
import sys
from datetime import datetime
from apps.backend.core.database import SessionLocal
from apps.backend.models.user import User
from apps.backend.models.role import Role
from apps.backend.models.organization import Organization
from apps.backend.models.telemetry import TelemetryEvent
from apps.backend.core.security import hash_password
import uuid

def load_csv_data(csv_path):
    """Load trainee data from CSV file."""
    users_data = {}
    telemetry_data = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            email = row.get('email', '').strip()

            # Group by email to get unique users
            if email not in users_data:
                users_data[email] = {
                    'trainee_id': row.get('trainee_id', '').strip(),
                    'password': row.get('password', '').strip(),
                    'full_name': row.get('full_name', '').strip(),
                    'gender': row.get('gender', '').strip(),
                    'age': row.get('age', ''),
                    'department': row.get('department', '').strip(),
                    'manager_name': row.get('manager_name', '').strip(),
                    'designation': row.get('designation', '').strip(),
                    'joining_date': row.get('joining_date', '').strip(),
                }

            # Collect telemetry data with all metrics
            date_str = row.get('date', '').strip()
            telemetry_data.append({
                'email': email,
                'date': date_str,
                'timestamp': datetime.strptime(date_str, '%d-%m-%Y') if date_str else None,
                'login_time': row.get('login_time', '').strip(),
                'logout_time': row.get('logout_time', '').strip(),
                'shift_name': row.get('shift_name', '').strip(),
                'work_duration_hours': float(row.get('work_duration_hours', 0)) if row.get('work_duration_hours') else 0,
                'break_count': int(row.get('break_count', 0)) if row.get('break_count') else 0,
                'break_duration_minutes': float(row.get('break_duration_minutes', 0)) if row.get('break_duration_minutes') else 0,
                'meeting_hours': float(row.get('meeting_hours', 0)) if row.get('meeting_hours') else 0,
                'focus_time_minutes': float(row.get('focus_time_minutes', 0)) if row.get('focus_time_minutes') else 0,
                'context_switches': int(row.get('context_switches', 0)) if row.get('context_switches') else 0,
                'tasks_completed': int(row.get('tasks_completed', 0)) if row.get('tasks_completed') else 0,
                'calls_count': int(row.get('calls_count', 0)) if row.get('calls_count') else 0,
                'emails_sent': int(row.get('emails_sent', 0)) if row.get('emails_sent') else 0,
                'stress_level': int(row.get('stress_level', 5)) if row.get('stress_level') else 5,
                'energy_level': int(row.get('energy_level', 5)) if row.get('energy_level') else 5,
                'sleep_hours': float(row.get('sleep_hours', 7)) if row.get('sleep_hours') else 7,
                'mood_score': int(row.get('mood_score', 7)) if row.get('mood_score') else 7,
                'productivity_score': int(row.get('productivity_score', 80)) if row.get('productivity_score') else 80,
                'work_life_balance_score': int(row.get('work_life_balance_score', 7)) if row.get('work_life_balance_score') else 7,
                'mental_health_score': int(row.get('mental_health_score', 7)) if row.get('mental_health_score') else 7,
                'burnout_risk': row.get('burnout_risk', 'Low').strip(),
                'physical_health': row.get('physical_health', 'Good').strip(),
                'sick_days': int(row.get('sick_days', 0)) if row.get('sick_days') else 0,
                'leave_used': int(row.get('leave_used', 0)) if row.get('leave_used') else 0,
                'leave_balance': int(row.get('leave_balance', 0)) if row.get('leave_balance') else 0,
                'current_project': row.get('current_project', '').strip(),
                'performance_rating': float(row.get('performance_rating', 3.5)) if row.get('performance_rating') else 3.5,
                'feedback_notes': row.get('feedback_notes', '').strip(),
                'attendance_percent': float(row.get('attendance_percent', 95)) if row.get('attendance_percent') else 95,
                'on_time_percent': float(row.get('on_time_percent', 95)) if row.get('on_time_percent') else 95,
                'current_status': row.get('current_status', 'Active').strip(),
                'follow_up_needed': row.get('follow_up_needed', 'No').strip() == 'Yes',
                'priority_level': row.get('priority_level', 'Low').strip(),
            })

    return users_data, telemetry_data

def create_or_update_users(users_data):
    """Create or update users in the database."""
    db = SessionLocal()
    try:
        # Get or create organization
        org = db.query(Organization).filter(Organization.name == "WorkWell Demo Org").first()
        if not org:
            print("Creating organization...")
            org = Organization(
                id=str(uuid.uuid4()),
                name="WorkWell Demo Org",
                email_domain="demo.workwell.ai"
            )
            db.add(org)
            db.commit()

        # Get employee role
        employee_role = db.query(Role).filter(Role.name == "employee").first()
        if not employee_role:
            print("Employee role not found!")
            return {}

        created_users = {}
        for email, data in users_data.items():
            # Check if user exists
            user = db.query(User).filter(User.email == email).first()

            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    full_name=data['full_name'],
                    hashed_password=hash_password(data['password']),
                    org_id=org.id,
                    role_id=employee_role.id,
                    is_active=True
                )
                db.add(user)
                print(f"✅ Created user: {email}")
            else:
                print(f"ℹ️  User already exists: {email}")

            created_users[email] = user

        db.commit()
        return created_users
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating users: {e}")
        return {}
    finally:
        db.close()

def load_telemetry_data(telemetry_data, users_data):
    """Load comprehensive telemetry data for users."""
    db = SessionLocal()
    try:
        # Re-query users from database
        users = {}
        for email in users_data.keys():
            user = db.query(User).filter(User.email == email).first()
            if user:
                users[email] = user

        count = 0
        for tel in telemetry_data:
            email = tel['email']
            user = users.get(email)

            if not user:
                continue

            try:
                # Create telemetry record with all metrics
                telemetry = TelemetryEvent(
                    id=str(uuid.uuid4()),
                    employee_id=user.id,
                    source='csv_import',
                    timestamp=tel['timestamp'],
                    features={
                        'work_duration_hours': tel['work_duration_hours'],
                        'break_count': tel['break_count'],
                        'break_duration_minutes': tel['break_duration_minutes'],
                        'meeting_hours': tel['meeting_hours'],
                        'focus_time_minutes': tel['focus_time_minutes'],
                        'context_switches': tel['context_switches'],
                        'tasks_completed': tel['tasks_completed'],
                        'calls_count': tel['calls_count'],
                        'emails_sent': tel['emails_sent'],
                        'stress_level': tel['stress_level'],
                        'energy_level': tel['energy_level'],
                        'sleep_hours': tel['sleep_hours'],
                        'mood_score': tel['mood_score'],
                        'productivity_score': tel['productivity_score'],
                        'work_life_balance_score': tel['work_life_balance_score'],
                        'mental_health_score': tel['mental_health_score'],
                        'burnout_risk': tel['burnout_risk'],
                        'physical_health': tel['physical_health'],
                        'sick_days': tel['sick_days'],
                        'leave_used': tel['leave_used'],
                        'leave_balance': tel['leave_balance'],
                        'current_project': tel['current_project'],
                        'performance_rating': tel['performance_rating'],
                        'attendance_percent': tel['attendance_percent'],
                        'on_time_percent': tel['on_time_percent'],
                        'current_status': tel['current_status'],
                        'priority_level': tel['priority_level'],
                        'login_time': tel['login_time'],
                        'logout_time': tel['logout_time'],
                        'shift_name': tel['shift_name'],
                        'date': tel['date'],
                    }
                )
                db.add(telemetry)
                count += 1

                if count % 50 == 0:
                    db.commit()
                    print(f"  Loaded {count} telemetry records...")
            except Exception as e:
                print(f"  Warning: Could not load telemetry for {email} on {tel['date']}: {e}")

        db.commit()
        print(f"✅ Loaded {count} telemetry records")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error loading telemetry: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_comprehensive_data.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Loading comprehensive data from: {csv_path}\n")

    # Load CSV
    users_data, telemetry_data = load_csv_data(csv_path)
    print(f"Found {len(users_data)} unique users and {len(telemetry_data)} telemetry records\n")

    # Create users
    print("Creating users...")
    users = create_or_update_users(users_data)

    if users:
        print(f"\nLoading telemetry data...")
        load_telemetry_data(telemetry_data, users_data)
        print("\n✅ Comprehensive data loading complete!")
        print(f"   {len(users)} users ready")
        print(f"   {len(telemetry_data)} data points loaded")
    else:
        print("\n❌ Failed to create users")
        sys.exit(1)
