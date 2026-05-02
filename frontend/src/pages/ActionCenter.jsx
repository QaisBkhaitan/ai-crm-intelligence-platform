import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

function ActionCenter() {
  const [actions, setActions] = useState([]);
  const [summary, setSummary] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [error, setError] = useState("");

  const [activeTab, setActiveTab] = useState("pending");

  const [filters, setFilters] = useState({
    status: "",
    priority: "",
    action_type: "",
    source: "",
    only_signal_actions: false,
    search: "",
  });

  const fetchActions = async (isRefresh = false) => {
    try {
      setError("");

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const [actionsRes, summaryRes] = await Promise.all([
        api.get("/actions"),
        api.get("/actions/summary"),
      ]);

      setActions(actionsRes.data || []);
      setSummary(summaryRes.data || null);
    } catch (error) {
      console.error("Error fetching actions:", error);
      setActions([]);
      setSummary(null);
      setError("Could not load action queue. Make sure the backend is running.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchActions();
  }, []);

  const completeAction = async (id) => {
    try {
      setUpdatingId(id);
      setError("");

      await api.put(`/actions/${id}/complete`);
      await fetchActions(true);
    } catch (error) {
      console.error("Error completing action:", error);
      setError("Could not complete this action.");
    } finally {
      setUpdatingId(null);
    }
  };

  const cancelAction = async (id) => {
    try {
      setUpdatingId(id);
      setError("");

      await api.put(`/actions/${id}/cancel`);
      await fetchActions(true);
    } catch (error) {
      console.error("Error cancelling action:", error);
      setError("Could not cancel this action.");
    } finally {
      setUpdatingId(null);
    }
  };

  const generateAIActions = async () => {
    try {
      setRefreshing(true);
      setError("");

      const response = await api.post("/ai/generate-actions");
      await fetchActions(true);

      if (response.data?.created_count === 0) {
        setError(
          "AI action generation finished, but no new actions were created. Existing pending actions may already cover the current priorities."
        );
      }
    } catch (error) {
      console.error("Error generating AI actions:", error);
      setError("Could not generate AI actions.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value, type, checked } = e.target;

    setFilters((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const clearFilters = () => {
    setFilters({
      status: "",
      priority: "",
      action_type: "",
      source: "",
      only_signal_actions: false,
      search: "",
    });
    setActiveTab("pending");
  };

  const baseTabActions = useMemo(() => {
    if (activeTab === "all") return actions;

    return actions.filter((action) => action.status === activeTab);
  }, [actions, activeTab]);

  const filteredActions = useMemo(() => {
    const searchValue = filters.search.trim().toLowerCase();

    return baseTabActions.filter((action) => {
      if (filters.status && action.status !== filters.status) return false;
      if (filters.priority && action.priority !== filters.priority) return false;
      if (filters.action_type && action.action_type !== filters.action_type) return false;
      if (filters.source && action.source !== filters.source) return false;
      if (filters.only_signal_actions && !action.signal_id) return false;

      if (searchValue) {
        const searchableText = [
          action.title,
          action.description,
          action.reason,
          action.suggested_reply,
          action.action_type,
          action.priority,
          action.status,
          action.source,
          action.customer_id ? `customer ${action.customer_id}` : "",
          action.signal_id ? `signal ${action.signal_id}` : "",
        ]
          .join(" ")
          .toLowerCase();

        if (!searchableText.includes(searchValue)) return false;
      }

      return true;
    });
  }, [baseTabActions, filters]);

  const computedStats = useMemo(() => {
    const total = actions.length;
    const pending = actions.filter((action) => action.status === "pending").length;
    const completed = actions.filter((action) => action.status === "completed").length;
    const cancelled = actions.filter((action) => action.status === "cancelled").length;

    const highPriority = actions.filter(
      (action) => action.priority === "high" && action.status === "pending"
    ).length;

    const signalActions = actions.filter((action) => action.signal_id).length;

    const aiActions = actions.filter((action) => action.source === "ai").length;

    const retentionActions = actions.filter(
      (action) => action.action_type === "retention" && action.status === "pending"
    ).length;

    const upsellActions = actions.filter(
      (action) => action.action_type === "upsell" && action.status === "pending"
    ).length;

    const completionRate =
      total > 0 ? Math.round((completed / total) * 100) : 0;

    return {
      total,
      pending,
      completed,
      cancelled,
      highPriority,
      signalActions,
      aiActions,
      retentionActions,
      upsellActions,
      completionRate,
    };
  }, [actions]);

  const priorityBuckets = useMemo(() => {
    const pending = actions.filter((action) => action.status === "pending");

    return {
      high: pending.filter((action) => action.priority === "high").length,
      medium: pending.filter((action) => action.priority === "medium").length,
      low: pending.filter((action) => action.priority === "low").length,
    };
  }, [actions]);

  const recommendedFocus = useMemo(() => {
    const pending = actions.filter((action) => action.status === "pending");

    const highRetention = pending.find(
      (action) =>
        action.priority === "high" && action.action_type === "retention"
    );

    if (highRetention) {
      return {
        title: highRetention.title,
        message:
          highRetention.reason ||
          "Start with this high-priority retention action before growth work.",
        badge: "Retention Risk",
      };
    }

    const highPriority = pending.find((action) => action.priority === "high");

    if (highPriority) {
      return {
        title: highPriority.title,
        message:
          highPriority.reason ||
          "This is currently the highest priority pending action.",
        badge: "High Priority",
      };
    }

    const upsell = pending.find((action) => action.action_type === "upsell");

    if (upsell) {
      return {
        title: upsell.title,
        message:
          upsell.reason ||
          "This action may help turn account activity into revenue.",
        badge: "Growth",
      };
    }

    if (pending.length > 0) {
      return {
        title: pending[0].title,
        message:
          pending[0].reason ||
          "This is the next pending execution item in the queue.",
        badge: "Next Action",
      };
    }

    return {
      title: "No pending actions",
      message:
        "The execution queue is clear. Generate AI actions or wait for new signals and business activity.",
      badge: "Clear",
    };
  }, [actions]);

  const formatDate = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString();
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
    if (type === "review") return "badge badge-purple";
    return "badge badge-purple";
  };

  const getSourceBadgeClass = (source) => {
    if (source === "ai") return "badge badge-purple";
    if (source === "manual") return "badge badge-blue";
    return "badge badge-yellow";
  };

  const formatActionType = (type) => {
    const labels = {
      follow_up: "Follow Up",
      upsell: "Upsell",
      retention: "Retention",
      data_cleanup: "Data Cleanup",
      review: "Review",
    };

    return labels[type] || type || "Action";
  };

  const getActionSourceLabel = (source) => {
    if (source === "ai") return "AI Generated";
    if (source === "manual") return "Manual";
    return source || "Unknown";
  };

  const getTabCount = (tab) => {
    if (tab === "all") return actions.length;
    return actions.filter((action) => action.status === tab).length;
  };

  const renderActionCard = (action) => {
    const aiConfidence =
      action.ai_confidence !== null && action.ai_confidence !== undefined
        ? Math.round(Number(action.ai_confidence) * 100)
        : null;

    return (
      <div key={action.id} className="list-row">
        <div>
          <div className="btn-row" style={{ marginBottom: 12 }}>
            <span className={getTypeBadgeClass(action.action_type)}>
              {formatActionType(action.action_type)}
            </span>

            <span className={getPriorityBadgeClass(action.priority)}>
              {String(action.priority || "medium").toUpperCase()} Priority
            </span>

            <span className={getStatusBadgeClass(action.status)}>
              {String(action.status || "pending").toUpperCase()}
            </span>

            <span className={getSourceBadgeClass(action.source)}>
              {getActionSourceLabel(action.source)}
            </span>

            {action.signal_id && (
              <span className="badge badge-blue">Signal Driven</span>
            )}
          </div>

          <p className="list-title">{action.title}</p>

          <p className="list-description" style={{ whiteSpace: "pre-line" }}>
            {action.description}
          </p>

          {action.reason && (
            <div className="summary-box" style={{ marginTop: 12 }}>
              <p className="section-eyebrow">AI Reason</p>
              <p className="summary-text">{action.reason}</p>
            </div>
          )}

          {action.suggested_reply && (
            <div className="summary-box" style={{ marginTop: 12 }}>
              <p className="section-eyebrow">Suggested Reply</p>
              <p className="summary-text">{action.suggested_reply}</p>
            </div>
          )}

          <div className="btn-row" style={{ marginTop: 12 }}>
            {aiConfidence !== null && (
              <span className="badge badge-purple">
                AI Confidence {aiConfidence}%
              </span>
            )}

            <span className="badge badge-blue">
              Created {formatDate(action.created_at)}
            </span>

            {action.completed_at && (
              <span className="badge badge-green">
                Completed {formatDate(action.completed_at)}
              </span>
            )}
          </div>
        </div>

        <div className="right-meta">
          <div className="kv-list">
            <div className="kv-row">
              <span className="kv-key">Action ID</span>
              <span className="kv-value">#{action.id}</span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Customer</span>
              <span className="kv-value">
                {action.customer_id ? `#${action.customer_id}` : "Unmatched"}
              </span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Signal</span>
              <span className="kv-value">
                {action.signal_id ? `#${action.signal_id}` : "None"}
              </span>
            </div>

            <div className="kv-row">
              <span className="kv-key">Type</span>
              <span className="kv-value">
                {formatActionType(action.action_type)}
              </span>
            </div>
          </div>

          {action.status === "pending" && (
            <div className="btn-row" style={{ marginTop: 16 }}>
              <button
                className="btn btn-primary"
                onClick={() => completeAction(action.id)}
                disabled={updatingId === action.id}
              >
                {updatingId === action.id ? "Updating..." : "Complete"}
              </button>

              <button
                className="btn btn-danger"
                onClick={() => cancelAction(action.id)}
                disabled={updatingId === action.id}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <p className="page-eyebrow">Execution Layer</p>
          <h1 className="page-title">Action Center</h1>
          <p className="page-subtitle">
            Review, prioritize, complete, or cancel business actions generated
            from customer intelligence, CRM analysis, and incoming customer
            signals.
          </p>
        </div>

        <div className="hero-actions">
          <button
            className="btn btn-secondary"
            onClick={() => fetchActions(true)}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh Queue"}
          </button>

          <button
            className="btn btn-primary"
            onClick={generateAIActions}
            disabled={refreshing}
          >
            {refreshing ? "Generating..." : "Generate AI Actions"}
          </button>
        </div>
      </section>

      {error && <div className="error-state">{error}</div>}

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Total Actions</p>
          <p className="metric-value">
            {summary?.total_actions ?? computedStats.total}
          </p>
          <p className="metric-meta">All execution items</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Pending</p>
          <p className="metric-value">
            {summary?.pending_count ?? computedStats.pending}
          </p>
          <p className="metric-meta">Actions waiting for follow-up</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">High Priority</p>
          <p className="metric-value">{computedStats.highPriority}</p>
          <p className="metric-meta">Urgent pending actions</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Completion Rate</p>
          <p className="metric-value">{computedStats.completionRate}%</p>
          <p className="metric-meta">
            {computedStats.completed} completed · {computedStats.cancelled} cancelled
          </p>
        </div>
      </section>

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Signal Actions</p>
          <p className="metric-value">{computedStats.signalActions}</p>
          <p className="metric-meta">Actions created from customer signals</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">AI Generated</p>
          <p className="metric-value">{computedStats.aiActions}</p>
          <p className="metric-meta">Actions created by intelligence logic</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Retention</p>
          <p className="metric-value">{computedStats.retentionActions}</p>
          <p className="metric-meta">Open customer risk actions</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Upsell</p>
          <p className="metric-value">{computedStats.upsellActions}</p>
          <p className="metric-meta">Open growth actions</p>
        </div>
      </section>

      <section className="grid-2">
        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Recommended Focus</p>
              <h2 className="section-title">{recommendedFocus.title}</h2>
              <p className="section-description">{recommendedFocus.message}</p>
            </div>

            <span
              className={
                recommendedFocus.badge === "Retention Risk"
                  ? "badge badge-red"
                  : recommendedFocus.badge === "Growth"
                  ? "badge badge-green"
                  : "badge badge-blue"
              }
            >
              {recommendedFocus.badge}
            </span>
          </div>
        </div>

        <div className="card">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Pending Priority Mix</p>
              <h2 className="section-title">Queue Pressure</h2>
              <p className="section-description">
                High priority should be cleared before medium and low priority
                actions.
              </p>
            </div>
          </div>

          <div className="btn-row">
            <span className="badge badge-red">High {priorityBuckets.high}</span>
            <span className="badge badge-yellow">
              Medium {priorityBuckets.medium}
            </span>
            <span className="badge badge-blue">Low {priorityBuckets.low}</span>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Queue Tabs</p>
            <h2 className="section-title">Execution Status</h2>
          </div>
        </div>

        <div className="btn-row">
          {["pending", "completed", "cancelled", "all"].map((tab) => (
            <button
              key={tab}
              className={activeTab === tab ? "btn btn-primary" : "btn btn-secondary"}
              onClick={() => setActiveTab(tab)}
            >
              {tab === "all"
                ? `All (${getTabCount(tab)})`
                : `${tab.charAt(0).toUpperCase() + tab.slice(1)} (${getTabCount(tab)})`}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Filters</p>
            <h2 className="section-title">Filter Execution Queue</h2>
            <p className="section-description">
              Narrow down actions by priority, type, source, signal linkage, or
              keywords.
            </p>
          </div>

          <button className="btn btn-secondary" onClick={clearFilters}>
            Clear Filters
          </button>
        </div>

        <div className="filters-grid">
          <div className="search-row">
            <input
              className="input"
              type="text"
              name="search"
              placeholder="Search title, reason, description, suggested reply, customer ID, or signal ID..."
              value={filters.search}
              onChange={handleFilterChange}
            />

            <button className="btn btn-primary" onClick={() => fetchActions(true)}>
              Refresh
            </button>
          </div>

          <div className="filter-row">
            <select
              className="select"
              name="priority"
              value={filters.priority}
              onChange={handleFilterChange}
            >
              <option value="">All Priorities</option>
              <option value="high">High Priority</option>
              <option value="medium">Medium Priority</option>
              <option value="low">Low Priority</option>
            </select>

            <select
              className="select"
              name="action_type"
              value={filters.action_type}
              onChange={handleFilterChange}
            >
              <option value="">All Action Types</option>
              <option value="follow_up">Follow Up</option>
              <option value="retention">Retention</option>
              <option value="upsell">Upsell</option>
              <option value="review">Review</option>
              <option value="data_cleanup">Data Cleanup</option>
            </select>

            <select
              className="select"
              name="source"
              value={filters.source}
              onChange={handleFilterChange}
            >
              <option value="">All Sources</option>
              <option value="ai">AI Generated</option>
              <option value="manual">Manual</option>
            </select>
          </div>

          <label className="summary-box" style={{ display: "block" }}>
            <input
              type="checkbox"
              name="only_signal_actions"
              checked={filters.only_signal_actions}
              onChange={handleFilterChange}
              style={{ marginRight: 8 }}
            />
            Show only actions linked to customer signals
          </label>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="section-eyebrow">Action Queue</p>
            <h2 className="section-title">Business Actions</h2>
            <p className="section-description">
              These actions represent AI-generated business decisions, customer
              follow-ups, retention risks, and growth opportunities.
            </p>
          </div>

          <p className="results-text">
            Showing {filteredActions.length} of {actions.length} actions
          </p>
        </div>

        {loading ? (
          <div className="loading-state">Loading action queue...</div>
        ) : filteredActions.length === 0 ? (
          <div className="empty-state">
            No actions match the current view. Generate AI actions, switch tabs,
            or clear filters.
          </div>
        ) : (
          <div className="list">
            {filteredActions.map((action) => renderActionCard(action))}
          </div>
        )}
      </section>
    </div>
  );
}

export default ActionCenter;