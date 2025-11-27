package com.example.jpwhiteaudio.ui.screens.voiceenrollment

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import kotlin.math.sin

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoiceEnrollmentScreen(
    onEnrollmentComplete: () -> Unit,
    onSkip: () -> Unit,
    viewModel: VoiceEnrollmentViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val recordingDurationMs by viewModel.recordingDurationMs.collectAsState()
    val amplitude by viewModel.amplitude.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    var permissionRequested by remember { mutableStateOf(false) }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            viewModel.beginEnrollment()
        } else {
            viewModel.clearError()
        }
    }

    // Show error in snackbar
    LaunchedEffect(uiState.error) {
        uiState.error?.let { error ->
            snackbarHostState.showSnackbar(error)
            viewModel.clearError()
        }
    }

    // Handle enrollment completion
    LaunchedEffect(uiState.enrollmentComplete) {
        if (uiState.enrollmentComplete) {
            // Small delay to show success state
            kotlinx.coroutines.delay(1500)
            onEnrollmentComplete()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Voice Enrollment") }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (uiState.enrollmentStep) {
                EnrollmentStep.Welcome -> WelcomeContent(
                    onBeginEnrollment = {
                        if (viewModel.hasRecordPermission()) {
                            viewModel.beginEnrollment()
                        } else {
                            permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    },
                    onSkip = onSkip
                )

                EnrollmentStep.Recording -> RecordingContent(
                    isRecording = uiState.isRecording,
                    isUploading = uiState.isUploading,
                    recordingDurationMs = recordingDurationMs,
                    amplitude = amplitude,
                    onStartRecording = viewModel::startRecording,
                    onStopRecording = viewModel::stopRecording,
                    onCancel = viewModel::cancelRecording
                )

                EnrollmentStep.Complete -> CompleteContent(
                    onContinue = onEnrollmentComplete
                )
            }
        }
    }
}

@Composable
private fun WelcomeContent(
    onBeginEnrollment: () -> Unit,
    onSkip: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Filled.Mic,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(32.dp))

        Text(
            text = "Voice Enrollment",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "We need to learn your voice to identify you as the primary user. " +
                    "This helps us transcribe only your conversations and those you consent to.",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "You'll be asked to speak for 15-30 seconds. Please speak naturally in a quiet environment.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(48.dp))

        Button(
            onClick = onBeginEnrollment,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
        ) {
            Text("Begin Enrollment")
        }

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedButton(
            onClick = onSkip,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
        ) {
            Text("Skip for Now")
        }
    }
}

private const val ENROLLMENT_SCRIPT = """
Please read the following passage aloud at your normal speaking pace:

"The quick brown fox jumps over the lazy dog near the riverbank. I enjoy taking long walks through the park on sunny afternoons, watching the clouds drift by overhead. Technology continues to shape our daily lives in remarkable ways, from how we communicate with friends and family to how we work and learn. The best conversations happen when people truly listen to each other and share their thoughts openly."
"""

@Composable
private fun RecordingContent(
    isRecording: Boolean,
    isUploading: Boolean,
    recordingDurationMs: Long,
    amplitude: Float,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onCancel: () -> Unit
) {
    val minDurationMs = 15000L
    val maxDurationMs = 30000L
    val canStop = recordingDurationMs >= minDurationMs

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp)
    ) {
        // Top section - scrollable content
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(16.dp))

            // Recording prompt
            Text(
                text = if (isRecording) "Recording..." else "Tap to start recording",
                style = MaterialTheme.typography.titleLarge,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Script to read
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = ENROLLMENT_SCRIPT.trim(),
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Start,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 22.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }

        // Bottom section - fixed buttons and controls
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Waveform visualization
            if (isRecording) {
                WaveformVisualization(
                    amplitude = amplitude,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp)
                )
            } else {
                Spacer(modifier = Modifier.height(50.dp))
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Recording timer
            val seconds = (recordingDurationMs / 1000).toInt()
            val minutes = seconds / 60
            val displaySeconds = seconds % 60
            Text(
                text = "%d:%02d".format(minutes, displaySeconds),
                style = MaterialTheme.typography.headlineMedium,
                color = if (isRecording) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
            )

            // Progress indicator
            Text(
                text = when {
                    recordingDurationMs < minDurationMs -> "Minimum: ${minDurationMs / 1000}s"
                    recordingDurationMs < maxDurationMs -> "Good! You can stop or continue"
                    else -> "Maximum reached"
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Record/Stop button
            if (isUploading) {
                CircularProgressIndicator()
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Processing your voice...",
                    style = MaterialTheme.typography.bodyMedium
                )
            } else {
                RecordButton(
                    isRecording = isRecording,
                    canStop = canStop,
                    onClick = {
                        if (isRecording) {
                            if (canStop) onStopRecording()
                        } else {
                            onStartRecording()
                        }
                    }
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Cancel button
            if (!isUploading) {
                OutlinedButton(
                    onClick = onCancel,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                ) {
                    Text("Cancel")
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun RecordButton(
    isRecording: Boolean,
    canStop: Boolean,
    onClick: () -> Unit
) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.1f,
        animationSpec = infiniteRepeatable(
            animation = tween(500, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )

    IconButton(
        onClick = onClick,
        modifier = Modifier
            .size(80.dp)
            .then(if (isRecording) Modifier.scale(scale) else Modifier)
            .background(
                color = if (isRecording) {
                    if (canStop) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.error.copy(alpha = 0.5f)
                } else {
                    MaterialTheme.colorScheme.primary
                },
                shape = CircleShape
            )
    ) {
        Icon(
            imageVector = if (isRecording) Icons.Filled.Stop else Icons.Filled.Mic,
            contentDescription = if (isRecording) "Stop recording" else "Start recording",
            tint = Color.White,
            modifier = Modifier.size(40.dp)
        )
    }
}

@Composable
private fun WaveformVisualization(
    amplitude: Float,
    modifier: Modifier = Modifier
) {
    val primaryColor = MaterialTheme.colorScheme.primary
    val infiniteTransition = rememberInfiniteTransition(label = "waveform")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 2f * Math.PI.toFloat(),
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "phase"
    )

    Canvas(modifier = modifier) {
        val width = size.width
        val height = size.height
        val centerY = height / 2

        // Draw multiple sine waves based on amplitude
        val baseAmplitude = height * 0.3f * amplitude.coerceIn(0.1f, 1f)

        for (i in 0 until width.toInt() step 4) {
            val x = i.toFloat()
            val normalizedX = x / width * 4 * Math.PI.toFloat()

            // Primary wave
            val y1 = centerY + sin(normalizedX + phase) * baseAmplitude
            // Secondary wave (higher frequency, lower amplitude)
            val y2 = centerY + sin(normalizedX * 2 + phase * 1.5f) * baseAmplitude * 0.5f

            drawCircle(
                color = primaryColor,
                radius = 3f,
                center = Offset(x, y1)
            )
            drawCircle(
                color = primaryColor.copy(alpha = 0.5f),
                radius = 2f,
                center = Offset(x, y2)
            )
        }
    }
}

@Composable
private fun CompleteContent(
    onContinue: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Filled.CheckCircle,
            contentDescription = null,
            modifier = Modifier.size(100.dp),
            tint = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(32.dp))

        Text(
            text = "Enrollment Complete!",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Your voice has been successfully enrolled. " +
                    "The app will now recognize you as the primary user.",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(48.dp))

        Button(
            onClick = onContinue,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
        ) {
            Text("Start Listening")
        }
    }
}
