

let currentCity = 'Delhi';
let currentLat = null;
let currentLon = null;
let currentData = null;
let eventSource = null;
let autoRefreshTimer = null;

function showLoading(show) {
    showLiquidLoading(show);
}

function showError(message) {
    const errorEl = document.getElementById('errorMessage');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        setTimeout(() => { errorEl.style.display = 'none'; }, 5000);
    }
    showToast(message, 'error');
}

function showNoData(show) {
    const el = document.getElementById('noDataMessage');
    if (el) {
        el.style.display = show ? 'block' : 'none';
    }
}

function updateStatusBar(status) {
    const dot = document.querySelector('.status-dot');
    const text = document.querySelector('.status-text');
    const message = document.getElementById('statusMessage');

    if (dot) {
        dot.className = 'status-dot ' + (status.status || 'no_data');
    }
    if (text) {
        text.textContent = status.label || '🔴 NO DATA AVAILABLE';
    }
    if (message) {
        message.textContent = status.message || '';
    }
}

function getFlagEmoji(countryCode) {
    if (!countryCode) return '🌍';
    const codePoints = countryCode
        .toUpperCase()
        .split('')
        .map(char => 127397 + char.charCodeAt(0));
    return String.fromCodePoint(...codePoints);
}

function setupCitySearch() {
    const searchInput = document.getElementById('citySearch');
    const resultsDiv = document.getElementById('searchResults');

    if (!searchInput || !resultsDiv) return;

    let debounceTimer;

    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 2) {
            resultsDiv.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/search-city?q=${encodeURIComponent(query)}&limit=10`)
                .then(response => response.json())
                .then(data => {
                    resultsDiv.innerHTML = '';
                    if (data.results && data.results.length > 0) {
                        data.results.forEach((location, index) => {
                            const item = document.createElement('div');
                            item.className = 'search-result-item';
                            item.style.animation = `fadeInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1) ${index * 0.05}s both`;

                            const flag = getFlagEmoji(location.country_code);
                            const displayName = location.admin1 && location.admin1 !== location.name
                                ? `${location.name}, ${location.admin1}`
                                : location.name;

                            item.innerHTML = `
                                <span class="flag">${flag}</span>
                                <span class="result-name">${displayName}</span>
                                <span class="result-country">${location.country || ''}</span>
                            `;

                            item.addEventListener('click', () => {
                                searchInput.value = location.name;
                                resultsDiv.style.display = 'none';
                                loadCoordinatesData(
                                    location.latitude,
                                    location.longitude,
                                    location.name
                                );
                            });
                            resultsDiv.appendChild(item);
                        });
                        resultsDiv.style.display = 'block';
                    } else {
                        resultsDiv.style.display = 'none';
                    }
                })
                .catch(() => {
                    resultsDiv.style.display = 'none';
                });
        }, 300);
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-container')) {
            resultsDiv.style.display = 'none';
        }
    });
}

function loadCityData(city) {
    currentCity = city;
    currentLat = null;
    currentLon = null;

    const locationEl = document.getElementById('selectedLocation');
    if (locationEl) {
        locationEl.textContent = city;
    }

    fetchCurrentAirQuality(`city=${encodeURIComponent(city)}`);
}

function loadCoordinatesData(lat, lon, cityName) {
    currentLat = lat;
    currentLon = lon;
    if (cityName) {
        currentCity = cityName;
        const locationEl = document.getElementById('selectedLocation');
        if (locationEl) {
            locationEl.textContent = `${cityName} (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
        }
    }

    fetchCurrentAirQuality(`lat=${lat}&lon=${lon}&city=${encodeURIComponent(cityName || '')}`);
}

function fetchCurrentAirQuality(params) {
    showLoading(true);
    showNoData(false);

    const cardsGrid = document.getElementById('cardsGrid');
    const metadata = document.getElementById('dataMetadata');
    const liveDataCard = document.getElementById('liveDataCard');
    if (cardsGrid) cardsGrid.style.display = 'none';
    if (metadata) metadata.style.display = 'none';
    if (liveDataCard) liveDataCard.style.display = 'none';

    fetch(`/api/current-air-quality?${params}`)
        .then(response => response.json())
        .then(data => {
            showLoading(false);

            if (data.error) {
                showError(data.error);
                showNoData(true);
                return;
            }

            currentData = data;
            displayDashboardData(data);
            displayLiveDataTable(data);

            fetch('/api/data-status')
                .then(r => r.json())
                .then(status => updateStatusBar(status))
                .catch(() => {});

            startLiveStreaming();
        })
        .catch(error => {
            showLoading(false);
            showError('Failed to fetch air quality data. Please try again.');
            showNoData(true);
        });
}

