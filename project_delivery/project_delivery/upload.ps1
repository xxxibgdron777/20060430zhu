# SSH Upload Script
# 使用方法: 右键点击此文件 -> 使用 PowerShell 运行

$sourcePath = "e:\项目\project_delivery"
$destServer = "root@122.51.134.23"
$destPath = "/root/"
$port = 22

Write-Host "开始上传项目到 $destServer ..."

# 使用 PowerShell 的 Start-Process 来执行 scp
# 这会打开一个命令窗口提示输入密码
$process = Start-Process -FilePath "scp.exe" -ArgumentList "-P $port -r `"$sourcePath`" $destServer``:$destPath" -NoNewWindow -Wait -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "上传成功!" -ForegroundColor Green
} else {
    Write-Host "上传失败，退出码: $($process.ExitCode)" -ForegroundColor Red
}

Read-Host "按 Enter 键退出"
