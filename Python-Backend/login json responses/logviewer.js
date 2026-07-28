let allRows = [];

async function loadData() {
    try {
        const response = await fetch('log.json');
        const data = await response.json();
        allRows = data.rows;
        updateSummary(allRows);
        renderTable(allRows);
    } catch (error) {
        document.getElementById('tableBody').innerHTML =
            '<tr><td colspan="7" class="no-results">Could not load log.json. Make sure it is in the same folder as this page.</td></tr>';
        console.error(error);
    }
}

function updateSummary(rows) {
    const total = rows.length;
    const success = rows.filter(r => r[5] === 'success').length;
    const failed = rows.filter(r => r[5] === 'failed').length;
    const rate = total > 0 ? ((success / total) * 100).toFixed(1) + '%' : '-';

    document.getElementById('totalCount').textContent = total;
    document.getElementById('successCount').textContent = success;
    document.getElementById('failedCount').textContent = failed;
    document.getElementById('successRate').textContent = rate;
}

function renderTable(rows) {
    const tableBody = document.getElementById('tableBody');

    if (rows.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="no-results">No matching requests found</td></tr>';
        return;
    }

    tableBody.innerHTML = rows.map(row => {
        const [id, name, email, timestamp, request, status, playbookId, playbookUrl] = row;
        const statusClass = status === 'success' ? 'status-success' : 'status-failed';
        const shortRequest = request.length > 60 ? request.slice(0, 60) + '...' : request;
        const playbookCell = (status === 'success' && playbookUrl)
            ? `<a class="playbook-link" href="${playbookUrl.replace(/"/g, '')}" target="_blank">View</a>`
            : '-';

        return `
            <tr>
                <td>${id}</td>
                <td>${escapeHtml(name)}</td>
                <td>${escapeHtml(email)}</td>
                <td>${timestamp}</td>
                <td class="request-cell" onclick="showFullRequest(${id})" title="Click to view full request">${escapeHtml(shortRequest)}</td>
                <td><span class="status-badge ${statusClass}">${status}</span></td>
                <td>${playbookCell}</td>
            </tr>
        `;
    }).join('');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showFullRequest(id) {
    const row = allRows.find(r => r[0] === id);
    if (row) {
        document.getElementById('modalText').textContent = row[4];
        document.getElementById('modalOverlay').classList.add('active');
    }
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
}

function applyFilters() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    const statusValue = document.getElementById('statusFilter').value;

    const filtered = allRows.filter(row => {
        const [id, name, email, timestamp, request, status] = row;

        const matchesSearch = !searchTerm ||
            name.toLowerCase().includes(searchTerm) ||
            email.toLowerCase().includes(searchTerm) ||
            request.toLowerCase().includes(searchTerm);

        const matchesStatus = statusValue === 'all' || status === statusValue;

        return matchesSearch && matchesStatus;
    });

    renderTable(filtered);
}

document.getElementById('searchBox').addEventListener('input', applyFilters);
document.getElementById('statusFilter').addEventListener('change', applyFilters);
document.getElementById('modalOverlay').addEventListener('click', function (e) {
    if (e.target === this) closeModal();
});

loadData();