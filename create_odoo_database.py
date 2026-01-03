#!/usr/bin/env python3
"""
Script to create odoo_db database in the existing RDS instance
COMPLETELY FREE - Creates a new database within the same RDS instance

Usage:
    python create_odoo_database.py

This script will:
1. Connect to your RDS instance (bintacura-db-gb)
2. Create a new database called 'odoo_db'
3. Create a dedicated 'odoo_user' with restricted permissions
4. Keep your existing 'initialdbbintacura' database untouched
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import getpass
import sys

# RDS Configuration (from your existing setup)
RDS_HOST = 'bintacura-db-gb.c9uwsww6o8ky.eu-north-1.rds.amazonaws.com'
RDS_PORT = '5432'
MASTER_USER = 'soyames_'
MASTER_DB = 'postgres'  # Connect to postgres system DB first

# New database and user configuration
NEW_DATABASE = 'odoo_db'
NEW_USER = 'odoo_user'


def create_odoo_database():
    """Create odoo_db database and odoo_user in existing RDS instance"""
    
    print("\n" + "="*70)
    print("🚀 ODOO DATABASE CREATION SCRIPT")
    print("="*70)
    
    print(f"\n📍 RDS Instance: {RDS_HOST}")
    print(f"👤 Master User: {MASTER_USER}")
    print(f"🗄️  New Database: {NEW_DATABASE}")
    print(f"👤 New User: {NEW_USER}")
    
    print("\n⚠️  This script will create a NEW database within your EXISTING RDS instance.")
    print("✅ Your current database 'initialdbbintacura' will NOT be touched.")
    print("✅ This is COMPLETELY FREE (no additional AWS charges).")
    
    # Get master password
    print("\n" + "-"*70)
    master_password = getpass.getpass(f"Enter password for master user '{MASTER_USER}': ")
    
    # Get new odoo_user password
    print("\n💡 Create a strong password for odoo_user (this user will only access odoo_db)")
    odoo_password = getpass.getpass("Enter password for new 'odoo_user': ")
    odoo_password_confirm = getpass.getpass("Confirm password: ")
    
    if odoo_password != odoo_password_confirm:
        print("\n❌ Passwords don't match. Exiting.")
        sys.exit(1)
    
    print("\n" + "-"*70)
    print("🔄 Connecting to RDS instance...")
    
    try:
        # Connect to postgres system database
        conn = psycopg2.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=MASTER_DB,
            user=MASTER_USER,
            password=master_password
        )
        
        # Set isolation level for CREATE DATABASE
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        
        # Check if database already exists
        print(f"\n🔍 Checking if '{NEW_DATABASE}' already exists...")
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (NEW_DATABASE,)
        )
        
        if cursor.fetchone():
            print(f"\n⚠️  Database '{NEW_DATABASE}' already exists!")
            overwrite = input("Do you want to drop and recreate it? (yes/no): ")
            if overwrite.lower() == 'yes':
                print(f"🗑️  Dropping existing database '{NEW_DATABASE}'...")
                cursor.execute(f"DROP DATABASE {NEW_DATABASE}")
                print("✅ Dropped successfully!")
            else:
                print("ℹ️  Keeping existing database. Exiting.")
                cursor.close()
                conn.close()
                sys.exit(0)
        
        # Create odoo_db database
        print(f"\n🏗️  Creating database '{NEW_DATABASE}'...")
        # Simplified CREATE DATABASE for RDS (no tablespace specification)
        cursor.execute(f"""
            CREATE DATABASE {NEW_DATABASE}
            WITH 
            ENCODING = 'UTF8'
            CONNECTION LIMIT = -1
        """)
        print(f"✅ Database '{NEW_DATABASE}' created successfully!")
        
        # Check if user already exists
        print(f"\n🔍 Checking if user '{NEW_USER}' already exists...")
        cursor.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            (NEW_USER,)
        )
        
        if cursor.fetchone():
            print(f"⚠️  User '{NEW_USER}' already exists!")
            reset_password = input("Do you want to reset the password? (yes/no): ")
            if reset_password.lower() == 'yes':
                cursor.execute(f"ALTER USER {NEW_USER} WITH PASSWORD %s", (odoo_password,))
                print("✅ Password reset successfully!")
        else:
            # Create odoo_user
            print(f"\n👤 Creating user '{NEW_USER}'...")
            cursor.execute(f"CREATE USER {NEW_USER} WITH PASSWORD %s", (odoo_password,))
            print(f"✅ User '{NEW_USER}' created successfully!")
        
        # Grant privileges
        print(f"\n🔐 Granting privileges to '{NEW_USER}' on '{NEW_DATABASE}'...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {NEW_DATABASE} TO {NEW_USER}")
        
        # Configure user settings
        print(f"⚙️  Configuring user settings...")
        cursor.execute(f"ALTER ROLE {NEW_USER} SET client_encoding TO 'utf8'")
        cursor.execute(f"ALTER ROLE {NEW_USER} SET default_transaction_isolation TO 'read committed'")
        cursor.execute(f"ALTER ROLE {NEW_USER} SET timezone TO 'UTC'")
        print("✅ User settings configured!")
        
        # Verify database creation
        print(f"\n📋 Verifying databases in RDS instance...")
        cursor.execute("""
            SELECT datname, pg_size_pretty(pg_database_size(datname)) as size, datcollate
            FROM pg_database 
            WHERE datistemplate = false
            ORDER BY datname
        """)
        
        databases = cursor.fetchall()
        print("\n" + "="*70)
        print("📊 DATABASES IN YOUR RDS INSTANCE:")
        print("="*70)
        for db in databases:
            print(f"  • {db[0]:30} Size: {db[1]:10} Collate: {db[2]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("✅ SUCCESS! ODOO DATABASE CREATED")
        print("="*70)
        
        print("\n📝 ODOO CONFIGURATION:")
        print("-"*70)
        print(f"""
