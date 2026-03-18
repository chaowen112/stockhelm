const API = {
    token: localStorage.getItem('token'),

    async fetch(url, options = {}) {
        if (!this.token) {
            window.location.href = '/login.html';
            return;
        }

        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };

        const response = await fetch(url, options);
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login.html';
            return;
        }
        return response;
    },

    async get(url) {
        const response = await this.fetch(url);
        return response ? response.json() : null;
    },

    async post(url, data) {
        const response = await this.fetch(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response ? response.json() : null;
    },

    async delete(url) {
        const response = await this.fetch(url, {
            method: 'DELETE'
        });
        return response ? response.json() : null;
    }
};
