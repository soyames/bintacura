import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections, transaction

def migrate_participants():
    """Migrate participants from Render to AWS first"""
    
    render_conn = connections['frankfurt']
    aws_conn = connections['default']
    
    print("\n" + "="*70)
    print("MIGRATING PARTICIPANTS FROM RENDER TO AWS")
    print("="*70 + "\n")
    
    # First, get all participants from Render
    with render_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM participants")
        render_count = cursor.fetchone()[0]
        print(f"Participants in Render: {render_count}")
    
    with aws_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM participants")
        aws_count = cursor.fetchone()[0]
        print(f"Participants in AWS (before): {aws_count}")
    
    if render_count == 0:
        print("\n⚠️  No participants in Render to migrate")
        return
    
    # Get column names from both databases
    with render_conn.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'participants' 
            ORDER BY ordinal_position
        """)
        render_cols = [row[0] for row in cursor.fetchall()]
    
    with aws_conn.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'participants' 
            ORDER BY ordinal_position
        """)
        aws_cols = [row[0] for row in cursor.fetchall()]
    
    # Find common columns
    common_cols = [col for col in render_cols if col in aws_cols]
    
    print(f"\nCommon columns: {len(common_cols)}")
    
    # Find uid column index
    try:
        uid_index = common_cols.index('uid')
    except ValueError:
        print("\n❌ 'uid' column not found!")
        return
    
    # Migrate participants using common columns
    try:
        with render_conn.cursor() as render_cursor:
            # Get all participants
            columns_str = ', '.join(f'"{col}"' for col in common_cols)
            render_cursor.execute(f"SELECT {columns_str} FROM participants")
            participants = render_cursor.fetchall()
            
            if not participants:
                print("\n⚠️  No participant records found")
                return
            
            # Insert into AWS, skipping duplicates (outside transaction for each insert)
            with aws_conn.cursor() as aws_cursor:
                migrated = 0
                skipped = 0
                
                for participant in participants:
                    # Extract uid from correct position
                    uid = participant[uid_index]
                    
                    # Check if already exists
                    aws_cursor.execute("SELECT COUNT(*) FROM participants WHERE uid = %s", [uid])
                    if aws_cursor.fetchone()[0] > 0:
                        skipped += 1
                        continue
                    
                    try:
                        placeholders = ', '.join(['%s'] * len(common_cols))
                        insert_sql = f"""
                            INSERT INTO participants ({columns_str})
                            VALUES ({placeholders})
                        """
                        aws_cursor.execute(insert_sql, participant)
                        migrated += 1
                    except Exception as e:
                        print(f"  [ERROR] Failed to migrate participant {uid}: {str(e)[:100]}")
                        skipped += 1
                
                print(f"\n✅ Migrated: {migrated} participants")
                print(f"⏭️  Skipped: {skipped} (already exist)")
        
        # Verify
        with aws_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM participants")
            new_aws_count = cursor.fetchone()[0]
            print(f"\nParticipants in AWS (after): {new_aws_count}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        raise

if __name__ == '__main__':
    migrate_participants()