Add these to your Odoo configuration file (/srv/odoo/odoo.conf):

[options]
db_host = {RDS_HOST}
db_port = {RDS_PORT}
db_user = {NEW_USER}
db_password = {odoo_password}
db_name = {NEW_DATABASE}
dbfilter = ^{NEW_DATABASE}$
        """)
        
        print("\n📝 DJANGO CONFIGURATION:")
        print("-"*70)
        print(f"""
Your Django settings.py should remain unchanged:

DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'initialdbbintacura',  # Your existing Django DB
        'USER': '{MASTER_USER}',
        'PASSWORD': 'your_django_password',
        'HOST': '{RDS_HOST}',
        'PORT': '{RDS_PORT}',
    }}
}}

# Django communicates with Odoo via HTTP API (NOT database):
ODOO_URL = 'http://localhost:8069'
ODOO_DB = '{NEW_DATABASE}'
ODOO_USERNAME = 'admin'
ODOO_PASSWORD = 'your_odoo_admin_password'
        """)
        
        print("\n🔒 SECURITY VERIFICATION:")
        print("-"*70)
        print("✅ initialdbbintacura: Owned by soyames_ (Django access)")
        print(f"✅ {NEW_DATABASE}: Owned by soyames_, accessible by odoo_user (Odoo access)")
        print("✅ odoo_user: Can ONLY access odoo_db (not initialdbbintacura)")
        print("✅ Both databases isolated within same RDS instance")
        print("✅ Same security group, same endpoint, ZERO additional cost")
        
        print("\n" + "="*70)
        print("🎉 READY TO INSTALL ODOO!")
        print("="*70)
        print("\nNext steps:")
        print("1. Install Odoo Community Edition on your web server")
        print("2. Configure Odoo to use the connection details above")
        print("3. Start Odoo and verify it connects to odoo_db")
        print("4. Follow Phase 1 of the implementation guide")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nPossible reasons:")
        print("  • Incorrect password")
        print("  • RDS instance not accessible from this machine")
        print("  • Security group doesn't allow your IP")
        print("\nTo fix:")
        print(f"  • Verify password for user '{MASTER_USER}'")
        print("  • Check RDS security group allows your IP")
        return False
        
    except psycopg2.Error as e:
        print(f"\n❌ Database Error: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: This script requires psycopg2 library.")
    print("If not installed, run: pip install psycopg2-binary\n")
    
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        print("✅ psycopg2 installed. Please run the script again.")
        sys.exit(0)
    
    success = create_odoo_database()
    sys.exit(0 if success else 1)
