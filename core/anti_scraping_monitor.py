from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


class AntiScrapingMonitor:
    @staticmethod
    def log_suspicious_activity(ip, user_agent, path, reason):
        cache_key = f"suspicious_log_{ip}"
        logs = cache.get(cache_key, [])

        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "ip": ip,
            "user_agent": user_agent,
            "path": path,
            "reason": reason,
        }

        logs.append(log_entry)
        cache.set(cache_key, logs, 86400)

        all_logs_key = "all_suspicious_activities"
        all_logs = cache.get(all_logs_key, [])
        all_logs.append(log_entry)
        cache.set(all_logs_key, all_logs[-1000:], 86400)

    @staticmethod
    def get_blocked_ips():
        blocked = []
        all_keys = cache.keys("ip_block_*")
        for key in all_keys:
            if cache.get(key):
                ip = key.replace("ip_block_", "")
                blocked.append(ip)
        return blocked

    @staticmethod
    def get_suspicious_activities(hours=24):
        all_logs_key = "all_suspicious_activities"
        logs = cache.get(all_logs_key, [])

        cutoff = timezone.now() - timedelta(hours=hours)
        recent_logs = [
            log
            for log in logs
            if timezone.datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

        return recent_logs

    @staticmethod
    def unblock_ip(ip):
        cache_key = f"ip_block_{ip}"
        cache.delete(cache_key)

        cache_key = f"bot_block_{ip}"
        cache.delete(cache_key)

        cache_key = f"rate_limit_{ip}"
        cache.delete(cache_key)

    @staticmethod
    def get_ip_statistics(ip):
        stats = {
            "ip": ip,
            "is_blocked": False,
            "block_reason": None,
            "suspicious_logs": [],
        }

        if cache.get(f"ip_block_{ip}"):
            stats["is_blocked"] = True
            stats["block_reason"] = "Trop de requêtes suspectes"
        elif cache.get(f"bot_block_{ip}"):
            stats["is_blocked"] = True
            stats["block_reason"] = "User-Agent de bot détecté"
        elif cache.get(f"rate_limit_{ip}"):
            stats["is_blocked"] = True
            stats["block_reason"] = "Limite de taux dépassée"

        logs_key = f"suspicious_log_{ip}"
        stats["suspicious_logs"] = cache.get(logs_key, [])

        return stats
