package com.example.jpwhiteaudio.ui.navigation

import androidx.compose.runtime.Composable
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
import com.example.jpwhiteaudio.ui.screens.welcome.WelcomeScreen
import com.example.jpwhiteaudio.ui.screens.welcome.WelcomeViewModel

@Composable
fun AppNavigation(
    navController: NavHostController = rememberNavController(),
    welcomeViewModel: WelcomeViewModel = hiltViewModel()
) {
    val isLoggedIn by welcomeViewModel.isLoggedIn.collectAsState(initial = false)

    val startDestination = if (isLoggedIn) {
        NavRoutes.Home.route
    } else {
        NavRoutes.Welcome.route
    }

    NavHost(
        navController = navController,
        startDestination = startDestination
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
                onLoginSuccess = {
                    navController.navigate(NavRoutes.Home.route) {
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
                onRegisterSuccess = {
                    navController.navigate(NavRoutes.Home.route) {
                        popUpTo(NavRoutes.Welcome.route) { inclusive = true }
                    }
                },
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }

        composable(NavRoutes.Home.route) {
            HomeScreen(
                onSignOut = {
                    navController.navigate(NavRoutes.Welcome.route) {
                        popUpTo(NavRoutes.Home.route) { inclusive = true }
                    }
                }
            )
        }
    }
}
