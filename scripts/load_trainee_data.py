#!/usr/bin/env python3
"""Load trainee wellness data from CSV into the system."""

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
        reader = csv.DictReader(f)
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

            # Collect telemetry data
            telemetry_data.append({
                'email': email,
                'date': row.get('date', '').strip(),
                'login_time': row.get('login_time', '').strip(),
                'logout_time': row.get('logout_time', '').strip(),
                'work_duration_hours': float(row.get('work_duration_hours', 0)) if row.get('work_duration_hours') else 0,
                'break_duration_minutes': float(row.get('break_duration_minutes', 0)) if row.get('break_duration_minutes') else 0,
                'meeting_hours': float(row.get('meeting_hours', 0)) if row.get('meeting_hours') else 0,
                'focus_time_minutes': float(row.get('focus_time_minutes', 0)) if row.get('focus_time_minutes') else 0,
                'context_switches': int(row.get('context_switches', 0)) if row.get('context_switches') else 0,
                'stress_level': int(row.get('stress_level', 5)) if row.get('stress_level') else 5,
                'energy_level': int(row.get('energy_level', 5)) if row.get('energy_level') else 5,
                'sleep_hours': float(row.get('sleep_hours', 7)) if row.get('sleep_hours') else 7,
                'mood_score': int(row.get('mood_score', 7)) if row.get('mood_score') else 7,
                'productivity_score': int(row.get('productivity_score', 80)) if row.get('productivity_score') else 80,
                'work_life_balance_score': int(row.get('work_life_balance_score', 7)) if row.get('work_life_balance_score') else 7,
                'mental_health_score': int(row.get('mental_health_score', 7)) if row.get('mental_health_score') else 7,
                'burnout_risk': row.get('burnout_risk', 'Low').strip(),
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
            return False

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
                    organization_id=org.id,
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

def load_telemetry_data(telemetry_data, users):
    """Load telemetry data for users."""
    db = SessionLocal()
    try:
        count = 0
        for tel in telemetry_data:
            email = tel['email']
            user = users.get(email)

            if not user:
                continue

            try:
                # Parse date
                date = datetime.strptime(tel['date'], '%Y-%m-%d').date() if tel['date'] else None

                # Create telemetry record
                telemetry = TelemetryEvent(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    source='csv_import',
                    collected_at=datetime.combine(date, datetime.min.time()) if date else datetime.now(),
                    data={
                        'work_duration_hours': tel['work_duration_hours'],
                        'break_duration_minutes': tel['break_duration_minutes'],
                        'meeting_hours': tel['meeting_hours'],
                        'focus_time_minutes': tel['focus_time_minutes'],
                        'context_switches': tel['context_switches'],
                        'stress_level': tel['stress_level'],
                        'energy_level': tel['energy_level'],
                        'sleep_hours': tel['sleep_hours'],
                        'mood_score': tel['mood_score'],
                        'productivity_score': tel['productivity_score'],
                        'work_life_balance_score': tel['work_life_balance_score'],
                        'mental_health_score': tel['mental_health_score'],
                        'burnout_risk': tel['burnout_risk'],
                        'date': tel['date'],
                    }
                )
                db.add(telemetry)
                count += 1

                if count % 100 == 0:
                    db.commit()
                    print(f"  Loaded {count} telemetry records...")
            except Exception as e:
                print(f"  Warning: Could not load telemetry for {email}: {e}")

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
        print("Usage: python load_trainee_data.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Loading data from: {csv_path}")

    # Load CSV
    users_data, telemetry_data = load_csv_data(csv_path)
    print(f"Found {len(users_data)} unique users and {len(telemetry_data)} telemetry records\n")

    # Create users
    print("Creating users...")
    users = create_or_update_users(users_data)

    if users:
        print(f"\nLoading telemetry data...")
        load_telemetry_data(telemetry_data, users)
        print("\n✅ Data loading complete!")
    else:
        print("\n❌ Failed to create users")
        sys.exit(1)
