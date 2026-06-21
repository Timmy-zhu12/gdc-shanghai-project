@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
python src\clinical_rule_engine.py --input-json examples\sample_patient_clinical.json --out outputs\sample_patient_clinical_result.json
if errorlevel 1 exit /b 1
python src\clinical_rule_engine.py --input-json examples\sample_patient_proxy_only.json --out outputs\sample_patient_proxy_only_result.json
if errorlevel 1 exit /b 1
echo Clinical rulebook smoke test finished.
