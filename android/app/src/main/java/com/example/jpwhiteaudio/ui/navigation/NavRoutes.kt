package com.example.jpwhiteaudio.ui.navigation

sealed class NavRoutes(val route: String) {
    data object Welcome : NavRoutes("welcome")
    data object Login : NavRoutes("login")
    data object Register : NavRoutes("register")
    data object VoiceEnrollment : NavRoutes("voice_enrollment")
    data object Home : NavRoutes("home")
}
