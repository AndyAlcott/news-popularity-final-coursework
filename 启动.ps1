$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$config = Join-Path $root 'local.ps1'
if (!(Test-Path $config)) { throw '请先复制 local.example.ps1 为 local.ps1 并填写本机设置。' }
. $config
docker start mysql | Out-Null
$redis = docker ps -a --filter "name=^news-final-redis$" --format '{{.Names}}'
if ($redis) { docker start news-final-redis | Out-Null } else { docker compose -f "$root\JavaWeb\compose.yml" up -d }
Set-Location "$root\JavaWeb"
if (!(Test-Path 'target\news-popularity-1.0.0.jar')) { mvn.cmd -q -DskipTests package; if ($LASTEXITCODE -ne 0) { throw 'Maven 构建失败' } }
New-Item -ItemType Directory -Force "$root\.runtime-temp" | Out-Null
java "-Djdk.net.unixdomain.tmpdir=$root\.runtime-temp" -jar 'target\news-popularity-1.0.0.jar'
