// State
let quotes = {};
let watchlist = [];
let positions = [];
let orders = [];
let fills = [];

// DOM Elements
const watchlistEl = document.getElementById('watchlist-items');
const positionsEl = document.getElementById('positions-body');
const ordersEl = document.getElementById('orders-body');
const fillsEl = document.getElementById('fills-body');
const pnlSummaryEl = document.getElementById('pnl-summary');

// Initialize
async function init() {
    if (!localStorage.getItem('token')) {
        window.location.href = '/login.html';
        return;
    }

    await loadWatchlist();
    await loadData();
    
    // Refresh loop
    setInterval(loadData, 5000);
}

async function loadWatchlist() {
    watchlist = await API.get('/watchlist/');
    renderWatchlist();
}

async function loadData() {
    const [q, p, o, f, pnl] = await Promise.all([
        API.get('/quotes/'),
        API.get('/paper/positions'),
        API.get('/paper/orders'),
        API.get('/paper/fills'),
        API.get('/paper/pnl')
    ]);

    quotes = q || {};
    positions = p || [];
    orders = (o || []).filter(ord => ord.status === 'PENDING');
    fills = (f || []).sort((a, b) => new Date(b.filled_at) - new Date(a.filled_at));

    renderQuotes();
    renderPositions();
    renderOrders();
    renderFills();
    renderPnL(pnl);
}

function renderWatchlist() {
    watchlistEl.innerHTML = watchlist.map(item => `
        <li class="flex justify-between items-center p-2 bg-gray-700 rounded text-sm group">
            <div class="cursor-pointer" onclick="selectSymbol('${item.symbol_code}', '${item.broker}')">
                <span class="font-bold">${item.symbol_code}</span>
                <span class="text-gray-400 text-xs ml-2">${item.broker} | ${item.exchange}</span>
            </div>
            <div class="flex items-center space-x-2">
                <span id="price-${item.symbol_code}" class="font-mono">--</span>
                <button onclick="removeFromWatchlist('${item.normalized_symbol}')" class="text-red-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">×</button>
            </div>
        </li>
    `).join('');
}

function renderQuotes() {
    for (const symbol in quotes) {
        const el = document.getElementById(`price-${symbol}`);
        if (el) {
            el.textContent = quotes[symbol].last_price.toFixed(2);
        }
    }
}

function renderPositions() {
    positionsEl.innerHTML = positions.map(p => {
        const last = quotes[p.symbol_code]?.last_price || p.average_cost;
        const upnl = (last - p.average_cost) * p.quantity;
        return `
            <tr class="border-t border-gray-700">
                <td class="py-2">${p.normalized_symbol}</td>
                <td class="py-2">${p.quantity}</td>
                <td class="py-2">${p.average_cost.toFixed(2)}</td>
                <td class="py-2">${last.toFixed(2)}</td>
                <td class="py-2 ${upnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${upnl.toFixed(2)}</td>
            </tr>
        `;
    }).join('');
}

function renderOrders() {
    ordersEl.innerHTML = orders.map(o => `
        <tr class="border-t border-gray-700 text-xs">
            <td class="py-2">${o.normalized_symbol}</td>
            <td class="py-2 ${o.action === 'BUY' ? 'text-green-400' : 'text-red-400'}">${o.action}</td>
            <td class="py-2">${o.quantity}</td>
            <td class="py-2">${o.order_type === 'MKT' ? 'Market' : o.price}</td>
            <td class="py-2">${o.status}</td>
            <td class="py-2">
                <button onclick="cancelOrder(${o.id})" class="text-red-500 hover:underline">Cancel</button>
            </td>
        </tr>
    `).join('');
}

function renderFills() {
    fillsEl.innerHTML = fills.slice(0, 10).map(f => `
        <tr class="border-t border-gray-700 text-xs">
            <td class="py-2">${new Date(f.filled_at).toLocaleTimeString()}</td>
            <td class="py-2">${f.normalized_symbol}</td>
            <td class="py-2">${f.quantity}</td>
            <td class="py-2">${f.price.toFixed(2)}</td>
        </tr>
    `).join('');
}

function renderPnL(pnl) {
    if (!pnl) return;
    const total = pnl.total_pnl;
    pnlSummaryEl.textContent = `PnL: ${total.toFixed(2)}`;
    pnlSummaryEl.className = `text-sm font-medium ${total >= 0 ? 'pnl-positive' : 'pnl-negative'}`;
}

// Actions
function selectSymbol(symbol, broker) {
    document.getElementById('order-symbol').value = symbol;
    document.getElementById('order-broker').value = broker;
}

async function removeFromWatchlist(normalizedSymbol) {
    await API.delete(`/watchlist/${normalizedSymbol}`);
    await loadWatchlist();
}

async function cancelOrder(id) {
    await API.post(`/paper/orders/${id}/cancel`);
    await loadData();
}

document.getElementById('add-watchlist-btn').onclick = async () => {
    const symbol = document.getElementById('symbol-input').value;
    if (symbol) {
        await API.post(`/watchlist/?symbol_code=${symbol}`);
        document.getElementById('symbol-input').value = '';
        await loadWatchlist();
    }
};

document.getElementById('order-form').onsubmit = async (e) => {
    e.preventDefault();
    const data = {
        broker: document.getElementById('order-broker').value,
        symbol_code: document.getElementById('order-symbol').value,
        action: document.getElementById('order-action').value,
        quantity: parseInt(document.getElementById('order-qty').value),
        order_type: document.getElementById('order-type').value,
        price: parseFloat(document.getElementById('order-price').value || 0)
    };
    await API.post('/paper/orders', data);
    await loadData();
};

document.getElementById('cancel-all-btn').onclick = async () => {
    await API.post('/paper/orders/cancel-all');
    await loadData();
};

document.getElementById('logout-btn').onclick = () => {
    localStorage.removeItem('token');
    window.location.href = '/login.html';
};

// Tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.onclick = () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active', 'border-blue-500'));
        btn.classList.add('active', 'border-blue-500');
        
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
        document.getElementById(`${btn.dataset.tab}-tab`).classList.remove('hidden');
    };
});

init();
