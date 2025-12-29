# BintaCura EC2 SSH Connection Script
# Save this as: connect-ec2.ps1

$keyPath = "C:\Users\soyam\.ssh\bintacura_ec2"
$server = "ec2-user@13.53.170.59"

Write-Host "Connecting to BintaCura EC2 Server..." -ForegroundColor Cyan
Write-Host "Server: $server" -ForegroundColor White
Write-Host "Instance: i-0b89178e5348db0a4" -ForegroundColor White
Write-Host "Key: $keyPath" -ForegroundColor White
Write-Host ""

ssh -i "$keyPath" $server
