

function useMyLocation() {
    if (!navigator.geolocation) {
        showError('Your browser does not support geolocation. Please use city search instead.');
        return;
    }

    showLoading(true);

    navigator.geolocation.getCurrentPosition(
        function(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            fetch(`/api/nearest-city?lat=${lat}&lon=${lon}`)
                .then(response => response.json())
                .then(data => {
                    showLoading(false);
                    const cityName = data.city ? data.city.name : null;
                    loadCoordinatesData(lat, lon, cityName);
                })
                .catch(() => {
                    showLoading(false);
                    loadCoordinatesData(lat, lon, null);
                });
        },
        function(error) {
            showLoading(false);
            let message = '';

            switch (error.code) {
                case error.PERMISSION_DENIED:
                    message = 'Location permission denied. Please allow location access or use city search.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = 'Location information is unavailable. Please use city search instead.';
                    break;
                case error.TIMEOUT:
                    message = 'Location request timed out. Please try again or use city search.';
                    break;
                default:
                    message = 'An unknown error occurred while getting your location.';
            }

            showError(message);
        },
        {
            enableHighAccuracy: false,
            timeout: 10000,
            maximumAge: 300000 // 5 minutes cache
        }
    );
}