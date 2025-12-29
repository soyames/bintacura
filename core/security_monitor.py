from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict


class SecurityMonitor:
    @staticmethod
    def log_security_event(event_type, ip, details, severity="medium"):
        cache_key = f"security_event_{event_type}_{ip}_{timezone.now().timestamp()}"

        event_data = {
            "type": event_type,
            "ip": ip,
            "details": details,
            "severity": severity,
            "timestamp": timezone.now().isoformat(),
        }

        cache.set(cache_key, event_data, 86400)

        all_events_key = "all_security_events"
        events = cache.get(all_events_key, [])
        events.append(event_data)
        cache.set(all_events_key, events[-5000:], 86400)

        if severity == "critical":
            critical_key = "critical_security_events"
            critical_events = cache.get(critical_key, [])
            critical_events.append(event_data)
            cache.set(critical_key, critical_events[-500:], 86400)

    @staticmethod
    def get_security_events(hours=24, severity=None):
        all_events_key = "all_security_events"
        events = cache.get(all_events_key, [])

        cutoff = timezone.now() - timedelta(hours=hours)

        filtered_events = []
        for event in events:
            event_time = timezone.datetime.fromisoformat(event["timestamp"])
            if event_time > cutoff:
                if severity is None or event.get("severity") == severity:
                    filtered_events.append(event)

        return filtered_events

    @staticmethod
    def get_attack_statistics():
        events = SecurityMonitor.get_security_events(hours=24)

        stats = {
            "total_events": len(events),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_ip": defaultdict(int),
            "timeline": [],
        }

        for event in events:
            stats["by_type"][event["type"]] += 1
            stats["by_severity"][event.get("severity", "medium")] += 1
            stats["by_ip"][event["ip"]] += 1

        stats["by_type"] = dict(stats["by_type"])
        stats["by_severity"] = dict(stats["by_severity"])
        stats["by_ip"] = dict(
            sorted(stats["by_ip"].items(), key=lambda x: x[1], reverse=True)[:20]
        )

        return stats

    @staticmethod
    def get_blocked_ips_summary():
        blocked_ips = {
            "ddos": [],
            "brute_force": [],
            "sql_injection": [],
            "bot": [],
            "rate_limit": [],
        }

        all_keys = []
        try:
            all_keys = list(cache._cache.keys()) if hasattr(cache, "_cache") else []
        except Exception:
            pass

        for key in all_keys:
            if isinstance(key, str):
                if key.startswith("ddos_block_"):
                    ip = key.replace("ddos_block_", "")
                    if cache.get(key):
                        blocked_ips["ddos"].append(ip)
                elif key.startswith("login_block_"):
                    ip = key.replace("login_block_", "")
                    if cache.get(key):
                        blocked_ips["brute_force"].append(ip)
                elif key.startswith("ip_block_"):
                    ip = key.replace("ip_block_", "")
                    if cache.get(key):
                        blocked_ips["sql_injection"].append(ip)
                elif key.startswith("bot_block_"):
                    ip = key.replace("bot_block_", "")
                    if cache.get(key):
                        blocked_ips["bot"].append(ip)
                elif key.startswith("rate_limit_"):
                    ip = key.replace("rate_limit_", "")
                    if cache.get(key):
                        blocked_ips["rate_limit"].append(ip)

        return blocked_ips

    @staticmethod
    def unblock_all_for_ip(ip):
        keys_to_delete = [
            f"ddos_block_{ip}",
            f"login_block_{ip}",
            f"ip_block_{ip}",
            f"bot_block_{ip}",
            f"rate_limit_{ip}",
            f"sql_injection_attempt_{ip}",
        ]

        for key in keys_to_delete:
            cache.delete(key)

        return True

    @staticmethod
    def get_security_health():
        events_24h = SecurityMonitor.get_security_events(hours=24)
        critical_events = [e for e in events_24h if e.get("severity") == "critical"]
        high_events = [e for e in events_24h if e.get("severity") == "high"]

        blocked_ips = SecurityMonitor.get_blocked_ips_summary()
        total_blocked = sum(len(ips) for ips in blocked_ips.values())

        health_score = 100

        if len(critical_events) > 0:
            health_score -= min(50, len(critical_events) * 10)

        if len(high_events) > 5:
            health_score -= min(30, (len(high_events) - 5) * 5)

        if total_blocked > 20:
            health_score -= min(20, (total_blocked - 20) * 2)

        health_score = max(0, health_score)

        status = "excellent"
        if health_score < 50:
            status = "critical"
        elif health_score < 70:
            status = "warning"
        elif health_score < 90:
            status = "good"

        return {
            "score": health_score,
            "status": status,
            "critical_events": len(critical_events),
            "high_events": len(high_events),
            "total_blocked_ips": total_blocked,
            "total_events_24h": len(events_24h),
        }
