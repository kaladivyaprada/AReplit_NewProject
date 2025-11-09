let map;
let drawnItems;
let currentGeometry = null;
let currentCenter = null;
let regionsData = null;
let cropData = null;
let currentResults = null;
let pieChart = null;
let barChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    loadRegionsData();
    loadCropData();
    setupEventListeners();
    setDefaultDates();
    checkHealth();
});

function initializeMap() {
    map = L.map('map').setView([20.5937, 78.9629], 5);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    
    const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
            polygon: {
                shapeOptions: {
                    color: '#2ecc71',
                    weight: 3
                }
            },
            rectangle: {
                shapeOptions: {
                    color: '#2ecc71',
                    weight: 3
                }
            },
            circle: false,
            circlemarker: false,
            marker: false,
            polyline: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
    });
    
    map.addControl(drawControl);
    
    map.on(L.Draw.Event.CREATED, function(e) {
        drawnItems.clearLayers();
        const layer = e.layer;
        drawnItems.addLayer(layer);
        
        currentGeometry = layer.toGeoJSON().geometry;
        currentCenter = layer.getBounds().getCenter();
        currentCenter = [currentCenter.lat, currentCenter.lng];
        
        document.getElementById('analyzeBtn').disabled = false;
        updateStatus('Region selected on map', 'success');
    });
    
    map.on(L.Draw.Event.DELETED, function() {
        currentGeometry = null;
        currentCenter = null;
        document.getElementById('analyzeBtn').disabled = true;
    });
}

async function loadRegionsData() {
    try {
        const response = await fetch('/api/regions');
        regionsData = await response.json();
        populateStateDropdown();
    } catch (error) {
        console.error('Error loading regions:', error);
        updateStatus('Error loading regions', 'danger');
    }
}

async function loadCropData() {
    try {
        const response = await fetch('/api/crop-types');
        cropData = await response.json();
    } catch (error) {
        console.error('Error loading crop data:', error);
    }
}

function populateStateDropdown() {
    const stateSelect = document.getElementById('stateSelect');
    regionsData.states.forEach(state => {
        const option = document.createElement('option');
        option.value = state.code;
        option.textContent = state.name;
        option.dataset.center = JSON.stringify(state.center);
        stateSelect.appendChild(option);
    });
}

function setupEventListeners() {
    document.getElementById('stateSelect').addEventListener('change', handleStateChange);
    document.getElementById('districtSelect').addEventListener('change', handleDistrictChange);
    document.getElementById('talukaSelect').addEventListener('change', handleTalukaChange);
    document.getElementById('analyzeBtn').addEventListener('click', analyzeRegion);
    document.getElementById('exportCsvBtn').addEventListener('click', exportCSV);
    document.getElementById('exportGeoJsonBtn').addEventListener('click', exportGeoJSON);
}

function handleStateChange(e) {
    const stateCode = e.target.value;
    const districtSelect = document.getElementById('districtSelect');
    const talukaSelect = document.getElementById('talukaSelect');
    
    districtSelect.innerHTML = '<option value="">Select District...</option>';
    talukaSelect.innerHTML = '<option value="">Select Taluka...</option>';
    talukaSelect.disabled = true;
    
    if (stateCode) {
        const state = regionsData.states.find(s => s.code === stateCode);
        state.districts.forEach(district => {
            const option = document.createElement('option');
            option.value = district.code;
            option.textContent = district.name;
            option.dataset.center = JSON.stringify(district.center);
            option.dataset.talukas = JSON.stringify(district.talukas);
            districtSelect.appendChild(option);
        });
        districtSelect.disabled = false;
        
        const center = JSON.parse(e.target.selectedOptions[0].dataset.center);
        map.setView(center, 7);
    } else {
        districtSelect.disabled = true;
    }
}

function handleDistrictChange(e) {
    const districtCode = e.target.value;
    const talukaSelect = document.getElementById('talukaSelect');
    
    talukaSelect.innerHTML = '<option value="">Select Taluka...</option>';
    
    if (districtCode) {
        const selectedOption = e.target.selectedOptions[0];
        const talukas = JSON.parse(selectedOption.dataset.talukas);
        const center = JSON.parse(selectedOption.dataset.center);
        
        talukas.forEach(taluka => {
            const option = document.createElement('option');
            option.value = taluka;
            option.textContent = taluka;
            talukaSelect.appendChild(option);
        });
        talukaSelect.disabled = false;
        
        map.setView(center, 10);
        
        currentCenter = center;
        currentGeometry = {
            type: 'Point',
            coordinates: [center[1], center[0]]
        };
        document.getElementById('analyzeBtn').disabled = false;
    } else {
        talukaSelect.disabled = true;
    }
}

function handleTalukaChange(e) {
    if (e.target.value) {
        document.getElementById('analyzeBtn').disabled = false;
    }
}

function setDefaultDates() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 90);
    
    document.getElementById('endDate').valueAsDate = endDate;
    document.getElementById('startDate').valueAsDate = startDate;
}