let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

function startLiveStreaming() {
    if (eventSource) {
        eventSource.close();
    }

    if (!currentLat || !currentLon) return;

    const params = `lat=${currentLat}&lon=${currentLon}&city=${encodeURIComponent(currentCity)}`;
    eventSource = new EventSource(`/api/stream?${params}`);

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'air_quality') {
                currentData = data.data;
                displayDashboardData(data.data, true);
                displayLiveDataTable(data.data);

                const liveBadge = document.getElementById('liveBadge');
                if (liveBadge) {
                    const time = new Date(data.timestamp);
                    liveBadge.innerHTML = `<span class="live-dot"></span> LIVE · Updated ${time.toLocaleTimeString()}`;
                }
            } else if (data.type === 'error') {
                console.warn('Live stream error:', data.error);
            }
        } catch (e) {
            console.error('Failed to parse SSE data:', e);
        }
    };

    eventSource.onerror = function() {
        reconnectAttempts++;
        if (reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
            console.log('Max reconnection attempts reached, stopping live stream');
            eventSource.close();
            eventSource = null;
            const liveBadge = document.getElementById('liveBadge');
            if (liveBadge) {
                liveBadge.innerHTML = '<span class="live-dot" style="background: var(--danger);"></span> LIVE OFFLINE';
            }
            return;
        }
        console.log(`Live stream connection lost, reconnecting... (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
    };
}

function displayDashboardData(data, isLiveUpdate = false) {
    const cardsGrid = document.getElementById('cardsGrid');
    const metadata = document.getElementById('dataMetadata');
    if (!cardsGrid) return;

    cardsGrid.style.display = 'grid';

    const aqiValue = document.getElementById('aqiValue');
    const aqiCategory = document.getElementById('aqiCategory');
    const aqiNote = document.getElementById('aqiNote');

    if (data.aqi && data.aqi.value !== null) {
        if (isLiveUpdate) {
            smoothValueUpdate(aqiValue, data.aqi.value, 0);
        } else {
            animateCountUp(aqiValue, data.aqi.value, 1000, 0);
        }
        aqiCategory.textContent = data.aqi.category;
        aqiNote.textContent = data.aqi.note || '';
        setAQITheme(data.aqi.value);
    } else {
        aqiValue.textContent = '--';
        aqiCategory.textContent = data.aqi ? data.aqi.category : 'Insufficient data';
        aqiNote.textContent = data.aqi ? data.aqi.note : '';
        setAQITheme(null);
    }

    const pollutantMap = {
        'pm2_5': 'pm25',
        'pm10': 'pm10',
        'nitrogen_dioxide': 'no2',
        'sulphur_dioxide': 'so2',
        'carbon_monoxide': 'co',
        'ozone': 'o3'
    };

    const safeLimits = {
        'pm2_5': 60,
        'pm10': 100,
        'nitrogen_dioxide': 80,
        'sulphur_dioxide': 80,
        'carbon_monoxide': 2000,
        'ozone': 100
    };

    Object.values(pollutantMap).forEach(prefix => {
        const card = document.getElementById(`${prefix}Card`);
        if (card) card.style.display = 'none';
    });

    if (data.pollutants) {
        for (const [key, info] of Object.entries(data.pollutants)) {
            const prefix = pollutantMap[key];
            if (prefix) {
                const card = document.getElementById(`${prefix}Card`);
                const valueEl = document.getElementById(`${prefix}Value`);
                const barFill = document.getElementById(`${prefix}BarFill`);

                if (card) card.style.display = 'block';
                if (valueEl) {
                    if (isLiveUpdate) {
                        smoothValueUpdate(valueEl, info.value, 1);
                    } else {
                        animateCountUp(valueEl, info.value, 1000, 1);
                    }
                }

                if (barFill && info.value !== null) {
                    const limit = safeLimits[key] || 100;
                    const percentage = Math.min((info.value / limit) * 100, 100);
                    barFill.style.width = `${percentage}%`;
                }
            }
        }
    }

    if (metadata) {
        metadata.style.display = 'block';
        document.getElementById('lastUpdated').textContent = data.timestamp || '--';
        document.getElementById('dataSource').textContent = data.source || '--';
        document.getElementById('dataLatitude').textContent = data.latitude || '--';
        document.getElementById('dataLongitude').textContent = data.longitude || '--';
    }
}

function displayLiveDataTable(data) {
    const liveDataCard = document.getElementById('liveDataCard');
    const tableBody = document.getElementById('liveDataTableBody');
    if (!liveDataCard || !tableBody) return;

    liveDataCard.style.display = 'block';
    tableBody.innerHTML = '';

    if (data.pollutants) {
        for (const [key, info] of Object.entries(data.pollutants)) {
            const row = document.createElement('tr');
            row.style.animation = `fadeInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1)`;
            row.innerHTML = `
                <td>${info.name}</td>
                <td>${info.value !== null ? info.value.toFixed(1) : '--'}</td>
                <td>${info.unit}</td>
                <td>${data.timestamp || '--'}</td>
                <td>Open-Meteo grid cell</td>
                <td>${data.source || '--'}</td>
            `;
            tableBody.appendChild(row);
        }
    }
}

function syncData() {
    const syncBtn = document.getElementById('syncBtn');
    if (syncBtn) {
        syncBtn.disabled = true;
        syncBtn.textContent = '⏳ Syncing...';
    }

    let params = `city=${encodeURIComponent(currentCity)}`;
    if (currentLat && currentLon) {
        params = `lat=${currentLat}&lon=${currentLon}&city=${encodeURIComponent(currentCity)}`;
    }

    fetch(`/api/sync?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
            } else {
                showToast(`✅ ${data.message}`, 'success');
                if (currentLat && currentLon) {
                    loadCoordinatesData(currentLat, currentLon, currentCity);
                } else {
                    loadCityData(currentCity);
                }
            }
        })
        .catch(error => {
            showError('Failed to synchronize data. Please try again.');
        })
        .finally(() => {
            if (syncBtn) {
                syncBtn.disabled = false;
                syncBtn.textContent = '🔄 Synchronize Data';
            }
        });
}

