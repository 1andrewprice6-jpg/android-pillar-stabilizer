@rem Gradle startup script for Windows
@if "%GRADLE_HOME%" == "" (
    gradle %*
) else (
    "%GRADLE_HOME%\bin\gradle.bat" %*
)
