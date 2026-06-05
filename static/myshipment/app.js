// App Logic
document.addEventListener('DOMContentLoaded', () => {
    // 1. Tab Routing
    const navItems = document.querySelectorAll('.nav-item');
    const viewSections = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            // Update active nav
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            // Update active section
            const target = item.getAttribute('data-target');
            viewSections.forEach(sec => sec.classList.remove('active'));
            document.getElementById(target).classList.add('active');
        });
    });

    // 2. Chat Widget Toggle
    const chatToggle = document.getElementById('chat-toggle');
    const chatWindow = document.getElementById('chat-window');
    const chatClose = document.getElementById('chat-close');

    chatToggle.addEventListener('click', () => {
        chatWindow.style.display = chatWindow.style.display === 'none' ? 'flex' : 'none';
    });

    chatClose.addEventListener('click', () => {
        chatWindow.style.display = 'none';
    });

    // 3. Mock Data for Visibility - Shipment List
    const mockShipments = [
        { id: 'SHP-2023-001', po: 'PO-99102', lane: 'Shanghai ➔ Los Angeles', mode: 'Ocean', eta: 'Oct 15, 2026', status: 'In Transit', statusCode: 'transit' },
        { id: 'SHP-2023-002', po: 'PO-99105', lane: 'Shenzhen ➔ New York', mode: 'Ocean', eta: 'Oct 12, 2026', status: 'Customs Hold', statusCode: 'exception' },
        { id: 'SHP-2023-003', po: 'PO-99110', lane: 'Frankfurt ➔ Chicago', mode: 'Air', eta: 'Oct 05, 2026', status: 'Delivered', statusCode: 'delivered' },
        { id: 'SHP-2023-004', po: 'PO-99118', lane: 'Ho Chi Minh ➔ Seattle', mode: 'Ocean', eta: 'Oct 20, 2026', status: 'Booked', statusCode: 'open' },
        { id: 'SHP-2023-005', po: 'PO-99120', lane: 'Mumbai ➔ London', mode: 'Ocean', eta: 'Oct 25, 2026', status: 'Booked', statusCode: 'open' },
        { id: 'SHP-2023-006', po: 'PO-99122', lane: 'Paris ➔ New York', mode: 'Air', eta: 'Oct 06, 2026', status: 'In Transit', statusCode: 'transit' }
    ];

    const tableBody = document.querySelector('#shipment-table tbody');
    mockShipments.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.id}</strong></td>
            <td>${s.po}</td>
            <td>${s.lane}</td>
            <td>${s.mode}</td>
            <td>${s.eta}</td>
            <td><span class="badge ${s.statusCode}">${s.status}</span></td>
            <td><button class="btn btn-primary btn-sm" onclick="openShipmentModal('${s.id}')">View</button></td>
        `;
        tableBody.appendChild(tr);
    });

    // 4. Modal logic
    const modal = document.getElementById('shipment-modal');
    const closeModalBtn = document.querySelector('.close-modal');

    window.openShipmentModal = (id) => {
        document.getElementById('modal-title').textContent = `Shipment Detail: ${id}`;
        modal.style.display = 'flex';
    };

    closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // 5. Mock Data for Exceptions
    const mockExceptions = [
        { id: 'SHP-2023-002', issue: 'Customs Hold', severity: 'High', milestone: 'Dest Port', delay: '48h', status: 'In Progress', owner: 'Jane Buyer' },
        { id: 'SHP-2023-018', issue: 'Missing Docs', severity: 'Medium', milestone: 'Origin Port', delay: '24h', status: 'Open', owner: 'Unassigned' },
        { id: 'SHP-2023-024', issue: 'Vessel Delay', severity: 'Low', milestone: 'In Transit', delay: '12h', status: 'Closed', owner: 'System' },
    ];

    const excTableBody = document.querySelector('#exception-table tbody');
    if (excTableBody) {
        mockExceptions.forEach(e => {
            const tr = document.createElement('tr');
            const sevColor = e.severity === 'High' ? 'color: #EF4444; font-weight: bold;' : (e.severity === 'Medium' ? 'color: #F59E0B;' : 'color: var(--text-muted);');
            tr.innerHTML = `
                <td><strong>${e.id}</strong></td>
                <td>${e.issue}</td>
                <td style="${sevColor}">${e.severity}</td>
                <td>${e.milestone}</td>
                <td>${e.delay}</td>
                <td>
                    <select class="status-select" style="padding:0.25rem; border-radius:4px; border:1px solid var(--border);">
                        <option ${e.status==='Open'?'selected':''}>Open</option>
                        <option ${e.status==='In Progress'?'selected':''}>In Progress</option>
                        <option ${e.status==='Closed'?'selected':''}>Closed</option>
                    </select>
                    <br><small style="color:var(--text-muted);">${e.owner}</small>
                </td>
            `;
            excTableBody.appendChild(tr);
        });
    }

    // 6. Chart.js Initialization
    const initCharts = () => {
        // Analytics Charts
        const volCtx = document.getElementById('volumeChart');
        if (volCtx) {
            new Chart(volCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{ label: 'Shipments', data: [65, 59, 80, 81, 56, 142], borderColor: '#4F46E5', tension: 0.1, fill: false }]
                },
                options: { maintainAspectRatio: false }
            });
        }

        const carrCtx = document.getElementById('carrierChart');
        if (carrCtx) {
            new Chart(carrCtx, {
                type: 'bar',
                data: {
                    labels: ['Maersk', 'MSC', 'CMA CGM', 'Hapag-Lloyd'],
                    datasets: [{ label: 'OTD %', data: [92, 88, 85, 90], backgroundColor: '#10B981' }]
                },
                options: { maintainAspectRatio: false, scales: { y: { min: 50, max: 100 } } }
            });
        }

        const spendCtx = document.getElementById('spendChart');
        if (spendCtx) {
            new Chart(spendCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Ocean', 'Air', 'Road'],
                    datasets: [{ data: [60, 30, 10], backgroundColor: ['#4F46E5', '#F59E0B', '#10B981'] }]
                }
            });
        }

        // Sustainability Chart
        const emissCtx = document.getElementById('emissionsChart');
        if (emissCtx) {
            new Chart(emissCtx, {
                type: 'pie',
                data: {
                    labels: ['Ocean', 'Air', 'Road'],
                    datasets: [{ data: [300, 800, 145], backgroundColor: ['#4F46E5', '#F59E0B', '#10B981'] }]
                }
            });
        }
    };
    initCharts();

});
