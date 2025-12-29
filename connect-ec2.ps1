# BintaCura EC2 SSH Connection Script
# Save this as: connect-ec2.ps1

$keyPath = "C:\Users\soyam\.ssh\bintacura_ec2"
$server = "ec2-user@16.171.180.104"

Write-Host "Connecting to BintaCura EC2 Server..." -ForegroundColor Cyan
Write-Host "Server: $server" -ForegroundColor White
Write-Host "Instance: i-074ee5b498fde1faa (bintacura-web-server-sg3)" -ForegroundColor White
Write-Host "Key: $keyPath" -ForegroundColor White
Write-Host ""

ssh -i "$keyPath" $server
