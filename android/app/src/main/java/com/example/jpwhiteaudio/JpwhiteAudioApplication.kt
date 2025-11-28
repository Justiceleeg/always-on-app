package com.example.jpwhiteaudio

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class JpwhiteAudioApplication : Application() {

    companion object {
        const val LISTENING_CHANNEL_ID = "listening_channel"
        const val LISTENING_CHANNEL_NAME = "Audio Listening"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val listeningChannel = NotificationChannel(
                LISTENING_CHANNEL_ID,
                LISTENING_CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows when the app is listening for speech"
                setShowBadge(false)
            }

            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(listeningChannel)
        }
    }
}
