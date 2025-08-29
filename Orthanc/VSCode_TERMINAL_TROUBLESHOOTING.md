If your integrated PowerShell terminal crashes with exit code -2147023895, follow these steps:

1) Switch to Command Prompt in VS Code (this workspace already sets Command Prompt as default):
   - Open View → Terminal. It should open cmd.exe instead of PowerShell.

2) Run the backend without Flask auto-reloader to avoid restart loops:
   - From the workspace root run:
     run_backend_no_reload.bat

3) If you need to use PowerShell, test it outside VS Code:
   - Open Windows PowerShell (Start → PowerShell) and run:
     py -V
     python -c "print('python ok')"

4) If PowerShell itself fails immediately, try restarting Windows Explorer / sign out, or use cmd.exe as an immediate workaround.

5) Long-term: avoid module-level circular imports. If the server fails on startup and the Flask reloader is enabled, the process can restart repeatedly and appear as terminal crashes. To debug, run without reloader and capture full stack traces.

If you want, I can:
- Add a dedicated VS Code task to run the backend using cmd.exe.
- Inspect recent changes that introduce circular imports and refactor.
