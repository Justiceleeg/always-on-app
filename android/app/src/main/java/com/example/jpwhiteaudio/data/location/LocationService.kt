package com.example.jpwhiteaudio.data.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Looper
import android.util.Log
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.callbackFlow
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "LocationService"

/**
 * Service for getting device location using FusedLocationProviderClient.
 * Provides continuous location updates while active.
 */
@Singleton
class LocationService @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val fusedLocationClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)

    private val _currentLocation = MutableStateFlow<Location?>(null)
    val currentLocation: StateFlow<Location?> = _currentLocation.asStateFlow()

    private var locationCallback: LocationCallback? = null
    private var isRequestingUpdates = false

    /**
     * Check if location permissions are granted
     */
    fun hasLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Start receiving location updates.
     * Updates will be available via the currentLocation StateFlow.
     */
    fun startLocationUpdates() {
        if (!hasLocationPermission()) {
            Log.w(TAG, "Location permission not granted")
            return
        }

        if (isRequestingUpdates) {
            Log.d(TAG, "Already requesting location updates")
            return
        }

        val locationRequest = LocationRequest.Builder(
            Priority.PRIORITY_BALANCED_POWER_ACCURACY,
            30_000L // Update every 30 seconds
        ).apply {
            setMinUpdateIntervalMillis(10_000L) // Fastest interval 10 seconds
            setMaxUpdateDelayMillis(60_000L) // Max delay 60 seconds for batching
        }.build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { location ->
                    Log.d(TAG, "Location update: ${location.latitude}, ${location.longitude}")
                    _currentLocation.value = location
                }
            }
        }

        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback!!,
                Looper.getMainLooper()
            )
            isRequestingUpdates = true
            Log.d(TAG, "Started location updates")

            // Also try to get last known location immediately
            fusedLocationClient.lastLocation.addOnSuccessListener { location ->
                location?.let {
                    Log.d(TAG, "Last known location: ${it.latitude}, ${it.longitude}")
                    if (_currentLocation.value == null) {
                        _currentLocation.value = it
                    }
                }
            }
        } catch (e: SecurityException) {
            Log.e(TAG, "Security exception when requesting location updates", e)
        }
    }

    /**
     * Stop receiving location updates to save battery.
     */
    fun stopLocationUpdates() {
        locationCallback?.let {
            fusedLocationClient.removeLocationUpdates(it)
            Log.d(TAG, "Stopped location updates")
        }
        locationCallback = null
        isRequestingUpdates = false
    }

    /**
     * Get the current latitude, or null if not available
     */
    fun getCurrentLatitude(): Double? = _currentLocation.value?.latitude

    /**
     * Get the current longitude, or null if not available
     */
    fun getCurrentLongitude(): Double? = _currentLocation.value?.longitude

    /**
     * Provides a Flow that emits location updates.
     * The flow automatically handles starting and stopping location updates.
     */
    fun locationFlow(): Flow<Location> = callbackFlow {
        if (!hasLocationPermission()) {
            close()
            return@callbackFlow
        }

        val locationRequest = LocationRequest.Builder(
            Priority.PRIORITY_BALANCED_POWER_ACCURACY,
            30_000L
        ).apply {
            setMinUpdateIntervalMillis(10_000L)
        }.build()

        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { location ->
                    trySend(location)
                }
            }
        }

        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                callback,
                Looper.getMainLooper()
            )
        } catch (e: SecurityException) {
            Log.e(TAG, "Security exception", e)
            close(e)
        }

        awaitClose {
            fusedLocationClient.removeLocationUpdates(callback)
        }
    }
}
