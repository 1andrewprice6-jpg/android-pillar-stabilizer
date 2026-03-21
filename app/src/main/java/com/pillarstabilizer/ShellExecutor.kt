package com.pillarstabilizer

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class ShellExecutor {
    private val _commandLog = MutableStateFlow<List<CommandLogEntry>>(emptyList())
    val commandLog: StateFlow<List<CommandLogEntry>> = _commandLog.asStateFlow()

    suspend fun execute(command: String): ShellResult {
        addLog("Executing: $command", LogLevel.INFO)

        val result = ShizukuService.executeCommand(command)

        if (result.isSuccess) {
            val preview = result.output.take(100)
            addLog("Success${if (preview.isNotEmpty()) ": $preview" else ""}", LogLevel.SUCCESS)
        } else {
            addLog("Error: ${result.error}", LogLevel.ERROR)
        }

        return result
    }

    suspend fun getSystemProperty(key: String): String? {
        val result = execute("getprop $key")
        return if (result.isSuccess) result.output.trim() else null
    }

    suspend fun setSystemSetting(namespace: String, key: String, value: String): Boolean {
        val result = execute("settings put $namespace $key $value")
        return result.isSuccess
    }

    suspend fun getSystemSetting(namespace: String, key: String): String? {
        val result = execute("settings get $namespace $key")
        return if (result.isSuccess) result.output.trim() else null
    }

    /**
     * Read all thermal zones in a single pass to avoid N+1 queries.
     */
    suspend fun getThermalData(): ThermalData {
        val zones = mutableListOf<ThermalZone>()

        // Find all thermal zone directories
        val listResult = execute("find /sys/class/thermal -maxdepth 1 -type d -name 'thermal_zone*' 2>/dev/null")
        if (!listResult.isSuccess) {
            return ThermalData(zones)
        }

        val thermalDirs = listResult.output.split("\n").filter { it.isNotBlank() }

        // Batch read all types and temps in one go
        for (dir in thermalDirs) {
            val typeFile = "$dir/type"
            val tempFile = "$dir/temp"

            val typeResult = execute("cat $typeFile 2>/dev/null")
            val tempResult = execute("cat $tempFile 2>/dev/null")

            if (typeResult.isSuccess && tempResult.isSuccess) {
                val temp = tempResult.output.trim().toLongOrNull()
                if (temp != null) {
                    zones.add(
                        ThermalZone(
                            name = typeResult.output.trim(),
                            temperature = temp / 1000.0 // Convert millidegrees to degrees
                        )
                    )
                }
            }
        }

        return ThermalData(zones)
    }

    /**
     * Read battery info with fallback paths for different devices.
     */
    suspend fun getBatteryInfo(): BatteryInfo {
        // Try primary path first
        var current = readBatteryValue("/sys/class/power_supply/battery/current_now")
        var voltage = readBatteryValue("/sys/class/power_supply/battery/voltage_now")
        var temp = readBatteryValue("/sys/class/power_supply/battery/temp")

        // Fallback to alternative paths if primary fails
        if (current == null || current == 0L) {
            current = readBatteryValue("/sys/class/power_supply/bms/current_now")
        }
        if (voltage == null || voltage == 0L) {
            voltage = readBatteryValue("/sys/class/power_supply/bms/voltage_now")
        }
        if (temp == null || temp == 0L) {
            temp = readBatteryValue("/sys/class/power_supply/bms/temp")
        }

        return BatteryInfo(
            currentMicroamps = current ?: 0L,
            voltageMicrovolts = voltage ?: 0L,
            temperatureDeciCelsius = temp?.toInt() ?: 0
        )
    }

    /**
     * Helper to safely read battery values with error handling.
     */
    private suspend fun readBatteryValue(path: String): Long? {
        val result = execute("cat $path 2>/dev/null")
        return if (result.isSuccess && result.output.isNotBlank()) {
            result.output.trim().toLongOrNull()
        } else {
            null
        }
    }

    suspend fun grantPermission(packageName: String, permission: String): Boolean {
        val result = execute("pm grant $packageName $permission")
        return result.isSuccess
    }

    suspend fun revokePermission(packageName: String, permission: String): Boolean {
        val result = execute("pm revoke $packageName $permission")
        return result.isSuccess
    }

    private fun addLog(message: String, level: LogLevel) {
        val entry = CommandLogEntry(
            message = message,
            level = level,
            timestamp = System.currentTimeMillis()
        )
        _commandLog.value = (_commandLog.value + entry).takeLast(100)
    }
}

data class CommandLogEntry(
    val message: String,
    val level: LogLevel,
    val timestamp: Long
)

enum class LogLevel {
    INFO, SUCCESS, ERROR, WARNING
}

data class ThermalData(
    val zones: List<ThermalZone>
)

data class ThermalZone(
    val name: String,
    val temperature: Double
)

data class BatteryInfo(
    val currentMicroamps: Long,
    val voltageMicrovolts: Long,
    val temperatureDeciCelsius: Int
) {
    val currentMilliamps: Double get() = currentMicroamps / 1000.0
    val voltageVolts: Double get() = voltageMicrovolts / 1_000_000.0
    val temperatureCelsius: Double get() = temperatureDeciCelsius / 10.0
    val powerWatts: Double get() = (currentMilliamps / 1000.0) * voltageVolts
}
