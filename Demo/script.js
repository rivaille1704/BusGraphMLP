const map = L.map('map', {zoomControl: false}).setView([21.0285, 105.8542], 13);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {attribution: '&copy; CARTO'}).addTo(map);

const now = new Date();
document.getElementById('time-picker').value = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

let mode = null, sPos = null, ePos = null;
let sMark, eMark;
let routeLayer = L.layerGroup().addTo(map);
let networkLayer = L.layerGroup();

fetch('http://127.0.0.1:5000/get_all_stops')
    .then(r => r.json())
    .then(stops => {
        stops.forEach(s => {
            L.circleMarker([s.lat, s.lon], {
                radius: 2, color: 'transparent', fillColor: '#2980b9', fillOpacity: 0.5
            }).addTo(networkLayer).bindPopup(s.name);
        });
    });

function toggleNetwork(btn) {
    if (map.hasLayer(networkLayer)) {
        map.removeLayer(networkLayer);
        btn.classList.remove('active');
    } else {
        map.addLayer(networkLayer);
        btn.classList.add('active');
    }
}

function pick(m) {
    mode = m;
    document.getElementById('map').classList.add('picking');
    document.querySelectorAll('.input-row').forEach(e => e.classList.remove('active'));
    document.getElementById(`btn-${m}`).classList.add('active');
}

map.on('click', e => {
    if(!mode) return;
    if(mode === 'start') {
        sPos = e.latlng;
        if(sMark) map.removeLayer(sMark);
        sMark = L.marker(sPos).addTo(map);
        document.getElementById('txt-start').innerText = "Đã chọn điểm đi";
    } else {
        ePos = e.latlng;
        if(eMark) map.removeLayer(eMark);
        eMark = L.marker(ePos).addTo(map);
        document.getElementById('txt-end').innerText = "Đã chọn điểm đến";
    }
    mode = null;
    document.getElementById('map').classList.remove('picking');
    document.querySelectorAll('.input-row').forEach(e => e.classList.remove('active'));
    if(sPos && ePos) document.getElementById('btn-find').disabled = false;
});

async function findRoute() {
    const btn = document.getElementById('btn-find');
    btn.innerText = "Calculating..."; btn.disabled = true;
    routeLayer.clearLayers();
    document.getElementById('result').style.display = 'none';

    try {
        const res = await fetch('http://127.0.0.1:5000/find_route', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                start: {lat: sPos.lat, lon: sPos.lng},
                end: {lat: ePos.lat, lon: ePos.lng},
                time: document.getElementById('time-picker').value
            })
        });
        const data = await res.json();
        if(data.status === 'error') { alert(data.message); return; }
        render(data);
    } catch(e) { console.error(e); alert("Lỗi server hoặc chưa chạy backend!"); }
    finally { btn.innerText = "TÌM LỘ TRÌNH"; btn.disabled = false; }
}

function render(data) {
    document.getElementById('result').style.display = 'block';
    document.getElementById('total-dur').innerText = data.total_duration + " phút";
    const list = document.getElementById('steps');
    list.innerHTML = '';

    data.segments.forEach(seg => {
        let color = '#2980b9', dash = null;
        if(seg.type === 'walk') { color = '#27ae60'; dash = '5, 10'; }
        if(seg.type === 'transfer') { color = '#f39c12'; dash = '3, 6'; }
        
        const line = L.polyline(seg.coords, {color, weight: 5, opacity: 0.8, dashArray: dash}).addTo(routeLayer);
        if(seg.type === 'bus') map.fitBounds(line.getBounds());

        const div = document.createElement('div');
        div.className = `step ${seg.type}`;
        
        div.innerHTML = `
            <div class="step-head">${seg.desc}</div>
            <div class="step-sub">${seg.sub}</div>
        `;
        list.appendChild(div);
    });
}