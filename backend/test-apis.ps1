# 修复编码问题
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

param([switch]$LoadEnv = $true)

if ($LoadEnv) {
    Write-Host "=== Loading Environment Variables ===" -ForegroundColor Cyan
    Get-Content .env.development | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        if ($_ -match '^([^=]+)=(.*)$' -and $matches[2].Trim()) {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
    Write-Host "Environment loaded`n" -ForegroundColor Green
}

function Test-API {
    param(
        [string]$Name,
        [scriptblock]$TestScript
    )
    
    Write-Host "=== Testing $Name ===" -ForegroundColor Cyan
    try {
        & $TestScript
    } catch {
        Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# Claude API
Test-API "Claude API" {
    $response = Invoke-RestMethod -Uri "https://api.anthropic.com/v1/messages" `
        -Method POST `
        -Headers @{
            "x-api-key" = $env:ANTHROPIC_API_KEY
            "anthropic-version" = "2023-06-01"
            "content-type" = "application/json"
        } `
        -Body (@{
            model = $env:ANTHROPIC_MODEL
            max_tokens = 50
            messages = @(@{ role = "user"; content = "Say 'OK'" })
        } | ConvertTo-Json -Depth 10)
    
    Write-Host "SUCCESS: $($response.content[0].text)" -ForegroundColor Green
    Write-Host "Model: $($response.model), Tokens: $($response.usage.input_tokens)/$($response.usage.output_tokens)" -ForegroundColor Gray
}

# OpenAI API
Test-API "OpenAI API" {
    $response = Invoke-RestMethod -Uri "https://api.openai.com/v1/chat/completions" `
        -Method POST `
        -Headers @{
            "Authorization" = "Bearer $env:OPENAI_API_KEY"
            "Content-Type" = "application/json"
        } `
        -Body (@{
            model = $env:OPENAI_MODEL
            messages = @(@{ role = "user"; content = "Say 'OK'" })
            max_tokens = 50
        } | ConvertTo-Json -Depth 10)
    
    Write-Host "SUCCESS: $($response.choices[0].message.content)" -ForegroundColor Green
    Write-Host "Model: $($response.model), Tokens: $($response.usage.prompt_tokens)/$($response.usage.completion_tokens)" -ForegroundColor Gray
}

# DeepSeek API
Test-API "DeepSeek API" {
    $response = Invoke-RestMethod -Uri "$env:DEEPSEEK_BASE_URL/chat/completions" `
        -Method POST `
        -Headers @{
            "Authorization" = "Bearer $env:DEEPSEEK_API_KEY"
            "Content-Type" = "application/json"
        } `
        -Body (@{
            model = $env:DEEPSEEK_MODEL
            messages = @(@{ role = "user"; content = "Say 'OK'" })
            max_tokens = 50
        } | ConvertTo-Json -Depth 10)
    
    Write-Host "SUCCESS: $($response.choices[0].message.content)" -ForegroundColor Green
    Write-Host "Model: $($response.model), Tokens: $($response.usage.prompt_tokens)/$($response.usage.completion_tokens)" -ForegroundColor Gray
}

Write-Host "=== All Tests Complete ===" -ForegroundColor Cyan