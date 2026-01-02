import re

with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add decorators to SecurityMonitorViewSet actions
replacements = [
    (r'(\s+)@action\(detail=False, methods=\["get"\]\)\s+def attack_statistics\(self, request\):',
     r'\1@extend_schema(summary="Get attack statistics", responses={200: OpenApiResponse(description="Attack statistics")})\n\1@action(detail=False, methods=["get"])\n\1def attack_statistics(self, request):'),
    
    (r'(\s+)@action\(detail=False, methods=\["get"\]\)\s+def blocked_ips_summary\(self, request\):',
     r'\1@extend_schema(summary="Get blocked IPs summary", responses={200: OpenApiResponse(description="Blocked IPs summary")})\n\1@action(detail=False, methods=["get"])\n\1def blocked_ips_summary(self, request):'),
    
    (r'(\s+)@action\(detail=False, methods=\["post"\]\)\s+def unblock_ip_all\(self, request\):',
     r'\1@extend_schema(summary="Unblock all IPs", responses={200: OpenApiResponse(description="All IPs unblocked")})\n\1@action(detail=False, methods=["post"])\n\1def unblock_ip_all(self, request):'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✓ Added decorators to SecurityMonitorViewSet actions')
