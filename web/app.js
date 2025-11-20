const FUSION_API = 'http://localhost:8002';

let refreshInterval;

async function fetchStats() {
    try {
        const response = await fetch(`${FUSION_API}/stats`);
        if (!response.ok) throw new Error('Error obteniendo estadísticas');
        
        const data = await response.json();
        
        // Actualizar total de alertas
        document.getElementById('total-alerts').textContent = data.total_alerts || 0;
        
        // Actualizar última alerta
        if (data.last_alert) {
            const date = new Date(data.last_alert);
            document.getElementById('last-alert').textContent = 
                date.toLocaleTimeString('es-ES');
        } else {
            document.getElementById('last-alert').textContent = 'N/A';
        }
        
        // Actualizar estadísticas de clases
        const classStatsDiv = document.getElementById('class-stats');
        if (Object.keys(data.class_counts || {}).length > 0) {
            let html = '<div class="stats-grid">';
            for (const [className, count] of Object.entries(data.class_counts)) {
                html += `
                    <div class="stat-item">
                        <div class="stat-value">${count}</div>
                        <div class="stat-label">${className}</div>
                    </div>
                `;
            }
            html += '</div>';
            classStatsDiv.innerHTML = html;
        } else {
            classStatsDiv.innerHTML = '<div class="loading">No hay datos</div>';
        }
        
    } catch (error) {
        console.error('Error obteniendo estadísticas:', error);
        document.getElementById('status').textContent = 'Desconectado';
        document.getElementById('status').className = 'status inactive';
    }
}

async function fetchAlerts() {
    try {
        const response = await fetch(`${FUSION_API}/alerts?limit=50`);
        if (!response.ok) throw new Error('Error obteniendo alertas');
        
        const data = await response.json();
        const alertsContainer = document.getElementById('alerts-container');
        
        if (data.alerts && data.alerts.length > 0) {
            let html = '';
            data.alerts.reverse().forEach(alert => {
                const date = new Date(alert.timestamp);
                const detections = alert.detections || [];
                
                // Agrupar detecciones por clase
                const classGroups = {};
                detections.forEach(det => {
                    const className = det.class_name || 'unknown';
                    classGroups[className] = (classGroups[className] || 0) + 1;
                });
                
                html += `
                    <div class="alert-item">
                        <div class="alert-header">
                            <strong>Alerta #${alert.count || 'N/A'}</strong>
                            <span class="alert-time">${date.toLocaleString('es-ES')}</span>
                        </div>
                        <div class="alert-detections">
                            ${Object.entries(classGroups).map(([className, count]) => 
                                `<span class="detection-badge">${className}: ${count}</span>`
                            ).join('')}
                        </div>
                    </div>
                `;
            });
            
            alertsContainer.innerHTML = html;
        } else {
            alertsContainer.innerHTML = '<div class="loading">No hay alertas registradas</div>';
        }
        
        // Actualizar estado
        document.getElementById('status').textContent = 'Conectado';
        document.getElementById('status').className = 'status active';
        
    } catch (error) {
        console.error('Error obteniendo alertas:', error);
        const alertsContainer = document.getElementById('alerts-container');
        alertsContainer.innerHTML = `
            <div class="error">
                Error conectando con el servidor. Verifique que el servicio Fusion esté ejecutándose.
            </div>
        `;
        document.getElementById('status').textContent = 'Desconectado';
        document.getElementById('status').className = 'status inactive';
    }
}

async function loadDashboard() {
    await Promise.all([fetchStats(), fetchAlerts()]);
}

// Cargar dashboard al inicio
loadDashboard();

// Actualizar cada 5 segundos
refreshInterval = setInterval(loadDashboard, 5000);

// Limpiar intervalo al cerrar
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

