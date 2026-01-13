package com.pillarstabilizer.ui

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pillarstabilizer.*
import com.pillarstabilizer.analysis.FrequencySpike
import kotlinx.coroutines.launch

@Composable
fun PillarStabilizerApp(viewModel: PillarViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val commandLog by viewModel.commandLog.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val context = LocalContext.current

    // Auto-scroll log to bottom
    val logListState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    LaunchedEffect(commandLog.size) {
        if (commandLog.isNotEmpty()) {
            coroutineScope.launch {
                logListState.animateScrollToItem(commandLog.size - 1)
            }
        }
    }

    Scaffold(
        containerColor = ObsidianColors.background
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header
            Text(
                text = "⬢ PILLAR STABILIZER",
                style = MaterialTheme.typography.headlineMedium,
                color = ObsidianColors.primary,
                fontFamily = FontFamily.Monospace
            )

            // Status Section
            StabilizationStatusCard(uiState, viewModel, context)

            // Monitoring Controls
            MonitoringControlCard(uiState, viewModel, context)

            // Mercury Flow (Command Log)
            MercuryFlowCard(commandLog, logListState)

            // Sulphur Intent (Manual Command Entry)
            SulphurIntentCard(viewModel, uiState.isExecuting)

            // Hardware Resonance Display
            ResonanceDisplayCard(uiState.resonanceData)
        }

        // Error Dialog
        if (errorMessage != null) {
            AlertDialog(
                onDismissRequest = { viewModel.clearError() },
                title = { Text("Error") },
                text = { Text(errorMessage!!) },
                confirmButton = {
                    Button(onClick = { viewModel.clearError() }) {
                        Text("Dismiss")
                    }
                },
                containerColor = ObsidianColors.surface,
                textContentColor = ObsidianColors.onSurface,
                titleContentColor = ObsidianColors.error
            )
        }
    }
}

@Composable
fun StabilizationStatusCard(
    uiState: PillarUiState,
    viewModel: PillarViewModel,
    context: Context
) {
    ObsidianCard(title = "🐢 LEGS OF THE TORTOISE") {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            StatusRow(
                label = "Shizuku Service",
                status = uiState.shizukuAvailable,
                statusText = if (uiState.shizukuAvailable) "ACTIVE" else "OFFLINE"
            )

            StatusRow(
                label = "ADB Privileges",
                status = uiState.shizukuPermissionGranted,
                statusText = if (uiState.shizukuPermissionGranted) "GRANTED" else "DENIED"
            )

            if (!uiState.shizukuPermissionGranted && uiState.shizukuAvailable) {
                Button(
                    onClick = { viewModel.requestShizukuPermission() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ObsidianColors.accent
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("REQUEST PERMISSION")
                }
            }
        }
    }
}

@Composable
fun MonitoringControlCard(
    uiState: PillarUiState,
    viewModel: PillarViewModel,
    context: Context
) {
    ObsidianCard(title = "📡 MONITORING") {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            StatusRow(
                label = "Sensor Monitoring",
                status = uiState.isMonitoring,
                statusText = if (uiState.isMonitoring) "ACTIVE" else "STOPPED"
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { viewModel.startMonitoring(context) },
                    enabled = !uiState.isMonitoring && uiState.shizukuPermissionGranted,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ObsidianColors.success
                    ),
                    modifier = Modifier.weight(1f)
                ) {
                    Text("START")
                }

                Button(
                    onClick = { viewModel.stopMonitoring(context) },
                    enabled = uiState.isMonitoring,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ObsidianColors.error
                    ),
                    modifier = Modifier.weight(1f)
                ) {
                    Text("STOP")
                }
            }
        }
    }
}

@Composable
fun MercuryFlowCard(
    commandLog: List<CommandLogEntry>,
    scrollState: androidx.compose.foundation.lazy.LazyListState
) {
    ObsidianCard(title = "☿ MERCURY FLOW") {
        LazyColumn(
            modifier = Modifier.height(200.dp),
            state = scrollState,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            items(commandLog) { entry ->
                LogEntry(entry)
            }
        }
    }
}

