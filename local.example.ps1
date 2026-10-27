# 复制为 local.ps1，按本机环境填写；不要上传密码。
$env:DB_USER = 'root'
$env:DB_PASSWORD = '填写 MySQL 密码'
$env:NEWS_LOGIN_USER = '填写演示账号'
$env:NEWS_LOGIN_PASSWORD = '填写演示密码'
$env:NEWS_PYTHON = 'D:\ProgramData\conda\envs\news_popularity\python.exe'
$env:NEWS_ANALYSIS = "$PSScriptRoot\JavaWeb\python"
