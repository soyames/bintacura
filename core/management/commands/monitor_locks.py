"""
Management command to monitor PostgreSQL locks and detect contention.

Usage:
    python manage.py monitor_locks
    python manage.py monitor_locks --watch
"""
from django.core.management.base import BaseCommand
from django.db import connection
import time


class Command(BaseCommand):
    help = 'Monitor PostgreSQL locks and detect lock contention'

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Continuously watch for locks (refresh every 5 seconds)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Refresh interval in seconds for watch mode (default: 5)',
        )

    def handle(self, *args, **options):
        watch_mode = options['watch']
        interval = options['interval']
        
        if watch_mode:
            self.stdout.write(
                self.style.WARNING(
                    f'👀 Watching for locks (refreshing every {interval}s, Ctrl+C to stop)...\n'
                )
            )
            try:
                while True:
                    self._check_locks()
                    time.sleep(interval)
                    self.stdout.write('\n' + '='*70 + '\n')
            except KeyboardInterrupt:
                self.stdout.write('\n\n✋ Monitoring stopped.')
        else:
            self._check_locks()
    
    def _check_locks(self):
        """Query PostgreSQL for current locks"""
        
        # Query for blocking locks
        blocking_query = """
        SELECT
            blocked_locks.pid AS blocked_pid,
            blocked_activity.usename AS blocked_user,
            blocking_locks.pid AS blocking_pid,
            blocking_activity.usename AS blocking_user,
            blocked_activity.query AS blocked_statement,
            blocking_activity.query AS blocking_statement,
            blocked_activity.application_name AS blocked_app,
            blocking_activity.application_name AS blocking_app,
            blocked_locks.locktype AS lock_type,
            blocked_locks.mode AS lock_mode,
            blocked_locks.relation::regclass AS locked_table,
            NOW() - blocked_activity.query_start AS blocked_duration
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity 
            ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_locks blocking_locks 
            ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
            AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
            AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
            AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
            AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
            AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
            AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
            AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
            AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity 
            ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.granted
        ORDER BY blocked_duration DESC;
        """
        
        # Query for all current locks
        all_locks_query = """
        SELECT
            l.locktype,
            l.database,
            l.relation::regclass AS table_name,
            l.page,
            l.tuple,
            l.mode,
            l.granted,
            a.usename,
            a.application_name,
            a.client_addr,
            a.query_start,
            NOW() - a.query_start AS duration,
            a.state,
            a.query
        FROM pg_catalog.pg_locks l
        LEFT JOIN pg_catalog.pg_stat_activity a ON l.pid = a.pid
        WHERE l.relation IS NOT NULL
        ORDER BY duration DESC
        LIMIT 20;
        """
        
        with connection.cursor() as cursor:
            # Check for blocking locks
            cursor.execute(blocking_query)
            blocking_locks = cursor.fetchall()
            
            if blocking_locks:
                self.stdout.write(
                    self.style.ERROR(
                        f'\n🔴 BLOCKING LOCKS DETECTED ({len(blocking_locks)})\n'
                    )
                )
                for lock in blocking_locks:
                    self.stdout.write(
                        self.style.ERROR(
                            f'\n  Blocked PID: {lock[0]} (by PID: {lock[2]})\n'
                            f'  Table: {lock[10]}\n'
                            f'  Lock Type: {lock[8]} ({lock[9]})\n'
                            f'  Blocked Duration: {lock[11]}\n'
                            f'  Blocked Query: {lock[4][:100]}...\n'
                            f'  Blocking Query: {lock[5][:100]}...\n'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ No blocking locks detected\n')
                )
            
            # Show current locks
            cursor.execute(all_locks_query)
            all_locks = cursor.fetchall()
            
            if all_locks:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n📊 Current Locks ({len(all_locks)} shown):\n'
                    )
                )
                
                granted_locks = [l for l in all_locks if l[6]]  # granted = True
                waiting_locks = [l for l in all_locks if not l[6]]  # granted = False
                
                self.stdout.write(
                    f'  Granted: {len(granted_locks)}\n'
                    f'  Waiting: {len(waiting_locks)}\n'
                )
                
                if waiting_locks:
                    self.stdout.write(
                        self.style.WARNING('\n  ⏳ Waiting Locks:\n')
                    )
                    for lock in waiting_locks[:5]:  # Show top 5
                        self.stdout.write(
                            f'    • {lock[2]} ({lock[5]}) - {lock[11]} - {lock[7]}\n'
                        )
                
                # Show locks by table
                table_locks = {}
                for lock in granted_locks:
                    table = str(lock[2]) if lock[2] else 'Unknown'
                    if table not in table_locks:
                        table_locks[table] = 0
                    table_locks[table] += 1
                
                if table_locks:
                    self.stdout.write('\n  📋 Locks by Table:')
                    for table, count in sorted(table_locks.items(), 
                                              key=lambda x: x[1], 
                                              reverse=True)[:10]:
                        self.stdout.write(f'    • {table}: {count} locks')
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ No significant locks present\n')
                )
            
            # Check for long-running queries
            long_queries_query = """
            SELECT
                pid,
                usename,
                application_name,
                client_addr,
                NOW() - query_start AS duration,
                state,
                wait_event_type,
                wait_event,
                LEFT(query, 100) AS query
            FROM pg_stat_activity
            WHERE state != 'idle'
                AND query NOT LIKE '%pg_stat_activity%'
                AND NOW() - query_start > interval '10 seconds'
            ORDER BY duration DESC
            LIMIT 10;
            """
            
            cursor.execute(long_queries_query)
            long_queries = cursor.fetchall()
            
            if long_queries:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⏱️  Long-Running Queries ({len(long_queries)}):\n'
                    )
                )
                for query in long_queries:
                    self.stdout.write(
                        f'  • PID {query[0]}: {query[4]} - {query[5]}\n'
                        f'    {query[8]}...\n'
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ No long-running queries\n')
                )
