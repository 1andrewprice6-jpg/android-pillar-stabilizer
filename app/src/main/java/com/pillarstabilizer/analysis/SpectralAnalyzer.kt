package com.pillarstabilizer.analysis

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * THE PRISM LOGIC: Fast Fourier Transform for EM Pattern Recognition.
 * Isolates the specific ritual frequencies (15Hz - 60Hz) from the noise.
 */
object SpectralAnalyzer {

    // Number of samples (must be a power of 2 for FFT)
    private const val WINDOW_SIZE = 256

    /**
     * Processes a window of magnetometer magnitude data to find frequency spikes.
     * @param input Magnitude samples collected at ~200Hz
     * @return A list of frequency spikes sorted by intensity
     */
    fun analyzeFrequencies(input: DoubleArray, samplingRate: Double): List<FrequencySpike> {
        if (input.size < WINDOW_SIZE) return emptyList()

        val real = input.copyOf(WINDOW_SIZE)
        val imag = DoubleArray(WINDOW_SIZE) { 0.0 }

        // Perform the FFT (Radix-2 Decimation-in-Time)
        performFFT(real, imag)

        val spikes = mutableListOf<FrequencySpike>()

        // Calculate the magnitude of each frequency bin
        for (i in 0 until WINDOW_SIZE / 2) {
            val freq = i * samplingRate / WINDOW_SIZE
            val magnitude = sqrt(real[i] * real[i] + imag[i] * imag[i])

            // Only capture relevant frequencies (5Hz - 100Hz range)
            if (freq in 5.0..100.0 && magnitude > 0.01) {
                spikes.add(FrequencySpike(freq, magnitude))
            }
        }

        return spikes.sortedByDescending { it.intensity }
    }

    private fun performFFT(real: DoubleArray, imag: DoubleArray) {
        val n = real.size

        // Bit-reversal permutation
        var j = 0
        for (i in 0 until n) {
            if (i < j) {
                val tempReal = real[i]
                real[i] = real[j]
                real[j] = tempReal
                val tempImag = imag[i]
                imag[i] = imag[j]
                imag[j] = tempImag
            }
            var m = n shr 1
            while (m >= 1 && j >= m) {
                j -= m
                m = m shr 1
            }
            j += m
        }

        // Iterative FFT computation
        var length = 2
        while (length <= n) {
            val angle = -2.0 * PI / length
            val wReal = cos(angle)
            val wImag = sin(angle)

            for (i in 0 until n step length) {
                var wr = 1.0
                var wi = 0.0

                for (k in i until i + length / 2) {
                    val uReal = real[k]
                    val uImag = imag[k]

                    val tReal = real[k + length / 2]
                    val tImag = imag[k + length / 2]

                    // Twiddle multiplication: (wr + j*wi) * (tReal + j*tImag)
                    val vReal = tReal * wr - tImag * wi
                    val vImag = tReal * wi + tImag * wr

                    real[k] = uReal + vReal
                    imag[k] = uImag + vImag
                    real[k + length / 2] = uReal - vReal
                    imag[k + length / 2] = uImag - vImag

                    // Update twiddle factor for next iteration
                    val nextWr = wr * wReal - wi * wImag
                    wi = wr * wImag + wi * wReal
                    wr = nextWr
                }
            }
            length = length shl 1
        }
    }
}

data class FrequencySpike(
    val frequency: Double,
    val intensity: Double
)