function loadHistoricalData() {
    const city = document.getElementById('histCity').value;
    const range = document.getElementById('histRange').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!city) {
        showError('Please select a city.');
        return;
    }

    showLoading(true);
    showNoData(false);

    let params = `city=${encodeURIComponent(city)}&range=${range}`;
    if (range === 'custom' && startDate && endDate) {
        params += `&start_date=${startDate}&end_date=${endDate}`;
    }

    fetch(`/api/historical-data?${params}`)
        .then(response => response.json())
        .then(data => {
            showLoading(false);

            if (data.error) {
                showError(data.error);
                showNoData(true);
                return;
            }

            if (!data.has_data) {
                showNoData(true);
                return;
            }

            const chartsContainer = document.getElementById('chartsContainer');
            chartsContainer.style.display = 'block';

            if (data.trend_chart) {
                Plotly.newPlot('trendChart', data.trend_chart.data, {
                    ...data.trend_chart.layout,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#94a3b8' },
                    xaxis: { ...data.trend_chart.layout.xaxis, gridcolor: 'rgba(255,255,255,0.05)' },
                    yaxis: { ...data.trend_chart.layout.yaxis, gridcolor: 'rgba(255,255,255,0.05)' }
                });
            }

            if (data.correlation_chart) {
                Plotly.newPlot('correlationChart', data.correlation_chart.data, {
                    ...data.correlation_chart.layout,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#94a3b8' }
                });
            }

            if (data.distribution_chart) {
                Plotly.newPlot('distributionChart', data.distribution_chart.data, {
                    ...data.distribution_chart.layout,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#94a3b8' },
                    xaxis: { ...data.distribution_chart.layout.xaxis, gridcolor: 'rgba(255,255,255,0.05)' },
                    yaxis: { ...data.distribution_chart.layout.yaxis, gridcolor: 'rgba(255,255,255,0.05)' }
                });
            }

            displayExtremes(data.extremes);
        })
        .catch(error => {
            showLoading(false);
            showError('Failed to load historical data.');
        });
}

