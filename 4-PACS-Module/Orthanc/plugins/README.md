# AI Triage Orthanc Plugin

This Python plugin integrates the AI Triage Engine with the Orthanc PACS server.

## Features
- Listens for `StableStudy` events (when a study is fully received).
- Automatically triggers the AI Triage pipeline.
- Updates study metadata with triage results (e.g., "Critical", "Normal").

## Installation
1.  Ensure Orthanc is installed with Python plugin support.
2.  Copy this folder to your Orthanc plugins directory or configure Orthanc to load `ai_triage_plugin.py`.
3.  Ensure `4-PACS-Module` is in the Python path.

## Configuration
Edit `ai_triage_config.json` to enable/disable triage or configure model paths.

## Dependencies
- `orthanc` (provided by Orthanc server)
- `ai_triage` package (Task B1, B2)