@Composable
fun SulphurIntentCard(viewModel: PillarViewModel, isExecuting: Boolean) {
    var command by remember { mutableStateOf("") }

    ObsidianCard(title = "🜍 SULPHUR INTENT") {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = command,
                onValueChange = { command = it },
                label = { Text("ADB Command") },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isExecuting,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ObsidianColors.primary,
                    unfocusedBorderColor = ObsidianColors.surface,
                    focusedTextColor = ObsidianColors.onSurface,
                    unfocusedTextColor = ObsidianColors.onSurface
                ),
                textStyle = LocalTextStyle.current.copy(fontFamily = FontFamily.Monospace),
                singleLine = false,
                maxLines = 3
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = {
                        viewModel.executeManualCommand(command)
                        command = ""
                    },
                    enabled = command.isNotBlank() && !isExecuting,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ObsidianColors.accent
                    ),
                    modifier = Modifier.weight(1f)
                ) {
                    Text(if (isExecuting) "EXECUTING..." else "EXECUTE")
                }

                Button(
                    onClick = { viewModel.getThermalSnapshot() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ObsidianColors.secondary
                    ),
                    modifier = Modifier.weight(1f)
                ) {
                    Text("THERMAL SNAP")
                }
            }
        }
    }
}

@Composable
fun ResonanceDisplayCard(data: ResonanceData) {
    ObsidianCard(title = "⚡ ELECTROMAGNETIC RESONANCE") {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            // Magnetic Field
            MetricRow("Magnetic Field", "%.2f µT".format(data.magneticField.magnitude))
            MetricRow("Field X", "%.2f mT".format(data.magneticField.x))
            MetricRow("Field Y", "%.2f mT".format(data.magneticField.y))
            MetricRow("Field Z", "%.2f mT".format(data.magneticField.z))

            Divider(color = ObsidianColors.surface, modifier = Modifier.padding(vertical = 4.dp))

            // Battery Info
            MetricRow("Battery Current", "%.1f mA".format(data.batteryInfo.currentMilliamps))
            MetricRow("Battery Voltage", "%.2f V".format(data.batteryInfo.voltageVolts))
            MetricRow("Power Draw", "%.2f W".format(data.batteryInfo.powerWatts))
            MetricRow("Battery Temp", "%.1f °C".format(data.batteryInfo.temperatureCelsius))

            Divider(color = ObsidianColors.surface, modifier = Modifier.padding(vertical = 4.dp))

            // Frequency Spikes (FFT results)
            if (data.frequencySpikes.isNotEmpty()) {
                Text(
                    "Frequency Spikes:",
                    style = MaterialTheme.typography.labelMedium,
                    color = ObsidianColors.primary
                )
                data.frequencySpikes.take(3).forEach { spike ->
                    MetricRow("%.1f Hz".format(spike.frequency), "%.2f".format(spike.intensity))
                }
                Divider(color = ObsidianColors.surface, modifier = Modifier.padding(vertical = 4.dp))
            }

            // Thermal Zones
            if (data.thermalData.zones.isNotEmpty()) {
                Text(
                    "Thermal Zones:",
                    style = MaterialTheme.typography.labelMedium,
                    color = ObsidianColors.primary
                )
                data.thermalData.zones.take(3).forEach { zone ->
                    MetricRow(zone.name, "%.1f °C".format(zone.temperature))
                }
            }

            MetricRow("Samples Collected", "${data.sampleCount}")
        }
    }
}

@Composable
fun ObsidianCard(
    title: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        color = ObsidianColors.surface,
        shadowElevation = 4.dp
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = ObsidianColors.primary,
                fontFamily = FontFamily.Monospace
            )
            Divider(color = ObsidianColors.primary.copy(alpha = 0.3f))
            content()
        }
    }
}

@Composable
fun StatusRow(label: String, status: Boolean, statusText: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = ObsidianColors.onSurface
        )
        Text(
            text = statusText,
            style = MaterialTheme.typography.bodyMedium,
            color = if (status) ObsidianColors.success else ObsidianColors.error,
            fontFamily = FontFamily.Monospace
        )
    }
}

@Composable
fun MetricRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = ObsidianColors.onSurface.copy(alpha = 0.7f)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            color = ObsidianColors.accent,
            fontFamily = FontFamily.Monospace
        )
    }
}

@Composable
fun LogEntry(entry: CommandLogEntry) {
    val color = when (entry.level) {
        LogLevel.SUCCESS -> ObsidianColors.success
        LogLevel.ERROR -> ObsidianColors.error
        LogLevel.WARNING -> ObsidianColors.warning
        LogLevel.INFO -> ObsidianColors.onSurface.copy(alpha = 0.7f)
    }

    Text(
        text = "▸ ${entry.message}",
        style = MaterialTheme.typography.bodySmall,
        color = color,
        fontFamily = FontFamily.Monospace,
        modifier = Modifier.fillMaxWidth()
    )
}