function displayExtremes(extremes) {
    const grid = document.getElementById('extremesGrid');
    if (!grid || !extremes) return;

    grid.innerHTML = '';

    const items = [
        { label: 'Highest PM2.5', value: extremes.highest_pm25, date: extremes.highest_pm25_date },
        { label: 'Highest PM10', value: extremes.highest_pm10, date: extremes.highest_pm10_date },
        { label: 'Lowest PM2.5', value: extremes.lowest_pm25, date: extremes.lowest_pm25_date },
        { label: 'Lowest PM10', value: extremes.lowest_pm10, date: extremes.lowest_pm10_date }
    ];

    items.forEach((item, index) => {
        if (item.value !== null) {
            const div = document.createElement('div');
            div.className = 'extreme-item';
            div.style.animation = `fadeInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1) ${index * 0.1}s both`;
            div.innerHTML = `
                <div class="extreme-label">${item.label}</div>
                <div class="extreme-value">${item.value.toFixed(1)} µg/m³</div>
                <div class="extreme-date">${item.date || ''}</div>
            `;
            grid.appendChild(div);
        }
    });
}

function generatePrediction() {
    const city = document.getElementById('predCity').value;
    const period = document.getElementById('predPeriod').value;

    if (!city) {
        showError('Please select a city.');
        return;
    }

    showLoading(true);
    showNoData(false);

    const predictionResults = document.getElementById('predictionResults');
    if (predictionResults) predictionResults.style.display = 'none';

    fetch(`/api/predict?city=${encodeURIComponent(city)}&period=${period}`)
        .then(response => response.json())
        .then(data => {
            showLoading(false);

            if (data.error) {
                showError(data.error);
                showNoData(true);
                return;
            }

            if (predictionResults) predictionResults.style.display = 'block';

            const predictedValue = document.getElementById('predictedValue');
            if (data.prediction) {
                animateCountUp(predictedValue, data.prediction, 1000, 1);
            } else {
                predictedValue.textContent = '--';
            }
            document.getElementById('predictionNote').textContent = data.note || '';

            const tableBody = document.getElementById('metricsTableBody');
            tableBody.innerHTML = '';
            if (data.metrics) {
                data.metrics.forEach(metric => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${metric.model_name}</td>
                        <td>${metric.mae ? metric.mae.toFixed(2) : '--'}</td>
                        <td>${metric.rmse ? metric.rmse.toFixed(2) : '--'}</td>
                        <td>${metric.r2 ? metric.r2.toFixed(4) : '--'}</td>
                        <td>${metric.best ? '⭐ Best' : ''}</td>
                    `;
                    tableBody.appendChild(row);
                });
            }

            if (data.actual_vs_predicted_chart) {
                Plotly.newPlot('actualVsPredictedChart', data.actual_vs_predicted_chart.data, {
                    ...data.actual_vs_predicted_chart.layout,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#94a3b8' }
                });
            }

            if (data.feature_importance_chart) {
                Plotly.newPlot('featureImportanceChart', data.feature_importance_chart.data, {
                    ...data.feature_importance_chart.layout,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#94a3b8' }
                });
            }
        })
        .catch(error => {
            showLoading(false);
            showError('Failed to generate prediction.');
        });
}

function explainCurrentAirQuality() {
    callAI('explain_current');
}

function explainPrediction() {
    callAI('explain_prediction');
}

function giveHealthPrecautions() {
    callAI('health_precautions');
}

function callAI(action) {
    showLoading(true);

    let params = `action=${action}&city=${encodeURIComponent(currentCity)}`;
    if (currentLat && currentLon) {
        params += `&lat=${currentLat}&lon=${currentLon}`;
    }

    fetch(`/api/ai?${params}`)
        .then(response => response.json())
        .then(data => {
            showLoading(false);

            if (data.error) {
                showError(data.error);
                return;
            }

            const aiResponse = document.getElementById('aiResponse');
            const aiContent = document.getElementById('aiResponseContent');
            if (aiResponse && aiContent) {
                aiResponse.style.display = 'block';
                aiContent.textContent = data.response || 'No response from AI.';
                fadeInUp(aiResponse);
            }
        })
        .catch(error => {
            showLoading(false);
            showError('Failed to get AI response. Please check your API key.');
        });
}

function setupNavToggle() {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');

    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('show');
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    setupCitySearch();
    setupNavToggle();

    const rangeSelect = document.getElementById('histRange');
    if (rangeSelect) {
        rangeSelect.addEventListener('change', function() {
            const customGroup = document.getElementById('customRangeGroup');
            if (customGroup) {
                customGroup.style.display = this.value === 'custom' ? 'flex' : 'none';
            }
        });
    }

    const dashboardInit = document.getElementById('dashboardInit');
    if (dashboardInit) {
        loadCityData('Delhi');
    }
});