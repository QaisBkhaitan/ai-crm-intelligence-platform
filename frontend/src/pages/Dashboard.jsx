import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [signalAnalytics, setSignalAnalytics] = useState(null);
  const [actions, setActions] = useState([]);
  const [actionSummary, setActionSummary] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboardData = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const [overviewRes, signalAnalyticsRes, actionsRes, actionSummaryRes] =
        await Promise.all([
          api.get("/dashboard/overview"),
          api.get("/social-listener/analytics"),
          api.get("/actions"),
          api.get("/actions/summary"),
        ]);

      setOverview(overviewRes.data);
      setSignalAnalytics(signalAnalyticsRes.data);
      setActions(actionsRes.data || []);
      setActionSummary(actionSummaryRes.data || null);
    } catch (error) {
      console.error("Error loading dashboard data:", error);
      setOverview(null);
      setSignalAnalytics(null);
      setActions([]);
      setActionSummary(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const completeAction = async (actionId) => {
    try {
      await api.put(`/actions/${actionId}/complete`);
      await loadDashboardData(true);
    } catch (error) {
      console.error("Error completing action:", error);
    }
  };

  const cancelAction = async (actionId) => {
    try {
      await api.put(`/actions/${actionId}/cancel`);
      await loadDashboardData(true);
    } catch (error) {
      console.error("Error cancelling action:", error);
    }
  };

  const formatCurrency = (value) => `$${Number(value || 0).toLocaleString()}`;

  const formatDate = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString();
  };

  const metrics = overview?.metrics || {
    total_customers: 0,
    total_orders: 0,
    total_sales: 0,
  };

  const signalSummary = signalAnalytics?.summary || {
    total_signals: 0,
    high_risk_signals: 0,
    medium_risk_signals: 0,
    low_risk_signals: 0,
    complaints: 0,
    inquiries: 0,
    praise: 0,
    other: 0,
    matched_signals: 0,
    unmatched_signals: 0,
    actions_from_signals: 0,
    pending_signal_actions: 0,
    high_priority_signal_actions: 0,
    conversion_rate: 0,
    match_rate: 0,
  };

  const pendingActions = useMemo(() => {
    return actions.filter((action) => action.status === "pending");
  }, [actions]);

  const urgentActions = useMemo(() => {
    return pendingActions
      .filter((action) => action.priority === "high")
      .slice(0, 5);
  }, [pendingActions]);

  const signalActions = useMemo(() => {
    return pendingActions
      .filter((action) => action.signal_id)
      .slice(0, 5);
  }, [pendingActions]);

  const latestSignals = signalAnalytics?.latest_signals || [];
  const topRiskSignals = signalAnalytics?.top_risk_signals || [];
  const bySource = signalAnalytics?.by_source || [];
  const byIntent = signalAnalytics?.by_intent || [];
  const byRisk = signalAnalytics?.by_risk || [];

  const topRisk = topRiskSignals[0] || null;
  const topPendingAction = urgentActions[0] || signalActions[0] || pendingActions[0] || null;

  const executiveNarrative =
    signalSummary.total_signals > 0
      ? `Your CRM has processed ${signalSummary.total_signals} customer signals. ${signalSummary.high_risk_signals} are high-risk, ${signalSummary.complaints} are complaints, and ${signalSummary.inquiries} are sales inquiries. ${signalSummary.actions_from_signals} actions were created from customer signals with a ${signalSummary.conversion_rate}% signal-to-action conversion rate.`
      : "No customer signals have been processed yet. Import customer signals to activate the AI decision pipeline.";

  const getRiskBadgeClass = (risk) => {
    if (risk === "high") return "badge badge-red";
    if (risk === "medium") return "badge badge-yellow";
    return "badge badge-green";
  };

  const getIntentBadgeClass = (intent) => {
    if (intent === "complaint") return "badge badge-red";
    if (intent === "inquiry") return "badge badge-blue";
    if (intent === "praise") return "badge badge-green";
    return "badge badge-purple";
  };

  const getPriorityBadgeClass = (priority) => {
    if (priority === "high") return "badge badge-red";
    if (priority === "medium") return "badge badge-yellow";
    return "badge badge-blue";
  };

  const getStatusBadgeClass = (status) => {
    if (status === "completed") return "badge badge-green";
    if (status === "cancelled") return "badge badge-red";
    return "badge badge-yellow";
  };

  const getTypeBadgeClass = (type) => {
    if (type === "retention") return "badge badge-red";
    if (type === "upsell") return "badge badge-green";
    if (type === "follow_up") return "badge badge-blue";
    return "badge badge-purple";
  };

  const formatActionType = (type) => {
    const labels = {
      follow_up: "Follow Up",
      retention: "Retention",
      upsell: "Upsell",
      review: "Review",
      data_cleanup: "Data Cleanup",
    };

    return labels[type] || type;
  };

  const getSourceLabel = (source) => {
    const labels = {
      facebook: "Facebook",
      instagram: "Instagram",
      website: "Website",
      website_form: "Website Form",
      support_ticket: "Support Ticket",
      email: "Email",
      api_webhook: "API Webhook",
      manual_import: "Manual Import",
    };

    return labels[source] || source || "Unknown";
  };

  const renderDistribution = (items, labelKey, valueFormatter) => {
    if (!items || items.length === 0) {
      return <div className="empty-state">No data available.</div>;
    }

    const maxValue = Math.max(...items.map((item) => item.count || 0), 1);

    return (
      <div className="list">
        {items.map((item) => {
          const label = item[labelKey] || "unknown";
          const width = `${Math.max(8, ((item.count || 0) / maxValue) * 100)}%`;

          return (
            <div key={label} className="summary-box">
              <div className="results-bar">
                <p className="summary-text">
                  <strong>{valueFormatter ? valueFormatter(label) : label}</strong>
                </p>
                <span className="badge badge-blue">{item.count}</span>
              </div>

              <div
                style={{
                  marginTop: 10,
                  width: "100%",
                  height: 10,
                  background: "#e2e8f0",
                  borderRadius: 999,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width,
                    height: "100%",
                    background: "#2563eb",
                    borderRadius: 999,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return <div className="loading-state">Loading AI command center...</div>;
  }

  if (!overview || !signalAnalytics) {
    return (
      <div className="error-state">
        Failed to load dashboard data. Make sure the backend is running and the
        signal analytics endpoint is available.
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <p className="page-eyebrow">AI Command Center</p>
          <h1 className="page-title">Customer Signal Intelligence</h1>
          <p className="page-subtitle">
            Monitor customer signals, AI classification, risk patterns, and the
            execution queue that converts customer interactions into business
            actions.
          </p>
        </div>

        <div className="hero-actions">
          <button
            className="btn btn-primary"
            onClick={() => loadDashboardData(true)}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh Command Center"}
          </button>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Executive Narrative</p>
            <h2 className="section-title">Today’s Signal Intelligence Summary</h2>
          </div>
        </div>

        <div className="summary-box">
          <p className="summary-text">{executiveNarrative}</p>

          <div className="btn-row" style={{ marginTop: 14 }}>
            <span className="badge badge-red">
              {signalSummary.high_risk_signals} High Risk
            </span>
            <span className="badge badge-blue">
              {signalSummary.inquiries} Inquiries
            </span>
            <span className="badge badge-yellow">
              {signalSummary.unmatched_signals} Unmatched
            </span>
            <span className="badge badge-green">
              {signalSummary.conversion_rate}% Converted
            </span>
          </div>
        </div>
      </section>

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Customer Signals</p>
          <p className="metric-value">{signalSummary.total_signals}</p>
          <p className="metric-meta">External interactions processed by AI</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">High Risk Signals</p>
          <p className="metric-value">{signalSummary.high_risk_signals}</p>
          <p className="metric-meta">Signals that may need urgent action</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Signal Actions</p>
          <p className="metric-value">{signalSummary.actions_from_signals}</p>
          <p className="metric-meta">Business actions created from signals</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Pending Actions</p>
          <p className="metric-value">
            {actionSummary?.pending_count || pendingActions.length}
          </p>
          <p className="metric-meta">Execution queue items waiting</p>
        </div>
      </section>

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Customers</p>
          <p className="metric-value">{metrics.total_customers}</p>
          <p className="metric-meta">CRM records available for linking</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Orders</p>
          <p className="metric-value">{metrics.total_orders}</p>
          <p className="metric-meta">Revenue events imported</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Sales</p>
          <p className="metric-value">{formatCurrency(metrics.total_sales)}</p>
          <p className="metric-meta">Tracked order value</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Match Rate</p>
          <p className="metric-value">{signalSummary.match_rate}%</p>
          <p className="metric-meta">Signals linked to CRM customers</p>
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Risk Radar</p>
              <h2 className="section-title">Top High-Risk Signals</h2>
              <p className="section-description">
                Recent complaints or urgent customer messages that should be
                reviewed first.
              </p>
            </div>
          </div>

          {topRiskSignals.length === 0 ? (
            <div className="empty-state">No high-risk signals detected.</div>
          ) : (
            <div className="list">
              {topRiskSignals.map((signal) => (
                <div key={signal.id} className="list-row-compact">
                  <div className="btn-row" style={{ marginBottom: 10 }}>
                    <span className="badge badge-blue">
                      {getSourceLabel(signal.source)}
                    </span>
                    <span className={getIntentBadgeClass(signal.intent)}>
                      {signal.intent}
                    </span>
                    <span className={getRiskBadgeClass(signal.risk_level)}>
                      {signal.risk_level} risk
                    </span>
                  </div>

                  <p className="list-title">
                    {signal.author_name || "Unknown Contact"}
                  </p>
                  <p className="list-description">{signal.content}</p>
                  <p className="list-meta" style={{ marginTop: 8 }}>
                    Customer:{" "}
                    {signal.customer_id ? `#${signal.customer_id}` : "Unmatched"} ·{" "}
                    {formatDate(signal.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Execution Focus</p>
              <h2 className="section-title">Priority AI Actions</h2>
              <p className="section-description">
                Pending actions generated from customer signals and business
                intelligence.
              </p>
            </div>
          </div>

          {signalActions.length === 0 && urgentActions.length === 0 ? (
            <div className="empty-state">No pending AI signal actions.</div>
          ) : (
            <div className="list">
              {(signalActions.length > 0 ? signalActions : urgentActions).map(
                (action) => (
                  <div key={action.id} className="list-row-compact">
                    <div className="btn-row" style={{ marginBottom: 10 }}>
                      <span className={getTypeBadgeClass(action.action_type)}>
                        {formatActionType(action.action_type)}
                      </span>
                      <span className={getPriorityBadgeClass(action.priority)}>
                        {action.priority}
                      </span>
                      <span className={getStatusBadgeClass(action.status)}>
                        {action.status}
                      </span>
                    </div>

                    <p className="list-title">{action.title}</p>

                    {action.reason && (
                      <p className="list-description">
                        <strong>Reason:</strong> {action.reason}
                      </p>
                    )}

                    {action.suggested_reply && (
                      <p className="list-description" style={{ marginTop: 8 }}>
                        <strong>Suggested Reply:</strong>{" "}
                        {action.suggested_reply}
                      </p>
                    )}

                    <p className="list-meta" style={{ marginTop: 8 }}>
                      Signal: {action.signal_id ? `#${action.signal_id}` : "No signal"} ·
                      Customer:{" "}
                      {action.customer_id ? `#${action.customer_id}` : "Unmatched"}
                    </p>

                    <div className="btn-row" style={{ marginTop: 12 }}>
                      <button
                        className="btn btn-primary"
                        onClick={() => completeAction(action.id)}
                      >
                        Complete
                      </button>

                      <button
                        className="btn btn-danger"
                        onClick={() => cancelAction(action.id)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      </section>

      <section className="grid-3">
        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Source Mix</p>
              <h2 className="section-title">Signals by Source</h2>
            </div>
          </div>

          {renderDistribution(bySource, "source", getSourceLabel)}
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Customer Intent</p>
              <h2 className="section-title">Signals by Intent</h2>
            </div>
          </div>

          {renderDistribution(byIntent, "intent")}
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Risk Levels</p>
              <h2 className="section-title">Signals by Risk</h2>
            </div>
          </div>

          {renderDistribution(byRisk, "risk_level")}
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Signal Feed</p>
              <h2 className="section-title">Latest Customer Signals</h2>
              <p className="section-description">
                Most recent customer interactions received from external sources.
              </p>
            </div>
          </div>

          {latestSignals.length === 0 ? (
            <div className="empty-state">No recent signals available.</div>
          ) : (
            <div className="list">
              {latestSignals.map((signal) => (
                <div key={signal.id} className="list-row-compact">
                  <div className="btn-row" style={{ marginBottom: 10 }}>
                    <span className="badge badge-blue">
                      {getSourceLabel(signal.source)}
                    </span>
                    <span className={getIntentBadgeClass(signal.intent)}>
                      {signal.intent}
                    </span>
                    <span className={getRiskBadgeClass(signal.risk_level)}>
                      {signal.risk_level}
                    </span>
                  </div>

                  <p className="list-title">
                    {signal.author_name || "Unknown Contact"}
                  </p>

                  <p className="list-description">{signal.content}</p>

                  <p className="list-meta" style={{ marginTop: 8 }}>
                    {signal.customer_id ? `Customer #${signal.customer_id}` : "Unmatched"} ·{" "}
                    {formatDate(signal.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Pipeline Health</p>
              <h2 className="section-title">AI Signal Pipeline</h2>
              <p className="section-description">
                A quick view of how external signals are converted into CRM
                execution.
              </p>
            </div>
          </div>

          <div className="kv-list">
            <div className="kv-row">
              <span className="kv-key">Total Signals</span>
              <span className="kv-value">{signalSummary.total_signals}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Matched Signals</span>
              <span className="kv-value">{signalSummary.matched_signals}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Unmatched Signals</span>
              <span className="kv-value">{signalSummary.unmatched_signals}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Actions from Signals</span>
              <span className="kv-value">{signalSummary.actions_from_signals}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Pending Signal Actions</span>
              <span className="kv-value">
                {signalSummary.pending_signal_actions}
              </span>
            </div>

            <div className="kv-row">
              <span className="kv-key">High Priority Signal Actions</span>
              <span className="kv-value">
                {signalSummary.high_priority_signal_actions}
              </span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Signal Match Rate</span>
              <span className="kv-value">{signalSummary.match_rate}%</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Signal-to-Action Conversion</span>
              <span className="kv-value">
                {signalSummary.conversion_rate}%
              </span>
            </div>
          </div>

          {topPendingAction && (
            <div className="summary-box" style={{ marginTop: 18 }}>
              <p className="summary-text">
                <strong>Recommended Focus:</strong> {topPendingAction.title}
              </p>
              {topPendingAction.reason && (
                <p className="summary-note">{topPendingAction.reason}</p>
              )}
            </div>
          )}

          {topRisk && (
            <div className="summary-box" style={{ marginTop: 14 }}>
              <p className="summary-text">
                <strong>Top Risk Signal:</strong>{" "}
                {topRisk.author_name || "Unknown Contact"}
              </p>
              <p className="summary-note">{topRisk.content}</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;