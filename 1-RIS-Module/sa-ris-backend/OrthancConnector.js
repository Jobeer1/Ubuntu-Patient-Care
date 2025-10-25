const axios = require('axios');

class OrthancConnector {
  constructor(opts = {}) {
    this.url = opts.url || 'http://localhost:8042';
    this.username = opts.username || null;
    this.password = opts.password || null;
    this.axios = axios.create({
      baseURL: this.url,
      timeout: opts.timeout || 15000,
      auth: this.username ? { username: this.username, password: this.password } : undefined
    });
  }

  async ping() {
    try {
      const res = await this.axios.get('/tools/version');
      return res.data;
    } catch (err) {
      return null;
    }
  }

  async getStudies() {
    try {
      // Try to call Orthanc search API; fall back to empty array on error
      const res = await this.axios.get('/tools/find', { params: { Level: 'Study' } });
      return res.data || [];
    } catch (err) {
      return [];
    }
  }

  async getStudy(studyId) {
    try {
      const res = await this.axios.get(`/studies/${encodeURIComponent(studyId)}`);
      return res.data;
    } catch (err) {
      return null;
    }
  }
}

module.exports = OrthancConnector;
