package com.example.jpwhiteaudio.ui.navigation

import android.util.Log
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.jpwhiteaudio.ui.screens.home.HomeScreen
import com.example.jpwhiteaudio.ui.screens.login.LoginScreen
import com.example.jpwhiteaudio.ui.screens.register.RegisterScreen
import com.example.jpwhiteaudio.ui.screens.voiceenrollment.VoiceEnrollmentScreen
import com.example.jpwhiteaudio.ui.screens.welcome.WelcomeScreen
import com.example.jpwhiteaudio.ui.screens.welcome.WelcomeViewModel

private const val TAG = "AppNavigation"

@Composable
fun AppNavigation(
    navController: NavHostController = rememberNavController(),
    welcomeViewModel: WelcomeViewModel = hiltViewModel()
) {
    val isLoggedIn by welcomeViewModel.isLoggedIn.collectAsState(initial = null)

    // Handle initial navigation based on auth state
    // Use null as initial to avoid navigating before we know the auth state
    LaunchedEffect(isLoggedIn) {
        val currentRoute = navController.currentDestination?.route
        Log.d(TAG, "LaunchedEffect: isLoggedIn=$isLoggedIn, currentRoute=$currentRoute")
        when (isLoggedIn) {
            true -> {
                // User is logged in, navigate to home if we're on welcome
                if (currentRoute == NavRoutes.Welcome.route) {
                    Log.d(TAG, "Navigating from Welcome to Home (already logged in)")
                    navController.navigate(NavRoutes.Home.route) {
                        popUpTo(NavRoutes.Welcome.route) { inclusive = true }
                    }
                }
            }
            false -> {
                // User is logged out, navigate to welcome if not already there
                if (currentRoute != NavRoutes.Welcome.route &&
                    currentRoute != NavRoutes.Login.route &&
                    currentRoute != NavRoutes.Register.route) {
                    Log.d(TAG, "Navigating to Welcome (logged out)")
                    navController.navigate(NavRoutes.Welcome.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            }
            null -> {
                // Still loading, do nothing
                Log.d(TAG, "Auth state loading...")
            }
        }
    }

    NavHost(
        navController = navController,
        startDestination = NavRoutes.Welcome.route
    ) {
        composable(NavRoutes.Welcome.route) {
            WelcomeScreen(
                onSignInClick = {
                    navController.navigate(NavRoutes.Login.route)
                },
                onCreateAccountClick = {
                    navController.navigate(NavRoutes.Register.route)
                }
            )
        }

        composable(NavRoutes.Login.route) {
            LoginScreen(
                onLoginSuccess = { isEnrolled ->
                    Log.d(TAG, "onLoginSuccess called, isEnrolled=$isEnrolled")
                    val destination = if (isEnrolled) {
                        NavRoutes.Home.route
                    } else {
                        NavRoutes.VoiceEnrollment.route
                    }
                    Log.d(TAG, "Navigating to $destination")
                    navController.navigate(destination) {
                        popUpTo(NavRoutes.Welcome.route) { inclusive = true }
                    }
                },
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }

        composable(NavRoutes.Register.route) {
            RegisterScreen(
                onRegisterSuccess = { isEnrolled ->
                    val destination = if (isEnrolled) {
                        NavRoutes.Home.route
                    } else {
                        NavRoutes.VoiceEnrollment.route
                    }
                    navController.navigate(destination) {
                        popUpTo(NavRoutes.Welcome.route) { inclusive = true }
                    }
                },
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }

        composable(NavRoutes.VoiceEnrollment.route) {
            VoiceEnrollmentScreen(
                onEnrollmentComplete = {
                    navController.navigate(NavRoutes.Home.route) {
                        popUpTo(NavRoutes.VoiceEnrollment.route) { inclusive = true }
                    }
                },
                onSkip = {
                    navController.navigate(NavRoutes.Home.route) {
                        popUpTo(NavRoutes.VoiceEnrollment.route) { inclusive = true }
                    }
                }
            )
        }

        composable(NavRoutes.Home.route) {
            HomeScreen(
                onSignOut = {
                    navController.navigate(NavRoutes.Welcome.route) {
                        popUpTo(NavRoutes.Home.route) { inclusive = true }
                    }
                },
                onNavigateToEnrollment = {
                    navController.navigate(NavRoutes.VoiceEnrollment.route)
                }
            )
        }
    }
}
