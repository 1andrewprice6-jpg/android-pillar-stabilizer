package com.pillarstabilizer

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.pillarstabilizer.analysis.SpectralAnalyzer
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.math.sqrt

class HardwareResonanceReader : Service(), SensorEventListener {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private lateinit var sensorManager: SensorManager
    private lateinit var notificationManager: NotificationManager

    private var magnetometer: Sensor? = null
    private val shellExecutor = ShellExecutor()

    private val _resonanceData = MutableStateFlow(ResonanceData())
    val resonanceData: StateFlow<ResonanceData> = _resonanceData.asStateFlow()

    // Buffer for FFT analysis
    private val magneticSamples = mutableListOf<Double>()
    private var lastSensorUpdate = 0L
    private var sampleCount = 0L

    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "pillar_stabilizer_channel"
        private const val SENSOR_UPDATE_THROTTLE_MS = 50L // Max 20Hz UI updates from 200Hz sensor

        private val _instance = MutableStateFlow<HardwareResonanceReader?>(null)
        val instance: StateFlow<HardwareResonanceReader?> = _instance.asStateFlow()
    }

    override fun onCreate() {
        super.onCreate()
        _instance.value = this

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        magnetometer = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification("Initializing..."))

        startMonitoring()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startMonitoring() {
        // Register magnetometer with highest sampling rate
        magnetometer?.let {
            sensorManager.registerListener(
                this,
                it,
                SensorManager.SENSOR_DELAY_FASTEST // ~200Hz on most devices
            )
        } ?: run {
            addLog("Magnetometer sensor not available", LogLevel.WARNING)
        }

        // Start periodic battery and thermal monitoring
        serviceScope.launch {
            while (true) {
                try {
                    updateSystemMetrics()
                    kotlinx.coroutines.delay(1000) // Update every second
                } catch (e: Exception) {
                    addLog("Metrics update failed: ${e.message}", LogLevel.ERROR)
                }
            }
        }
    }

    private suspend fun updateSystemMetrics() {
        val battery = shellExecutor.getBatteryInfo()
        val thermal = shellExecutor.getThermalData()

        // Perform FFT on buffered samples if we have enough data
        val frequencies = if (magneticSamples.size >= 256) {
            val samplesArray = magneticSamples.take(256).toDoubleArray()
            val spikes = SpectralAnalyzer.analyzeFrequencies(samplesArray, 200.0) // ~200Hz sampling rate
            magneticSamples.clear()
            spikes
        } else {
            emptyList()
        }

        val currentData = _resonanceData.value
        _resonanceData.value = currentData.copy(
            batteryInfo = battery,
            thermalData = thermal,
            frequencySpikes = frequencies.take(5), // Keep top 5 spikes
            lastUpdate = System.currentTimeMillis()
        )

        // Update notification with current metrics
        updateNotification(battery, thermal)
    }

    override fun onSensorChanged(event: SensorEvent?) {
        event?.let {
            if (it.sensor.type == Sensor.TYPE_MAGNETIC_FIELD) {
                val now = System.currentTimeMillis()

                // Throttle updates to prevent main thread jank
                if (now - lastSensorUpdate < SENSOR_UPDATE_THROTTLE_MS) {
                    return
                }
                lastSensorUpdate = now

                val x = it.values[0]
                val y = it.values[1]
                val z = it.values[2]

                val magnitude = sqrt(x * x + y * y + z * z)

                // Collect samples for FFT
                magneticSamples.add(magnitude.toDouble())
                if (magneticSamples.size > 512) { // Keep reasonable buffer
                    magneticSamples.removeAt(0)
                }

                sampleCount++

                _resonanceData.value = _resonanceData.value.copy(
                    magneticField = MagneticFieldData(x, y, z, magnitude),
                    sampleCount = sampleCount
                )
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not needed for this implementation
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Pillar Stabilizer Service",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Monitoring electromagnetic resonance and system metrics"
            enableVibration(false)
            enableLights(false)
        }

        notificationManager.createNotificationChannel(channel)
    }

    private fun createNotification(text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Pillar Stabilizer")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(battery: BatteryInfo, thermal: ThermalData) {
        val topThermal = thermal.zones.maxByOrNull { it.temperature }
        val text = "Battery: ${battery.voltageVolts}V, ${battery.currentMilliamps.toInt()}mA" +
                if (topThermal != null) {
                    ", Temp: ${topThermal.temperature.toInt()}°C"
                } else {
                    ""
                }

        val notification = createNotification(text)
        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    private fun addLog(message: String, level: LogLevel) {
        val entry = CommandLogEntry(
            message = message,
            level = level,
            timestamp = System.currentTimeMillis()
        )
        // Simple in-memory log
    }

    override fun onDestroy() {
        super.onDestroy()
        sensorManager.unregisterListener(this)
        serviceScope.cancel()
        _instance.value = null
    }
}

data class ResonanceData(
    val magneticField: MagneticFieldData = MagneticFieldData(0f, 0f, 0f, 0f),
    val batteryInfo: BatteryInfo = BatteryInfo(0, 0, 0),
    val thermalData: ThermalData = ThermalData(emptyList()),
    val frequencySpikes: List<com.pillarstabilizer.analysis.FrequencySpike> = emptyList(),
    val sampleCount: Long = 0,
    val lastUpdate: Long = System.currentTimeMillis()
)

data class MagneticFieldData(
    val x: Float,
    val y: Float,
    val z: Float,
    val magnitude: Float
)
