# BintaCura EC2 SSH Connection Script
# Save this as: connect-ec2.ps1

$keyPath = "C:\Users\soyam\Downloads\bintacura-web-server-key.pem"
$server = "ec2-user@13.53.194.95"

Write-Host "Connecting to BintaCura EC2 Server..." -ForegroundColor Cyan
Write-Host "Server: $server" -ForegroundColor White
Write-Host "Key: $keyPath" -ForegroundColor White

ssh -i "$keyPath" $server
