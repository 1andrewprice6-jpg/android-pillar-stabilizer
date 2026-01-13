package com.pillarstabilizer.analysis

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.sin

/**
 * THE INVERSE PILLAR: Generates a counter-frequency to negate resonant signals.
 * Uses phase-shifted sine waves for destructive interference cancellation.
 */
class CounterResonanceGenerator {

    private val sampleRate = 44100
    private var audioTrack: AudioTrack? = null
    private var generatorJob: Job? = null
    private val generatorScope = CoroutineScope(Dispatchers.IO)

    private var isShieldActive = false
    private var currentPhase = 0.0

    /**
     * Activates the counter-frequency shield.
     * @param targetFrequency The frequency to counter (Hz)
     */
    fun activateShield(targetFrequency: Double) {
        synchronized(this) {
            if (isShieldActive) {
                stopShield()
            }

            try {
                val bufferSize = AudioTrack.getMinBufferSize(
                    sampleRate,
                    AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT
                )

                if (bufferSize <= 0) {
                    return // Audio system not available
                }

                audioTrack = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(sampleRate)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build()
                    )
                    .setBufferSizeInBytes(bufferSize * 2)
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .build()

                isShieldActive = true
                currentPhase = 0.0

                generatorJob = generatorScope.launch {
                    generateAndPlayCounterWave(targetFrequency, bufferSize)
                }

                audioTrack?.play()
            } catch (e: Exception) {
                isShieldActive = false
                audioTrack?.release()
                audioTrack = null
            }
        }
    }

    private suspend fun generateAndPlayCounterWave(targetFrequency: Double, bufferSize: Int) {
        val samples = ShortArray(bufferSize)
        val phaseIncrement = 2.0 * PI * targetFrequency / sampleRate

        while (isShieldActive && audioTrack != null) {
            try {
                for (i in samples.indices) {
                    // 180-degree phase shift for destructive interference
                    samples[i] = (sin(currentPhase + PI) * Short.MAX_VALUE).toInt().toShort()
                    currentPhase += phaseIncrement

                    // Wrap phase to prevent overflow
                    if (currentPhase >= 2.0 * PI) {
                        currentPhase -= 2.0 * PI
                    }
                }

                val written = audioTrack?.write(samples, 0, samples.size) ?: 0
                if (written < 0) {
                    // Error occurred, stop the shield
                    isShieldActive = false
                }
            } catch (e: Exception) {
                isShieldActive = false
                break
            }
        }
    }

    fun stopShield() {
        synchronized(this) {
            isShieldActive = false
            generatorJob?.cancel()

            try {
                audioTrack?.stop()
                audioTrack?.flush()
                audioTrack?.release()
            } catch (e: Exception) {
                // Already stopped
            }
            audioTrack = null
        }
    }

    fun isActive(): Boolean = synchronized(this) { isShieldActive }

    fun cleanup() {
        stopShield()
        generatorScope.cancel()
    }

    override fun finalize() {
        try {
            cleanup()
        } catch (e: Exception) {
            // Cleanup failed, but object is being GC'd anyway
        }
    }
}
