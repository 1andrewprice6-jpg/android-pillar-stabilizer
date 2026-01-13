package com.pillarstabilizer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pillarstabilizer.ui.ObsidianTheme
import com.pillarstabilizer.ui.PillarStabilizerApp
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            // Permission granted, app can post notifications
        } else {
            // Permission denied, notification won't work but app can still function
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize Shizuku
        ShizukuService.initialize(this)

        // Request notification permission for Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        setContent {
            ObsidianTheme {
                PillarStabilizerApp()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        ShizukuService.cleanup()
    }
}

class PillarViewModel : ViewModel() {
    private val shellExecutor = ShellExecutor()

    private val _uiState = MutableStateFlow(PillarUiState())
    val uiState: StateFlow<PillarUiState> = _uiState.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    val commandLog = shellExecutor.commandLog

    init {
        checkShizukuStatus()
        observeResonanceData()
        // Observe Shizuku permission changes
        viewModelScope.launch {
            while (true) {
                checkShizukuStatus()
                kotlinx.coroutines.delay(1000) // Check every second
            }
        }
    }

    private fun checkShizukuStatus() {
        _uiState.value = _uiState.value.copy(
            shizukuAvailable = ShizukuService.isShizukuAvailable,
            shizukuPermissionGranted = ShizukuService.isPermissionGranted
        )
    }

    fun requestShizukuPermission() {
        ShizukuService.requestPermission()
        // Status will update via the listener
    }

    fun startMonitoring(context: android.content.Context) {
        try {
            val intent = Intent(context, HardwareResonanceReader::class.java)
            androidx.core.content.ContextCompat.startForegroundService(context, intent)
            _uiState.value = _uiState.value.copy(isMonitoring = true)
        } catch (e: Exception) {
            _errorMessage.value = "Failed to start monitoring: ${e.message}"
            _uiState.value = _uiState.value.copy(isMonitoring = false)
        }
    }

    fun stopMonitoring(context: android.content.Context) {
        try {
            val intent = Intent(context, HardwareResonanceReader::class.java)
            context.stopService(intent)
            _uiState.value = _uiState.value.copy(isMonitoring = false)
        } catch (e: Exception) {
            _errorMessage.value = "Failed to stop monitoring: ${e.message}"
        }
    }

    private fun observeResonanceData() {
        viewModelScope.launch {
            HardwareResonanceReader.instance.flatMapLatest { service ->
                service?.resonanceData ?: MutableStateFlow(ResonanceData())
            }.collect { data ->
                _uiState.value = _uiState.value.copy(
                    resonanceData = data
                )
            }
        }
    }

    fun executeManualCommand(command: String) {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isExecuting = true)
                val result = shellExecutor.execute(command)
                if (!result.isSuccess) {
                    _errorMessage.value = "Command failed: ${result.error}"
                }
            } catch (e: Exception) {
                _errorMessage.value = "Execution error: ${e.message}"
            } finally {
                _uiState.value = _uiState.value.copy(isExecuting = false)
            }
        }
    }

    fun getThermalSnapshot() {
        viewModelScope.launch {
            try {
                val thermal = shellExecutor.getThermalData()
                _uiState.value = _uiState.value.copy(
                    resonanceData = _uiState.value.resonanceData.copy(thermalData = thermal)
                )
            } catch (e: Exception) {
                _errorMessage.value = "Failed to get thermal data: ${e.message}"
            }
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }
}

data class PillarUiState(
    val shizukuAvailable: Boolean = false,
    val shizukuPermissionGranted: Boolean = false,
    val isMonitoring: Boolean = false,
    val resonanceData: ResonanceData = ResonanceData(),
    val isExecuting: Boolean = false
)
