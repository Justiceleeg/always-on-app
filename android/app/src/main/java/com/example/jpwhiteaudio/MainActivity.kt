package com.example.jpwhiteaudio

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.example.jpwhiteaudio.ui.navigation.AppNavigation
import com.example.jpwhiteaudio.ui.theme.JpwhiteAudioTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            JpwhiteAudioTheme {
                AppNavigation()
            }
        }
    }
}