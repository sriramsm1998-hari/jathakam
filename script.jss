function getLocation() {

    if (!navigator.geolocation) {
        alert("Geolocation not supported");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function(position) {

            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            calculateSunrise(lat, lng);

        },
        function(error) {
            alert("Location access denied");
        }
    );
}

async function calculateSunrise(lat, lng) {

    const date =
        document.getElementById("date").value;

    if(!date){
        alert("Select date");
        return;
    }

    const url =
`https://api.sunrise-sunset.org/json?lat=${lat}&lng=${lng}&date=${date}&formatted=0`;

    const response = await fetch(url);

    const data = await response.json();

    const sunriseUTC = data.results.sunrise;

    const sunriseLocal =
        new Date(sunriseUTC).toLocaleTimeString(
            "en-IN",
            {
                hour:'2-digit',
                minute:'2-digit',
                second:'2-digit'
            }
        );

    document.getElementById("result").innerHTML =
        `Sunrise: ${sunriseLocal}`;
}