async function analyzeRegion() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const spinner = document.getElementById('analyzeSpinner');
    const progressBar = document.getElementById('progressBar');
    const progressBarInner = progressBar.querySelector('.progress-bar');
    
    analyzeBtn.disabled = true;
    spinner.classList.remove('d-none');
    progressBar.classList.remove('d-none');
    
    updateStatus('Analyzing...', 'warning');
    progressBarInner.style.width = '30%';
    
    const stateName = document.getElementById('stateSelect').selectedOptions[0]?.textContent || 'Unknown';
    const districtName = document.getElementById('districtSelect').selectedOptions[0]?.textContent || '';
    const talukaName = document.getElementById('talukaSelect').value || '';
    
    const regionName = [stateName, districtName, talukaName].filter(x => x).join(' - ');
    
    const payload = {
        geometry: currentGeometry,
        center: currentCenter,
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        region_name: regionName
    };
    
    try {
        progressBarInner.style.width = '60%';
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        progressBarInner.style.width = '90%';
        
        if (!response.ok) {
            throw new Error('Analysis failed');
        }
        
        currentResults = await response.json();
        progressBarInner.style.width = '100%';
        
        displayResults(currentResults);
        updateStatus('Analysis complete', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        updateStatus('Analysis failed', 'danger');
        alert('Error analyzing region. Please try again.');
    } finally {
        setTimeout(() => {
            analyzeBtn.disabled = false;
            spinner.classList.add('d-none');
            progressBar.classList.add('d-none');
            progressBarInner.style.width = '0%';
        }, 500);
    }
}

function displayResults(results) {
    const resultsCard = document.getElementById('resultsCard');
    const resultsContent = document.getElementById('resultsContent');
    
    let html = '';
    
    if (results.demo_mode) {
        html += `<div class="demo-warning">
            <strong>⚠️ Demo Mode</strong><br>
            ${results.warning}
        </div>`;
    }
    
    html += `
        <div class="results-header">
            <h6>${results.region_name}</h6>
            <p>${results.analysis_date}</p>
        </div>
        
        <div class="mb-3">
            <div class="stat-label">Total Area</div>
            <div class="stat-value">${results.total_area_ha.toFixed(2)} hectares</div>
        </div>
        
        <div class="mb-3">
            <div class="stat-label">Dominant Crop</div>
            <div class="stat-value">${results.dominant_crop}</div>
        </div>
        
        <h6 class="mt-3 mb-2">Crop Distribution:</h6>
    `;
    
    for (const [crop, data] of Object.entries(results.crop_distribution)) {
        html += `
            <div class="crop-stat">
                <div>
                    <span class="crop-color" style="background-color: ${data.color}"></span>
                    <span>${crop}</span>
                </div>
                <div>
                    <strong>${data.percentage}%</strong>
                    <small class="text-muted">(${data.area_ha.toFixed(2)} ha)</small>
                </div>
            </div>
        `;
    }
    
    resultsContent.innerHTML = html;
    resultsCard.style.display = 'block';
    
    displayCharts(results);
    addCropLayersToMap(results);
}

function displayCharts(results) {
    const chartPanel = document.getElementById('chartPanel');
    chartPanel.style.display = 'block';
    
    const labels = [];
    const areas = [];
    const percentages = [];
    const colors = [];
    
    for (const [crop, data] of Object.entries(results.crop_distribution)) {
        labels.push(crop);
        areas.push(data.area_ha);
        percentages.push(data.percentage);
        colors.push(data.color);
    }
    
    if (pieChart) pieChart.destroy();
    if (barChart) barChart.destroy();
    
    const pieCtx = document.getElementById('cropPieChart').getContext('2d');
    pieChart = new Chart(pieCtx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: percentages,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Crop Distribution (%)'
                }
            }
        }
    });
    
    const barCtx = document.getElementById('cropBarChart').getContext('2d');
    barChart = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Area (Hectares)',
                data: areas,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Area by Crop Type'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function addCropLayersToMap(results) {
    drawnItems.clearLayers();
    
    if (currentGeometry && currentGeometry.type === 'Polygon') {
        const geoJsonLayer = L.geoJSON(currentGeometry, {
            style: {
                fillColor: results.crop_distribution[results.dominant_crop].color,
                color: '#2ecc71',
                weight: 3,
                fillOpacity: 0.4
            }
        }).addTo(drawnItems);
        
        const bounds = geoJsonLayer.getBounds();
        map.fitBounds(bounds);
    }
}

async function exportCSV() {
    if (!currentResults) return;
    
    try {
        const response = await fetch('/api/export/csv', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                crop_distribution: currentResults.crop_distribution,
                region_name: currentResults.region_name
            })
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentResults.region_name.replace(/\s+/g, '_')}_analysis.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        updateStatus('CSV exported successfully', 'success');
    } catch (error) {
        console.error('Export error:', error);
        updateStatus('Export failed', 'danger');
    }
}

async function exportGeoJSON() {
    if (!currentResults || !currentGeometry) return;
    
    try {
        const response = await fetch('/api/export/geojson', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                geometry: currentGeometry,
                properties: {
                    region: currentResults.region_name,
                    analysis_date: currentResults.analysis_date,
                    dominant_crop: currentResults.dominant_crop,
                    total_area_ha: currentResults.total_area_ha,
                    crop_distribution: currentResults.crop_distribution
                }
            })
        });
        
        const geojson = await response.json();
        const dataStr = JSON.stringify(geojson, null, 2);
        const blob = new Blob([dataStr], {type: 'application/json'});
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentResults.region_name.replace(/\s+/g, '_')}_analysis.geojson`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        updateStatus('GeoJSON exported successfully', 'success');
    } catch (error) {
        console.error('Export error:', error);
        updateStatus('Export failed', 'danger');
    }
}

function updateStatus(message, type) {
    const badge = document.getElementById('statusBadge');
    badge.textContent = message;
    badge.className = 'badge';
    
    if (type === 'success') {
        badge.classList.add('bg-success');
    } else if (type === 'danger') {
        badge.classList.add('bg-danger');
    } else if (type === 'warning') {
        badge.classList.add('bg-warning', 'text-dark');
    } else {
        badge.classList.add('bg-light', 'text-success');
    }
}

async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const health = await response.json();
        console.log('System health:', health);
    } catch (error) {
        console.error('Health check failed:', error);
    }
}
