package com.pillarstabilizer

import android.content.Context
import android.content.pm.PackageManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import rikka.shizuku.Shizuku
import java.util.concurrent.TimeUnit

object ShizukuService {
    private const val SHIZUKU_PERMISSION_CODE = 1001
    private const val DEFAULT_TIMEOUT_MS = 10000L

    var isShizukuAvailable = false
        private set

    var isPermissionGranted = false
        private set

    private val requestPermissionResultListener =
        Shizuku.OnRequestPermissionResultListener { requestCode, grantResult ->
            if (requestCode == SHIZUKU_PERMISSION_CODE) {
                isPermissionGranted = grantResult == PackageManager.PERMISSION_GRANTED
            }
        }

    private val binderReceivedListener = Shizuku.OnBinderReceivedListener {
        isShizukuAvailable = Shizuku.pingBinder()
    }

    private val binderDeadListener = Shizuku.OnBinderDeadListener {
        isShizukuAvailable = false
    }

    fun initialize(context: Context) {
        try {
            isShizukuAvailable = Shizuku.pingBinder()
            Shizuku.addRequestPermissionResultListener(requestPermissionResultListener)
            Shizuku.addBinderReceivedListener(binderReceivedListener)
            Shizuku.addBinderDeadListener(binderDeadListener)

            if (isShizukuAvailable) {
                checkPermission()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            isShizukuAvailable = false
        }
    }

    fun cleanup() {
        try {
            Shizuku.removeRequestPermissionResultListener(requestPermissionResultListener)
            Shizuku.removeBinderReceivedListener(binderReceivedListener)
            Shizuku.removeBinderDeadListener(binderDeadListener)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun checkPermission(): Boolean {
        return try {
            if (!isShizukuAvailable) return false

            when {
                Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED -> {
                    isPermissionGranted = true
                    true
                }
                else -> {
                    isPermissionGranted = false
                    false
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    fun requestPermission() {
        try {
            if (isShizukuAvailable && !isPermissionGranted) {
                Shizuku.requestPermission(SHIZUKU_PERMISSION_CODE)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun executeCommand(
        command: String,
        timeoutMs: Long = DEFAULT_TIMEOUT_MS
    ): ShellResult = withContext(Dispatchers.IO) {
        try {
            if (!isShizukuAvailable || !isPermissionGranted) {
                return@withContext ShellResult(
                    output = "",
                    error = "Shizuku not available or permission not granted",
                    exitCode = -1
                )
            }

            val process = try {
                Shizuku.newProcess(arrayOf("sh", "-c", command), null, null)
            } catch (e: Exception) {
                return@withContext ShellResult(
                    output = "",
                    error = "Failed to create process: ${e.message}",
                    exitCode = -1
                )
            }

            return@withContext process.use { p ->
                val outputBuilder = StringBuilder()
                val errorBuilder = StringBuilder()

                val outputThread = Thread {
                    try {
                        p.inputStream.bufferedReader().use { reader ->
                            reader.forEachLine { outputBuilder.appendLine(it) }
                        }
                    } catch (e: Exception) {
                        // Stream closed, which is expected on process termination
                    }
                }

                val errorThread = Thread {
                    try {
                        p.errorStream.bufferedReader().use { reader ->
                            reader.forEachLine { errorBuilder.appendLine(it) }
                        }
                    } catch (e: Exception) {
                        // Stream closed, which is expected on process termination
                    }
                }

                outputThread.start()
                errorThread.start()

                val completed = p.waitFor(timeoutMs, TimeUnit.MILLISECONDS)

                if (!completed) {
                    p.destroyForcibly()
                    outputThread.interrupt()
                    errorThread.interrupt()
                    return@use ShellResult(
                        output = outputBuilder.toString().trim(),
                        error = "Command timeout after ${timeoutMs}ms",
                        exitCode = -1
                    )
                }

                // Wait for threads to finish reading streams
                outputThread.join(1000)
                errorThread.join(1000)

                ShellResult(
                    output = outputBuilder.toString().trim(),
                    error = errorBuilder.toString().trim(),
                    exitCode = p.exitValue()
                )
            }
        } catch (e: Exception) {
            ShellResult(
                output = "",
                error = e.message ?: "Unknown error",
                exitCode = -1
            )
        }
    }
}

data class ShellResult(
    val output: String,
    val error: String,
    val exitCode: Int
) {
    val isSuccess: Boolean get() = exitCode == 0
}
