class RISWorkflowEngine {
  constructor(options = null, settings = {}) {
    this.options = options || {};
    this.settings = settings || {};
  }

  async getDashboardData() {
    return { queues: [], stats: {} };
  }

  async createReport(studyId, reportData) {
    return { studyId, reportId: `r-${Date.now()}`, status: 'created', reportData };
  }
}

module.exports = RISWorkflowEngine;
