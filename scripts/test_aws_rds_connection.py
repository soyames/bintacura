#!/usr/bin/env python
"""
AWS RDS Connection Test Script for BintaCura
=============================================
This script tests connectivity to your AWS RDS PostgreSQL database
and verifies that all configuration is correct.

Usage:
    python scripts/test_aws_rds_connection.py

Requirements:
    - psycopg2-binary
    - python-decouple
    - .env file configured with AWS RDS credentials
"""

import os
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from decouple import config
    import psycopg2
    from psycopg2 import OperationalError
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip install psycopg2-binary python-decouple")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def load_db_config():
    """Load database configuration from .env"""
    print_info("Loading database configuration from .env file...")
    
    try:
        db_config = {
            'dbname': config('DB_NAME'),
            'user': config('DB_USER'),
            'password': config('DB_PASSWORD'),
            'host': config('DB_HOST'),
            'port': config('DB_PORT', default='5432'),
            'sslmode': 'require',
        }
        
        print_success("Configuration loaded successfully")
        return db_config
        
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        print_warning("Make sure .env file exists and contains all required variables:")
        print("  - DB_NAME")
        print("  - DB_USER")
        print("  - DB_PASSWORD")
        print("  - DB_HOST")
        print("  - DB_PORT (optional, defaults to 5432)")
        return None


def display_config(db_config):
    """Display database configuration (hide password)"""
    print("\n" + "─" * 70)
    print(f"{Colors.BOLD}Database Configuration:{Colors.END}")
    print("─" * 70)
    print(f"  Host:     {db_config['host']}")
    print(f"  Port:     {db_config['port']}")
    print(f"  Database: {db_config['dbname']}")
    print(f"  User:     {db_config['user']}")
    print(f"  Password: {'*' * len(db_config['password'])}")
    print(f"  SSL Mode: {db_config['sslmode']}")
    print("─" * 70 + "\n")


def test_connection(db_config):
    """Test database connection"""
    print_info("Testing connection to AWS RDS PostgreSQL...")
    
    try:
        # Attempt connection
        conn = psycopg2.connect(**db_config)
        print_success("Connection established successfully!")
        
        # Create cursor
        cur = conn.cursor()
        
        # Test query - Get PostgreSQL version
        print_info("Fetching database version...")
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print_success(f"PostgreSQL Version: {version.split(',')[0]}")
        
        # Get database size
        print_info("Fetching database size...")
        cur.execute(f"""
            SELECT pg_size_pretty(pg_database_size('{db_config['dbname']}'));
        """)
        db_size = cur.fetchone()[0]
        print_success(f"Database Size: {db_size}")
        
        # List tables
        print_info("Listing tables...")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        if tables:
            print_success(f"Found {len(tables)} tables:")
            for table in tables[:10]:  # Show first 10 tables
                print(f"    - {table[0]}")
            if len(tables) > 10:
                print(f"    ... and {len(tables) - 10} more")
        else:
            print_warning("No tables found. Run migrations: python manage.py migrate")
        
        # Check connection info
        print_info("Checking connection details...")
        cur.execute("""
            SELECT 
                inet_server_addr() as server_ip,
                inet_server_port() as server_port,
                current_database() as database,
                current_user as user,
                version() as version
        """)
        conn_info = cur.fetchone()
        print_success("Connection Details:")
        print(f"    Server IP:   {conn_info[0]}")
        print(f"    Server Port: {conn_info[1]}")
        print(f"    Database:    {conn_info[2]}")
        print(f"    User:        {conn_info[3]}")
        
        # Close connection
        cur.close()
        conn.close()
        print_success("Connection closed gracefully")
        
        return True
        
    except OperationalError as e:
        print_error(f"Connection failed: {e}")
        print("\n" + "─" * 70)
        print(f"{Colors.BOLD}Troubleshooting Tips:{Colors.END}")
        print("─" * 70)
        print("1. Verify AWS RDS instance is running:")
        print("   aws rds describe-db-instances --db-instance-identifier bintacura-db-gb")
        print("\n2. Check security group allows your IP:")
        print("   aws ec2 describe-security-groups --group-ids sg-039fd372435eae5ce")
        print("\n3. Verify credentials are correct in .env file")
        print("\n4. Ensure database exists:")
        print("   psql -h <host> -U <user> -d postgres -c '\\l'")
        print("─" * 70 + "\n")
        return False
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_django_connection():
    """Test Django database connection"""
    print_info("Testing Django database configuration...")
    
    try:
        # Set Django settings module
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
        
        # Import Django
        import django
        django.setup()
        
        from django.db import connection
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print_success("Django database connection successful!")
            
        return True
        
    except Exception as e:
        print_error(f"Django connection failed: {e}")
        return False


def main():
    """Main test function"""
    print_header("AWS RDS Connection Test - BintaCura")
    
    # Load configuration
    db_config = load_db_config()
    if not db_config:
        sys.exit(1)
    
    # Display configuration
    display_config(db_config)
    
    # Test connection
    print_header("Testing Connection")
    success = test_connection(db_config)
    
    if success:
        print_header("Testing Django Integration")
        django_success = test_django_connection()
        
        if django_success:
            print_header("All Tests Passed! ✅")
            print_success("Your AWS RDS database is ready to use!")
            print_info("Next steps:")
            print("  1. Run migrations: python manage.py migrate")
            print("  2. Create superuser: python manage.py createsuperuser")
            print("  3. Run server: python manage.py runserver 8080")
        else:
            print_header("Connection Test Passed, Django Test Failed")
            print_warning("Database connection works, but Django configuration may need adjustment")
    else:
        print_header("Connection Test Failed ❌")
        print_error("Unable to connect to AWS RDS database")
        sys.exit(1)


if __name__ == '__main__':
    main()
